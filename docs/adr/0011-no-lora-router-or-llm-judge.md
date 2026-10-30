# 0011: No LoRA fine-tune, LLM router or LLM judge

**Status:** Accepted, 2026-10-29. Decided without the owner, under the instruction to take decisions where blocked.

## Context
- Week 8 asks for a LoRA fine-tune of a small open model for reply drafting, compared with a hosted model on quality, p95 latency and cost, and an LLM router built on the measured costs.
- Week 6 asks for an LLM judge validated against human labels with Cohen's kappa.
- This machine has no usable GPU (4 GB, and the CUDA wheel did not install). No hosted model key exists.

## Decision
Do not build the LoRA model, the router or the LLM judge. Record them as not done, with the reason.

## Why not a CPU stand-in
A small model trained on CPU, compared against nothing, would produce latency and quality numbers that look like evidence for a router decision. There would be no hosted comparator, so the router's "cheap first, escalate when needed" claim would be untestable. Better to say it is not done.

## Consequences
- The answer path is extractive. Answer quality beyond citation correctness is unmeasured.
- Citation correctness, scenario results and human review are the only quality measures.
- Any router decision needs a hosted model key and a GPU first. See `docs/product/exec-memos/memo-2-week8.md` for the decisions the owner must make.
