"""Human labelling kit for the judge (Week 6).

Build the sheet, then compute agreement from the returns.

Step 1, `python -m ml.eval.human_labels build`:
  writes ml/eval/human/labelling_sheet.csv with 50 in-scope answers. Each row shows the
  question, the answer the assistant would give, and the policy text it cites.
  Reviewers fill in `human_label` with CORRECT or INCORRECT. Leave `notes` for anything unclear.

Step 2, `python -m ml.eval.human_labels score <filled_csv>`:
  computes agreement and Cohen's kappa between the human labels and the programmatic label (cited ==
  expected), and between the humans and any `judge` column. Writes ml/eval/results/human_kappa.json.

Two or more reviewers: fill separate copies, then run `score` on each. Inter-reviewer kappa is not
computed here yet, and should be added before the numbers are quoted.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from ml.eval.llm_eval import cohen_kappa
from ml.eval.retrieval_eval import GOLDEN_PATH, POLICY_PATH, load_golden
from services.assistant.rag.answer import compose_answer
from services.assistant.rag.chunking import load_chunks
from services.assistant.rag.lexical import BM25Index

SHEET = Path("ml/eval/human/labelling_sheet.csv")
RESULTS = Path("ml/eval/results/human_kappa.json")
SAMPLE = 50
FIELDS = [
    "id",
    "question",
    "answer",
    "cited_policy",
    "policy_text",
    "human_label",
    "judge",
    "notes",
]


def build() -> int:
    chunks = load_chunks(POLICY_PATH, window=2, overlap=1)
    index = BM25Index(chunks)
    policy_text: dict[str, str] = {}
    for c in chunks:
        policy_text[c.policy_id] = (policy_text.get(c.policy_id, "") + " " + c.text).strip()

    rows = []
    for case in load_golden(GOLDEN_PATH):
        if case.expected_policy is None:
            continue
        answer = compose_answer(case.question, index.search(case.question, k=5))
        if not answer.answered:
            continue
        cited = answer.citations[0].policy_id
        rows.append(
            {
                "id": case.id,
                "question": case.question,
                "answer": answer.text,
                "cited_policy": cited,
                "policy_text": policy_text[cited],
                "human_label": "",
                "judge": "",
                "notes": "",
            }
        )
        if len(rows) == SAMPLE:
            break

    SHEET.parent.mkdir(parents=True, exist_ok=True)
    with SHEET.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {SHEET}")
    return len(rows)


def score(path: Path) -> dict[str, object]:
    golden = {c.id: c for c in load_golden(GOLDEN_PATH)}
    with path.open(encoding="utf-8", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r["human_label"].strip()]
    if not rows:
        raise SystemExit("no human labels found in the file")

    human: list[bool] = []
    programmatic: list[bool] = []
    judge_pairs: list[tuple[bool, bool]] = []
    for r in rows:
        label = r["human_label"].strip().upper()
        if label not in {"CORRECT", "INCORRECT"}:
            raise SystemExit(
                f"row {r['id']}: human_label must be CORRECT or INCORRECT, got {label!r}"
            )
        is_correct = label == "CORRECT"
        human.append(is_correct)
        expected = golden[r["id"]].expected_policy
        programmatic.append(r["cited_policy"] == expected)
        if r.get("judge", "").strip():
            judge_pairs.append((is_correct, r["judge"].strip().upper().startswith("SUPPORTED")))

    n = len(human)
    result: dict[str, object] = {
        "n_labelled": n,
        "human_correct_share": round(sum(human) / n, 3),
        "agreement_human_vs_programmatic": round(
            sum(h == p for h, p in zip(human, programmatic, strict=True)) / n, 3
        ),
        "kappa_human_vs_programmatic": round(cohen_kappa(human, programmatic), 3),
    }
    if judge_pairs:
        hj = [h for h, _ in judge_pairs]
        jj = [j for _, j in judge_pairs]
        result["n_with_judge"] = len(judge_pairs)
        result["kappa_human_vs_judge"] = round(cohen_kappa(hj, jj), 3)
        result["agreement_human_vs_judge"] = round(
            sum(a == b for a, b in judge_pairs) / len(judge_pairs), 3
        )
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main(argv: list[str]) -> int:
    if argv[:1] == ["build"]:
        build()
        return 0
    if argv[:1] == ["score"] and len(argv) == 2:
        print(json.dumps(score(Path(argv[1])), indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
