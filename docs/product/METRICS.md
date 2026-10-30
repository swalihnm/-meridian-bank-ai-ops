# Metrics and targets

**Status:** PROPOSED, 2026-10-28. Not yet approved by the product owner. Approve or amend before Week 2 starts, then commit.

**Rule (from CLAUDE.md):** targets are set in week 1 and are never edited to match results. If a target changes, add a dated note under "Change log" below, with the reason.

Targets are written before any model exists, so each one is a guess reasoned from public benchmarks and the product's risk appetite. Where a number is a guess, the reasoning says so.

---

## 1. North-star metric

**Cost per correctly resolved case (CPRC)**

```
CPRC = (total model + infra + human-review cost) / (cases resolved with correct outcome)
```

- A case is "resolved" when the customer's need is met without a human having to redo the work.
- "Correct" is judged on the golden set and by LLM-judge with a human spot check (see section 4).
- Baseline: not known until Week 2 (the mock bank has no real traffic). Recorded in the first LOG entry after the baseline is built.

## 2. Metric tree

```
CPRC (north star)
├── Automation rate (share of conversations the assistant or triage handles end to end)
│   ├── Containment without harm (automated AND correct AND no guardrail breach)
│   └── Escalation precision (escalated cases that truly needed a human)
├── Accuracy of resolved cases (judge score plus human spot check)
│   ├── Intent macro-F1
│   ├── Retrieval recall@5
│   └── Citation correctness
├── Cost per conversation (model tokens, infra, human review time)
└── Latency (p50 and p95, assistant and triage separately)

Guardrails (any breach blocks release)
├── Wrong-action rate
├── PII leak rate
├── Unsafe-answer rate
└── Hallucinated-policy rate
```

## 3. Targets (proposed)

Each target shows the threshold, what it measures, and the reasoning. "Eval" means the offline golden set or simulated traffic, not live customers.

### 3.1 North star and product

| ID | Metric | Target | Reasoning |
|---|---|---|---|
| T1 | Containment without harm (eval) | >= 40% of in-scope conversations by Week 11 | Policy questions and simple actions are a large share of contacts in most banks; 40% is a stretch, not a promise. Real share is unknown until measured. |
| T2 | Accuracy of resolved cases (judge + human spot check) | >= 92% | A resolved case that is wrong costs more than it saves. Set high on purpose. |
| T3 | CPRC reduction vs human-only baseline | >= 30% | Enough to justify the system; the baseline is the cost of the same cases handled by humans in the model. |

### 3.2 Model quality

| ID | Metric | Target | Reasoning |
|---|---|---|---|
| T4 | Intent accuracy on Banking77 test (fine-tuned PyTorch) | >= 92% | Published fine-tuned transformer results on Banking77 are in the low 90s; TF-IDF plus logistic regression is typically lower. Beat the baseline by a clear margin. |
| T5 | Intent macro-F1 on Banking77 test | >= 0.91 | Macro-F1 punishes rare intents, so it is the stricter number. |
| T6 | Calibration (ECE) after temperature scaling | <= 0.05 | Needed for the escalation threshold to mean anything. |
| T7 | Retrieval recall@5 on policy eval set | >= 0.85 | Citations are useless if the right passage is not retrieved. |
| T8 | Citation correctness (cited passage supports the claim) | >= 95% | This is the hallucination control; judged by LLM-judge plus human subset. |
| T9 | Escalation recall on must-escalate scenarios | >= 95% | Missing an escalation is a harm; false escalations only cost time. |
| T10 | Escalation precision on escalated cases | >= 80% | Enough to keep agents trusting the routing. |
| T11 | Risk model AUC (dispute or fraud-proxy label, synthetic) | >= 0.80 | Synthetic labels; value is in method and explainability, not the number. Label as synthetic. |

### 3.3 Guardrails (hard limits)

| ID | Metric | Target | Reasoning |
|---|---|---|---|
| G1 | Wrong-action rate (any action tool called wrongly) | 0 on the adversarial and action suites | No tool can move money; a single wrong action is a release blocker. |
| G2 | PII leak rate (PII in output or logs, eval set) | 0 | Presidio redaction plus tests; any leak blocks release. |
| G3 | Unsafe-answer rate (judge-labelled) | <= 1% | Strict but achievable for scoped policy answers. |
| G4 | Hallucinated-policy rate (claims not in any policy document) | <= 2% | Measured on the RAG eval. |
| G5 | Adversarial prompts blocked (injection, jailbreak, direct and indirect) | >= 95% of the suite; 100% for action-level attacks | Week 5 acceptance asks for 20+ blocked; this sets the proportion. |

### 3.4 Operations and cost

| ID | Metric | Target | Reasoning |
|---|---|---|---|
| O1 | Assistant p95 latency (end to end) | <= 4 s | Chat users tolerate a few seconds with streaming. |
| O2 | Triage p95 latency (ticket to draft) | <= 10 s | Batch-like; not customer-facing. |
| O3 | Cost per conversation (assistant, hosted-LLM path) | <= USD 0.05 | Provisional. Re-set in Week 8 when router and LoRA costs are measured. |
| O4 | Uptime of the demo during evaluation week | >= 99% | Demo credibility. |

### 3.5 Language

| ID | Metric | Target | Reasoning |
|---|---|---|---|
| L1 | Arabic intent and retrieval quality vs English | Gap <= 5 points | Parity is the claim; a gap must be reported if it exists. |
| L2 | Dialect and Arabizi test cases passed | >= 80% | Honest target; these are hard. |

## 4. Measurement notes

- **Offline replay and simulated users only.** No live customer traffic. Every result says which.
- **LLM-as-judge** is validated against a human-labelled subset; agreement is reported as Cohen's kappa (target kappa >= 0.6, set in Week 6).
- **Confidence intervals** are reported on every headline number.
- **Slices** (language, channel, complaint category) are reported for every metric; gaps are documented, not hidden.

## 5. Change log

| Date | Target | Change | Reason |
|---|---|---|---|
| 2026-10-28 | All | Initial proposal | Week 1 |
