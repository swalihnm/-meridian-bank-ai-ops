# 0009: PII redaction stays rule-based (Presidio not adopted)

**Status:** Accepted, 2026-10-29. Decided without the owner, who asked for the work to be finished without stopping for decisions. Revisit if real customer data is ever used.

## Context
The plan calls for Microsoft Presidio. Presidio's default recognisers rely on a spaCy language model, which is downloaded at install time. That download could not be verified on this machine, and the model is large.

## Decision
Keep the rule-based redactor in `services/assistant/guardrails.py`. It covers Emirates IDs, UAE phone numbers, emails, UAE IBANs (checked with mod-97) and card numbers (checked with Luhn). Tests cover each rule and a control case (`tests/test_assistant_safety.py`).

## Consequences
- Names and free-text addresses are not redacted. The assistant does not ask for them, but a customer can type them.
- The rules were tested on a small set written by the project, not on real messages.
- Adopting Presidio later means replacing `redact_pii` behind the same signature.
