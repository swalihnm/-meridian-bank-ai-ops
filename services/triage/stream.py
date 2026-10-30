"""Kafka (Redpanda) stream for the triage service.

Flow: a producer writes synthetic tickets to `tickets.raw`. The triage consumer reads them, runs
TriagePipeline, and writes results to `tickets.triaged`. The producer does NOT send the intent
label, so the pipeline cannot see the answer. Labels are kept aside and used only for evaluation.

Run against a broker (default 127.0.0.1:9092):
    python -m services.triage.stream --n 500
Results: ml/eval/results/triage_stream.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import uuid
from pathlib import Path

import pandas as pd
from kafka import KafkaAdminClient, KafkaConsumer, KafkaProducer
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError

from data.generator.tickets import generate_tickets
from services.triage.build import Built, build
from services.triage.pipeline import TriagePipeline

RESULTS_PATH = Path("ml/eval/results/triage_stream.json")


def ensure_topics(bootstrap: str, raw: str, triaged: str) -> None:
    admin = KafkaAdminClient(bootstrap_servers=bootstrap)
    try:
        admin.create_topics([NewTopic(raw, 1, 1), NewTopic(triaged, 1, 1)])
    except TopicAlreadyExistsError:
        pass
    finally:
        admin.close()


def produce(bootstrap: str, raw: str, tickets: pd.DataFrame) -> None:
    producer = KafkaProducer(
        bootstrap_servers=bootstrap, value_serializer=lambda v: json.dumps(v).encode()
    )
    for row in tickets.itertuples(index=False):
        producer.send(
            raw,
            {
                "ticket_id": row.ticket_id,
                "customer_id": row.customer_id,
                "text": row.text,
                "created_at": str(row.created_at),
            },
        )
    producer.flush()
    producer.close()


def consume_and_triage(
    bootstrap: str, raw: str, triaged: str, pipeline: TriagePipeline, expected: int, group: str
) -> list[dict[str, object]]:
    consumer = KafkaConsumer(
        raw,
        bootstrap_servers=bootstrap,
        group_id=group,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda b: json.loads(b.decode()),
        consumer_timeout_ms=15_000,
    )
    producer = KafkaProducer(
        bootstrap_servers=bootstrap, value_serializer=lambda v: json.dumps(v).encode()
    )
    results: list[dict[str, object]] = []
    for message in consumer:
        started = time.perf_counter()
        result = pipeline.triage(message.value)
        elapsed = time.perf_counter() - started
        record: dict[str, object] = {
            "ticket_id": result.ticket_id,
            "intent": result.intent,
            "confidence": result.confidence,
            "risk": result.risk,
            "route": result.route,
            "reason": result.reason,
            "draft": result.draft,
            "citations": result.citations,
            "triage_ms": 1000 * elapsed,
        }
        producer.send(triaged, record)
        results.append(record)
        if len(results) >= expected:
            break
    producer.flush()
    producer.close()
    consumer.close()
    return results


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", default="127.0.0.1:9092")
    parser.add_argument("--n", type=int, default=500)
    args = parser.parse_args()

    built: Built = build()
    # Held-out tickets: a different seed from the training tickets.
    tickets = generate_tickets(built.customer_ids, args.n, seed=99)

    # Fresh topics and consumer group per run, so earlier runs cannot leak into this one.
    run = uuid.uuid4().hex[:8]
    raw, triaged, group = f"tickets.raw.{run}", f"tickets.triaged.{run}", f"triage-{run}"
    ensure_topics(args.bootstrap, raw, triaged)
    started = time.perf_counter()
    produce(args.bootstrap, raw, tickets)
    results = consume_and_triage(
        args.bootstrap, raw, triaged, built.pipeline, expected=args.n, group=group
    )
    wall = time.perf_counter() - started

    truth = dict(zip(tickets["ticket_id"], tickets["intent"], strict=True))
    correct = sum(1 for r in results if r["intent"] == truth[str(r["ticket_id"])])
    routes: dict[str, int] = {}
    for r in results:
        routes[str(r["route"])] = routes.get(str(r["route"]), 0) + 1
    reasons: dict[str, int] = {}
    for r in results:
        reasons[str(r["reason"])] = reasons.get(str(r["reason"]), 0) + 1
    latencies = [float(r["triage_ms"]) for r in results]  # type: ignore[arg-type]
    summary = {
        "tickets_sent": int(args.n),
        "tickets_triaged": len(results),
        "intent_accuracy_synthetic": correct / len(results) if results else 0.0,
        "routes": routes,
        "reasons": reasons,
        "triage_latency_p50_ms": round(statistics.median(latencies), 2) if latencies else None,
        "triage_latency_p95_ms": round(_p95(latencies), 2) if latencies else None,
        "end_to_end_seconds": round(wall, 2),
        "end_to_end_tickets_per_second": round(len(results) / wall, 1) if wall else None,
        "labels": "SYNTHETIC tickets; accuracy is a method check, not real-world performance",
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
