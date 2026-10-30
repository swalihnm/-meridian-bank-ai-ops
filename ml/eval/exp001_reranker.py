"""EXP-001: does the cross-encoder reranker improve retrieval on the policy golden set?

Design: offline replay, paired by question. Both arms see the same 60 in-scope questions.
- Control (A): hybrid retrieval (BM25 + dense, RRF), top 5.
- Treatment (B): hybrid retrieval, then the cross-encoder reranker, top 5.
Primary metric: recall@5 (expected policy in the top 5), compared with a paired exact McNemar test.
Secondary: citation correctness (the composed answer cites the expected policy).

Run: python -m ml.eval.exp001_reranker   (writes ml/eval/results/exp001_reranker.json)
"""

from __future__ import annotations

import json
from pathlib import Path

from ml.eval.retrieval_eval import GOLDEN_PATH, POLICY_PATH, Case, load_golden, ranked
from services.assistant.rag.answer import compose_answer
from services.assistant.rag.chunking import load_chunks
from services.assistant.rag.retrieval import CrossEncoderReranker, HybridIndex, TransformerEmbedder
from services.experiments.stats import mcnemar_exact, wilson_interval

RESULTS_PATH = Path("ml/eval/results/exp001_reranker.json")


def paired_outcomes(
    index: HybridIndex, cases: list[Case], reranker: CrossEncoderReranker | None
) -> tuple[list[bool], list[bool]]:
    recall: list[bool] = []
    citation: list[bool] = []
    for case in cases:
        hits = ranked(index, case.question, use_dense=True, use_bm25=True, reranker=reranker)
        policies = [h.chunk.policy_id for h in hits]
        recall.append(case.expected_policy in policies)
        answer = compose_answer(case.question, hits)
        citation.append(answer.answered and answer.citations[0].policy_id == case.expected_policy)
    return recall, citation


def discordant(a: list[bool], b: list[bool]) -> tuple[int, int]:
    a_only = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
    b_only = sum(1 for x, y in zip(a, b, strict=True) if y and not x)
    return a_only, b_only


def main() -> None:
    cases = [c for c in load_golden(GOLDEN_PATH) if c.expected_policy is not None]
    index = HybridIndex(load_chunks(POLICY_PATH, window=2, overlap=1), TransformerEmbedder())
    reranker = CrossEncoderReranker()

    recall_a, cite_a = paired_outcomes(index, cases, reranker=None)
    recall_b, cite_b = paired_outcomes(index, cases, reranker=reranker)

    rec_a_only, rec_b_only = discordant(recall_a, recall_b)
    cit_a_only, cit_b_only = discordant(cite_a, cite_b)
    n = len(cases)
    result = {
        "hypothesis": "The cross-encoder reranker improves recall@5 over hybrid retrieval.",
        "traffic": "offline replay, 60 in-scope golden questions, paired",
        "n": n,
        "recall_at_5_control": sum(recall_a) / n,
        "recall_at_5_treatment": sum(recall_b) / n,
        "recall_discordant_control_only": rec_a_only,
        "recall_discordant_treatment_only": rec_b_only,
        "recall_mcnemar_p": mcnemar_exact(rec_a_only, rec_b_only),
        "recall_treatment_ci95": wilson_interval(sum(recall_b), n),
        "citation_control": sum(cite_a) / n,
        "citation_treatment": sum(cite_b) / n,
        "citation_discordant_control_only": cit_a_only,
        "citation_discordant_treatment_only": cit_b_only,
        "citation_mcnemar_p": mcnemar_exact(cit_a_only, cit_b_only),
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(result, indent=2, default=list), encoding="utf-8")
    print(json.dumps(result, indent=2, default=list))


if __name__ == "__main__":
    main()
