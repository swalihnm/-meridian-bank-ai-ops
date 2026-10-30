PYTHON ?= python

.PHONY: install lint typecheck test gate check reproduce data baseline finetune retrieval-eval exp001 exp002 arabic risk red-team load-test

# Each target is listed only once its code exists. See docs/PROJECT_PLAN.md Section 8.

install:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

typecheck:
	$(PYTHON) -m mypy

test:
	$(PYTHON) -m pytest

# Guardrail regression gate: fails on any wrong action, PII leak, low escalation recall or low injection block.
gate:
	$(PYTHON) -m ml.eval.scenario_eval --gate

check: lint typecheck test gate

# Week 2: synthetic bank (seeded, validated) and the TF-IDF baseline on Banking77.
data:
	$(PYTHON) -m data.generator.generate --customers 100000 --txns-per-account 20

baseline:
	$(PYTHON) -m ml.intent.baseline

# Week 3: DistilBERT intent model with calibration (about 1 hour on CPU).
finetune:
	$(PYTHON) -m ml.intent.finetune

# Week 4: retrieval configurations on the policy golden set.
retrieval-eval:
	$(PYTHON) -m ml.eval.retrieval_eval

# Week 10: abstain-rule experiment (offline replay).
exp002:
	$(PYTHON) -m ml.eval.exp002_abstain

# Cheap evaluations that need no GPU, no Kafka and no model downloads.
reproduce: gate arabic exp002 red-team risk

arabic:
	$(PYTHON) -m ml.eval.arabic_eval

red-team:
	$(PYTHON) -m ml.eval.red_team

risk:
	$(PYTHON) -m ml.risk.model

# Week 10: reranker experiment (needs the embedder and reranker models).
exp001:
	$(PYTHON) -m ml.eval.exp001_reranker

# Week 11: needs a running API at MERIDIAN_LOAD_URL (default http://127.0.0.1:8080).
load-test:
	$(PYTHON) -m ml.eval.load_test
