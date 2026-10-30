"""Load Banking77 (PolyAI, 77 banking intents) with a fixed, stratified validation split.

Licence and attribution: see docs/DATA_LICENCES.md. The official test split is never used
for training, tuning or temperature fitting; only for the reported scores.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from datasets import load_dataset
from sklearn.model_selection import train_test_split

# Parquet mirror of PolyAI/banking77 (the original repo ships only a loading script,
# which the datasets library no longer runs). Same text and labels; see docs/DATA_LICENCES.md.
DATASET_ID = "legacy-datasets/banking77"


@dataclass(frozen=True)
class IntentSplits:
    train_text: list[str]
    train_label: npt.NDArray[np.int64]
    val_text: list[str]
    val_label: npt.NDArray[np.int64]
    test_text: list[str]
    test_label: npt.NDArray[np.int64]
    label_names: list[str]


def load_banking77(val_fraction: float = 0.1, seed: int = 42) -> IntentSplits:
    raw = load_dataset(DATASET_ID)
    label_names = list(raw["train"].features["label"].names)
    train_text = list(raw["train"]["text"])
    train_label = np.asarray(raw["train"]["label"], dtype=np.int64)
    tr_text, va_text, tr_label, va_label = train_test_split(
        train_text,
        train_label,
        test_size=val_fraction,
        random_state=seed,
        stratify=train_label,
    )
    return IntentSplits(
        train_text=list(tr_text),
        train_label=np.asarray(tr_label, dtype=np.int64),
        val_text=list(va_text),
        val_label=np.asarray(va_label, dtype=np.int64),
        test_text=list(raw["test"]["text"]),
        test_label=np.asarray(raw["test"]["label"], dtype=np.int64),
        label_names=label_names,
    )
