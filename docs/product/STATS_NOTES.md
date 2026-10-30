# Statistics notes

Working notes on the statistical methods used in Meridian. Written so that any number in the repo can be checked.

## Principles
1. **Pre-register** each hypothesis, metric and sample size before running.
2. **Report effect sizes with 95% confidence intervals**, not only p-values.
3. **Correct for multiple comparisons** when a single experiment tests several slices or variants (Holm or Bonferroni; state which).
4. **Label the traffic type.** Offline replay and simulated users are not live customer behaviour.
5. **Report slices** (language, channel, complaint category). A gap is a finding, not something to hide.

## Methods (to be filled in as they are used)
- Sample size: two-proportion test, alpha 0.05, power 0.8. Formula and worked example to be added in Week 10.
- Intervals: Wilson score interval for proportions; bootstrap for F1 and other composite metrics.
- Calibration: expected calibration error (ECE) with equal-width bins; reported with bin count.
- Judge agreement: Cohen's kappa between LLM-judge and human labels.

## Open questions
- How many human-labelled items are needed for a stable kappa estimate? (Week 6.)
