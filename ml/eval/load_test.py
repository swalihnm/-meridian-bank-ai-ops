"""Load test for the assistant API (Week 11).

Opens several sessions, then sends a realistic mix of messages from concurrent workers and records
latency and error counts. Results go to ml/eval/results/load_test.json.

Run against a running API:
    MERIDIAN_LOAD_URL=http://127.0.0.1:8080 python -m ml.eval.load_test

The mix is a hand-chosen assumption (mostly policy questions), not measured production traffic.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import httpx

RESULTS_PATH = Path("ml/eval/results/load_test.json")
SESSIONS = 12
REQUESTS_PER_SESSION = 25  # stays under the 30-per-minute per-session limit
CONCURRENCY = 8
MIX = [
    ("What is the monthly maintenance fee on my current account?", 0.30),
    ("How many free ATM withdrawals do I get each month?", 0.20),
    ("What is my default daily card spending limit?", 0.15),
    ("How do I close my account?", 0.10),
    ("Please freeze my card, I lost it", 0.10),
    ("What is the weather in Dubai tomorrow?", 0.10),
    ("Can I speak to a real person please?", 0.05),
]


@dataclass(frozen=True)
class Sample:
    latency: float
    status: int


def _messages(n: int) -> list[str]:
    """Deterministic message sequence that follows the mix weights."""
    out: list[str] = []
    for message, weight in MIX:
        out.extend([message] * round(weight * n))
    while len(out) < n:
        out.append(MIX[0][0])
    return out[:n]


def _session(base: str) -> str:
    with httpx.Client(base_url=base, timeout=30) as client:
        return str(client.post("/session").json()["session_token"])


def _worker(base: str, token: str, messages: list[str]) -> list[Sample]:
    samples: list[Sample] = []
    with httpx.Client(base_url=base, timeout=30, headers={"X-Session-Token": token}) as client:
        for message in messages:
            started = time.perf_counter()
            response = client.post("/chat", json={"message": message})
            samples.append(Sample(time.perf_counter() - started, response.status_code))
    return samples


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))
    return ordered[index]


def main() -> None:
    base = os.environ.get("MERIDIAN_LOAD_URL", "http://127.0.0.1:8080")
    tokens = [_session(base) for _ in range(SESSIONS)]
    messages = _messages(REQUESTS_PER_SESSION)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = [pool.submit(_worker, base, token, messages) for token in tokens]
        samples = [s for f in futures for s in f.result()]
    wall = time.perf_counter() - started

    latencies = [s.latency for s in samples]
    ok = [s for s in samples if s.status == 200]
    result = {
        "requests": len(samples),
        "ok": len(ok),
        "non_200": len(samples) - len(ok),
        "status_counts": {
            str(c): sum(1 for s in samples if s.status == c)
            for c in sorted({s.status for s in samples})
        },
        "concurrency": CONCURRENCY,
        "sessions": SESSIONS,
        "wall_seconds": round(wall, 2),
        "throughput_rps": round(len(samples) / wall, 2),
        "latency_p50_ms": round(1000 * _percentile(latencies, 50), 1),
        "latency_p95_ms": round(1000 * _percentile(latencies, 95), 1),
        "latency_mean_ms": round(1000 * statistics.mean(latencies), 1),
        "mix": {m: w for m, w in MIX},
        "target": base,
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
