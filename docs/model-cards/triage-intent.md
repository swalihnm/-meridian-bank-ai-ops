# Model card: ticket intent (triage), logistic regression on synthetic tickets

**Version:** v1, 2026-10-29. Code: `services/triage/build.py`, `services/triage/pipeline.py`.

## Intended use
Label incoming tickets with one of eight synthetic intents to decide routing. A low-confidence label goes to a human (threshold 0.5).

## Data
Synthetic tickets from `data/generator/tickets.py`, built from hand-written templates with light noise. Training uses seed 1000 plus the build seed; the Kafka evaluation uses seed 99, which is held out.

## Results
- Held-out synthetic tickets (500, through Redpanda): intent accuracy **1.0**.

## Why this number means nothing
The templates are few and fixed, so a linear model separates the classes almost perfectly. Accuracy of 1.0 shows the pipeline runs end to end. **It is not evidence that the classifier would work on real tickets.** Real tickets would need Banking77-style text and a labelled sample from the bank.

## Limits
- Eight synthetic intents only; the Banking77 model is a different label set.
- Arabic tickets: the tokenizer now handles Arabic, but the training templates are almost all English.
- Routing thresholds (0.5 confidence, risk 0.5) were chosen by the author, not calibrated.
