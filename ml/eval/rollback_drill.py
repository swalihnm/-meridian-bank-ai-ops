"""Rollback drill against a running API (Week 11 acceptance: rollback demonstrated).

Steps, each checked:
1. Chat works before the drill.
2. A request without the admin token cannot trip the kill-switch (403).
3. The admin token trips the kill-switch; chat then returns the paused reply.
4. The admin token resumes; chat works again.

The admin token is read from MERIDIAN_ADMIN_TOKEN and is never written to disk.
Writes ml/eval/results/rollback_drill.json. Exit code 1 if any step fails.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

API = os.environ.get("MERIDIAN_API_URL", "http://127.0.0.1:8000")
RESULTS = Path("ml/eval/results/rollback_drill.json")
QUESTION = "What is the monthly maintenance fee on my current account?"


def chat(client: httpx.Client, token: str) -> dict[str, object]:
    response = client.post("/chat", json={"message": QUESTION}, headers={"X-Session-Token": token})
    return {
        "status": response.status_code,
        "body": response.json() if response.status_code == 200 else {},
    }


def main() -> int:
    admin = os.environ.get("MERIDIAN_ADMIN_TOKEN")
    if not admin:
        print("MERIDIAN_ADMIN_TOKEN is not set; cannot run the drill.")
        return 1

    steps: dict[str, bool] = {}
    with httpx.Client(base_url=API, timeout=30) as client:
        token = client.post("/session").json()["session_token"]

        before = chat(client, token)
        steps["chat_works_before"] = before["status"] == 200 and "paused" not in str(before["body"])

        refused = client.post("/admin/kill", headers={"X-Admin-Token": "not-the-token"})
        steps["non_admin_cannot_kill"] = refused.status_code == 403

        tripped = client.post("/admin/kill?reason=rollback-drill", headers={"X-Admin-Token": admin})
        steps["admin_trips_kill_switch"] = tripped.status_code == 200
        paused = chat(client, token)
        steps["chat_paused_while_killed"] = paused["status"] == 200 and "paused" in str(
            paused["body"]
        )

        resumed = client.post("/admin/resume", headers={"X-Admin-Token": admin})
        steps["admin_resumes"] = resumed.status_code == 200
        after = chat(client, token)
        steps["chat_works_after_resume"] = after["status"] == 200 and "paused" not in str(
            after["body"]
        )

    result = {"api": API, "steps": steps, "all_passed": all(steps.values())}
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
