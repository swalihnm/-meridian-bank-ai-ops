"""Retrieval and answer evaluation for the policy assistant (Week 4).

Measures, for each retrieval configuration:
- recall@5 and MRR on in-scope questions (expected policy in the top 5 / reciprocal rank)
- answer rate and citation correctness (answer cites the expected policy)
- abstain rate on out-of-scope questions (should not answer)

Run with `make retrieval-eval`. Results are written to ml/eval/results/retrieval.json.
Golden set: data/golden/retrieval_en.jsonl. It was written by hand for this project, so it
measures how the system handles the questions WE thought of; see docs/LOG.md for the caveat.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from services.assistant.rag.answer import compose_answer
from services.assistant.rag.chunking import Chunk, load_chunks
from services.assistant.rag.lexical import Hit
from services.assistant.rag.retrieval import (
    CrossEncoderReranker,
    HybridIndex,
    TransformerEmbedder,
)

POLICY_PATH = Path("data/policies/POLICIES.md")
GOLDEN_PATH = Path("data/golden/retrieval_en.jsonl")
RESULTS_PATH = Path("ml/eval/results/retrieval.json")
K = 5


@dataclass(frozen=True)
class Case:
    id: str
    question: str
    expected_policy: str | None


def load_golden(path: Path) -> list[Case]:
    cases: list[Case] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            cases.append(Case(row["id"], row["question"], row["expected_policy"]))
    return cases


def ranked(
    index: HybridIndex,
    question: str,
    use_dense: bool,
    use_bm25: bool,
    reranker: CrossEncoderReranker | None,
) -> list[Hit]:
    """Top-K hits for one question, after the optional reranker."""
    hits = index.search(question, k=20, use_dense=use_dense, use_bm25=use_bm25)
    if reranker is not None:
        hits = reranker.rerank(question, hits)
    return hits[:K]


def evaluate(
    index: HybridIndex,
    cases: list[Case],
    use_dense: bool,
    use_bm25: bool,
    reranker: CrossEncoderReranker | None = None,
) -> dict[str, float]:
    in_scope = [c for c in cases if c.expected_policy is not None]
    out_scope = [c for c in cases if c.expected_policy is None]

    recall_hits = 0
    reciprocal_ranks: list[float] = []
    answered = 0
    correct_citations = 0
    for case in in_scope:
        hits = ranked(index, case.question, use_dense, use_bm25, reranker)
        policies = [h.chunk.policy_id for h in hits]
        if case.expected_policy in policies:
            recall_hits += 1
            reciprocal_ranks.append(1.0 / (policies.index(case.expected_policy) + 1))
        else:
            reciprocal_ranks.append(0.0)
        answer = compose_answer(case.question, hits)
        if answer.answered:
            answered += 1
            if answer.citations[0].policy_id == case.expected_policy:
                correct_citations += 1

    abstained = sum(
        1
        for case in out_scope
        if not compose_answer(
            case.question, ranked(index, case.question, use_dense, use_bm25, reranker)
        ).answered
    )

    return {
        "recall_at_5": recall_hits / len(in_scope),
        "mrr": sum(reciprocal_ranks) / len(in_scope),
        "answer_rate_in_scope": answered / len(in_scope),
        "citation_correct_in_scope": correct_citations / len(in_scope),
        "abstain_rate_out_of_scope": abstained / len(out_scope),
        "n_in_scope": float(len(in_scope)),
        "n_out_of_scope": float(len(out_scope)),
    }


def main() -> None:
    chunks: list[Chunk] = load_chunks(POLICY_PATH, window=2, overlap=1)
    cases = load_golden(GOLDEN_PATH)
    embedder = TransformerEmbedder()
    index = HybridIndex(chunks, embedder)
    reranker = CrossEncoderReranker()

    configs = {
        "bm25_only": (False, True, None),
        "dense_only": (True, False, None),
        "hybrid": (True, True, None),
        "hybrid_rerank": (True, True, reranker),
    }
    results = {
        name: evaluate(index, cases, use_dense=d, use_bm25=b, reranker=r)
        for name, (d, b, r) in configs.items()
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    for name, metrics in results.items():
        print(name, {k: round(v, 3) for k, v in metrics.items()})


if __name__ == "__main__":
    main()
