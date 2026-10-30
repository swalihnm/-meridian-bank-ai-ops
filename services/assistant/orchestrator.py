"""Assistant orchestrator: guard, route, act, respond, with a checkpoint after every step.

Each customer message is one run, identified by a run_id (use a new id per turn). Within a turn,
a checkpoint is written after every step. If a step raises, the last checkpoint stays on disk, and
calling `handle` again with the same run_id resumes at the next step without repeating completed
steps (so a write is never proposed twice).

The pending confirmation token lives on the Session, not in the run state, because the customer's
"yes" arrives in a later turn.

Routing is keyword-based for now. It stands in for a trained router; wiring the Week 3 intent model
in is a later task.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from opentelemetry import trace

from services.assistant.checkpoint import CheckpointStore
from services.assistant.guardrails import DailyBudget, KillSwitch, detect_injection, redact_pii
from services.assistant.rag.answer import Answer, compose_answer
from services.assistant.rag.lexical import Hit
from services.mcp_bank.server import BankToolServer, ToolError

_TRACER = trace.get_tracer("meridian.assistant")

STEPS = ("guard", "route", "act", "respond")
COST_PER_TURN_CENTS = 1  # placeholder until a hosted model is wired in

FREEZE = re.compile(r"\b(freeze|block|lock|stolen|lost)\b", re.IGNORECASE)
DISPUTE = re.compile(r"\b(dispute|chargeback|did not make|didn't make)\b", re.IGNORECASE)
HUMAN = re.compile(r"\b(human|agent|person|complaint|complain|manager)\b", re.IGNORECASE)
CONFIRM = re.compile(r"^\s*(yes|confirm|ok|okay|proceed)\b", re.IGNORECASE)


@dataclass
class Session:
    actor: str
    customer_id: str
    card_id: str | None = None
    txn_id: str | None = None
    pending_token: str | None = None
    pending_label: str | None = None


@dataclass
class Assistant:
    tools: BankToolServer
    retrieve: Callable[[str], list[Hit]]
    checkpoints: CheckpointStore
    kill_switch: KillSwitch = field(default_factory=KillSwitch)
    budget: DailyBudget = field(default_factory=lambda: DailyBudget(limit_cents=10_000))
    fail_after: str | None = None  # test hook: simulate a crash after this step

    def handle(self, run_id: str, session: Session, message: str) -> dict[str, Any]:
        # Tracing records the route and counts only. Message text never goes into a span.
        with _TRACER.start_as_current_span("assistant.turn") as span:
            out = self._handle(run_id, session, message)
            span.set_attribute("meridian.run_id", run_id)
            span.set_attribute("meridian.route", str(out.get("route")))
            span.set_attribute("meridian.citations", len(out.get("citations", [])))
            return out

    def _handle(self, run_id: str, session: Session, message: str) -> dict[str, Any]:
        state = self._resume_or_start(run_id, message)
        start = 0 if state.get("done_through") is None else STEPS.index(state["done_through"]) + 1
        for index in range(start, len(STEPS)):
            name = STEPS[index]
            state = _STEP_FUNCTIONS[name](self, state, session)
            state["done_through"] = name
            self.checkpoints.save(run_id, index, name, state)
            if self.fail_after == name:
                raise RuntimeError(f"simulated crash after {name}")
        return {
            "reply": state["reply"],
            "route": state.get("route"),
            "citations": state.get("citations", []),
        }

    def _resume_or_start(self, run_id: str, message: str) -> dict[str, Any]:
        latest = self.checkpoints.latest(run_id)
        if latest is not None:
            return latest[2]
        return {"message": message, "done_through": None, "route": None, "reply": None}

    # ---- steps --------------------------------------------------------------------

    def _guard(self, state: dict[str, Any], session: Session) -> dict[str, Any]:
        if self.kill_switch.enabled:
            state.update(
                route="blocked",
                reply=(
                    f"The assistant is paused ({self.kill_switch.reason}). "
                    "A human agent will help you."
                ),
            )
            return state
        if not self.budget.can_spend(COST_PER_TURN_CENTS):
            state.update(
                route="blocked",
                reply="The assistant is unavailable right now. A human agent will help you.",
            )
            return state
        redaction = redact_pii(str(state["message"]))
        state["redacted"] = redaction.text
        state["pii_kinds"] = list(redaction.kinds)
        if detect_injection(str(state["message"])) is not None:
            self.tools.audit.append(
                session.actor, "input_guard", {"kinds": ["injection"]}, "blocked"
            )
            state.update(
                route="blocked",
                reply=(
                    "I can't do that. I can help with questions about your account "
                    "or connect you to an agent."
                ),
            )
        return state

    def _route(self, state: dict[str, Any], session: Session) -> dict[str, Any]:
        if state["route"] == "blocked":
            return state
        text = str(state["redacted"])
        if session.pending_token and CONFIRM.search(text):
            state["route"] = "confirm"
        elif FREEZE.search(text):
            state["route"] = "freeze"
        elif DISPUTE.search(text):
            state["route"] = "dispute"
        elif HUMAN.search(text):
            state["route"] = "escalate"
        else:
            state["route"] = "policy"
        return state

    def _act(self, state: dict[str, Any], session: Session) -> dict[str, Any]:
        route = state["route"]
        if route == "blocked":
            return state
        if route == "confirm":
            token, session.pending_token = session.pending_token, None
            try:
                state["action_result"] = self.tools.confirm(session.actor, str(token))
            except ToolError as exc:
                state["action_error"] = str(exc)
            self.budget.record(COST_PER_TURN_CENTS)
        elif route == "freeze":
            if session.card_id is None:
                state["action_error"] = "no card on this session"
            else:
                session.pending_token = self.tools.propose(
                    session.actor, "freeze_card", {"card_id": session.card_id}
                )
                last4 = self.tools.bank.get_card(session.card_id)["last4"]
                session.pending_label = f"freeze your card ending {last4}"
        elif route == "dispute":
            if session.txn_id is None:
                state["action_error"] = "no transaction selected"
            else:
                session.pending_token = self.tools.propose(
                    session.actor,
                    "open_dispute",
                    {"txn_id": session.txn_id, "reason": str(state["redacted"])[:200]},
                )
                session.pending_label = "open this dispute"
        elif route == "escalate":
            self.tools.call(
                session.actor, "request_human_agent", {"summary": str(state["redacted"])}
            )
        elif route == "policy":
            answer: Answer = compose_answer(
                str(state["redacted"]), self.retrieve(str(state["redacted"]))
            )
            state["answer"] = answer.text
            state["citations"] = [c.policy_id for c in answer.citations]
            state["blocked_reason"] = answer.blocked_reason
            self.budget.record(COST_PER_TURN_CENTS)
        return state

    def _respond(self, state: dict[str, Any], session: Session) -> dict[str, Any]:
        route = state["route"]
        if route == "blocked":
            return state
        if route in ("freeze", "dispute"):
            if state.get("action_error"):
                state["reply"] = f"I could not do that: {state['action_error']}."
            else:
                state["reply"] = (
                    f"Please confirm: do you want me to {session.pending_label}? "
                    "Reply yes to proceed."
                )
        elif route == "confirm":
            state["reply"] = (
                f"I could not complete that: {state['action_error']}."
                if state.get("action_error")
                else "Done. It is recorded in your account history."
            )
        elif route == "escalate":
            state["reply"] = "I have passed your case to a human agent with a summary."
        elif state.get("answer"):
            state["reply"] = f"{state['answer']} (source: {', '.join(state['citations'])})"
        else:
            state["reply"] = (
                "I could not find that in our policies, so I will connect you to a human "
                "agent (POL-028)."
            )
            self.tools.call(
                session.actor, "request_human_agent", {"summary": str(state["redacted"])}
            )
        return state


StepFn = Callable[["Assistant", dict[str, Any], Session], dict[str, Any]]
_STEP_FUNCTIONS: dict[str, StepFn] = {
    "guard": Assistant._guard,
    "route": Assistant._route,
    "act": Assistant._act,
    "respond": Assistant._respond,
}
