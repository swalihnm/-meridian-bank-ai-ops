# 0013: Drift-triggered retraining, promoted only through the gate

**Status:** Accepted, 2026-10-29.

## Context
Plan Week 9 asks for scheduled retraining, drift detection, and a simulated drift event that triggers detection and response.

## Decision
`ml/pipelines/retrain.py` detects drift with PSI on message length and on the intent mix, retrains only when a significant drift is found, and evaluates the new model with the same gate as every other model. Retraining does not promote anything by itself.

## Consequences
- The simulated drift event (PSI 7.19 on message length, 1.03 on intent mix) triggers a retrain. The retrained model fails the gate, correctly.
- The incoming stream cannot be used as training data: it uses synthetic intent names with no mapping to Banking77's 77 labels. Retraining is therefore on the original training split only. A real pipeline needs a labelling step first.
- The schedule is not running. The job is a script; a cron or CI schedule is not set up.
