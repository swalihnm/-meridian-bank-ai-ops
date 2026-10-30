"""Hash-chained audit log for every tool call.

Each record stores the hash of the previous record. Editing or deleting any record breaks the
chain, and `verify()` reports the first broken index. The log is append-only by design: there is
no update or delete method.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

GENESIS = "0" * 64


@dataclass(frozen=True)
class AuditRecord:
    index: int
    timestamp: str
    actor: str
    tool: str
    args: dict[str, Any]
    outcome: str
    prev_hash: str
    hash: str


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class AuditLog:
    _records: list[AuditRecord] = field(default_factory=list)

    def append(self, actor: str, tool: str, args: dict[str, Any], outcome: str) -> AuditRecord:
        prev = self._records[-1].hash if self._records else GENESIS
        body = {
            "index": len(self._records),
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": actor,
            "tool": tool,
            "args": args,
            "outcome": outcome,
            "prev_hash": prev,
        }
        record = AuditRecord(
            index=len(self._records),
            timestamp=str(body["timestamp"]),
            actor=actor,
            tool=tool,
            args=args,
            outcome=outcome,
            prev_hash=prev,
            hash=_digest(body),
        )
        self._records.append(record)
        return record

    def records(self) -> list[AuditRecord]:
        return list(self._records)

    def verify(self) -> int | None:
        """Return None if the chain is intact, else the index of the first broken record."""
        prev = GENESIS
        for rec in self._records:
            body = {
                "index": rec.index,
                "timestamp": rec.timestamp,
                "actor": rec.actor,
                "tool": rec.tool,
                "args": rec.args,
                "outcome": rec.outcome,
                "prev_hash": rec.prev_hash,
            }
            if rec.prev_hash != prev or rec.hash != _digest(body):
                return rec.index
            prev = rec.hash
        return None
