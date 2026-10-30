"""Ticket triage logic: intent, risk, route and a drafted reply.

No Kafka here, so it is easy to test.

Steps for each ticket:
1. Intent: TF-IDF and logistic regression, trained on the synthetic ticket templates. This is a
   deliberately simple baseline. Its accuracy is measured on held-out SYNTHETIC tickets only.
2. Risk: the dispute-risk model from ml/risk (LightGBM), looked up by customer. Synthetic label.
3. Route, one of:
   - human_review: complaints, low-confidence intents, or high-risk disputes
     (POL-007, POL-027, POL-028)
   - agent_draft: a drafted reply is ready for an agent to approve or edit
   - human_review also when no policy answers the ticket (abstain)
4. Draft: extractive answer from the policy index, with the policy cited.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline

from services.assistant.rag.answer import compose_answer
from services.assistant.rag.lexical import BM25Index

LOW_CONFIDENCE = 0.5
HIGH_RISK = 0.5
HUMAN_INTENTS = {"complaint"}


@dataclass(frozen=True)
class TriageResult:
    ticket_id: str
    intent: str
    confidence: float
    risk: float
    route: str
    reason: str
    draft: str | None
    citations: list[str]


class IntentModel:
    def __init__(self, pipeline: Pipeline, classes: list[str]) -> None:
        self.pipeline = pipeline
        self.classes = classes

    @classmethod
    def fit(cls, texts: list[str], labels: list[str], seed: int = 0) -> IntentModel:
        model = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True),
            LogisticRegression(max_iter=2000, C=10.0, random_state=seed),
        )
        model.fit(texts, labels)
        return cls(model, list(model.classes_))

    def predict(self, text: str) -> tuple[str, float]:
        probs = self.pipeline.predict_proba([text])[0]
        idx = int(np.argmax(probs))
        return self.classes[idx], float(probs[idx])


class RiskScorer:
    """Dispute-risk score per customer, from the same feature function used in training."""

    def __init__(self, scores: dict[str, float]) -> None:
        self.scores = scores

    def score(self, customer_id: str) -> float:
        return self.scores.get(customer_id, 0.0)


class TriagePipeline:
    def __init__(
        self,
        intents: IntentModel,
        risk: RiskScorer,
        index: BM25Index,
    ) -> None:
        self.intents = intents
        self.risk = risk
        self.index = index

    def triage(self, ticket: dict[str, Any]) -> TriageResult:
        text = str(ticket["text"])
        customer_id = str(ticket["customer_id"])
        intent, confidence = self.intents.predict(text)
        risk = self.risk.score(customer_id)

        if intent in HUMAN_INTENTS:
            return self._human(ticket, intent, confidence, risk, "complaint_needs_agent")
        if confidence < LOW_CONFIDENCE:
            return self._human(ticket, intent, confidence, risk, "low_confidence")
        if intent == "card_dispute" and risk >= HIGH_RISK:
            return self._human(ticket, intent, confidence, risk, "high_risk_dispute_needs_approval")

        answer = compose_answer(text, self.index.search(text, k=5))
        if not answer.answered:
            return self._human(
                ticket, intent, confidence, risk, f"no_policy_match:{answer.blocked_reason}"
            )
        return TriageResult(
            ticket_id=str(ticket["ticket_id"]),
            intent=intent,
            confidence=confidence,
            risk=risk,
            route="agent_draft",
            reason="policy_draft_ready",
            draft=answer.text,
            citations=[c.policy_id for c in answer.citations],
        )

    @staticmethod
    def _human(
        ticket: dict[str, Any], intent: str, confidence: float, risk: float, reason: str
    ) -> TriageResult:
        return TriageResult(
            ticket_id=str(ticket["ticket_id"]),
            intent=intent,
            confidence=confidence,
            risk=risk,
            route="human_review",
            reason=reason,
            draft=None,
            citations=[],
        )


def risk_scores(features: pd.DataFrame, model: Any) -> dict[str, float]:
    """Score every customer in a feature frame (indexed by customer_id) with a fitted classifier."""
    from ml.risk.model import FEATURES

    proba = np.asarray(model.predict_proba(features[FEATURES]))[:, 1]
    return {str(cid): float(p) for cid, p in zip(features.index, proba, strict=True)}
