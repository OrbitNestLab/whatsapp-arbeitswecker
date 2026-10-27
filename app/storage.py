from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Iterable

from .parser import ScheduleEntry


class Storage:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detail TEXT
                );
                CREATE TABLE IF NOT EXISTS schedule (
                    work_date TEXT PRIMARY KEY,
                    start_time TEXT,
                    is_free INTEGER NOT NULL,
                    source_message_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def seen(self, message_id: str) -> bool:
        with self._connect() as db:
            return db.execute("SELECT 1 FROM messages WHERE message_id = ?", (message_id,)).fetchone() is not None

    def record_message(self, message_id: str, sender: str, status: str, detail: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO messages(message_id, sender, received_at, status, detail) VALUES(?,?,?,?,?)",
                (message_id, sender, now, status, detail[:500]),
            )

    def upsert_entries(self, entries: Iterable[ScheduleEntry], message_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as db:
            for entry in entries:
                db.execute(
                    """
                    INSERT INTO schedule(work_date, start_time, is_free, source_message_id, updated_at)
                    VALUES(?,?,?,?,?)
                    ON CONFLICT(work_date) DO UPDATE SET
                      start_time=excluded.start_time,
                      is_free=excluded.is_free,
                      source_message_id=excluded.source_message_id,
                      updated_at=excluded.updated_at
                    """,
                    (entry.date, entry.start, int(entry.free), message_id, now),
                )

    def schedule(self) -> dict[str, object]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT work_date, start_time, is_free, updated_at FROM schedule ORDER BY work_date"
            ).fetchall()
        entries = [
            {
                "date": row["work_date"],
                "start": row["start_time"],
                "free": bool(row["is_free"]),
                "updated_at": row["updated_at"],
                "source": "whatsapp",
            }
            for row in rows
        ]
        updated_at = max((entry["updated_at"] for entry in entries), default=None)
        return {
            "version": 1,
            "count": len(entries),
            "updated_at": updated_at,
            "entries": entries,
        }
