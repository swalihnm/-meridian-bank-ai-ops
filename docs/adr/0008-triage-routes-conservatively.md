# 0008: Triage routes conservatively to humans

**Status:** Accepted, 2026-10-29.

## Context
Ticket triage can draft replies. A wrong draft that reaches a customer is worse than a delay.

## Decision
Complaints, low-confidence intents, high-risk disputes, unanswerable tickets and all Arabic tickets without a policy match go to a human. Only policy questions with a cited draft are marked `agent_draft`, and a human still approves them.

## Consequences
- 57 percent of the 500 synthetic tickets go to humans (see docs/LOG.md). That is the intended default, not a failure of the classifier.
- Action requests (card freeze, address change) go to humans until they are routed to assistant tools.
