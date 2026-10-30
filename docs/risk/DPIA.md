# DPIA-style assessment: Meridian assistant and triage

**Version:** v1, 2026-10-29. Modelled on a data protection impact assessment. **This is a portfolio exercise over synthetic data. It is not a legal assessment and has not been reviewed by a data protection officer.** A real deployment would need a full assessment under the applicable law (UAE PDPL or the relevant regulator's rules) and a qualified reviewer.

## 1. Description of processing

| Item | Description |
|---|---|
| Data subjects | Customers who write to the chat or to the ticket channel (synthetic in this project) |
| Data processed | Chat and ticket text; customer ID; account, card and transaction references; dispute-risk scores; policy citations; audit log of tool calls |
| Purpose | Answer policy questions, perform reversible account actions on request with confirmation, route tickets to humans, measure quality |
| Automated decisions | No decision with legal or significant effect is made automatically. Actions need the customer's confirmation. Dispute risk supports routing only. |
| Recipients | Operations staff reading triage output; the mock core-banking service |
| Retention | Chat transcripts: 12 months (POL-029). Audit log: kept, hash-chained (no retention rule implemented yet). |

## 2. Necessity and proportionality

- Only the fields the task needs are used. Country and language are not inputs to the risk model; they are used only to slice metrics.
- Card numbers, emails and phone numbers in customer text are redacted before the assistant or the audit log sees them (PII guard, `services/assistant/guardrails.py`). The redaction is rule-based, not Presidio, and was tested on a small set (`tests/test_assistant_safety.py`).
- The audit log records tool arguments. Those can include a card ID or a dispute reason. Dispute reasons are truncated to 200 characters but are not redacted by the PII guard beyond what the guard does on input.

## 3. Risks to individuals

| # | Risk | Likelihood | Impact | Current control | Residual |
|---|---|---|---|---|---|
| R1 | Customer's personal data leaks into output or logs | Low | High | PII redaction on input; leak tests (0 leaks on 25 scenarios) | Medium: redaction is rule-based and incomplete |
| R2 | Assistant performs an action the customer did not intend | Low | Medium | Two-step confirmation; agent approval for large disputes; audit | Low |
| R3 | Customer sees or acts on another customer's data | Low | High | Session-bound identity; API ownership checks (403) | Low, tested |
| R4 | Wrong policy answer leads to a bad decision | Medium | Medium | Citations; abstain and hand over to a human when unsure; EN and AR tested | Medium: citation correctness 0.78 on English, below the 0.95 target |
| R5 | Triage risk score unfairly disadvantages a group | Unknown | High | Fairness slices reported; country and language excluded as inputs | Medium: slices measured on synthetic labels only |
| R6 | Customers are not told they are talking to an AI | Medium | Medium | Not implemented. The chat has no disclosure text. | **High until added** |
| R7 | Customer cannot reach a human | Low | Medium | Human handover on request, on complaint, and on abstain (POL-028) | Low |
| R8 | Kill-switch or outage leaves customers stuck | Low | Low | Kill-switch returns a human-agent message; rate limit | Low |

## 4. Gaps found in this assessment

1. **No AI disclosure in the chat (R6).** A real deployment must tell customers they are speaking to an automated assistant. This is a required fix before any use with real customers.
2. **No retention rule on the audit log.** The 12-month chat retention in POL-029 is not implemented, and the audit log has no retention at all.
3. **Redaction is rule-based.** It is not Presidio and has not been checked against a real corpus of customer messages.
4. **No data subject access or deletion path.** POL-029 promises copies of data on request; nothing implements it.
5. **Arabic personal-data handling is untested** beyond the EN and AR policy text.

## 5. Consultation

None with customers, regulators or data protection staff. This is a gap for any real use.

## 6. Decision

For portfolio use over synthetic data: proceed, with the limits above stated. **Not approved for use with real customer data.** Items 1 to 4 in section 4 must be closed first.
