"""SQLite event log for MVP 05."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict


class EventLog:
    """publish/command 이력을 SQLite에 저장하는 최소 logger."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS gateway_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    topic TEXT,
                    command TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gateway_events_created_at ON gateway_events(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gateway_events_kind ON gateway_events(kind)")

    def record(self, created_at: str, kind: str, payload: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO gateway_events(created_at, kind, topic, command, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    kind,
                    payload.get("topic"),
                    payload.get("command"),
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                ),
            )

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM gateway_events").fetchone()[0])
