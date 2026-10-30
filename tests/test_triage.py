"""Triage rule tests and feature parity between batch and per-customer computation."""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pytest

from data.generator.generate import GeneratorConfig, generate_bank
from data.generator.tickets import TEMPLATES_EN, generate_tickets
from ml.risk.model import build_features
from services.assistant.rag.chunking import load_chunks
from services.assistant.rag.lexical import BM25Index
from services.triage.build import POLICY_PATH
from services.triage.pipeline import IntentModel, RiskScorer, TriagePipeline


@pytest.fixture(scope="module")
def pipeline() -> Iterator[TriagePipeline]:
    tickets = generate_tickets(["C0000001"], 1500, seed=5)
    intents = IntentModel.fit(list(tickets["text"]), list(tickets["intent"]), seed=5)
    index = BM25Index(load_chunks(POLICY_PATH, window=2, overlap=1))
    risk = RiskScorer({"C0000001": 0.1, "C0000002": 0.9})
    yield TriagePipeline(intents, risk, index)


def _ticket(text: str, customer: str = "C0000001") -> dict[str, str]:
    return {"ticket_id": "TK-test", "customer_id": customer, "text": text}


def test_complaint_always_goes_to_a_human(pipeline: TriagePipeline) -> None:
    result = pipeline.triage(_ticket("I want to file a formal complaint about the rude agent"))
    assert result.intent == "complaint"
    assert result.route == "human_review"
    assert result.draft is None


def test_high_risk_dispute_needs_approval(pipeline: TriagePipeline) -> None:
    result = pipeline.triage(
        _ticket("I see a charge that I did not make, I want to dispute it", customer="C0000002")
    )
    assert result.intent == "card_dispute"
    assert result.route == "human_review"
    assert result.reason == "high_risk_dispute_needs_approval"


def test_policy_question_gets_a_cited_draft(pipeline: TriagePipeline) -> None:
    result = pipeline.triage(_ticket("What is the monthly maintenance fee on my current account?"))
    assert result.route == "agent_draft"
    assert "POL-001" in result.citations
    assert result.draft is not None


def test_arabic_ticket_is_not_silently_drafted(pipeline: TriagePipeline) -> None:
    """Known gap: the lexical tokenizer ignores Arabic, so Arabic tickets must go to a human."""
    result = pipeline.triage(_ticket("ما هي رسوم الحساب الشهرية"))
    assert result.route == "human_review"


def test_every_ticket_gets_a_route(pipeline: TriagePipeline) -> None:
    for text in TEMPLATES_EN["fee_question"] + TEMPLATES_EN["other"]:
        assert pipeline.triage(_ticket(text)).route in {"agent_draft", "human_review"}


def test_feature_parity_batch_vs_single_customer() -> None:
    """Features for one customer computed alone must equal the batch features for that customer."""
    bank = generate_bank(
        GeneratorConfig(seed=31, n_customers=400, mean_transactions_per_account=20)
    )
    batch = build_features(bank)
    target = str(bank.customers.iloc[17]["customer_id"])

    single_bank_customers = bank.customers[bank.customers["customer_id"] == target]
    accounts = bank.accounts[bank.accounts["customer_id"] == target]
    txns = bank.transactions[bank.transactions["account_id"].isin(accounts["account_id"])]
    cards = bank.cards[bank.cards["account_id"].isin(accounts["account_id"])]

    from data.generator.generate import SyntheticBank

    alone = build_features(SyntheticBank(single_bank_customers, accounts, cards, txns))
    numeric = [c for c in batch.columns if c not in ("country", "language")]
    np.testing.assert_allclose(
        alone.loc[target, numeric].to_numpy(dtype=float),
        batch.loc[target, numeric].to_numpy(dtype=float),
        rtol=1e-9,
    )
