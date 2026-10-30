"""SQLite checkpoint store for assistant runs.

The PLAN calls for Postgres checkpoints (Oliver Wyman JD keyword). SQLite is used here so the
checkpoint logic can be tested without a database server; the interface is the same and can move
to Postgres when the docker stack exists.

FastAPI runs synchronous endpoints in worker threads, so the connection is shared across threads
and every access is serialised with a lock.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class CheckpointStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS checkpoints ("
                " run_id TEXT NOT NULL, step_index INTEGER NOT NULL, step_name TEXT NOT NULL,"
                " state TEXT NOT NULL, PRIMARY KEY (run_id, step_index))"
            )
            self.conn.commit()

    def save(self, run_id: str, step_index: int, step_name: str, state: dict[str, Any]) -> None:
        payload = json.dumps(state, sort_keys=True, default=str)
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO checkpoints VALUES (?, ?, ?, ?)",
                (run_id, step_index, step_name, payload),
            )
            self.conn.commit()

    def latest(self, run_id: str) -> tuple[int, str, dict[str, Any]] | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT step_index, step_name, state FROM checkpoints WHERE run_id = ?"
                " ORDER BY step_index DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return int(row[0]), str(row[1]), json.loads(row[2])
