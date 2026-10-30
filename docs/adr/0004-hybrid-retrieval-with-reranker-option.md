# 0004: Hybrid retrieval with an optional reranker

**Status:** Accepted for the index, reranker not enabled by default, 2026-10-29.

## Context
Policy questions need the right policy in the top results and a correct citation. Lexical search misses paraphrases; dense search misses rare exact terms.

## Decision
- BM25 and dense embeddings, fused by reciprocal rank fusion (`services/assistant/rag/retrieval.py`).
- The cross-encoder reranker is available but **not** enabled: EXP-001 showed a recall gain that is not significant (p = 0.25) and no citation gain.
- The API and the scenario gate use a lexical index (BM25) so they run without model downloads. The dense path is used in offline evaluation.

## Consequences
- The product is currently lexical-only in production (`services/api/app.py`). Dense retrieval needs the model in the container image, which is not done.
- Re-test the reranker on a larger, independent question set before enabling it.
