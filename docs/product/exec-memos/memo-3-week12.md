# Executive memo 3: Meridian, Week 12

**Date:** 2026-10-29.
**To:** Senior operations leader.
**From:** Product owner, Meridian project.
**Status:** Amber overall. The core assistant, triage and evidence work is done. Deployment, the language-model work and the LLM judge are not done.

## What works (measured, reproducible in the repo)
- **Assistant safety:** 25 scenarios including injections, out-of-scope questions and PII. Zero wrong actions, zero PII leaks, escalation recall 1.0, injection block 1.0 on the scenario set. The scenario gate runs in CI.
- **Policy answers:** recall at 5 is 0.93 (hybrid). Citation correctness is 0.78, short of the 0.95 target. Out-of-scope questions are refused in all tested cases.
- **Arabic:** with a combined index, Arabic recall rises from 0.40 to 0.90 on 10 questions. The Arabic policies cover five of thirty, and the translations are not yet checked by a native speaker.
- **Triage:** 500 synthetic tickets flowed through a Kafka-compatible broker and were triaged. About 57 percent go to a human by design. The conservative routing is intentional.
- **Data platform:** a feature store and a Spark pipeline both reproduce the training features with no mismatches on the samples tested.
- **Load:** on a local single worker, 300 of 300 requests succeeded with a p95 of 37 ms, on an assumed traffic mix.

## What does not work or is not done
- **Intent model:** misses its accuracy target and is not clearly better than the baseline.
- **Language-model drafting and cost comparison:** not done (no GPU, no hosted key).
- **LLM judge:** not built, so answer quality is not measured beyond citations.
- **Deployment:** not deployed. The Helm chart lints and renders, but there is no cluster. No public demo exists.
- **Red team:** done by the project author only. A 70 percent block rate on paraphrases overstates the guard, since the patterns were written from the same examples.
- **Data licence:** the Banking77 mirror licence still needs checking. The CFPB dataset could not be downloaded.

## Risks
- Overclaiming: the numbers are on synthetic and hand-written sets. Each claim in the repo points to a result file, but the sets are small.
- Citation accuracy below target means wrong policy answers can reach customers if the assistant is deployed as is.
- The privacy assessment lists a blocking gap: customers are not told they are talking to an AI.

## Decisions needed
1. **Do not deploy to real customers yet.** The AI disclosure and data retention items in the privacy assessment must close first.
2. Fund a GPU and a hosted model key if the language-model work matters for the next phase.
3. Commission an external red team before any pilot.
4. Set an interim citation target and a weekly human review of answers.
