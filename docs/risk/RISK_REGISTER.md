# Risk register

**Version:** v1, 2026-10-28. Scored 1 (low) to 5 (high). Score = likelihood x impact. Reviewed at the end of each week; v2 at Week 6, v3 at Week 12.

| ID | Risk | L | I | Score | Owner | Mitigation | Residual |
|---|---|---|---|---|---|---|---|
| R1 | Scope too large for 12 weeks | 4 | 4 | 16 | Owner | Phases 1 to 3 are the core; cut stretch goals first; MVP fallback in PLAN Section 13 | Medium |
| R2 | Assistant gives a wrong policy answer that sounds confident | 4 | 4 | 16 | Owner | RAG with citation check; unsupported claims blocked; hallucination metric G4 | Medium |
| R3 | Prompt injection makes the assistant call an action tool it should not | 3 | 5 | 15 | Owner | Permissions per tool, confirmation steps, approval gate, audit log, injection suite | Low to medium |
| R4 | PII appears in output, logs or traces | 3 | 5 | 15 | Owner | Presidio redaction at input and output; PII leak tests (G2); log scrubbing | Low |
| R5 | Synthetic data is judged unrealistic, so results look weak | 4 | 3 | 12 | Owner | Real public datasets for ML; label synthetic clearly; claim method, not market size | Medium |
| R6 | GPU access for LoRA fine-tuning is unreliable | 3 | 3 | 9 | Owner | Free Colab or Kaggle; small model; keep hosted-LLM path as fallback | Low |
| R7 | Cloud cost overruns during deployment | 3 | 3 | 9 | Owner | Budgets and alerts; tear down after demos; local `kind` fallback | Low |
| R8 | Dataset or model licence prevents use or publication | 2 | 4 | 8 | Owner | Record every licence in `docs/DATA_LICENCES.md` before use | Low |
| R9 | Over-claiming on the resume or in interviews | 3 | 4 | 12 | Owner | Only claim what the repo reproduces; cite `make` targets | Low |
| R10 | Judge (LLM-as-judge) disagrees with humans, so quality numbers are unreliable | 3 | 4 | 12 | Owner | Kappa against human labels (Week 6); report kappa; do not rely on judge alone | Medium |
| R11 | Arabic and dialect quality much worse than English | 4 | 3 | 12 | Owner | Per-language metrics (L1, L2); document gaps; limit Arabic scope if needed | Medium |
| R12 | Burnout or falling behind the weekly plan | 3 | 3 | 9 | Owner | Weekly log; ~15 to 20 hours per week; cut before quality | Low |

## Governance risks (for compliance reviewer)

| ID | Risk | Mitigation |
|---|---|---|
| GR1 | Model used for credit decisions by mistake | Stated out of scope in VISION.md; risk model labelled for triage and review only |
| GR2 | Action taken without consent | Confirmation and audit on every action tool; kill-switch |
| GR3 | Bias across languages or channels | Slice reporting (PLAN Section 7); gaps documented |

## Open questions
- Which hosted LLM API will be used for the strong model, and what data terms apply to synthetic prompts? (Decide in Week 5.)
- Is a Databricks free edition available for Week 7, or is local PySpark enough? (Decide in Week 7.)

---

## Version 3 status (Week 12, 2026-10-29)

Changes from v1, each with the evidence behind it. v1 ratings above are kept for the record.

| ID | Status now | Evidence | Note |
|---|---|---|---|
| R1 Scope too large | **Materialised.** Weeks 1 to 7 substantially done; Week 8 blocked; Weeks 9 to 12 partly done | `docs/LOG.md` progress table | LoRA (Week 8), deployment (Week 11, cloud), LLM judge, Arabic at full scale, demo video |
| R2 Wrong policy answer | **Partly mitigated, not closed.** Citation correctness 0.78 (English), target 0.95 | `docs/model-cards/assistant-retrieval.md` | Out-of-scope answered 0 of 10 |
| R3 Prompt injection drives a tool call | **Partly mitigated.** Regex guard blocks 70 percent of paraphrases, but the set was used to write the patterns | `docs/risk/RED_TEAM.md` | Confirmation and approval gates held in every test |
| R4 PII in output or logs | **Partly mitigated.** Rule-based redaction, 0 leaks on the test set | `docs/risk/DPIA.md` | Not Presidio; untested on real messages |
| R5 Synthetic data judged unrealistic | **Materialised for the risk model.** Label is synthetic; AUC 0.72 is a method check | `docs/model-cards/risk.md` | Intent accuracy 1.0 on synthetic tickets is a template artefact |
| R6 GPU unavailable | **Materialised.** CUDA wheel failed; fine-tune ran on CPU, with frozen embeddings and 3 epochs | `docs/model-cards/intent.md` | Intent targets missed (0.8935 vs 0.92) |
| R7 Cloud cost | **Not applicable yet.** Nothing deployed to a cloud | n/a | |
| R8 Licence | **Open.** Banking77 mirror licence to verify; CFPB blocked | `docs/DATA_LICENCES.md` | |
| R9 Over-claiming | **Mitigated by process.** Claims in docs are tied to result files | `docs/LOG.md` | Several earlier numbers were superseded and are noted |
| R10 Judge disagrees with humans | **Partly mitigated.** Judge built on a hosted model; agreement 0.90 with a rule (kappa 0.70), but no human labels yet | `ml/eval/results/llm_eval.json` | Human-labelled kappa still open. Judge had 2 false approvals in 50 |
| R11 Arabic much worse than English | **Partly mitigated.** Combined index brings Arabic from recall 0.40 to 0.90 on 10 questions | `docs/product/EXPERIMENTS.md` EXP-003 | Machine-written translations, five policies only |
| R12 Burnout or falling behind | **Materialised in scope, not in effort.** Work continued across many sessions | n/a | Cut list below |

### New risks found during the build

| ID | Risk | L | I | Mitigation | Residual |
|---|---|---|---|---|---|
| NR1 | Cross-customer access through client-supplied card or transaction IDs | Was high before the fix | High | Ownership checks in the API (403), tested | Low |
| NR2 | Threads and SQLite: API crash under load | Was high before the fix | Medium | Lock and cross-thread connection (`services/assistant/checkpoint.py`) | Low; load-tested at 300 requests |
| NR3 | Lexical retrieval cannot handle Arabic | Was certain | High | Tokenizer change and combined index (ADR 0007) | Medium |
| NR4 | Action requests (freeze, address change) go to humans in triage | Certain | Low | Conservative default (ADR 0008) | Low; design choice |
| NR5 | Model promotion without meeting targets | Low | High | Registry gate refuses promotion (tested; refused the current model) | Low |
| NR6 | Fine-tune run crashed under memory pressure | Happened twice | Medium | Run alone; frozen embeddings; logged in `docs/LOG.md` | Low |

### Cut list (what was not done, and why)

- LoRA fine-tune and LLM router (Week 8): no usable GPU. A hosted model now exists for evaluation (ADR 0014) but no cost comparison has been run.
- Kubernetes deployment, Terraform, AWS (Week 11): no cluster, no cloud account on this machine. The Helm chart lints and renders but is not deployed.
- Human-labelled kappa (Week 6): the judge is built and measured against a rule, but no people have labelled answers.
- CFPB complaint data (Week 2): blocked from this machine.
- Demo video (Week 12): not produced.
- Keras or TensorFlow baseline (Week 3): not started.
- OpenTelemetry exporter: spans are created but not exported to a backend.
