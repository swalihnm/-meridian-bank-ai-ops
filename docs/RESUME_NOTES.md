# Resume and interview notes (Meridian)

Only claims the repo can reproduce are listed. Each has the file that holds the number. Things not done are left out on purpose.

## Resume bullets (measured)

- Built an AI policy assistant for a synthetic bank with hybrid retrieval, citation checks and abstention: recall at 5 of 0.93 on 60 hand-written questions; out-of-scope questions refused on 10 of 10. Citation correctness is 0.78, below the 0.95 target, and is reported as a miss. (`docs/model-cards/assistant-retrieval.md`)
- Designed an agent tool layer where no tool can move money; writes need confirmation, large disputes need agent approval, and every call is in a hash-chained audit log. 25-scenario safety gate runs in CI with zero wrong actions and zero PII leaks. (`ml/eval/scenario_eval.py`, `docs/adr/0002-no-tool-moves-money.md`)
- Ran controlled comparisons (McNemar tests, Wilson intervals) on retrieval reranking and an abstain rule; both decisions recorded with their limits. (`docs/product/EXPERIMENTS.md`)
- Built a Kafka-based triage pipeline: 500 synthetic tickets triaged end to end, p95 2.9 ms per ticket on a single broker. (`ml/eval/results/triage_stream.json`)
- Verified feature parity across a Feast online/offline store and a Spark-to-Delta pipeline: zero mismatches on 300 customers (Feast) and 20,000 customers (Spark vs pandas). (`ml/eval/results/feast_parity.json`, `spark_parity.json`)
- Compared three intent classifiers on Banking77 with paired McNemar tests: a Keras network beat the TF-IDF baseline significantly (0.9010 vs 0.8896, p = 0.002); a fine-tuned DistilBERT did not (p = 0.53). Temperature scaling cut calibration error from 0.132 to 0.016. (`docs/model-cards/intent.md`, `ml/intent/paired_compare.py`)
- Built a model registry promotion gate that refused to promote a model missing its targets. (`ml/pipelines/registry.py`)
- Served the assistant over FastAPI with per-session tokens, rate limits, a kill-switch and a fix for cross-customer access found in review; 300 of 300 requests succeeded in a local load test (p95 37 ms, single worker, assumed mix). (`ml/eval/load_test.py`)

## Interview stories (use these; they are true)

1. **A target missed and what was decided.** Citation correctness target 0.95, measured 0.78. Decision: report it as a miss, do not promote the assistant to real customers, and set a weekly human review. (`docs/risk/RISK_REGISTER.md`, `docs/product/LAUNCH.md`)
2. **An experiment rejected on evidence.** The reranker raised recall from 0.933 to 0.983 but not significantly (p = 0.25), and did not help citations. Not enabled. (`docs/product/EXPERIMENTS.md` EXP-001)
3. **A guardrail found by review.** The chat endpoint accepted any card or transaction ID. Fixed with ownership checks and tested. Found while building the API.
4. **A safety test that was too weak.** The injection guard blocked none of 20 paraphrases before the patch. After the patch it blocks 14, but the patches were written from the same attacks, so 70 percent overstates it. (`docs/risk/RED_TEAM.md`)
5. **A trade-off between safety and answers.** Requiring two matched words before answering cut out-of-scope answers from 1 to 0, and cut in-scope correct answers from 41 to 39 (not significant). Shipped for safety. (EXP-002)
6. **Infrastructure that was blocked and what was done instead.** No GPU and no cloud: the fine-tune ran on CPU with frozen embeddings; deployment was checked by linting and rendering a Helm chart, not by deploying it.

## Be honest in interviews

- Synthetic bank, synthetic labels for risk and triage, hand-written test sets, and machine-written Arabic translations. Say so first.
- Not deployed, not reviewed by an external red team, no language model in the answer path, no LLM judge.
- Some numbers were superseded after fixes. Say which ones and why.
