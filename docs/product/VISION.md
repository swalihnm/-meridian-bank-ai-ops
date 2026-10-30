# Vision and strategy

**Status:** Draft v1, 2026-10-28. Written before any model exists.

## The problem
Customer operations at a digital bank is repetitive and expensive. Most contacts are policy questions ("what is the fee for a foreign card payment?") or simple account actions ("freeze my card"). Human agents spend most of their time on these, while the cases that need judgement wait in the same queue. Customers in the Gulf also expect service in Arabic and English, often in the same conversation.

## Who it is for
- **Customers** who want a fast, correct answer, and a human when they need one.
- **Support agents** who want the hard cases routed to them with context and a draft reply.
- **Operations leads** who need to see whether automation is working, safely, and what it costs.

Detail is in [USERS.md](USERS.md).

## What Meridian is
An AI layer for customer operations with two parts:
1. **Customer assistant:** answers policy questions with citations, and performs a small set of account actions with confirmation and audit.
2. **Automation platform:** triages incoming tickets, classifies intent, scores risk, drafts replies for human agents, and routes hard cases.

## Why now
Banks in the region are adopting LLM assistants quickly, and the failure modes (wrong policy answers, unauthorised actions, PII leaks) are well known. The product question is not "can an LLM answer?" but "what share of cases can be resolved correctly, safely and cheaply, and how do we prove it?"

## What we will not build
- **Anything that moves money.** No tool can transfer funds, pay a bill or change a limit. This is a design rule, not a preference.
- **Autonomous high-risk actions.** Disputes above a threshold need agent approval. Address changes are blocked without verification.
- **Real customer data.** Everything is synthetic. Public datasets are used only for the ML parts.
- **Voice in v1.** Voice is a stretch goal (see [ROADMAP.md](ROADMAP.md)).
- **A consumer mobile app.** The chat is a web component; the value is in the logic, metrics and evidence.
- **Credit decisions.** The risk model scores disputes and tickets for routing and review. It does not decide credit.

## Success, in one line
Maximise **cost per correctly resolved case**, with the guardrail metrics (wrong action, PII leak, hallucinated policy) held at or near zero. Full definitions and targets are in [METRICS.md](METRICS.md).

## Principles
1. Measure before claiming. Every number in the README comes from a command in the repo.
2. A documented miss beats a hidden one.
3. Safety checks come before features.
4. Keep scope to what one person can finish in 12 weeks; cut stretch goals first.
