# 0014: Hosted LLM used for evaluation, not in the customer answer path

**Status:** Accepted, 2026-10-29. Decided without the owner, under the instruction to finish what can be finished.

## Context
The plan asks for an LLM judge and a strong-model path. A hosted model (Ollama's cloud API, key supplied by the owner) makes both possible. The key is a billed account credential and was pasted into a chat, so it is treated as exposed.

## Decision
- The client (`services/assistant/llm/ollama_client.py`) reads `OLLAMA_API_KEY` from the environment only. Nothing stores the key. A repository scan after the runs found no copy.
- The hosted model is used for evaluation: the judge (`ml/eval/llm_eval.py`) and generated-answer measurement. The customer answer path stays extractive. The model is not wired into the live assistant.
- The owner should rotate the key, since it has appeared in chat.

## Consequences
- Judge agreement with a programmatic label is 0.90 (kappa 0.70, n = 50). The reference is a rule, not human labels, so this is weak evidence for judge quality. Human-labelled kappa is still open.
- With the first prompt, generated answers had 10.7 percent unsupported sentences. A tighter prompt (prompt v2) brings this to 1.6 percent, but the metric is word overlap and rewards close copying. Generation is still not in the customer path.
- Wiring generation into production would be a new decision with its own gate.
