# Architecture (as built)

Matches the code on 2026-10-29. Parts marked *not deployed* exist as code and checks only.

```mermaid
flowchart LR
  subgraph Customer
    C[Chat client EN/AR]
  end
  subgraph API[services/api, FastAPI]
    G[Session token, rate limit, kill-switch, metrics]
  end
  subgraph Assistant[services/assistant]
    GU[Guard: injection, PII redaction]
    RT[Route]
    AC[Act]
    RS[Respond]
    CP[(SQLite checkpoints)]
    OT[[OpenTelemetry span]]
  end
  subgraph Index[Policy index]
    BM[BM25, EN + AR chunks]
  end
  subgraph Tools[services/mcp_bank]
    TS[Tool server: confirm, approval, audit chain]
  end
  MB[(services/mockbank: synthetic core banking, no money movement)]
  subgraph Ticketing
    K[[Redpanda / Kafka: tickets.raw]] --> TR[services/triage: intent, risk, route, cited draft]
    TR --> K2[[tickets.triaged]]
  end
  subgraph Data
    FE[(Feast online/offline)]
    SP[Spark -> Delta]
    PD[pandas training features]
  end
  subgraph Models
    ML[MLflow registry: staging to production gate]
  end
  C --> G --> GU --> RT --> AC --> RS
  AC --> TS --> MB
  AC --> BM
  RS --> CP
  GU -.-> OT
  PD --> FE
  PD -. parity .- SP
  SP -. parity .- FE
  ML -.-> TR
```

## Components and their checks

| Component | Code | Check |
|---|---|---|
| Gateway | `services/api/app.py` | `tests/test_api.py` (10 tests), container health check |
| Guard | `services/assistant/guardrails.py` | `tests/test_assistant_safety.py`, `ml/eval/red_team.py` |
| Orchestrator | `services/assistant/orchestrator.py` | crash-and-resume test; scenario gate |
| Policy index | `services/assistant/rag/` | `ml/eval/retrieval_eval.py`, `ml/eval/arabic_eval.py` |
| Tool server | `services/mcp_bank/` | ownership, approval and confirmation tests |
| MCP server | `services/mcp_bank/mcp_server.py` (MCP SDK v1, bound to one customer) | `tests/test_mcp_bank.py`, through a real MCP client session |
| Core banking mock | `services/mockbank/bank.py` | no-money-movement test |
| Triage | `services/triage/` | `tests/test_triage.py`, `ml/eval/results/triage_stream.json` |
| Feature store | `feature_repo/`, `ml/pipelines/feast_parity.py` | parity result, 0 mismatches |
| Spark job | `ml/pipelines/spark_features.py`, `spark_parity.py` | parity result, 0 mismatches |
| Registry | `ml/pipelines/registry.py` | gate tests; refused current model |
| Drift | `ml/pipelines/drift.py` | `tests/test_drift.py` |
| Scheduled retrain | `ml/pipelines/retrain.py` | drift-triggered run, gate refused the model |
| Live local stack | `infra/docker/compose.yml` | `ml/eval/stack_check.py`, `ml/eval/rollback_drill.py` |
| Deployment | `infra/` | Helm lint, Terraform validate, promtool check (*not deployed*) |
