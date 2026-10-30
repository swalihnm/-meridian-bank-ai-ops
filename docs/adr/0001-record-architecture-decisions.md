# 0001: Record architecture decisions

**Status:** Accepted, 2026-10-28.

## Context
Meridian makes many choices that will be questioned later: which LLM to use, how retrieval is built, what is allowed to act. Without a record, the reasons are lost.

## Decision
Each significant decision gets a short numbered file in `docs/adr/`, using this format:

- **Status**, **Context**, **Decision**, **Consequences**.
- Numbered in order; never renumbered. Superseded decisions are marked, not deleted.

## Consequences
- Decisions are reviewable in the same way as code.
- Interview stories (PLAN Section 11) can point to specific ADRs.

## Early decisions to record (planned)
- 0002: No tool may move money (design rule, PLAN Section 5).
- 0003: Synthetic bank data with public datasets for ML.
- 0004: Retrieval approach (hybrid BM25 and pgvector, reranker).
- 0005: Orchestration framework (LangGraph) and checkpoint store.
