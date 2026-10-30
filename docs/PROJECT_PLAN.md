# Meridian: AI-Native Customer Operations Platform for a Digital Bank

A 12-week portfolio project for Abdulla Swalih NM, owned like a real product.

---

## 0. How to use this file

1. Put this file in the root of a new repo as `docs/PROJECT_PLAN.md`.
2. Copy Section 14 into a `CLAUDE.md` file at the repo root so Claude Code knows the rules.
3. Work week by week (Section 8). Do not skip the product documents; they are what make this different from your other projects.
4. At the end of each week, update `docs/LOG.md` with what you built, what broke, and the numbers you measured.
5. Only put a claim on your resume if the number is in the repo and you can reproduce it.

---

## 1. Why this project

You already have strong engineering projects (agents, RAG, evals, credit risk, treasury). Your gap on recent job descriptions is **proof of product ownership** and a few **platform skills** (Spark, Kubernetes, fine-tuning, feature store, A/B testing, infrastructure as code).

Meridian closes both gaps in one project, and it is built to be reused for the next 12 months of applications:

| Target role | What Meridian proves |
|---|---|
| Revolut: Applied AI Engineer (product-owner flavour) | Vision, roadmap, success metrics, AI assistant and automation platform, deep learning, launch from scratch |
| Dubai banking AI/ML (Finance/Treasury) | RAG, agents with MCP, fine-tuning, MLOps, drift, governance, Spark, Kubernetes, feature store |
| Oliver Wyman (AWS-first) | AWS deployment with infrastructure as code, agent checkpointing |
| Echelon (Riyadh) | Arabic and English, regulated-domain RAG, client-style engagement write-up |
| SAP and enterprise roles | Integration into existing enterprise systems, guardrails, observability, handover documentation |

---

## 2. The product in one paragraph

**Meridian** is the AI layer a fictional digital bank ("Meridian Bank") uses to run customer operations. Customers chat in English or Arabic. An AI assistant answers policy questions with citations, and, with strict controls, performs actions such as freezing a card or opening a dispute. A second system (the **automation platform**) triages incoming tickets, classifies intent, scores risk, drafts replies for human agents, and routes the hard cases. Operations leads get a dashboard showing the product metrics, experiment results and model health.

You play three roles: **product owner** (vision, roadmap, metrics, risk), **ML engineer** (models, evaluation, deployment) and **platform engineer** (data, infrastructure, monitoring).

### Fictional bank, real data
- The bank, its customers and its policies are **synthetic**. Say so clearly in the README.
- Use real public datasets for the ML parts (verify each licence before use):
  - **Banking77** (77 banking intents, public on Hugging Face) for intent classification.
  - **CFPB Consumer Complaint Database** (US regulator, public) for complaint text, categories and routing.
  - A **synthetic transactions and tickets generator** that you write (seeded, reproducible) for customer, account and transaction data.
- Write 30 to 50 synthetic policy documents (fees, card disputes, limits, KYC, fraud, refunds, account closure) in English, then translate and review a core subset into Arabic.

---

## 3. Keyword coverage map (all target job descriptions)

Every keyword below must trace to a module and a piece of evidence in the repo.

### 3.1 Revolut Applied AI Engineer

| JD keyword | Where it lives in Meridian | Evidence to produce |
|---|---|---|
| Product vision, strategy, roadmap | `docs/product/` (vision, strategy, roadmap) | One-page vision, quarterly roadmap with now/next/later |
| Day-to-day operations, project execution | Weekly log, sprint board | `docs/LOG.md`, GitHub Projects board |
| Risk assessment | Risk register + red-team report | `docs/risk/RISK_REGISTER.md`, `docs/risk/RED_TEAM.md` |
| Cross-functional collaboration, senior management | Monthly exec memos written as if to leadership | `docs/product/exec-memos/` (3 memos) |
| LLMs and ML | Assistant, intent classifier, risk model | Model cards with numbers |
| AI assistants and AI automation platform | Customer assistant + ticket triage automation | Two deployed services |
| Goals, success metrics, roadmap | Metric tree, OKRs, targets set before building | `docs/product/METRICS.md` |
| Measurable results under ambiguity | Experiment log with decisions | `docs/product/EXPERIMENTS.md` |
| Developing and launching AI from scratch | Public demo + launch checklist + post-launch review | Live URL, `docs/product/LAUNCH.md` |
| Python, SQL | Whole stack | Code |
| TensorFlow, Keras, PyTorch | PyTorch fine-tuning of intent model; Keras or TensorFlow baseline | `ml/intent/` |
| Version control, model deployment, developer environments | Git workflow, CI/CD, devcontainer, registry | `.github/`, `.devcontainer/` |
| Mathematics and statistics | Power analysis, significance tests, calibration, uncertainty | `docs/product/STATS_NOTES.md` |
| Entrepreneurial drive | You scope, ship and measure it yourself | The whole repo |

### 3.2 Dubai banking AI/ML (Finance/Treasury)

| JD keyword | Where it lives |
|---|---|
| Prompt engineering, RAG, embeddings, vector search | `services/assistant/rag/` (hybrid BM25 + pgvector, reranker) |
| Fine-tuning or adapting foundation models | `ml/finetune/` (LoRA on a small open model, e.g. Llama or Mistral class, on tickets) |
| Agentic workflows, orchestrator and sub-agents | LangGraph orchestrator with specialist sub-agents |
| Tool calling, MCP, guardrails, human-in-the-loop | MCP server for bank tools, approval gates, kill-switch |
| ML pipelines, feature engineering | `ml/pipelines/` with Spark and Feast |
| CI/CD for ML, versioning, retraining, A/B testing, drift monitoring | MLflow registry, scheduled retraining, drift jobs, experiment engine |
| Feature stores | Feast (offline Parquet/Delta, online Redis) |
| Latency, throughput, cost optimisation | Load tests, caching, model routing, cost dashboard |
| Observability, logging, alerting | OpenTelemetry, Prometheus, Grafana, alert rules |
| Responsible AI: fairness, explainability, privacy | Fairness slices, SHAP, Presidio, DPIA-style assessment |
| Spark, Databricks, Delta Lake | PySpark jobs writing Delta tables (local, or Databricks free edition if available) |
| Kubernetes, Docker | `kind` cluster locally, Helm charts, then a cloud deploy |
| Streaming and event-driven | Kafka (or Redpanda) ticket stream |
| Distributed training, GPU optimisation | Free Colab or Kaggle GPU for the LoRA run; mixed precision, batch tuning, documented honestly |
| Model risk, red-teaming, DPIA | `docs/risk/` |
| Evaluation of non-deterministic GenAI | Golden sets, LLM-as-judge, regression gates |
| Cost and latency for LLM apps | Cost per resolved conversation, p95 latency tracked |

### 3.3 Other roles
- **AWS-first:** Terraform or AWS CDK deploy to ECS Fargate or EKS, S3, Bedrock, Secrets Manager. Agent state checkpointing in Postgres (Oliver Wyman).
- **Arabic and Gulf:** bilingual assistant, Arabic eval set, dialect and Arabizi test cases (Echelon, Dubai, Riyadh).
- **Enterprise integration (SAP-style):** adapters to a mock core-banking API and a mock CRM, plus a handover pack for an operations team.

---

## 4. Product documents (write these first, keep them updated)

These are the missing piece on your resume. Treat them as real deliverables.

1. **Vision and strategy** (1 page): who the users are, the problem, why now, what you will not build.
2. **Users and jobs to be done:** customers, support agents, operations leads, compliance reviewer.
3. **North-star metric and metric tree:**
   - North star: **cost per correctly resolved case** (blend of automation rate, accuracy and cost).
   - Inputs: automation rate, containment without harm, first-contact resolution, escalation precision, p95 latency, cost per conversation, customer satisfaction proxy (LLM-judge plus human spot check).
   - Guardrail metrics: wrong-action rate, PII leak rate, unsafe-answer rate, hallucinated-policy rate.
4. **Targets set in week 1, before building** (you will report against these honestly, including misses).
5. **Roadmap:** now / next / later, with what you cut and why.
6. **Experiment log:** hypothesis, metric, sample size, result, decision.
7. **Risk register:** likelihood, impact, owner, mitigation, residual risk.
8. **Launch plan and post-launch review.**
9. **Three exec memos** (weeks 4, 8, 12): half a page each, written to a senior leader: status, metrics versus targets, risks, decisions needed.

---

## 5. System architecture

```
Customer (EN/AR chat)                 Ticket stream (email/app/complaint)
        |                                      |
   Web chat (Next.js)                    Kafka/Redpanda topic
        |                                      |
   API gateway (FastAPI) -------- Guardrails: input guard, PII redaction (Presidio),
        |                          injection defence, rate limits, kill-switch
        v                                      v
 Assistant orchestrator (LangGraph)     Triage pipeline (consumer)
   |- Policy RAG agent  ---> hybrid retrieval (BM25 + pgvector) + reranker + citation check
   |- Account-action agent ---> MCP server (bank tools) ---> mock core banking API
   |- Escalation agent  ---> human agent console (approval, edit, send)
   |- Checkpoints (Postgres) so runs resume after failure
        |                                      |
        +------------- Model layer -----------+
          Intent classifier (PyTorch, fine-tuned)
          Risk/dispute model (LightGBM + SHAP)
          LoRA-tuned small model (reply drafting, tested vs hosted LLM)
          LLM router (cheap model first, strong model when needed)
        |
 Data platform: Spark + Delta (batch), Feast (features), Postgres, Redis
        |
 MLOps: MLflow registry, GitHub Actions CI/CD, scheduled retraining, drift jobs
        |
 Observability: OpenTelemetry traces, Prometheus metrics, Grafana dashboards, alerts
        |
 Experiment engine: assignment, logging, stats (power, tests, CUPED optional)
        |
 Infra: Docker, Kubernetes (kind then cloud), Terraform/CDK, secrets manager
```

### Services
| Service | Purpose |
|---|---|
| `services/api` | FastAPI gateway, auth (JWT), rate limits, kill-switch, feature flags |
| `services/assistant` | LangGraph orchestrator, RAG, tool calls via MCP |
| `services/mcp-bank` | MCP server exposing bank tools with policy and audit |
| `services/triage` | Kafka consumer: classify, score, route, draft |
| `services/experiments` | Variant assignment, event logging, analysis |
| `services/mockbank` | Fake core-banking and CRM APIs (the "existing enterprise system") |
| `apps/chat` | Customer chat UI (EN/AR, RTL) |
| `apps/console` | Agent console and operations dashboard |
| `ml/` | Training, evaluation, fine-tuning, pipelines |
| `infra/` | Docker, Helm, Terraform/CDK |

### Bank tools exposed through MCP (all audited, all permissioned)
`get_balance`, `list_transactions`, `explain_fee`, `freeze_card` (needs confirmation), `open_dispute` (needs confirmation and agent approval above a threshold), `update_address` (blocked without verification), `request_human_agent`. No tool can move money. State this as a design rule.

---

## 6. Tech stack

- **Languages:** Python 3.11+, TypeScript.
- **LLM and agents:** LangGraph, MCP (Python SDK), Hugging Face Transformers and PEFT, one hosted LLM API for the strong model, Ollama or vLLM for the small model.
- **Retrieval:** Postgres + pgvector, BM25, cross-encoder reranker.
- **ML:** PyTorch (intent model), a Keras or TensorFlow baseline for comparison, scikit-learn, LightGBM, SHAP.
- **Data:** PySpark, Delta Lake, Feast, Kafka or Redpanda, Postgres, Redis, dbt for analytics models.
- **MLOps:** MLflow, GitHub Actions, Docker, Kubernetes (`kind`, Helm), Terraform or AWS CDK.
- **Observability:** OpenTelemetry, Prometheus, Grafana, Langfuse or equivalent for LLM traces.
- **Quality:** pytest, hypothesis, ruff, mypy, Playwright, pre-commit.
- **Cloud:** AWS (ECS Fargate or EKS, S3, Bedrock, Secrets Manager). Optionally add an Azure variant later.

---

## 7. Evaluation and responsible AI (non-negotiable)

- **Golden sets:** 300+ English and 150+ Arabic conversations with expected behaviour, including **failure cases** (must refuse, must escalate, must not act).
- **Metrics:** intent accuracy and macro-F1, retrieval recall@k, citation correctness, answer faithfulness (LLM-judge, with a human-labelled subset and Cohen's kappa), action correctness, escalation precision and recall, p50 and p95 latency, cost per conversation.
- **Regression gate:** CI fails if any guardrail metric worsens beyond a set tolerance. Nightly full eval.
- **Safety:** prompt-injection suite (direct, indirect through retrieved documents, tool-output injection), PII leak tests, jailbreak tests in English, Arabic, Gulf dialect and Arabizi.
- **Fairness and slices:** report accuracy and escalation rate by language, channel and complaint category. Document gaps; do not hide them.
- **Explainability:** SHAP for the risk model; citations and reasoning traces for the assistant.
- **Statistics:** pre-register hypotheses, compute sample sizes, use confidence intervals, correct for multiple comparisons, report effect sizes. Be clear which experiments are **offline replay or simulated users**, not real traffic.
- **Honesty rules:** state every limitation in the model cards. A documented miss is worth more than a hidden one.

---

## 8. Twelve-week plan

Each week has deliverables and an acceptance check. Plan for roughly 15 to 20 hours per week. If you fall behind, cut from the "stretch" items, never from the product documents or evaluation.

### Phase 1: Product foundation (Weeks 1 to 2)

**Week 1: Define the product and set targets**
- Write vision, users, jobs to be done, metric tree, targets, first roadmap, risk register v1.
- Set up the repo, devcontainer, CI skeleton, pre-commit, `CLAUDE.md`, GitHub Projects board.
- Build the synthetic data generator design (schema for customers, accounts, transactions, tickets).
- **Acceptance:** targets are written down and committed before any model exists; CI runs lint and tests on an empty skeleton.

**Week 2: Data, mock bank and baseline**
- Build `mockbank` (balances, transactions, cards, disputes) and the seeded data generator (100k customers, a few million transactions).
- Load Banking77 and CFPB data; write data validation (pandera or Great Expectations).
- Baseline intent classifier (TF-IDF + logistic regression) with a measured score.
- **Acceptance:** `make data` rebuilds everything from seed; baseline score recorded in MLflow.

### Phase 2: Models and GenAI core (Weeks 3 to 6)

**Week 3: Deep learning intent model**
- Fine-tune a transformer in PyTorch on Banking77 plus synthetic tickets; add a Keras or TensorFlow baseline for comparison.
- Mixed precision, learning-rate sweep, early stopping, calibration (temperature scaling), confusion analysis.
- **Acceptance:** model beats the baseline; calibration (ECE) reported; model card v1.

**Week 4: Policy RAG and exec memo 1**
- Write policy documents, chunk, embed, index in pgvector, add BM25 hybrid, reranker, citation verification.
- Retrieval eval set; tune chunking and k.
- Write **exec memo 1** (status, metrics versus targets, risks).
- **Acceptance:** recall@5 and citation correctness measured; unsupported claims are blocked.

**Week 5: Assistant orchestrator, MCP tools and guardrails**
- LangGraph orchestrator with RAG, account-action and escalation agents.
- MCP server `mcp-bank` with permissions, confirmation steps, audit log (hash-chained).
- Input guard, Presidio PII redaction, kill-switch, daily budget cap.
- Checkpointing in Postgres so interrupted runs resume.
- **Acceptance:** 20+ adversarial prompts blocked; a killed run resumes from its checkpoint; no tool can move money.

**Week 6: Evaluation harness and LLM-as-judge**
- Golden sets (EN first), scenario suite with failure cases, LLM-as-judge validated against human labels (kappa).
- CI regression gate and nightly eval.
- **Acceptance:** CI blocks a deliberately broken prompt change; judge kappa reported.

### Phase 3: Platform and MLOps (Weeks 7 to 9)

**Week 7: Data platform (Spark, Delta, Feast, Kafka)**
- PySpark jobs build features into Delta tables; Feast serves offline and online features.
- Kafka topic streams tickets; the triage service consumes, classifies, scores risk and drafts replies.
- Risk/dispute model (LightGBM + SHAP) using the feature store; fairness slices.
- **Acceptance:** end-to-end stream to triage works; feature parity between training and serving is tested.

**Week 8: Fine-tuning, routing, cost and exec memo 2**
- LoRA-fine-tune a small open model for reply drafting on a Colab or Kaggle GPU; compare against the hosted LLM on quality, latency and cost.
- Build the LLM router (cheap first, escalate to strong) and measure cost per resolved case.
- Write **exec memo 2**.
- **Acceptance:** a table of quality, p95 latency and cost per 1,000 conversations for each model option; router decision justified with data.

**Week 9: MLOps: registry, retraining, drift and observability**
- MLflow registry with staging and production stages; GitHub Actions promotes a model only if it passes gates.
- Scheduled retraining job; drift monitoring (PSI, embedding drift, retrieval drift); simulate a drift event and show detection and response.
- OpenTelemetry traces, Prometheus metrics, Grafana dashboards, alert rules.
- **Acceptance:** a simulated drift triggers an alert and a retraining run; dashboards show latency, cost, error and quality.

### Phase 4: Product experiments and deployment (Weeks 10 to 11)

**Week 10: Experiments and Arabic**
- Experiment engine: variant assignment, event logging, power calculation, significance tests, guardrail checks.
- Run at least **three experiments** (for example prompt A vs B, small model vs hosted model, with vs without reranker) using replayed and simulated traffic. Log decisions in `EXPERIMENTS.md`.
- Add Arabic: bilingual UI with RTL, Arabic golden set, dialect and Arabizi cases, per-language metrics.
- **Acceptance:** each experiment has a hypothesis, sample size, result with confidence interval and a ship/no-ship decision.

**Week 11: Deploy to Kubernetes and AWS**
- Helm charts, `kind` cluster for local; Terraform or CDK to AWS (ECS Fargate or EKS, S3, Secrets Manager, Bedrock).
- Load test (k6 or Locust), tune for p95 latency and cost; blue/green or canary rollout with automatic rollback on guardrail breach.
- **Acceptance:** public demo URL; load test report; rollback demonstrated.

### Phase 5: Launch and story (Week 12)

**Week 12: Governance, launch and portfolio**
- Model cards for every model, DPIA-style assessment, final red-team report, risk register v3.
- Launch checklist, post-launch review (what worked, what missed, what next), **exec memo 3**.
- 3-minute demo video, architecture diagram, README with a results table, ADRs for the main decisions.
- Resume and interview pack (Section 11).
- **Acceptance:** a stranger can clone, run `make demo`, and reproduce the headline numbers.

### Stretch goals (only if ahead)
- Voice channel (speech-to-speech on Bedrock Nova Sonic), reusing your earlier voice work.
- Multi-region data residency demo (UAE and KSA flavoured policy rules).
- CUPED variance reduction and sequential testing in the experiment engine.
- Azure variant (Azure OpenAI, AI Search, AKS) for an Azure-first employer.
- Semantic caching and prompt compression experiments.

---

## 9. Repository structure

```
meridian/
  CLAUDE.md
  README.md
  Makefile
  docs/
    PROJECT_PLAN.md          # this file
    LOG.md                   # weekly log
    product/
      VISION.md  USERS.md  METRICS.md  ROADMAP.md  EXPERIMENTS.md
      LAUNCH.md  STATS_NOTES.md  exec-memos/
    risk/
      RISK_REGISTER.md  RED_TEAM.md  DPIA.md
    model-cards/
    adr/                     # architecture decision records
  apps/        chat/  console/
  services/    api/  assistant/  mcp-bank/  triage/  experiments/  mockbank/
  ml/          intent/  risk/  finetune/  pipelines/  eval/
  data/        generator/  policies/  golden/
  infra/       docker/  helm/  terraform/  grafana/
  .github/workflows/
```

---

## 10. Definition of done (the project is finished when all are true)

- [ ] Public demo, README with results table, architecture diagram and demo video
- [ ] Product documents complete, with targets set in week 1 and reported against honestly
- [ ] Three exec memos written
- [ ] Intent model (PyTorch) with model card; Keras/TensorFlow baseline compared
- [ ] RAG with citation verification and measured retrieval quality
- [ ] Agent with MCP tools, human approval, audit log, kill-switch, checkpoint resume
- [ ] LoRA fine-tuned model compared with a hosted LLM on quality, latency and cost
- [ ] Spark and Delta pipeline, Feast feature store, Kafka stream
- [ ] MLflow registry, CI gates, scheduled retraining, simulated drift detected
- [ ] At least three experiments with decisions logged
- [ ] Arabic and English evaluated separately
- [ ] Kubernetes and AWS deployment with load test and rollback demonstrated
- [ ] Red-team report, DPIA-style assessment, risk register
- [ ] 300+ tests, CI green, `mypy --strict` and `ruff` clean

---

## 11. How to turn this into resume lines, cover letter points and interview stories

Fill in the real numbers at the end. Do not copy a template number you did not measure.

**Resume bullet templates**
- Owned an AI-native bank operations product end to end (vision, roadmap, metrics, launch): [X]% of tickets automated at [Y]% accuracy, cost per resolved case down [Z]% against a [baseline].
- Fine-tuned [model] with LoRA on [N] tickets; matched [Z]% of hosted-LLM quality at [A]% of the cost and [B] ms lower p95 latency.
- Built an experiment engine and ran [N] experiments (power analysis, confidence intervals, guardrail metrics); shipped [N] changes and rejected [N] on evidence.
- Built an MCP-based agent platform with human approval, audit log, kill-switch and checkpoint resume; [N]/[N] adversarial prompts blocked.
- Built Spark + Delta + Feast pipelines and MLflow-gated retraining; detected a simulated drift event within [N] minutes.
- Deployed to Kubernetes and AWS with canary rollout and automatic rollback; p95 latency [X] ms at [Y] requests per second.

**Cover letter paragraph (adapt per role)**
"To show how I work as a product owner, I built Meridian, an AI operations platform for a digital bank, from vision and metrics through launch. I set targets before building, ran experiments with logged decisions, and report where I missed them."

**Interview stories to prepare (use the STAR format)**
1. A target you missed and what you decided.
2. An experiment you rejected on the evidence.
3. A guardrail failure the red-team found and how you fixed it.
4. A trade-off between cost, latency and quality, and the data behind your choice.
5. What you would do with a team and a real roadmap.

**Be honest in interviews:** it is a solo project with synthetic bank data and simulated traffic. Say what is real (public datasets, real models, real deployment) and what is simulated. Recruiters respect that.

---

## 12. Risks and how to manage scope

| Risk | Mitigation |
|---|---|
| Scope too large for 12 weeks | Phase 1 to 3 are the core; cut stretch goals and the Azure variant first |
| Spending too long on UI | Use a simple component library; the product value is in the logic, metrics and evidence |
| GPU access for fine-tuning | Use free Colab or Kaggle GPU; keep the model small; document the limits |
| Cloud cost | Use budgets and alerts; tear down after demos; keep a local `kind` fallback |
| Synthetic-data criticism | Label it clearly; use real public datasets for ML; focus claims on method and evidence |
| Claiming too much on the resume | Only claim what the repo can prove |
| Licence issues on datasets and models | Check and record every licence in `docs/DATA_LICENCES.md` |
| Burnout or falling behind | Keep a weekly log; the minimum viable version is Phases 1 to 3 plus one experiment |

---

## 13. Minimum viable version (if you only have 6 weeks)

Keep: product documents, intent model, RAG, MCP agent with guardrails, evaluation harness, one experiment, a Docker-based deploy, README and demo video.
Cut: Spark/Delta/Feast, Kubernetes, fine-tuning, Arabic, load testing.
Expected effect on applications: stronger product-ownership proof, but fewer platform keywords.

---

## 14. Paste this into `CLAUDE.md`

```
# Project: Meridian (AI-native bank operations platform)
Read docs/PROJECT_PLAN.md first. Follow the current week's plan.

Rules
- Synthetic bank, public datasets for ML. Never present synthetic results as real-world.
- No tool may move money. Every action tool is audited and permissioned.
- Write the test or eval first for anything user-facing or safety-related.
- Every model gets a model card with numbers and limitations.
- Every claim in the README must be reproducible with `make <target>`.
- Keep ruff and mypy --strict clean; CI must stay green.
- Record decisions as ADRs in docs/adr and log weekly progress in docs/LOG.md.
- Targets in docs/product/METRICS.md are set in week 1 and never edited to match results;
  add a dated note if a target changes.
- Never hard-code secrets; use env vars and a secrets manager.
- Prefer small, reviewable commits. Explain failures honestly in the log.

Working style
- At the start of each week: restate the deliverables and acceptance checks.
- At the end of each week: run the evals, update METRICS and LOG, list what is left.
```

---

## 15. Suggested first prompts for Claude Code

1. "Read docs/PROJECT_PLAN.md and CLAUDE.md. Create the repo skeleton from Section 9 with a Makefile, devcontainer, pre-commit, CI workflow and empty service folders. Do not write feature code yet."
2. "Help me write docs/product/VISION.md, USERS.md and METRICS.md. Ask me questions one at a time, propose targets with reasoning, and wait for my approval before writing."
3. "Build the seeded synthetic data generator for customers, accounts, transactions and tickets, with a schema, validation tests and `make data`."
4. "Implement the baseline intent classifier on Banking77, log it to MLflow, and write the model card v0."

Continue in the same pattern each week: plan, ask, build, evaluate, document.
