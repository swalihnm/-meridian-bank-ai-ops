"""Week 3: fine-tune a transformer intent classifier (PyTorch) on Banking77.

Choices, all logged to MLflow:
- DistilBERT (small enough for a 4 GB GPU; the plan allows a small transformer).
- Mixed precision (fp16 autocast) on CUDA; falls back to fp32 on CPU.
- Linear warmup/decay, weight decay, early stopping on validation accuracy.
- Temperature scaling fitted on the VALIDATION split only, then ECE reported before and after.
- The official test split is used once, for the final reported numbers.

Run with `make finetune` (about 15 to 40 minutes on a GTX 1650 depending on settings).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import numpy.typing as npt
import torch
from scipy.special import softmax
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

from ml.intent.banking77 import IntentSplits, load_banking77
from ml.intent.metrics import (
    accuracy,
    expected_calibration_error,
    fit_temperature,
    macro_f1,
)

MODEL_ID = "distilbert-base-uncased"
EXPERIMENT = "meridian-intent"
ARTIFACT_DIR = Path("ml/intent/artifacts")


@dataclass(frozen=True)
class TrainConfig:
    model_id: str = MODEL_ID
    max_len: int = 64
    batch_size: int = 32
    lr: float = 5e-5
    weight_decay: float = 0.01
    epochs: int = 3
    freeze_embeddings: bool = True  # True on the 7 GB laptop; False on a GPU with enough memory
    patience: int = 1
    warmup_ratio: float = 0.06
    seed: int = 42


class TextDataset(Dataset[dict[str, torch.Tensor]]):
    def __init__(
        self,
        texts: list[str],
        labels: npt.NDArray[np.int64],
        tokenizer: Any,
        max_len: int,
    ) -> None:
        enc = tokenizer(texts, truncation=True, padding="max_length", max_length=max_len)
        self.input_ids = torch.tensor(enc["input_ids"])
        self.attention_mask = torch.tensor(enc["attention_mask"])
        self.labels = torch.tensor(labels)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, i: int) -> dict[str, torch.Tensor]:
        return {
            "input_ids": self.input_ids[i],
            "attention_mask": self.attention_mask[i],
            "labels": self.labels[i],
        }


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@torch.no_grad()
def predict_logits(
    model: torch.nn.Module, loader: DataLoader[dict[str, torch.Tensor]], device: torch.device
) -> npt.NDArray[np.float64]:
    model.eval()
    chunks = []
    for batch in loader:
        with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
            out = model(
                input_ids=batch["input_ids"].to(device),
                attention_mask=batch["attention_mask"].to(device),
            )
        chunks.append(out.logits.float().cpu().numpy())
    return np.concatenate(chunks).astype(np.float64)


def train(config: TrainConfig, splits: IntentSplits) -> dict[str, float]:
    torch.manual_seed(config.seed)
    device = _device()
    n_classes = len(splits.label_names)
    tokenizer: Any = AutoTokenizer.from_pretrained(config.model_id)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.model_id, num_labels=n_classes
    ).to(device)

    train_ds = TextDataset(splits.train_text, splits.train_label, tokenizer, config.max_len)
    val_ds = TextDataset(splits.val_text, splits.val_label, tokenizer, config.max_len)
    test_ds = TextDataset(splits.test_text, splits.test_label, tokenizer, config.max_len)
    train_loader = DataLoader(train_ds, batch_size=config.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=config.batch_size * 2)
    test_loader = DataLoader(test_ds, batch_size=config.batch_size * 2)

    # Freeze the word-embedding table: about a third of DistilBERT's parameters. This keeps
    # optimiser state within the memory of a 7 GB machine shared with other apps.
    if config.freeze_embeddings:
        for name, param in model.named_parameters():
            if "word_embeddings" in name:
                param.requires_grad = False
    trainable = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=config.lr, weight_decay=config.weight_decay)
    total_steps = len(train_loader) * config.epochs
    # transformers ships without type annotations for this function.
    scheduler = get_linear_schedule_with_warmup(  # type: ignore[no-untyped-call]
        optimizer, int(config.warmup_ratio * total_steps), total_steps
    )
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    best_acc, best_state, bad_epochs = -1.0, None, 0
    step_no = 0
    for epoch in range(config.epochs):
        model.train()
        for batch in train_loader:
            optimizer.zero_grad()
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
                loss = model(
                    input_ids=batch["input_ids"].to(device),
                    attention_mask=batch["attention_mask"].to(device),
                    labels=batch["labels"].to(device),
                ).loss
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            step_no += 1
            if step_no % 100 == 0:
                print(f"epoch {epoch} step {step_no} loss {loss.item():.4f}", flush=True)

        val_logits = predict_logits(model, val_loader, device)
        val_acc = accuracy(splits.val_label, val_logits.argmax(axis=1))
        mlflow.log_metric("val_accuracy", val_acc, step=epoch)
        if val_acc > best_acc:
            best_acc, bad_epochs = val_acc, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad_epochs += 1
            if bad_epochs > config.patience:
                break

    if best_state is None:
        raise RuntimeError("training produced no checkpoint")
    model.load_state_dict(best_state)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, ARTIFACT_DIR / "distilbert_intent.pt")

    # Calibration uses validation only.
    val_logits = predict_logits(model, val_loader, device)
    temperature = fit_temperature(val_logits, splits.val_label)
    test_logits = predict_logits(model, test_loader, device)
    raw_probs = softmax(test_logits, axis=1)
    cal_probs = softmax(test_logits / temperature, axis=1)
    pred = test_logits.argmax(axis=1)
    return {
        "best_val_accuracy": best_acc,
        "temperature": temperature,
        "test_accuracy": accuracy(splits.test_label, pred),
        "test_macro_f1": macro_f1(splits.test_label, pred, n_classes),
        "test_ece_raw": expected_calibration_error(raw_probs, splits.test_label),
        "test_ece_calibrated": expected_calibration_error(cal_probs, splits.test_label),
    }


def run(config: TrainConfig | None = None) -> dict[str, float]:
    cfg = config or TrainConfig()
    splits = load_banking77(seed=cfg.seed)
    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run(run_name="distilbert-finetune"):
        mlflow.log_params(
            {
                "model_id": cfg.model_id,
                "max_len": cfg.max_len,
                "batch_size": cfg.batch_size,
                "lr": cfg.lr,
                "epochs": cfg.epochs,
                "device": _device().type,
            }
        )
        metrics = train(cfg, splits)
        mlflow.log_metrics({k: v for k, v in metrics.items()})
    return metrics


if __name__ == "__main__":
    for name, value in run().items():
        print(f"{name}: {value:.4f}")
