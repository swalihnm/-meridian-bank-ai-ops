"""Keras baseline for the intent comparison (Week 3, plan requirement).

A small dense network on TF-IDF features, trained on the same Banking77 splits as the
DistilBERT model and the TF-IDF logistic regression. Run in the TensorFlow environment
(.venv-keras), which does not include PyTorch:

    .venv-keras\\Scripts\\python.exe -m ml.intent.keras_baseline

Writes ml/intent/results/keras_baseline.json. Metrics come from the official test split, used once.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np  # noqa: E402
import tensorflow as tf  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402

from ml.intent.banking77 import load_banking77  # noqa: E402
from ml.intent.metrics import accuracy, macro_f1  # noqa: E402

RESULTS = Path("ml/intent/results/keras_baseline.json")
SEED = 42
MAX_FEATURES = 20_000
EPOCHS = 20
BATCH = 64


def main() -> None:
    tf.keras.utils.set_random_seed(SEED)
    splits = load_banking77(seed=SEED)
    n_classes = len(splits.label_names)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, max_features=MAX_FEATURES)
    x_train = vectorizer.fit_transform(splits.train_text).toarray().astype(np.float32)
    x_val = vectorizer.transform(splits.val_text).toarray().astype(np.float32)
    x_test = vectorizer.transform(splits.test_text).toarray().astype(np.float32)

    model = tf.keras.Sequential(
        [
            tf.keras.Input(shape=(x_train.shape[1],)),
            tf.keras.layers.Dense(256, activation="relu"),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.Dense(n_classes, activation="softmax"),
        ]
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    early = tf.keras.callbacks.EarlyStopping(
        monitor="val_accuracy", patience=3, restore_best_weights=True
    )
    history = model.fit(
        x_train,
        splits.train_label,
        validation_data=(x_val, splits.val_label),
        epochs=EPOCHS,
        batch_size=BATCH,
        callbacks=[early],
        verbose=0,
    )

    pred = np.argmax(model.predict(x_test, verbose=0), axis=1).astype(np.int64)
    np.save(RESULTS.parent / "keras_test_pred.npy", pred)
    result = {
        "model": "keras dense on tf-idf (256 hidden, dropout 0.3)",
        "epochs_run": len(history.history["loss"]),
        "best_val_accuracy": float(max(history.history["val_accuracy"])),
        "test_accuracy": accuracy(splits.test_label, pred),
        "test_macro_f1": macro_f1(splits.test_label, pred, n_classes),
        "tensorflow_version": tf.__version__,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
