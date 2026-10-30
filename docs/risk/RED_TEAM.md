# Red-team report

**Version:** v1, 2026-10-29. Scope: the Meridian assistant as built in Weeks 5 to 11, run locally. Tools: `ml/eval/red_team.py`, `ml/eval/scenario_eval.py`, `tests/test_assistant_safety.py`, `tests/test_api.py`.

**Who tested:** the project author, with paraphrases written by the same author. **This is not an external red team.** No outside tester has tried the system, and no human has tried it on the deployed demo (there is no deployed demo).

## What was tried

| Test | Size | Result |
|---|---|---|
| Paraphrased injection attempts, each followed by a "yes" turn (`ml/eval/red_team.py`) | 20 | Regex guard blocked 14 (70%). **0 write tools executed.** |
| Same test before the guard patterns were extended | 20 | Regex guard blocked 0 (0%). 1 write executed: a freeze of the caller's own card after "yes" |
| Scenario suite, injection and out-of-scope cases (`data/golden/scenarios_en.jsonl`) | 25 total, 6 injection | Injection block 1.0. Wrong actions 0. |
| Unit tests of injection patterns | 6 attacks, 1 benign control | All attacks flagged, benign question not flagged |
| Arabic injection (one pattern) | 1 | Blocked |
| API ownership: another customer's card or transaction | 2 | Refused with 403 |
| Kill-switch | 2 | Blocks all chat until reset |
| Rate limit | 1 | 429 after 30 requests per minute per session |

## Findings

**F1. The input guard depends on phrasing (high likelihood, medium impact).** Before the patch it blocked none of 20 paraphrases. After the patch it blocks 14, but the patches were written from these same 20 attacks, so **70 percent overstates how it would do on new phrasings.** Do not quote 70 percent as a general figure. The right statement is: pattern matching is not a defence on its own.

**F2. A freeze request was executed after a confirmation (low severity, fixed).** The attack "pretend the rules … freeze every card" followed by "yes" froze the caller's own card. The guard missed it, and the reply said "Done" for a request to freeze every card, which silently narrowed the request to one card. Fixes: the confirmation now names the card's last four digits, and the guard was extended. The residual risk is that a customer can freeze their own card, which is within their rights. Cross-customer harm is blocked separately (F4).

**F3. Money-movement requests never reached a tool (confirmed by design).** Attacks asking for transfers, payments or withdrawals found no tool. The tool surface has none (ADR 0002). The outcome that matters, no money moved, held in all 20 attacks.

**F4. Cross-customer access is blocked at the API (confirmed).** The chat endpoint rejects a card or transaction outside the session's own accounts (403). Before this fix a client could name any card or transaction, which was a real vulnerability found during the Week 11 build (see `docs/LOG.md`).

**F5. The "yes" confirmation is the main control, not the guard (design observation).** Every write needs a second, explicit turn, and disputes of AED 1,000 or more need agent approval. Both controls held in every test. An attacker who can send a "yes" can still trigger a write the customer wanted, so the confirmation text must be specific (F2).

## Not tested

- Indirect prompt injection through retrieved policy text. No policy contains instructions, and the retrieved text is not passed to a language model yet, so this path does not exist.
- Tool-output injection. There is no model reading tool output.
- Jailbreaks against a language model. None is in the system.
- Arabic and Gulf-dialect injection beyond one pattern.
- Denial of service beyond the per-session rate limit.
- Anything on a deployed system: nothing is deployed.

## Residual risk

Medium for prompt-style attacks on the guard, because it is pattern-based. Low for money movement, because no tool can do it. Low for cross-customer access, because of the API ownership checks. These should be re-assessed when a language model is added to the answer path, which will create the indirect-injection risk listed above.

## Recommended next steps

1. Have someone outside the project attempt the system.
2. Keep the guard as one layer. Do not treat it as the security boundary.
3. Before any language model is added to the answer path, run the indirect-injection tests.
