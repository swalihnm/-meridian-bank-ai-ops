# Model card: intent classifier (DistilBERT, fine-tuned)

**Version:** v1, 2026-10-29. Code: `ml/intent/finetune.py`, metrics in `ml/intent/metrics.py`. Run: `make finetune`. Checkpoint: `ml/intent/artifacts/distilbert_intent.pt` (not committed).

## Intended use
Classify a customer message into one of the 77 Banking77 intents, as the first step of routing. Used for routing support only, not for any action on an account.

**Out of scope:** the assistant's own eight routes (`services/assistant/orchestrator.py`). The keyword router still does live routing. Wiring this model in is a later task.

## Data
- Banking77 (PolyAI, 77 intents), loaded from the Parquet mirror `legacy-datasets/banking77` because the original repo ships only a loading script. Same text and labels; see `docs/DATA_LICENCES.md`.
- Train 9,002 and validation 1,001, both carved from the official training split with a fixed seed (42), stratified. Test 3,080 is the official test split and was used once, for the final numbers only.

## Model and training
- `distilbert-base-uncased`, 66M parameters, with the word-embedding table frozen to fit in memory (see below).
- 3 epochs, batch 32, max length 64, AdamW, learning rate 5e-5, weight decay 0.01, linear warmup over 6 percent of steps.
- Early stopping on validation accuracy (patience 1). Best validation accuracy: 0.8971.
- Mixed precision was not used: the run was CPU-only (see Environment).
- Temperature scaling fitted on the validation split only. T = 0.6916.

## Results (official test split, 3,080 examples)

| Model | Accuracy | Macro-F1 | ECE (15 bins) |
|---|---|---|---|
| TF-IDF + logistic regression (baseline) | 0.8896 | 0.8897 | not measured |
| DistilBERT, raw | 0.8935 | 0.8900 | 0.132 |
| DistilBERT, temperature-scaled | 0.8935 | 0.8900 | 0.016 |

Accuracy 95% interval for the fine-tuned model (Wilson): about 0.88 to 0.91. The gap to the baseline (0.4 points) is inside that interval, so **the fine-tuned model does not clearly beat the baseline on accuracy in this run.** A paired test on per-example predictions has not been run yet.

**Against targets (docs/product/METRICS.md):**
- T4, accuracy at least 0.92: **not met** (0.8935).
- T5, macro-F1 at least 0.91: **not met** (0.8900).
- T6, ECE at most 0.05 after calibration: **met** (0.016).

## Environment and deviations from the plan
- The PyTorch CUDA install failed (MemoryError during download). Training ran on CPU on a 7 GB machine shared with other applications.
- The first two runs crashed (one segfault, one stall that turned out to be slow CPU training). Memory pressure from parallel jobs is the likely cause of the segfault. The final run ran alone.
- To fit memory, the word-embedding table was frozen and epochs were cut from 4 to 3. Both changes may cost accuracy; no ablation was run.

## Limitations
- Accuracy is not clearly above the TF-IDF baseline on this test set.
- Banking77 is English only. No Arabic evaluation exists for this model.
- Synthetic tickets (`data/generator/tickets.py`) use a different 8-label scheme and are not evaluated here.
- Single seed. No confidence interval beyond the binomial one above.
- Calibration was checked on the test split with ECE; a per-bin reliability plot has not been produced.

## Keras comparison and paired tests (Plan Week 3)

Run 2026-10-29. Same test split, predictions saved per example (`ml/intent/paired_compare.py`).

| Model | Test accuracy (95% Wilson CI) |
|---|---|
| TF-IDF + logistic regression | 0.8896 (0.878 to 0.900) |
| DistilBERT, fine-tuned (CPU, frozen embeddings, 3 epochs) | 0.8935 (0.882 to 0.904) |
| Keras dense network on TF-IDF (256 hidden, dropout 0.3, 11 epochs) | 0.9010 (0.890 to 0.911); macro-F1 0.9016 |

Exact McNemar tests on disagreeing examples:
- Keras vs TF-IDF: p = 0.0017. **Keras is significantly better than the baseline.**
- Keras vs DistilBERT: p = 0.19. Not significant.
- DistilBERT vs TF-IDF: p = 0.53. **The fine-tuned transformer did not beat the baseline.**

**Conclusion:** the simple Keras network is the best-supported intent model here, and the DistilBERT fine-tune is not an improvement on the baseline in this setup. Neither reaches the 0.92 accuracy target, so neither is promoted. The DistilBERT result may improve with the full recipe (unfrozen embeddings, 4 epochs, a hyperparameter search), which the memory limits ruled out. That has not been tested.

## GPU run (Kaggle T4, full recipe, 2026-10-30)

| Metric | Value | Target | Met? |
|---|---|---|---|
| Test accuracy | 0.9166 | 0.92 | No (by 0.0034) |
| Test macro-F1 | 0.9168 | 0.91 | Yes |
| ECE after temperature scaling (T = 0.834) | 0.0128 | 0.05 | Yes |

The promotion gate refuses this model on accuracy. The paired comparison against the Keras baseline is still to be run; it needs the checkpoint.

Paired comparison with the GPU checkpoint (test split, exact McNemar):
- DistilBERT (GPU, full recipe) 0.9166 vs Keras 0.9010: p = 0.0022.
- DistilBERT (GPU) vs TF-IDF 0.8896: p = 3.8e-7.

The GPU-trained transformer beats both baselines significantly. It still misses the 0.92 accuracy target by 0.0034; the 95% interval (0.906 to 0.926) includes 0.92.
