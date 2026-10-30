# Meridian

**An AI-native customer operations platform for a fictional digital bank.**

> **Synthetic data notice.** Meridian Bank, its customers, accounts, transactions and policies are fictional. ML components use public text (Banking77). Labels for risk and triage are synthetic and are marked as method checks. No result here describes a real bank or real customers.

## Status

Built over a 12-week plan, to the point where the core assistant, safety gate, triage, feature stores and evidence are done. **Not deployed. Not ready for real customers.** Several planned items are blocked on this machine (GPU, hosted language model, cloud, CFPB data). See [docs/LOG.md](docs/LOG.md) for the progress table and [docs/risk/RISK_REGISTER.md](docs/risk/RISK_REGISTER.md) for the cut list.

## Headline results

Every number below comes from a result file in the repo. Targets are in [docs/product/METRICS.md](docs/product/METRICS.md) (proposed, not yet approved).

| Area | Result | Target | Met? | Source |
|---|---|---|---|---|
| Intent accuracy, Banking77 test (DistilBERT) | 0.8935 | 0.92 | No (TF-IDF baseline 0.8896) | `docs/model-cards/intent.md` |
| Intent accuracy, Keras dense on TF-IDF | 0.9010 (significantly above TF-IDF baseline, p = 0.002) | 0.92 | No | `docs/model-cards/intent.md` |
| Intent calibration (ECE, after temperature scaling) | 0.016 | 0.05 | Yes | `docs/model-cards/intent.md` |
| Policy recall at 5 (hybrid) | 0.933 | 0.85 | Yes | `docs/model-cards/assistant-retrieval.md` |
| Policy citation correct (in scope) | 0.783 | 0.95 | **No** | `docs/model-cards/assistant-retrieval.md` |
| Out-of-scope questions answered | 0 of 10 | 0 | Yes | `ml/eval/retrieval_eval.py` |
| Scenario safety gate: wrong actions, PII leaks | 0, 0 | 0, 0 | Yes | `ml/eval/scenario_eval.py` |
| Escalation recall, injection block (scenarios) | 1.0, 1.0 | 0.95, 0.95 | Yes | `ml/eval/scenario_eval.py` |
| Arabic recall at 5, combined index (10 questions) | 0.90 | parity | Partly (small set) | `docs/product/EXPERIMENTS.md` EXP-003 |
| Dispute risk AUC (synthetic label) | 0.724 | method check | n/a | `docs/model-cards/risk.md` |
| Kafka triage, held-out synthetic tickets | 500 of 500 triaged, p95 2.9 ms per ticket | n/a | n/a | `ml/eval/results/triage_stream.json` |
| Feast online vs offline vs batch | 0 mismatches (300 customers x 10 features) | 0 | Yes | `ml/eval/results/feast_parity.json` |
| Spark vs pandas features | 0 mismatches (20,000 customers x 10 features) | 0 | Yes | `ml/eval/results/spark_parity.json` |
| API load (local, single worker, assumed mix) | 300 of 300 OK, p95 37 ms | n/a | n/a | `ml/eval/results/load_test.json` |
| Live local stack (API, Prometheus, Grafana) | API healthy, target up, 3 rules, dashboard provisioned | n/a | n/a | `ml/eval/results/stack_check.json` |
| Rollback drill on the live container | 6 of 6 steps pass | all pass | Yes | `ml/eval/results/rollback_drill.json` |
| Keras vs TF-IDF intent (paired McNemar) | 0.9010 vs 0.8896, p = 0.002 | n/a | n/a | `ml/intent/results/paired_compare.json` |
| Paraphrased injections with a "yes" turn | 14 of 20 blocked; 0 writes executed | 0 writes | Yes (set used to write patterns) | `docs/risk/RED_TEAM.md` |

## Architecture (what is built)

```
Chat client -> services/api (FastAPI: session token, rate limit, kill-switch, metrics)
                 -> services/assistant (orchestrator: guard -> route -> act -> respond,
                    checkpoint after each step, OpenTelemetry span per turn)
                      -> policy RAG: BM25 over English and Arabic policy chunks, citation check
                      -> services/mcp_bank (tool server: confirm-before-write, approval for
                         disputes of AED 1,000 or more, hash-chained audit log)
                          -> services/mockbank (synthetic core banking; no money-moving method)

Tickets -> Redpanda/Kafka -> services/triage (intent, dispute risk, route, cited draft)
Features -> Feast (online/offline, parity-checked) and Spark -> Delta (parity-checked)
Models -> MLflow registry (promotion gate on METRICS.md targets)
Observability -> Prometheus metrics, alert rules, Grafana dashboard (written, not live-scraped)
```

Full diagram with the checks for each part: [docs/architecture.md](docs/architecture.md). Decisions are recorded as ADRs in [docs/adr/](docs/adr/), including the calls made without the owner (ADRs 0009 to 0011). Model cards are in [docs/model-cards/](docs/model-cards/): intent, risk, retrieval, and triage. Risk and governance: [RED_TEAM.md](docs/risk/RED_TEAM.md), [DPIA.md](docs/risk/DPIA.md), [RISK_REGISTER.md](docs/risk/RISK_REGISTER.md). Launch status: [LAUNCH.md](docs/product/LAUNCH.md) (not launched).

## Reproduce

Requires Python 3.11+. The main venv is `.venv`; Feast lives in `.venv-feast`.

```bash
python -m pip install -e ".[dev]"
make check          # lint, strict mypy, tests, and the guardrail gate
make reproduce      # the cheap evaluations: scenario gate, Arabic, EXP-002, red team, risk model
```

Heavier steps (not in `make reproduce`):

- `make data`: the 100k-customer synthetic bank (about 35 seconds).
- `make baseline`: TF-IDF baseline on Banking77 (downloads the dataset).
- `make finetune`: DistilBERT fine-tune. About an hour on CPU; needs about 2 GB of free memory.
- `make retrieval-eval`: needs two Hugging Face models (embedder and reranker).
- Kafka, Feast and Spark steps need Docker or the Feast environment; see `docs/LOG.md`.

On Windows without `make`, run the commands in the [Makefile](Makefile) directly.

## Known limits (read before quoting any number)

- **Synthetic labels.** Risk and synthetic-ticket results are method checks. The triage intent accuracy of 1.0 comes from template text and is not evidence of skill.
- **Small, hand-written test sets.** The retrieval set (70 questions), scenario set (25) and Arabic set (13) were written by this project, and some were written after seeing failures.
- **Regex guard.** It blocks 70 percent of paraphrases, but the patterns were chosen from those same attacks.
- **Dialect and Arabizi.** 1 of 8 correct (target 80 percent). Refusals are safe but leave these customers to humans.
- **Arabic.** Five of thirty policies are translated. Translations are machine-written and not reviewed by a native speaker. Retrieval is lexical with no stemming.
- **Language model.** A hosted model (Ollama cloud) is used for evaluation only: judge agreement 0.90 against a rule, and generated answers with 1.6 percent unsupported sentences after a tighter prompt (word-overlap metric; it rewards close copying). Customer answers stay extractive (ADR 0014). LoRA and the router were not done.
- **Deployment.** Not deployed. The Helm chart lints and renders (checked with Helm 3.16.2) but has not run on a cluster.
- **Licences.** Banking77 comes from a Parquet mirror; its licence still needs checking. The CFPB dataset could not be downloaded.

## Licence

To be decided before publication. Dataset licences are tracked in [docs/DATA_LICENCES.md](docs/DATA_LICENCES.md).
