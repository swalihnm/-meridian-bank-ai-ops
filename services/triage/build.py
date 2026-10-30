"""Build a ready-to-run triage pipeline from the synthetic data.

Trains the intent model on synthetic tickets (one seed) and the dispute-risk model on a seeded bank.
Returns the pipeline plus the bank's customer IDs, so a ticket producer can refer to real customers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import lightgbm as lgb
import pandas as pd

from data.generator.generate import GeneratorConfig, generate_bank
from data.generator.tickets import generate_tickets
from ml.risk.model import FEATURES, build_features, synthetic_label
from services.assistant.rag.chunking import load_chunks
from services.assistant.rag.lexical import BM25Index
from services.triage.pipeline import IntentModel, RiskScorer, TriagePipeline, risk_scores

POLICY_PATH = Path("data/policies/POLICIES.md")


@dataclass(frozen=True)
class Built:
    pipeline: TriagePipeline
    customer_ids: list[str]


def build(seed: int = 7, n_customers: int = 5_000, n_train_tickets: int = 4_000) -> Built:
    bank = generate_bank(
        GeneratorConfig(seed=seed, n_customers=n_customers, mean_transactions_per_account=20)
    )
    features: pd.DataFrame = build_features(bank)
    labels = synthetic_label(features, seed)
    risk_model = lgb.LGBMClassifier(
        n_estimators=200, learning_rate=0.05, num_leaves=31, random_state=seed, verbose=-1
    )
    risk_model.fit(features[FEATURES], labels)
    scores = risk_scores(features, risk_model)

    train = generate_tickets(list(features.index), n_train_tickets, seed=seed + 1000)
    intents = IntentModel.fit(list(train["text"]), list(train["intent"]), seed=seed)

    index = BM25Index(load_chunks(POLICY_PATH, window=2, overlap=1))
    pipeline = TriagePipeline(intents, RiskScorer(scores), index)
    return Built(pipeline, [str(c) for c in features.index])
