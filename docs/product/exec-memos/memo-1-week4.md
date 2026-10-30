# Executive memo 1: Meridian, Week 4

**Date:** 2026-10-28 (Week 4 of 12, as the plan defines it; the work was actually done on this date and the memos are written up together).
**To:** Senior operations leader.
**From:** Product owner, Meridian project.
**Status:** Amber. Retrieval works; the citation target is not met.

## Status
- Product foundations are written: vision, users, metrics and targets, roadmap, risk register.
- A policy assistant index covers 30 synthetic bank policies. It uses keyword search and sentence-embedding search together.
- The answer step is extractive: it quotes the best matching sentence from the top policy, with the policy ID.

## Metrics against targets (retrieval golden set, 60 in-scope and 10 out-of-scope questions)

| Metric | Target | Result (Week 4) | Met? |
|---|---|---|---|
| Recall at 5 | 0.85 | 0.93 (hybrid) | Yes |
| Citation correct | 0.95 | 0.85 (hybrid) | No |
| Out-of-scope questions answered | 0 | 20 percent | No |

**Correction, added at Week 12:** the Week 4 figures for citation correctness and out-of-scope answers were later re-run after an abstain-rule fix. The current figures are 0.78 citation correct and 0 of 10 out-of-scope answered. The Week 4 numbers are kept here as the record of what was known at the time.

## Risks
- A confident wrong policy answer is the main risk. Citation correctness is below target, so answers can cite the wrong policy.
- The question set was written by the team, so the numbers may flatter the system.
- No language model is in the answer path yet, so answer fluency is untested.

## Decisions needed
1. Accept an interim target of 0.85 citation correctness until more questions are labelled, or hold the 0.95 target and delay the assistant.
2. Agree who reviews a sample of assistant answers each week.
