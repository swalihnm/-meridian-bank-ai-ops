# Launch plan and checklist

**Status (2026-10-29): not launched.** This checklist records what is true today. Each item is marked done, partly done, or open, with a pointer to the evidence. No item is ticked by assumption.

## Gate: a launch to real customers needs every "must" item done

| # | Item | Type | Status | Evidence |
|---|---|---|---|---|
| 1 | Targets written before building | must | Done, but still PROPOSED. Owner has not approved them | `docs/product/METRICS.md` |
| 2 | Assistant safety gate passes in CI | must | Done (0 wrong actions, 0 PII leaks, escalation 1.0, injection 1.0 on 25 scenarios) | `ml/eval/scenario_eval.py`, CI workflow |
| 3 | Citation correctness at least 0.95 | must | **Open.** 0.78 | `docs/model-cards/assistant-retrieval.md` |
| 4 | Out-of-scope questions refused | must | Done on 10 English and 3 Arabic questions | `ml/eval/retrieval_eval.py`, `ml/eval/arabic_eval.py` |
| 5 | Customers told they are talking to an AI | must | **Open.** Not implemented | `docs/risk/DPIA.md` R6 |
| 6 | Data retention rule for chats and audit log | must | **Open.** Not implemented | `docs/risk/DPIA.md` section 4 |
| 7 | Customers can request their data or deletion | must | **Open.** Not implemented | `docs/risk/DPIA.md` section 4 |
| 8 | External red team | must | **Open.** Only the author has tested | `docs/risk/RED_TEAM.md` |
| 9 | Own card and transaction only (API ownership) | must | Done and tested (403) | `tests/test_api.py` |
| 10 | Kill-switch works | must | Done and tested | `tests/test_api.py` |
| 11 | Human handover on request and on complaint | must | Done and tested | `tests/test_assistant_safety.py` |
| 12 | No tool can move money | must | Done and tested | `tests/test_mockbank.py`, ADR 0002 |
| 13 | Model promoted only if it meets targets | must | Done (registry gate, refused the current model) | `ml/pipelines/registry.py` |
| 14 | Load test under realistic traffic | should | Partly done: local, single worker, assumed mix | `ml/eval/load_test.py` |
| 15 | Rollback path | should | Partly: kill-switch rollback drill run against the live local container (all 6 steps pass). Model rollback by alias not run | `ml/eval/rollback_drill.py`, `ml/eval/results/rollback_drill.json` |
| 16 | Monitoring and alerts live | should | Done for the local stack: Prometheus scrapes the API (up), 3 rules loaded, Grafana dashboard provisioned. Not a production stack | `ml/eval/stack_check.py`, `ml/eval/results/stack_check.json` |
| 17 | Arabic reviewed by a native speaker | should | **Open.** Machine-written translations | `data/policies/POLICIES_AR.md` |
| 18 | Licences of datasets and models verified | must | Partly: Hub licence tags checked (Banking77 CC BY 4.0; models Apache 2.0). Full licence text not read; CFPB blocked | `docs/DATA_LICENCES.md` |

**Result:** five must items are open (3, 5, 6, 7, 8), and item 18 is partly done. Should items 15 and 14 are partly done, item 17 is open, and item 16 is done for the local stack. **Do not launch.**

## Rollout plan (for when the gate is met)
1. Internal staff only, using synthetic data, for two weeks.
2. Pilot with a small group of consenting customers, human review of every draft, and a daily check of the citation and escalation metrics.
3. Full release only after the pilot meets the targets in `METRICS.md`, with a dated note for any change.
4. Rollback: the kill-switch (`POST /admin/kill`) pauses the assistant at once. Restore by `POST /admin/resume`. Rollback of a model is by alias: point `production` at the previous version.

## Post-launch review
Not applicable. Nothing has launched.

## What would be reviewed afterwards
- Which questions were wrongly answered, and which policies they cited.
- Escalation rate and whether handovers were needed.
- Any PII leak or wrong action, with its trace.
- Cost per resolved case, once a hosted model exists.
