"""Bank tool server: the only path from the assistant to the mock bank.

Design rules (PLAN Section 5):
- No tool can move money. The tool list is fixed and tests check it.
- Writes need a two-step confirmation: `propose` returns a token, `confirm` executes it.
- Disputes at or above AED 1,000 also need an agent approval token (POL-007).
- Every call, including refusals, is written to the hash-chained audit log.

The shape of each tool (name, description, JSON-schema input) follows the MCP tool format, so an
MCP transport can wrap this later. The MCP Python SDK is not installed yet; see docs/LOG.md.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any

from services.mcp_bank.audit import AuditLog
from services.mockbank.bank import MockBank, NotFoundError, VerificationRequiredError

DISPUTE_APPROVAL_THRESHOLD_FILS = 100_000  # AED 1,000 (POL-007)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    schema: dict[str, Any]
    needs_confirmation: bool = False


TOOLS: dict[str, ToolSpec] = {
    "get_balance": ToolSpec(
        "get_balance",
        "Return the balance of one of the customer's accounts, in fils.",
        {"account_id": "str"},
    ),
    "list_transactions": ToolSpec(
        "list_transactions",
        "List recent transactions on an account, newest first.",
        {"account_id": "str", "limit": "int"},
    ),
    "explain_fee": ToolSpec(
        "explain_fee",
        "Explain a fee type by name, with the policy it comes from.",
        {"fee": "str"},
    ),
    "freeze_card": ToolSpec(
        "freeze_card",
        "Freeze a card. Reversible. Needs confirmation.",
        {"card_id": "str"},
        needs_confirmation=True,
    ),
    "open_dispute": ToolSpec(
        "open_dispute",
        "Open a dispute on a transaction. Needs confirmation; amounts of AED 1,000 "
        "or more also need agent approval.",
        {"txn_id": "str", "reason": "str"},
        needs_confirmation=True,
    ),
    "update_address": ToolSpec(
        "update_address",
        "Change the postal address. Blocked unless the customer is verified.",
        {"customer_id": "str", "address": "str"},
        needs_confirmation=True,
    ),
    "request_human_agent": ToolSpec(
        "request_human_agent",
        "Hand the conversation to a human agent with a summary.",
        {"summary": "str"},
    ),
}

FEES = {
    "monthly_maintenance": "POL-001",
    "foreign_currency": "POL-002",
    "atm": "POL-003",
    "late_payment": "POL-004",
}
FEE_TEXT = {
    "monthly_maintenance": (
        "A current account carries AED 15 a month, waived by a salary of AED 5,000 "
        "or an average balance of AED 10,000."
    ),
    "foreign_currency": (
        "Card payments in other currencies carry a 2.5 percent foreign currency fee."
    ),
    "atm": (
        "Five free UAE ATM withdrawals a month, then AED 5 each. "
        "Other banks in the UAE cost AED 10."
    ),
    "late_payment": (
        "A late payment charge of AED 100 applies, AED 200 for a second late payment "
        "within six months."
    ),
}


class ToolError(Exception):
    """A refused or failed tool call. The message is safe to show the customer."""


@dataclass
class _Pending:
    tool: str
    args: dict[str, Any]
    actor: str
    approved_by: str | None = None


@dataclass
class BankToolServer:
    bank: MockBank
    audit: AuditLog = field(default_factory=AuditLog)
    _pending: dict[str, _Pending] = field(default_factory=dict)
    _approvals: dict[str, str] = field(default_factory=dict)

    def tool_names(self) -> list[str]:
        return sorted(TOOLS)

    # ---- two-step flow for writes ------------------------------------------

    def propose(self, actor: str, tool: str, args: dict[str, Any]) -> str:
        spec = self._spec(tool)
        if not spec.needs_confirmation:
            raise ToolError(f"{tool} does not need confirmation; call it directly")
        token = secrets.token_urlsafe(12)
        self._pending[token] = _Pending(tool, args, actor)
        self.audit.append(actor, tool, args, "proposed")
        return token

    def approve(self, token: str, agent_id: str) -> None:
        """Agent approval for a pending dispute (POL-007)."""
        pending = self._pending.get(token)
        if pending is None:
            raise ToolError("unknown or expired token")
        pending.approved_by = agent_id
        self.audit.append(agent_id, "approve", {"token": token}, "approved")

    def confirm(self, actor: str, token: str) -> dict[str, Any]:
        pending = self._pending.pop(token, None)
        if pending is None:
            raise ToolError("unknown or expired token")
        if pending.actor != actor:
            self.audit.append(actor, pending.tool, pending.args, "refused:wrong_actor")
            raise ToolError("this confirmation belongs to another customer session")
        try:
            needs_approval = pending.tool == "open_dispute" and self._needs_approval(pending.args)
            if needs_approval and pending.approved_by is None:
                raise ToolError("disputes of AED 1,000 or more need agent approval first")
            result = self._execute(pending.tool, pending.args)
        except (ToolError, NotFoundError, VerificationRequiredError) as exc:
            self.audit.append(actor, pending.tool, pending.args, f"refused:{type(exc).__name__}")
            raise ToolError(str(exc)) from exc
        self.audit.append(actor, pending.tool, pending.args, "executed")
        return result

    # ---- direct (read-only or handoff) tools --------------------------------

    def call(self, actor: str, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        spec = self._spec(tool)
        if spec.needs_confirmation:
            raise ToolError(f"{tool} needs propose() and confirm()")
        try:
            result = self._execute(tool, args)
        except (ToolError, NotFoundError) as exc:
            self.audit.append(actor, tool, args, f"refused:{type(exc).__name__}")
            raise ToolError(str(exc)) from exc
        self.audit.append(actor, tool, args, "executed")
        return result

    # ---- internals -----------------------------------------------------------

    def _spec(self, tool: str) -> ToolSpec:
        if tool not in TOOLS:
            raise ToolError(f"unknown tool: {tool}")
        return TOOLS[tool]

    def _needs_approval(self, args: dict[str, Any]) -> bool:
        txn = self.bank.find_transaction(str(args["txn_id"]))
        return abs(int(txn["amount_fils"])) >= DISPUTE_APPROVAL_THRESHOLD_FILS

    def _execute(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        if tool == "get_balance":
            return {"balance_fils": self.bank.get_balance(str(args["account_id"]))}
        if tool == "list_transactions":
            limit = min(int(args.get("limit", 20)), 50)
            return {"transactions": self.bank.list_transactions(str(args["account_id"]), limit)}
        if tool == "explain_fee":
            key = str(args["fee"])
            if key not in FEES:
                raise ToolError("fee type not recognised")
            return {"explanation": FEE_TEXT[key], "policy_id": FEES[key]}
        if tool == "freeze_card":
            self.bank.set_card_status(str(args["card_id"]), "frozen")
            return {"card_id": args["card_id"], "status": "frozen"}
        if tool == "open_dispute":
            dispute = self.bank.open_dispute(str(args["txn_id"]), str(args["reason"]))
            return {"dispute_id": dispute.dispute_id, "status": dispute.status}
        if tool == "update_address":
            self.bank.update_address(str(args["customer_id"]), str(args["address"]))
            return {"status": "updated"}
        if tool == "request_human_agent":
            return {"status": "queued", "summary": str(args["summary"])[:500]}
        raise ToolError(f"unknown tool: {tool}")
