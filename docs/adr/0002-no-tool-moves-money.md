# 0002: No tool may move money

**Status:** Accepted, 2026-10-28.

## Context
The assistant can act on accounts (freeze a card, open a dispute). A wrong or manipulated action that moves money would be the most serious failure the system can have.

## Decision
The bank tool surface has no transfer, payment or withdrawal method. `services/mockbank/bank.py` and `services/mcp_bank/server.py` enforce this, and tests fail if such a method appears (`tests/test_mockbank.py::test_no_method_moves_money`, `tests/test_assistant_safety.py::test_no_tool_can_move_money`).

## Consequences
- Wrong actions are limited to reversible account state (card status, dispute records, address).
- Write tools need confirmation; disputes of AED 1,000 or more need agent approval.
- Adding a money-moving tool later requires a new ADR and a deliberate change to these tests.
