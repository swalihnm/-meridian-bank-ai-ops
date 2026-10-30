# Model card: policy retrieval and answer (RAG, extractive)

**Version:** v1, 2026-10-28. Code: `services/assistant/rag/`. Results: `ml/eval/results/retrieval.json`, `ml/eval/results/exp002_abstain.json`.

## Intended use
Answer customer questions about the 30 synthetic Meridian policies, with the policy ID cited. Abstain and hand over to a human (POL-028) when no policy answers the question.

**Out of scope:** any question outside the policy set, legal or investment advice (POL-030), and any real customer's account.

## Components
- Chunking: two-sentence windows, one-sentence overlap, policy ID kept on each chunk.
- Retrieval: BM25 (lexical) fused with dense embeddings (`sentence-transformers/all-MiniLM-L6-v2`, mean pooled) by reciprocal rank fusion. Optional cross-encoder reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
- Answer: **extractive**. The best matching sentences from the top policy. No generator is used yet, so the hallucination risk sits in retrieval and abstention, not in generation.
- Citation check: each answer sentence must share at least 60 percent of its content words with the cited policy. Extractive answers pass by construction; the check becomes meaningful when a generator is added.
- Abstain rule: needs two matched content words, or half the question (EXP-002).

## Evaluation data
- Retrieval golden set: 60 in-scope and 10 out-of-scope questions, written by hand for this project. Some questions were written after looking at the policy wording, so the set is not independent of the policies.
- Scenario set (`data/golden/scenarios_en.jsonl`): 25 end-to-end scenarios, 5 of them policy questions.

## Results (re-run 2026-10-29, current abstain rule)

| Configuration | recall@5 | MRR | Citation correct (in scope) | Abstain on out-of-scope |
|---|---|---|---|---|
| BM25 only | 0.867 | 0.772 | 0.650 | 1.00 |
| Dense only | 0.950 | 0.897 | 0.700 | 1.00 |
| Hybrid (RRF) | 0.933 | 0.895 | 0.783 | 1.00 |
| Hybrid + reranker | 0.983 | 0.917 | 0.750 | 1.00 |

**Against targets (docs/product/METRICS.md):**
- Recall@5 at least 0.85: met by all four configurations.
- Citation correct at least 0.95: **not met** by any configuration (best 0.78).
- Hallucinated-policy rate at most 2 percent (G4), measured as out-of-scope questions answered: **met** on this set (0 of 10 answered). In-scope questions that the assistant abstains on are counted as misses in citation correctness, not as hallucinations.

**Note on earlier numbers:** the first run (before the abstain fix) reported citation correct 0.85 for hybrid and out-of-scope abstain 0.80. Those figures are superseded. The abstain fix traded some in-scope answers for safety: hybrid in-scope answer rate fell from 0.98 to 0.90.

## Experiments on this configuration
- EXP-001 (reranker, paired, 60 in-scope questions): recall@5 0.933 to 0.983, 3 questions gained, 0 lost, McNemar p = 0.25. Citation correct 0.783 to 0.750, 1 gained, 3 lost, p = 0.63. The reranker helps recall, not significantly, and does not help citation. See `docs/product/EXPERIMENTS.md`.
- EXP-002 (abstain rule, BM25): see `docs/product/EXPERIMENTS.md`.

## Known weaknesses (from the scenario suite)
- A dispute-timing question abstained (S004): the wording did not match POL-006 lexically.
- A card-limit question with a card number removed cited the card-replacement policy (S021).
- A fee question cited the ATM policy (S023).
These are lexical misses. The hybrid and reranker configurations were not used in the scenario suite, so the scenario results describe BM25 only.

## Gulf dialect and Arabizi (plan target L2: at least 80 percent)

8 hand-written questions (4 Gulf dialect in Arabic script, 4 Arabizi). Result: **1 of 8 correct (12.5 percent). Target not met.** The one correct answer is a dialect question that shares its key word with the policy. The other seven were refused (low query overlap), so the assistant handed them to a human rather than answering wrongly. Refusal is the safe failure, but it means these customers are not served. Measured in `ml/eval/results/arabic_dialect.json`. Not tuned against this set: a synonym list written from the same questions would overfit.

## Generated answers from a hosted model (evaluation only)

`ml/eval/llm_eval.py`, model gpt-oss:20b via Ollama's hosted API. Excerpts are the top 3 BM25 policies. Results in `ml/eval/results/llm_eval.json`.

- Prompt v2 (current): citation correct 0.78 (47 of 60 in-scope). Unsupported sentences 1.6 percent, against a 2 percent target. Met. The v1 prompt gave 10.7 percent unsupported. Caveat: the check is word overlap, so this rewards close copying.
- Out-of-scope: 0 of 10 answered.
- Not in the customer answer path (ADR 0014).

## Limitations
- Golden set is small (70). Confidence intervals on citation correctness are wide: at n = 60, roughly plus or minus 0.09.
- English only. The Arabic policy subset and Arabic eval set are not built yet (Week 10).
- No generator, so answer fluency is not measured.
