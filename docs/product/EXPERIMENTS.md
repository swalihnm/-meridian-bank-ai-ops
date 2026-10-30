# Experiment log

Every experiment is recorded here with its hypothesis, metric, sample size, result and decision. Experiments are **offline replay or simulated users** unless stated otherwise. Statistical method is in [STATS_NOTES.md](STATS_NOTES.md).

## Template

```
### EXP-000: <short name>
- Date registered:           (before the run)
- Hypothesis:                "If we change X, metric Y will move by at least Z."
- Primary metric:            
- Guardrail metrics:         
- Variants:                  A (control) vs B
- Sample size and power:     (alpha 0.05, power 0.8, minimum detectable effect)
- Traffic type:              replay | simulated users
- Result:                    effect size, 95% CI, p-value (if used), slice breakdown
- Guardrail outcome:         
- Decision:                  ship | no-ship | iterate
- Reason:                    
```

## Planned experiments (Week 10)
1. Prompt A vs prompt B for the policy assistant.
2. Small model vs hosted model for reply drafting.
3. Retrieval with vs without reranker.

## Registered experiments

### EXP-002: Two-match abstain rule (offline replay)
- Date registered: 2026-10-28, written just before the run and after the Week 6 scenario suite exposed the bug. This is not a strict pre-registration: the hypothesis was formed with the failure in view.
- Hypothesis: requiring two matched content words before answering reduces out-of-scope answers without losing in-scope correct answers.
- Primary metric: out-of-scope questions answered (lower is better). Target: 0.
- Guardrail: in-scope answered-and-correct count, paired McNemar test.
- Variants: A (control) abstains only when under 20 percent of question words match; B requires two matched words, or at least half the question.
- Traffic type: offline replay, BM25 retrieval, retrieval golden set (70 questions: 60 in scope, 10 out of scope).
- Sample size and power: not computed for this run. With 70 questions the test can only detect large changes; the result below is therefore weak evidence.
- Result: out-of-scope answered 1 to 0. In-scope correct 41 to 39 (2 discordant pairs, both lost under B). McNemar exact p = 0.5. Treatment in-scope correct 95% CI 52% to 76%.
- Traffic caveat: the golden set was also used to find the bug, so this is not a clean holdout.
- Decision: ship B. The safety cost is the design goal: an abstain hands the customer to a human (POL-028). The 2 lost answers are recorded as a known cost to re-check on a larger set.

### EXP-001: Cross-encoder reranker on hybrid retrieval (offline replay, paired)
- Date registered: 2026-10-29, before the run. Hypothesis and design were written in `ml/eval/exp001_reranker.py` before the run.
- Hypothesis: the reranker improves recall@5 over hybrid retrieval.
- Primary metric: recall@5 on 60 in-scope questions. Secondary: citation correctness.
- Variants: A hybrid (BM25 + dense, RRF); B the same plus the cross-encoder reranker on the top 20.
- Traffic type: offline replay, paired by question. The golden set was written by hand for this project.
- Result: recall@5 0.933 to 0.983; discordant pairs 0 (A only) and 3 (B only); exact McNemar p = 0.25; treatment 95% CI 0.91 to 1.00. Citation correct 0.783 to 0.750; discordant 3 (A only) and 1 (B only); p = 0.63.
- Decision: no-ship on the evidence we have. The recall gain is not significant, and citation correctness, the metric the product depends on, gets slightly worse. The reranker adds cost and latency. Re-test on a larger, independent set before deciding.

### EXP-003: Combined English and Arabic policy index (offline replay, BM25)
- Date registered: 2026-10-29, written after the Arabic evaluation showed the gap. Not a strict pre-registration.
- Hypothesis: one index holding English and Arabic policy chunks answers Arabic questions without hurting English answers.
- Primary metric: Arabic recall@5 and citation correctness on 10 in-scope Arabic questions (the same 5 policies in both languages).
- Guardrails: English recall@5 and citation correctness on the full 60-question English set; out-of-scope answered (English 10 questions, Arabic 3).
- Variants: A English-only index (today); B combined index.
- Traffic type: offline replay. Arabic golden set is 13 questions written by the project; translations not native-speaker reviewed.
- Result, Arabic: A recall 0.40, citation 0.00. B recall 0.90 (95% CI 0.60 to 0.98), citation 0.90.
- Result, English, full set: A recall 0.867, citation 0.65, answered 0.833. B recall 0.883, citation 0.65, answered 0.85. No regression.
- Result, English, 5-policy subset: citation 0.80 (A) and 0.70 (B), one question out of 10. Within noise, and the full-set result is the better guardrail.
- Out-of-scope: 0 of 10 English and 0 of 3 Arabic questions answered under B.
- Decision: ship B (wired into the API and the scenario gate). Arabic results are small-sample and use machine-written translations; re-test with a reviewed set.
