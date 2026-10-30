# 0005: SQLite checkpoints now, Postgres later

**Status:** Accepted, 2026-10-28. Partly superseded when a Postgres container is added.

## Context
The plan asks for Postgres checkpoints so runs resume after failure. The Postgres container is not part of the local stack yet, and tests should not need a database server.

## Decision
`services/assistant/checkpoint.py` uses SQLite with the same interface. It is thread-safe because FastAPI calls sync endpoints from worker threads (a real bug found by the API tests).

## Consequences
- Crash-and-resume is tested (`test_crash_after_act_resumes_without_proposing_twice`).
- Moving to Postgres is a change to one class. The pgvector index is also not built yet.
