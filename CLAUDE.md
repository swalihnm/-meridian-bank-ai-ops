# Project: Meridian (AI-native bank operations platform)
Read docs/PROJECT_PLAN.md first. Follow the current week's plan.

Rules
- Synthetic bank, public datasets for ML. Never present synthetic results as real-world.
- No tool may move money. Every action tool is audited and permissioned.
- Write the test or eval first for anything user-facing or safety-related.
- Every model gets a model card with numbers and limitations.
- Every claim in the README must be reproducible with `make <target>`.
- Keep ruff and mypy --strict clean; CI must stay green.
- Record decisions as ADRs in docs/adr and log weekly progress in docs/LOG.md.
- Targets in docs/product/METRICS.md are set in week 1 and never edited to match results;
  add a dated note if a target changes.
- Never hard-code secrets; use env vars and a secrets manager.
- Prefer small, reviewable commits. Explain failures honestly in the log.

Working style
- At the start of each week: restate the deliverables and acceptance checks.
- At the end of each week: run the evals, update METRICS and LOG, list what is left.
