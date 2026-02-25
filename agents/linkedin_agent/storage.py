from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

from config.settings_linkedin import linkedin_settings
from .models import ScheduleRequest, TokenBundle

_DB_PATH = Path(linkedin_settings.li_db_path)


def configure(path: str) -> None:
    """Override the database path (primarily for tests)."""

    global _DB_PATH
    _DB_PATH = Path(path)


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            access_token TEXT NOT NULL,
            expires_at REAL NOT NULL,
            refresh_token TEXT,
            scope TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at REAL NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )
    conn.commit()


def save_tokens(bundle: TokenBundle) -> None:
    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute(
            "REPLACE INTO tokens (id, access_token, expires_at, refresh_token, scope) VALUES (1, ?, ?, ?, ?)",
            (bundle.access_token, bundle.expires_at, bundle.refresh_token, bundle.scope),
        )
        conn.commit()


def get_tokens() -> TokenBundle | None:
    with _connect() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT access_token, expires_at, refresh_token, scope FROM tokens WHERE id = 1").fetchone()
    if row is None:
        return None
    data = {
        "access_token": row["access_token"],
        "expires_at": float(row["expires_at"]),
        "refresh_token": row["refresh_token"],
        "scope": row["scope"],
    }
    return TokenBundle(**data)


def upsert_scheduled_post(request: ScheduleRequest) -> int:
    payload_data = request.model_dump()
    if isinstance(payload_data.get("run_at"), dt.datetime):
        payload_data["run_at"] = payload_data["run_at"].isoformat()
    payload = json.dumps(payload_data)
    run_at = request.next_run_ts()
    now = dt.datetime.utcnow().timestamp()
    with _connect() as conn:
        _ensure_schema(conn)
        cur = conn.execute(
            "INSERT INTO scheduled_posts (run_at, payload, status, created_at) VALUES (?, ?, ?, ?)",
            (run_at, payload, request.state, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def due_posts(now: float | None = None) -> List[Tuple[int, ScheduleRequest]]:
    reference = now if now is not None else dt.datetime.utcnow().timestamp()
    with _connect() as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            "SELECT id, payload FROM scheduled_posts WHERE status = ? AND run_at <= ? ORDER BY run_at ASC",
            ("pending", reference),
        ).fetchall()
    results: List[Tuple[int, ScheduleRequest]] = []
    for row in rows:
        payload = json.loads(row["payload"])
        if "run_at" in payload and isinstance(payload["run_at"], str):
            payload["run_at"] = dt.datetime.fromisoformat(payload["run_at"])
        results.append((int(row["id"]), ScheduleRequest(**payload)))
    return results


def mark_done(post_id: int, status: str) -> None:
    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute(
            "UPDATE scheduled_posts SET status = ? WHERE id = ?",
            (status, post_id),
        )
        conn.commit()


def list_scheduled() -> List[Dict[str, Any]]:
    with _connect() as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            "SELECT id, run_at, payload, status FROM scheduled_posts WHERE status = ? ORDER BY run_at",
            ("pending",),
        ).fetchall()
    items: List[Dict[str, Any]] = []
    for row in rows:
        payload = json.loads(row["payload"])
        items.append(
            {
                "id": int(row["id"]),
                "run_at": float(row["run_at"]),
                "status": row["status"],
                "payload": payload,
            }
        )
    return items
