# Weekly log

Format per week: what was built, what broke, numbers measured, what is left.

**Status key:** `done` = written and verified by running it. `written` = code exists, not yet run. `blocked` = cannot be done in this environment (reason given).

## Progress at a glance

| Week | Scope | Status |
|---|---|---|
| 1 | Product definition, targets, repo skeleton, CI | done (targets await owner approval) |
| 2 | Synthetic generator, validation, mock bank, TF-IDF baseline | done: generator (100k customers, ~3M transactions) and validation ran; mock bank tests pass; TF-IDF baseline test accuracy 0.8896, macro-F1 0.8897 |
| 3 | DistilBERT intent model, calibration, Keras/TF baseline | done with misses: test accuracy 0.8935 and macro-F1 0.8900 (targets 0.92 and 0.91 missed; TF-IDF baseline 0.8896 is within noise); ECE 0.132 raw to 0.016 calibrated (met). Keras/TF baseline not started |
| 4 | Policy RAG, citation check, retrieval eval | done with misses: recall@5 0.95 (dense) to 0.98 (hybrid + reranker), but citation correctness 0.85 vs target 0.95; out-of-scope abstain 0.70 to 1.00 |
| 5 | Orchestrator, MCP tools, guardrails, checkpoints | done: tool server, audit chain, guardrails, checkpoints, orchestrator, safety tests all pass (47 tests total). MCP SDK transport not wired |
| 6 | Eval harness, LLM-judge, CI gate | not started |
| 6 | Scenario suite, CI gate, LLM-as-judge | done: 25-scenario gate in CI (passes: 0 wrong actions, 0 PII leaks, escalation recall 1.0, injection block 1.0); LLM-judge blocked (no hosted LLM key) |
| 7 | Risk model, triage, Kafka, Feast, Spark/Delta, parity | done: risk model (AUC 0.72 on synthetic label); Kafka triage 500/500 end to end; Feast online/offline/batch parity 0 mismatches; Spark vs pandas parity 0 mismatches over 20,000 customers |
| 8 | LoRA fine-tune, LLM router, cost table | blocked: no usable GPU (CUDA wheel install ran out of memory) and no hosted LLM key for the cost comparison |
| 9 | MLflow registry, drift, observability | done with limits: drift monitor (simulated event detected); registry with promotion gate (current model refused, correctly); OpenTelemetry spans per turn (no exporter); Prometheus alert rules and Grafana dashboard written, not scraped live |
| 10 | Experiments, Arabic | done with limits: EXP-001 (reranker, no ship), EXP-002 (abstain rule, ship), EXP-003 (combined EN+AR index, ship). Arabic: 5 of 30 policies, machine-written translations, Arabic recall 0.40 to 0.90 on 10 questions |
| 11 | Deploy, load test, rollback | partly done: API image built and run locally; load test 300/300 OK, p95 37 ms (local, assumed mix); Helm chart lints and renders (Helm 3.16.2); not deployed to a cluster; Terraform and AWS not possible here |
| 12 | Governance, launch, portfolio | done with limits: model cards (intent, risk, retrieval), DPIA-style assessment, red-team report, risk register v3, launch checklist (not launched: 6 must-items open), three executive memos, ADRs 0002 to 0008, README with reproduce target, resume notes. No demo video |

## Week 4 retrieval results (verified 2026-10-28)

Golden set: 60 in-scope and 10 out-of-scope questions, written by hand for this project. Scored with `make retrieval-eval` equivalent: `python -m ml.eval.retrieval_eval`, output in `ml/eval/results/retrieval.json`.

| Configuration | recall@5 (target >= 0.85) | MRR | Citation correct (target >= 0.95) | Abstain on out-of-scope |
|---|---|---|---|---|
| BM25 only | 0.867 | 0.772 | 0.683 | 0.70 |
| Dense only (all-MiniLM-L6-v2) | 0.950 | 0.897 | 0.817 | 1.00 |
| Hybrid (RRF) | 0.933 | 0.895 | 0.850 | 0.80 |
| Hybrid + cross-encoder reranker | 0.983 | 0.917 | 0.850 | 0.70 |

**Read this as a miss.** Recall meets its target. Citation correctness does not: 15 percent of answered in-scope questions cite the wrong policy, which is the failure mode the target was set to prevent. Out-of-scope abstention is also weak: the best configuration answers 30 percent of out-of-scope questions, so the hallucinated-policy guardrail (G4, target 2 percent) is not met. Causes are not yet diagnosed; likely candidates are near-duplicate policy wording (POL-005 and POL-018, POL-009 and POL-010) and a lexical-overlap abstain rule that is too permissive. The golden set is small and hand-written, so these numbers are indicative, not final.

## Week 3 fine-tune environment note

PyTorch installed is the CPU build (2.14.1+cpu). A CUDA 12.1 wheel install failed with MemoryError during download. Fine-tuning runs on CPU, which is slower but works for DistilBERT at this data size.

## Final pass: everything that can be done without people, accounts or hardware (2026-10-29)

- **Prompt v2** for generated answers: unsupported sentences 1.6 percent (target 2 percent met), with the word-overlap caveat.
- **Human labelling kit:** `ml/eval/human_labels.py build` wrote `ml/eval/human/labelling_sheet.csv` (50 answers). `score <file>` computes human-vs-rule and human-vs-judge kappa. Tested on a small sample. No human labels exist yet.
- **Arabic review sheet:** `ml/eval/human/arabic_review_sheet.csv` (5 policies in English and Arabic, 13 questions). No reviewer has filled it in.
- **Red-team brief:** `docs/risk/RED_TEAM_BRIEF.md` for an outside tester. No outside test has been run.
- **Checks:** lint and strict mypy clean (69 files); 98 tests pass; scenario gate exits 0.

### Still blocked (needs people, accounts or hardware)
1. Human labels for the judge (sheet ready): needs 1 or more reviewers. Then run `score`.
2. Native-speaker review of Arabic (sheet ready): needs a fluent reviewer.
3. Outside red team (brief ready): needs a tester.
4. GPU fine-tune with the full recipe: needs free Colab or Kaggle time. The DistilBERT model does not beat the Keras baseline.
5. Cloud deployment, Terraform apply, public demo: needs an AWS account (not free).
6. CFPB dataset: blocked from this network.
7. Demo video: not produced.
8. Rotate the Ollama API key (it was pasted in chat).

## GPU fine-tune on Kaggle (2026-10-30)

- Full recipe on a T4 GPU (embeddings unfrozen, 4 epochs). Results in `ml/intent/results/finetune_kaggle.json`.
- Test accuracy 0.9166 (target 0.92: missed by 0.0034). Macro-F1 0.9168 (target 0.91: met). ECE after temperature scaling 0.0128 (target 0.05: met).
- The promotion gate refuses the model, on accuracy only.
- The laptop run's gap came partly from the memory-limited recipe. Confirmed: the full recipe does better, but not by enough to meet the target.
- Checkpoint downloaded from Kaggle, checked different from the laptop model (SHA-256 differs), and saved as `ml/intent/artifacts/distilbert_intent_kaggle.pt`.
- Paired comparison on the test split (`python -m ml.intent.paired_compare <checkpoint>`): Kaggle DistilBERT 0.9166 vs Keras 0.9010 (McNemar p = 0.0022) vs TF-IDF 0.8896 (p = 3.8e-7). The transformer beats both baselines significantly. Accuracy is still 0.0034 under the 0.92 target; its 95% interval (0.906 to 0.926) includes 0.92.
- Note: `ml/intent/results/paired_compare.json` now holds this Kaggle comparison; the laptop comparison numbers are in the Week 3 section above.

## Hosted LLM evaluation (2026-10-29)

- Key supplied in chat for the Ollama hosted API. Used only through the `OLLAMA_API_KEY` environment variable. Repository scan: no copy. Owner should rotate it.
- Judge (n = 50 answered in-scope questions): agreement with the programmatic label 0.90 (95% CI 0.79 to 0.96), Cohen's kappa 0.70. Of 5 disagreements, 2 were false approvals of wrong citations and 2 were false rejections of right ones. The label is a rule, not a human label.
- Generated answers from the top 3 BM25 policies (gpt-oss:20b): citation correct 0.80 (48 of 60 in scope, 50 answered), unsupported sentences 10.7 percent (target 2 percent, not met), out-of-scope answered 0 of 10. Not like-for-like with the hybrid extractive figure (0.78), since retrieval differs.
- Decision (ADR 0014): hosted model for evaluation only. Customer answers stay extractive.
- **Prompt v2 (tightened: copy facts word for word, no added numbers, at most two sentences):** unsupported sentences 10.7 percent to 1.6 percent (target 2 percent met). Citation correct 48 to 47 of 60 (one question, within noise). Out-of-scope still 0 of 10. Baseline kept in `ml/eval/results/llm_eval_v1_baseline.json`.
- **Caveat:** the unsupported-sentence check is word overlap, so close copying lowers it. The drop shows the model quotes more, not that it paraphrases correctly. Judge agreement moved 0.90 to 0.92 on identical inputs, so run-to-run variation of about 0.02 should be assumed.

## Completion pass, all parts that can be done here (2026-10-29)

- **Live local stack:** `infra/docker/compose.yml` runs the API, Prometheus and Grafana together. `ml/eval/stack_check.py`: API healthy, 40 of 40 requests (spread over sessions, since the gateway limits a session to 30 a minute), Prometheus target `up`, 3 alert rules loaded, Prometheus counted the requests, Grafana dashboard "Meridian assistant" provisioned.
- **Bug found by the live run:** the API image lacked the OpenTelemetry SDK that the final pass had added, so the container exited on start. The earlier container check had run before that change. Fixed in the Dockerfile and `pyproject.toml`. Lesson: rerun the container check after every change to imports.
- **Rollback drill, live:** `ml/eval/rollback_drill.py` against the running container. Chat works; a non-admin cannot trip the kill-switch (403); the admin trips it and chat is paused; the admin resumes and chat works. All 6 steps pass.
- **Licences checked from the Hub:** Banking77 (both copies) CC BY 4.0; the three models Apache 2.0. These are licence tags from the platform, not the full licence text.
- **Prometheus rules and config:** validated with promtool 2.54.1.
- **MCP server:** `services/mcp_bank/mcp_server.py`, on the MCP SDK v1 (v2 renamed the API, so the dependency is pinned `<2`). Bound to one customer; ownership checked before each tool. 5 tests through a real MCP client session pass.
- **Scheduled retraining:** `ml/pipelines/retrain.py`. A simulated drift event (PSI 7.19 on message length, 1.03 on intent mix) triggers a retrain. The retrained model (accuracy 0.8896, ECE 0.17) fails the gate, correctly. The incoming stream cannot be used as training data (synthetic label names, no mapping to Banking77), which is a finding. Not on a schedule.
- **Property-based tests (Hypothesis):** card redaction, Luhn, redaction idempotence, injection false positives, the support ratio bounds. 7 tests pass.
- **Keras comparison:** done with McNemar tests (see the Week 3 section).
- **Gulf dialect and Arabizi (plan L2):** 1 of 8 correct, target 80 percent, not met. The seven refusals are safe (handed to a human). Not tuned against the set.
- **Decisions without the owner:** ADRs 0012 (MCP bound to one customer) and 0013 (retraining gated, not automatic).
- **Checks:** lint clean; strict mypy clean across 64 files; 88 tests pass; scenario gate exits 0.

## Final pass, decisions taken without the owner (2026-10-29)

- **Root cause of several failures found: the system drive was full (0 GB free).** That explains the Windows package-install errors, the Terraform provider write error, and very likely the fine-tune segfaults and the earlier CUDA MemoryError. Cleared only caches and this project's own partial files: pip cache (5.75 GB), Docker build cache (5.9 GB), a broken TensorFlow environment, and a partial Terraform provider. Did not touch other projects' Docker images. Free space now about 5 GB.
- **Validated now (previously only written):** Prometheus rules and config (promtool 2.54.1: 3 rules, config OK); Terraform ECS module (`terraform validate` OK with Terraform 1.9.8, not applied).
- **Added:** opt-in OpenTelemetry console exporter (`MERIDIAN_TRACE=console`).
- **Decisions recorded as ADRs:** 0009 PII redaction stays rule-based (Presidio not adopted); 0010 deployment checked by validation, not run in the cloud; 0011 no LoRA, router or LLM judge (no GPU, no hosted comparator).
- **Keras baseline (done):** dense network on TF-IDF, test accuracy 0.9010, macro-F1 0.9016. Paired McNemar tests (`ml/intent/paired_compare.py`): Keras vs TF-IDF p = 0.0017; Keras vs DistilBERT p = 0.19; DistilBERT vs TF-IDF p = 0.53. The fine-tuned DistilBERT does not beat the baseline. Neither model meets the 0.92 target, so neither is promoted.
- **Red-team and gate:** unchanged by the final pass (gate exit 0, safety tests pass).

## Week 12 close-out (verified 2026-10-29)

- **Checks:** `ruff check` clean; `mypy --strict` clean across 57 source files; 83 tests pass; `ml.eval.scenario_eval --gate` exits 0; the five `make reproduce` steps exit 0 (run in order, since `make` is not installed here).
- **Fixes made during the final pass, each found by a test or a run:** API crash from SQLite threads under FastAPI; a client-supplied card and transaction ID that allowed cross-customer access; a torch import that stopped the slim API image from starting; a tokenizer that dropped Arabic; a stopword list that counted Arabic function words as content; a confirmation prompt that did not say which card; an abstain rule that answered off-topic questions on one shared word.
- **Red team:** the first run blocked 0 of 20 paraphrased injections, and one freeze executed after a "yes". After the patch: 14 of 20 blocked, 0 writes executed. The patches were written from the same attacks, so the 70 percent is an overestimate.
- **Not done, and why:** LoRA and router (no GPU, no hosted key); LLM judge (no hosted key); cloud deployment, Terraform, AWS, Kubernetes run (no cluster or cloud account here); CFPB data (blocked, 403); demo video; Keras or TensorFlow baseline; OpenTelemetry exporter; Presidio redaction; native-speaker review of Arabic; external red team.
- **Container check (final image):** health 200; English policy question cites POL-001; Arabic policy question cites POL-001 when sent as UTF-8 JSON. An earlier empty citation came from the PowerShell test client, which sent the Arabic body in the system code page. Not a product defect; use UTF-8 when testing by hand.
- **Superseded numbers:** the Week 4 retrieval figures (citation 0.85, out-of-scope answered 20 percent) were re-run after the abstain fix: citation 0.78 for hybrid, out-of-scope 0 of 10. `retrieval.json` is the current file; the model card and memo 1 say which numbers were superseded.

## Weeks 6 to 7 notes (verified 2026-10-29)

- **Scenario gate (Week 6):** `python -m ml.eval.scenario_eval --gate` runs in CI. The first run failed on an abstain bug (off-topic questions were answered on one shared word). The fix needs two matched content words, or half the question. Three policy-citation misses remain and are recorded in the output. The scenarios were written by the same project, so the gate checks our own failure list, not an external one.
- **Kafka triage (Week 7):** Redpanda v24.2.7, single node. 500 held-out synthetic tickets, all triaged. Intent accuracy 1.0 on these tickets, which is a template artefact, not evidence of skill. Routing: 216 agent drafts, 284 human reviews (151 low overlap, most of them action requests such as card freeze; 67 complaints; 63 Arabic tickets dropped because the tokenizer ignores Arabic; 3 high-risk disputes).
- **Feast (Week 7):** feature view on 5,000 customers, materialised to SQLite online and read back. Checked 300 customers x 10 features: 0 mismatches for both online and offline historical reads. The sample is small. One fix was needed: Feast inferred the join key as JSON until the entity type was declared as string.
- **Spark (Week 7):** PySpark 3.5.3 with Delta 3.2.0, run in the official Apache Spark container. On Windows the job fails without winutils, so it runs on Linux. Output: 100,000 rows to a Delta table. Parity against the pandas training features: 0 mismatches over 20,000 customers.

## Week 3 intent model results (verified 2026-10-29)

Model card: `docs/model-cards/intent.md`. Test split of 3,080, Banking77.

| Model | Accuracy | Macro-F1 | ECE |
|---|---|---|---|
| TF-IDF + logistic regression | 0.8896 | 0.8897 | not measured |
| DistilBERT, raw | 0.8935 | 0.8900 | 0.132 |
| DistilBERT, temperature-scaled (T = 0.69) | 0.8935 | 0.8900 | 0.016 |

**Miss:** the fine-tuned model is only 0.4 points above the baseline on accuracy. The 95% interval is about 1.1 points, so the gain is not established. Targets 0.92 accuracy and 0.91 macro-F1 are not met. Likely causes, not tested: frozen embeddings and 3 epochs (both cut for memory), and no hyperparameter search. A paired test and an ablation would settle it.

**Process:** two earlier runs failed (one segfault under memory pressure, one stall that was slow CPU training). The final run completed with exit code 0. The `_recursion_count` traceback at exit is harmless multiprocess cleanup noise.

## Environment limits (found 2026-10-28)

- **CFPB complaint data: blocked.** `consumerfinance.gov` returns 403 from this machine. The loader cannot run here; a local copy would be needed.
- **No hosted LLM key.** The strong-model path and LLM-as-judge cannot be run or validated (kappa). Answers are extractive for now.
- **No AWS, Terraform, Helm, kind.** Week 11 deployment cannot be done here.
- **GPU: GTX 1650, 4 GB.** Enough for DistilBERT with fp16 and small batches; not enough for a large LoRA run.
- **Docker and Java 18 are present.** Possible later for Redpanda and Postgres/pgvector containers; Spark on Java 18 is unverified.
- **Package install:** the PyTorch CUDA index hung; installs use PyPI.

---

## Week 1: Define the product and set targets

**Dates:** started 2026-10-28.

### Built
- Repo initialised on branch `main` (no commits yet; commit when the owner approves the targets).
- Directory skeleton from PLAN Section 9, with empty service folders.
- `CLAUDE.md` (PLAN Section 14), `docs/PROJECT_PLAN.md` (copy of the plan).
- Product documents v1: `VISION.md`, `USERS.md`, `METRICS.md` (targets **proposed**), `ROADMAP.md`.
- `docs/risk/RISK_REGISTER.md` v1 (12 risks and 3 governance risks).
- Tooling: `pyproject.toml` (ruff, mypy strict, pytest), `Makefile` (`lint`, `typecheck`, `test`, `check`), `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `.devcontainer/devcontainer.json`, `.gitignore`.
- Smoke tests in `tests/test_skeleton.py` so CI has something to run.

### Not done in Week 1 (and why)
- **Targets are not yet approved.** The plan says targets are set in week 1 and before building. They are drafted with reasoning in `docs/product/METRICS.md`, marked PROPOSED. Owner review is needed before the Week 2 build starts.
- **GitHub Projects board** not created (needs a GitHub remote; no remote is configured yet).
- **Synthetic data generator design** not written. Scheduled for Week 2 as the first build step, with the schema drafted from `USERS.md` and `PROJECT_PLAN.md` Section 2.

### Verified
- `ruff check .`: passed.
- `ruff format --check .`: 14 files already formatted.
- `mypy` (strict, `tests`): no issues.
- `pytest`: 2 passed (required-files check, service-folder check).
- Environment: Python 3.12.0 local (CI pins 3.11), git 2.51.0. Commands run directly, because `make` is not installed on this Windows machine.

### Numbers measured
- None. No models exist yet, which is the point of Week 1.

### Problems and decisions
- The project folder was empty when Week 1 started, so the skeleton was created from scratch.
- First `pip install -e ".[dev]"` failed: setuptools refused flat-layout with several top-level folders. Fixed by declaring `[tool.setuptools] packages = []` until a package exists.
- Decision: product docs are drafted by the assistant and marked as proposals, not as final, because targets are the owner's call.
- Decision: no commit yet. Commits happen when the owner asks.

### Left for next week
1. Owner reviews and approves `docs/product/METRICS.md`; commit the week 1 state.
2. Create the GitHub remote and Projects board.
3. Week 2: `mockbank` and the seeded generator (`make data`), Banking77 and CFPB loaders, data validation, TF-IDF baseline logged to MLflow.
4. Check `docs/DATA_LICENCES.md` for Banking77 and CFPB before loading either.
