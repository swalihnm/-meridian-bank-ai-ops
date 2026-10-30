# Users and jobs to be done

**Status:** Draft v1, 2026-10-28.

## Personas

### 1. Customer (Aisha, 29, Dubai, uses the app daily)
- **Job:** "When something goes wrong with my card or account, get a correct answer or a fix in one conversation, in my language."
- **Pains:** Long waits, scripted replies that do not answer the question, not knowing whether a fee is valid.
- **Needs:** Fast answers with a source. Clear confirmation before any action. An easy path to a human.
- **Languages:** English, Arabic, and mixed or Arabizi messages.

### 2. Support agent (Omar, 34, works the dispute queue)
- **Job:** "Resolve the hard cases quickly, with the context I need, and without re-asking the customer questions."
- **Pains:** Context is scattered across systems. Drafting replies from scratch takes time.
- **Needs:** Triage notes, a risk score with reasons (SHAP), a draft reply with citations, one-click approve or edit.

### 3. Operations lead (Lena, 41, runs customer operations)
- **Job:** "Know whether automation is saving money without hurting customers, and know when to pull it back."
- **Pains:** Dashboards show volume, not quality. Experiments run without clear decisions.
- **Needs:** North-star and guardrail metrics on one page. Experiment results with confidence intervals. A kill-switch and an alert when quality drops.

### 4. Compliance reviewer (Karim, 46, model risk and conduct)
- **Job:** "Confirm the system follows policy, cannot act beyond its permissions, and that its limits are documented."
- **Needs:** Audit log of every action, model cards, a red-team report, a DPIA-style assessment, and a risk register with owners.

## Jobs to be done, prioritised

| # | Who | Job | Priority | Shipped in |
|---|---|---|---|---|
| J1 | Customer | Get a cited answer to a policy question | Must | Week 4 |
| J2 | Customer | Freeze a card with confirmation | Must | Week 5 |
| J3 | Customer | Open a dispute, with approval above threshold | Must | Week 5 |
| J4 | Customer | Reach a human when needed, with context passed on | Must | Week 5 |
| J5 | Agent | See a triaged ticket with intent, risk and a draft reply | Must | Week 7 |
| J6 | Ops lead | See north-star, guardrails and model health on one page | Must | Week 9 to 10 |
| J7 | Ops lead | Decide ship or no-ship on an experiment | Should | Week 10 |
| J8 | Compliance | Audit every action and read every model card | Must | Week 5, Week 12 |
| J9 | Customer | Get the same quality in Arabic | Should | Week 10 |
| J10 | Agent | Check the reasons behind a risk score | Should | Week 7 |

## Out of scope for users
- Retail customers outside the UAE and KSA flavour (the policy set is written for these).
- Corporate and treasury clients.
