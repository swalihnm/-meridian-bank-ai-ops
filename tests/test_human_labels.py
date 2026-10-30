"""Tests for the human-labelling scorer: kappa maths and reading a filled sheet."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ml.eval.human_labels import FIELDS, score
from ml.eval.llm_eval import cohen_kappa


def test_kappa_perfect_and_chance() -> None:
    assert cohen_kappa([True, False, True, False], [True, False, True, False]) == pytest.approx(1.0)
    # Half agreement on balanced classes is chance level: kappa 0.
    assert cohen_kappa([True, True, False, False], [True, False, True, False]) == pytest.approx(0.0)


def test_score_reads_a_filled_sheet(tmp_path: Path) -> None:
    # Two labelled rows from the real golden set (R001 cites the expected POL-001; R004 is wrong).
    sheet = tmp_path / "sheet.csv"
    with sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "id": "R001",
                "question": "",
                "answer": "",
                "cited_policy": "POL-001",
                "policy_text": "",
                "human_label": "CORRECT",
                "judge": "SUPPORTED",
                "notes": "",
            }
        )
        writer.writerow(
            {
                "id": "R004",
                "question": "",
                "answer": "",
                "cited_policy": "POL-003",
                "policy_text": "",
                "human_label": "INCORRECT",
                "judge": "NOT_SUPPORTED",
                "notes": "",
            }
        )
    result = score(sheet)
    assert result["n_labelled"] == 2
    assert result["agreement_human_vs_programmatic"] == 1.0
    assert result["kappa_human_vs_judge"] == 1.0


def test_score_rejects_a_bad_label(tmp_path: Path) -> None:
    sheet = tmp_path / "bad.csv"
    with sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "id": "R001",
                "question": "",
                "answer": "",
                "cited_policy": "POL-001",
                "policy_text": "",
                "human_label": "maybe",
                "judge": "",
                "notes": "",
            }
        )
    with pytest.raises(SystemExit):
        score(sheet)
