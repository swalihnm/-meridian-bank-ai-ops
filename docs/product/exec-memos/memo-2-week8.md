# Executive memo 2: Meridian, Week 8

**Date:** 2026-10-29 (Week 8 as planned; written with the state at that point).
**To:** Senior operations leader.
**From:** Product owner, Meridian project.
**Status:** Red for the fine-tuning and routing work. Blocked, not failed in design.

## Status
- The fine-tuned intent classifier misses its targets: test accuracy 0.8935 against 0.92, macro-F1 0.8900 against 0.91. It does not beat a simple baseline (0.8896) by a significant margin (p = 0.53).
- A small Keras network on the same text features scores 0.9010 and beats the baseline significantly (p = 0.002). It is still below the 0.92 target.
- Calibration works: after temperature scaling, the expected calibration error is 0.016 against a 0.05 target.
- The planned step to fine-tune a small language model for drafting replies (LoRA) cannot run on this machine. The graphics card is too small, and the GPU build of the training library failed to install.
- The planned cost comparison between a hosted language model and the small one cannot be done: there is no hosted model key, so no real cost or quality numbers exist.

## Metrics against targets

| Metric | Target | Result | Met? |
|---|---|---|---|
| Intent accuracy (Banking77 test) | 0.92 | 0.8935 | No |
| Intent macro-F1 | 0.91 | 0.8900 | No |
| Calibration (ECE) | 0.05 | 0.016 | Yes |
| Cost and latency table for reply drafting | exists | not produced | No |

## Risks
- The intent model is not clearly better than the simple baseline, so it should not be used for routing without more work.
- Without a hosted model, we cannot tell how a drafting model would compare on quality or cost.
- Machine memory forced a smaller training setup, which may explain part of the accuracy gap.

## Decisions needed
1. Approve access to a GPU (cloud or workstation) for a fair fine-tune, or accept that the intent model stays a baseline.
2. Decide whether to fund a hosted language model key so the router and cost comparison can be measured.
3. Confirm that the intent model stays out of production routing until it beats the baseline on a paired test.
