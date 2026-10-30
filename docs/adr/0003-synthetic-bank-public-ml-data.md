# 0003: Synthetic bank data with public datasets for ML

**Status:** Accepted, 2026-10-28.

## Context
No real customer data is available, and it could not be used for a portfolio project in any case. The ML parts need realistic text.

## Decision
- The bank, customers, accounts, transactions, cards and policies are synthetic and seeded (`data/generator/`, `data/policies/`).
- Intent classification uses Banking77 (public text). The loader uses a Parquet mirror because the original repo ships only a loading script (`ml/intent/banking77.py`).
- Synthetic labels are used only where no public label exists (dispute risk, synthetic tickets). Every such result is labelled as a method check.

## Consequences
- Claims about real-world accuracy can only come from Banking77 (and the reviewed Arabic set, once it exists).
- The risk model's AUC is a check that the pipeline recovers a planted signal, not evidence of real performance.
