"""Arabic evaluation for the policy assistant (Week 10, plan target L1 and L2).

Compares, on the same five core policies (POL-001, 003, 005, 009, 028):
- Arabic questions against the Arabic policy subset (POLICIES_AR.md)
- English questions for the same policies against the English subset (the parity baseline)
- Arabic questions against the full English index, which is what the product has today

Lexical retrieval only (BM25). The dense embedder is English-only, so it is not used for Arabic.
Writes ml/eval/results/arabic.json.

Translations are project-written and not yet reviewed by a native speaker.
Results describe those texts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ml.eval.retrieval_eval import GOLDEN_PATH, POLICY_PATH, Case, load_golden
from services.assistant.rag.answer import compose_answer
from services.assistant.rag.chunking import Chunk, load_chunks
from services.assistant.rag.lexical import BM25Index
from services.experiments.stats import wilson_interval

AR_POLICY_PATH = Path("data/policies/POLICIES_AR.md")
AR_GOLDEN_PATH = Path("data/golden/retrieval_ar.jsonl")
RESULTS_PATH = Path("ml/eval/results/arabic.json")
SUBSET = {"POL-001", "POL-003", "POL-005", "POL-009", "POL-028"}
K = 5


@dataclass
class Scores:
    n: int
    recall_at_5: float
    citation_correct: float
    answer_rate: float
    recall_ci95: tuple[float, float]


def _score(index: BM25Index, cases: list[Case]) -> Scores:
    in_scope = [c for c in cases if c.expected_policy is not None]
    recall_hits = 0
    correct = 0
    answered = 0
    for case in in_scope:
        hits = index.search(case.question, k=K)
        if case.expected_policy in [h.chunk.policy_id for h in hits]:
            recall_hits += 1
        answer = compose_answer(case.question, hits)
        if answer.answered:
            answered += 1
            if answer.citations[0].policy_id == case.expected_policy:
                correct += 1
    n = len(in_scope)
    return Scores(
        n=n,
        recall_at_5=recall_hits / n,
        citation_correct=correct / n,
        answer_rate=answered / n,
        recall_ci95=wilson_interval(recall_hits, n),
    )


def _subset(chunks: list[Chunk]) -> list[Chunk]:
    return [c for c in chunks if c.policy_id in SUBSET]


def _load_ar_golden() -> list[Case]:
    cases: list[Case] = []
    for line in AR_GOLDEN_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            cases.append(Case(row["id"], row["question"], row["expected_policy"]))
    return cases


def main() -> None:
    en_chunks = load_chunks(POLICY_PATH, window=2, overlap=1)
    ar_chunks = load_chunks(AR_POLICY_PATH, window=2, overlap=1)
    ar_cases = _load_ar_golden()
    en_cases = [c for c in load_golden(GOLDEN_PATH) if c.expected_policy in SUBSET]

    ar_index = BM25Index(ar_chunks)
    en_subset_index = BM25Index(_subset(en_chunks))
    en_full_index = BM25Index(en_chunks)
    # One index holding both languages: the candidate for the product.
    combined_index = BM25Index(en_chunks + ar_chunks)
    ar_out = [c for c in ar_cases if c.expected_policy is None]

    result = {
        "arabic_on_arabic_subset": _as_dict(_score(ar_index, ar_cases)),
        "english_on_english_subset": _as_dict(_score(en_subset_index, en_cases)),
        "arabic_on_full_english_index": _as_dict(_score(en_full_index, ar_cases)),
        "arabic_on_combined_index": _as_dict(_score(combined_index, ar_cases)),
        "english_on_combined_index": _as_dict(_score(combined_index, en_cases)),
        "arabic_out_of_scope_answered": {
            "index": "arabic_subset",
            "answered": sum(
                compose_answer(c.question, ar_index.search(c.question, k=K)).answered
                for c in ar_out
            ),
            "n": len(ar_out),
        },
        "note": (
            "Arabic golden set is 10 in-scope and 3 out-of-scope questions, written by the "
            "project. "
            "Translations are not native-speaker reviewed. Tokenization is lexical (no stemming), "
            "so inflected forms can miss."
        ),
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def _as_dict(s: Scores) -> dict[str, object]:
    return {
        "n": s.n,
        "recall_at_5": round(s.recall_at_5, 3),
        "recall_at_5_ci95": [round(s.recall_ci95[0], 3), round(s.recall_ci95[1], 3)],
        "citation_correct": round(s.citation_correct, 3),
        "answer_rate": round(s.answer_rate, 3),
    }


if __name__ == "__main__":
    main()
