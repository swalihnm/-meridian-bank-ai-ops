# Roadmap (now / next / later)

**Status:** Draft v1, 2026-10-28. Mirrors the 12-week plan in [PROJECT_PLAN.md](../PROJECT_PLAN.md) Section 8.

## Now (Weeks 1 to 4)
- Product documents, targets, repo skeleton, CI (Week 1).
- Mock bank, synthetic data generator, Banking77 and CFPB loaders, baseline classifier (Week 2).
- PyTorch intent model with calibration and a Keras or TensorFlow baseline (Week 3).
- Policy RAG with hybrid retrieval, reranker and citation checks (Week 4).

## Next (Weeks 5 to 8)
- Assistant orchestrator with MCP bank tools, approvals, audit log, kill-switch (Week 5).
- Evaluation harness and LLM-as-judge with CI regression gate (Week 6).
- Kafka ticket stream, triage service, risk model with SHAP (Week 7).
- LoRA fine-tune, LLM router, cost comparison (Week 8).

## Later (Weeks 9 to 12)
- MLflow registry, retraining, drift monitoring, observability (Week 9).
- Experiment engine and three experiments; Arabic evaluation (Week 10).
- Kubernetes and AWS deployment, load test, canary and rollback (Week 11).
- Launch, governance pack, exec memo 3, portfolio (Week 12).

## Cut or deferred (and why)

| Item | Decision | Why |
|---|---|---|
| Voice channel | Stretch | Adds a modality without adding evidence about the core question. |
| Azure variant | Stretch | Only if an Azure-first role needs it. AWS is the primary target. |
| Multi-region residency demo | Stretch | Policy-rule work; valuable but not on the critical path. |
| CUPED and sequential testing | Stretch | Plain power analysis and t-tests answer the Week 10 questions. |
| Semantic caching | Stretch | Only if cost targets are missed in Week 8. |
| Consumer mobile app | Not planned | Out of scope (see [VISION.md](VISION.md)). |

## Risk to the roadmap
Scope is the biggest risk. If Week 5 or Week 7 slips, cut stretch items first and protect the product documents and evaluation. See [../risk/RISK_REGISTER.md](../risk/RISK_REGISTER.md).
