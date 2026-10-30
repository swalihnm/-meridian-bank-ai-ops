"""Live check of the local monitoring stack (Week 9, Week 11).

Run after `docker compose -p meridian up -d` in infra/docker. Checks, in order:
1. The API answers /health and serves traffic (a short mixed load).
2. Prometheus scrapes the API target as healthy, loads the alert rules, and sees the counter.
3. Grafana is up and the Meridian dashboard is provisioned.

Credentials are read from the environment and never written to disk:
    MERIDIAN_ADMIN_TOKEN (not needed here), GRAFANA_ADMIN_PASSWORD (for the Grafana API).

Writes ml/eval/results/stack_check.json.
"""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path

import httpx

API = "http://127.0.0.1:8000"
PROM = "http://127.0.0.1:9090"
GRAFANA = "http://127.0.0.1:3000"
RESULTS = Path("ml/eval/results/stack_check.json")
MESSAGES = [
    "What is the monthly maintenance fee on my current account?",
    "How many free ATM withdrawals do I get each month?",
    "What is the weather in Dubai tomorrow?",
    "Can I speak to a real person please?",
]


def wait_for(url: str, attempts: int = 30) -> bool:
    for _ in range(attempts):
        try:
            if httpx.get(url, timeout=5).status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(2)
    return False


def main() -> int:
    report: dict[str, object] = {}

    report["api_healthy"] = wait_for(f"{API}/health")
    if report["api_healthy"]:
        # Spread the load over sessions: the gateway limits each session to 30 requests a minute.
        ok = 0
        with httpx.Client(base_url=API, timeout=30) as client:
            for session_no in range(5):
                token = client.post("/session").json()["session_token"]
                for i in range(8):
                    response = client.post(
                        "/chat",
                        json={"message": MESSAGES[(session_no + i) % len(MESSAGES)]},
                        headers={"X-Session-Token": token},
                    )
                    ok += response.status_code == 200
        report["traffic_ok"] = f"{ok}/40"

    wait_for(f"{PROM}/-/ready")
    time.sleep(20)  # allow one scrape interval (15 s) to pick up the new traffic
    targets = httpx.get(f"{PROM}/api/v1/targets", timeout=30).json()["data"]["activeTargets"]
    report["prometheus_targets"] = {t["labels"]["job"]: t["health"] for t in targets}
    rules = httpx.get(f"{PROM}/api/v1/rules", timeout=30).json()["data"]["groups"]
    report["alert_rules_loaded"] = sum(len(g["rules"]) for g in rules)
    query = httpx.get(
        f"{PROM}/api/v1/query",
        params={"query": "sum(meridian_chat_requests_total)"},
        timeout=30,
    ).json()["data"]["result"]
    report["requests_seen_by_prometheus"] = float(query[0]["value"][1]) if query else 0.0

    password = os.environ.get("GRAFANA_ADMIN_PASSWORD")
    if password and wait_for(f"{GRAFANA}/api/health"):
        auth = base64.b64encode(f"admin:{password}".encode()).decode()
        dashboards = httpx.get(
            f"{GRAFANA}/api/search",
            params={"query": "Meridian"},
            headers={"Authorization": f"Basic {auth}"},
            timeout=30,
        ).json()
        report["grafana_dashboards"] = [d["title"] for d in dashboards]
    else:
        report["grafana_dashboards"] = "skipped (GRAFANA_ADMIN_PASSWORD not set or Grafana not up)"

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    targets_seen = report["prometheus_targets"]
    assert isinstance(targets_seen, dict)
    healthy = report["api_healthy"] is True and targets_seen.get("meridian-api") == "up"
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
