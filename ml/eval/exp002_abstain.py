"""EXP-002: does requiring two matched content words before answering reduce wrong answers?

Design: offline replay on the retrieval golden set with BM25 (deterministic, no model download).
- Control (A): the old rule, abstain only when less than 20 percent of question words match.
- Treatment (B): the new rule, two matched words, or at least half of the question.
Primary metric: out-of-scope questions answered (lower is better).
Guardrail: in-scope answered-and-correct count, compared with a paired McNemar test.
The golden set was also used to find this bug, so this is a sanity check, not a clean holdout.

Run: python -m ml.eval.exp002_abstain   (writes ml/eval/results/exp002_abstain.json)
"""

from __future__ import annotations

import json
from pathlib import Path

from ml.eval.retrieval_eval import GOLDEN_PATH, POLICY_PATH, Case, load_golden
from services.assistant.rag.answer import compose_answer
from services.assistant.rag.chunking import load_chunks
from services.assistant.rag.lexical import BM25Index
from services.experiments.stats import mcnemar_exact, wilson_interval

RESULTS_PATH = Path("ml/eval/results/exp002_abstain.json")
# Control never satisfies min_matches, so it abstains on the ratio alone (the old rule).
CONTROL_MATCHES, CONTROL_SHARE = 10_000, 0.2
TREATMENT_MATCHES, TREATMENT_SHARE = 2, 0.5


def outcome(index: BM25Index, case: Case, min_matches: int, min_share: float) -> bool:
    """True when the assistant answers and the answer is correct (for in-scope)
    or answers at all (for out-of-scope, where answering is the error)."""
    hits = index.search(case.question, k=5)
    answer = compose_answer(case.question, hits, min_matches=min_matches, min_share=min_share)
    if case.expected_policy is None:
        return answer.answered
    return answer.answered and answer.citations[0].policy_id == case.expected_policy


def main() -> None:
    cases = load_golden(GOLDEN_PATH)
    index = BM25Index(load_chunks(POLICY_PATH, window=2, overlap=1))
    in_scope = [c for c in cases if c.expected_policy is not None]
    out_scope = [c for c in cases if c.expected_policy is None]

    a_correct = [outcome(index, c, CONTROL_MATCHES, CONTROL_SHARE) for c in in_scope]
    b_correct = [outcome(index, c, TREATMENT_MATCHES, TREATMENT_SHARE) for c in in_scope]
    b_only = sum(1 for a, b in zip(a_correct, b_correct, strict=True) if b and not a)
    a_only = sum(1 for a, b in zip(a_correct, b_correct, strict=True) if a and not b)

    oos_a = sum(outcome(index, c, CONTROL_MATCHES, CONTROL_SHARE) for c in out_scope)
    oos_b = sum(outcome(index, c, TREATMENT_MATCHES, TREATMENT_SHARE) for c in out_scope)

    result = {
        "hypothesis": (
            "Two-match rule reduces out-of-scope answers without losing in-scope correct answers."
        ),
        "traffic": "offline replay, BM25, golden set (hand-written, also used to find the bug)",
        "control_oos_answered": oos_a,
        "treatment_oos_answered": oos_b,
        "n_out_of_scope": len(out_scope),
        "control_in_scope_correct": sum(a_correct),
        "treatment_in_scope_correct": sum(b_correct),
        "n_in_scope": len(in_scope),
        "discordant_control_only": a_only,
        "discordant_treatment_only": b_only,
        "mcnemar_p": mcnemar_exact(a_only, b_only),
        "treatment_in_scope_ci95": wilson_interval(sum(b_correct), len(in_scope)),
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(result, indent=2, default=list), encoding="utf-8")
    print(json.dumps(result, indent=2, default=list))


if __name__ == "__main__":
    main()
