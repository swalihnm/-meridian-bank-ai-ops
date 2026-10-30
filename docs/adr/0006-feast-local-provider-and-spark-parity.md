# 0006: Feast with a local provider, and Spark-computed features checked against pandas

**Status:** Accepted, 2026-10-29.

## Context
The plan asks for a feature store with training and serving parity, and a Spark pipeline writing Delta tables.

## Decision
- Feast 0.67 with a local provider (Parquet offline, SQLite online), in its own virtualenv (`.venv-feast`) to avoid dependency clashes. Parity check: `ml/pipelines/feast_parity.py`.
- Spark 3.5.3 with Delta 3.2.0, run in the official Apache Spark container. Windows needs winutils for Hadoop, so the job runs on Linux (`ml/pipelines/spark_features.py`). Parity check against pandas: `ml/pipelines/spark_parity.py`.

## Consequences
- Materialisation is run by hand in the parity script, not on a schedule.
- No cloud feature store; the local provider is not production-scale.
- Feast needed the join key declared as a string to avoid a JSON type error.
