# Model card: dispute risk model (LightGBM)

**Version:** v1, 2026-10-28. Code: `ml/risk/model.py`. Results: `ml/risk/results/risk_model.json`.

## Intended use
Score customers for dispute propensity so the triage queue can prioritise review and explain its reasons (SHAP). Scores support routing; they do not decide credit or block customers.

**Out of scope:** credit decisions (VISION.md), any automated action on an account, use on real customers.

## Data
- Synthetic bank, 20,000 customers, seed 42 (`data/generator/generate.py`).
- Features (10): accounts held, transaction count, mean absolute amount, shares of online, ATM, travel and transfer-out transactions, total salary income, and segment flags.
- Country and language are **not** model inputs. They are used only to slice metrics.

## Label: SYNTHETIC, not real outcomes
The synthetic data has no dispute outcomes. The label is drawn from a documented, seeded logistic rule (`SYNTHETIC_WEIGHTS` in `ml/risk/model.py`) plus noise, with the intercept set for a 15 percent base rate.

This means the metrics below check that the pipeline recovers a signal we planted. **They say nothing about real-world accuracy.**

## Results (test split, 20 percent, stratified)

| Metric | Value |
|---|---|
| AUC, test | 0.724 |
| Positive rate (base rate) | 0.151 |

**Fairness slices (AUC by group):**

| Slice | Group | AUC |
|---|---|---|
| Country | AE | 0.735 |
| Country | SA | 0.702 |
| Language | ar | 0.733 |
| Language | en | 0.718 |

Gaps are 3 to 4 AUC points. Sample sizes per slice are not yet reported and confidence intervals are not computed, so no fairness claim is made beyond "measured and not large on this synthetic label".

**Explanations (mean absolute SHAP, top 5):** share_online 0.64, share_travel 0.60, share_atm 0.30, income_total 0.11, mean_abs_amount 0.11. The ranking matches the planted rule, as expected for this check.

## Development history (kept on purpose)
- First rule (weights 3.0, 2.0, 1.0): AUC **0.536**. The signal was too weak for the label noise, so the rule was changed.
- Second rule (weights 12.0, 12.0, 6.0, recalibrated intercept): AUC **0.724**.
The change was made to the data-generating rule after seeing the first result. It is a method check, so this is a development choice to report, not a tuned result.

## Limitations
- Labels are synthetic. Real dispute behaviour will differ in ways this card cannot show.
- No calibration check yet. Scores are not calibrated probabilities.
- No drift monitoring on the risk model yet (see `ml/pipelines/drift.py` and Week 9).
- Single seed, single split. No confidence interval on AUC.
