"""SQLite persistence for monitored pages, snapshots, checks, and changes."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..config import get_settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(value: datetime | None = None) -> str:
    return (value or _now()).isoformat(timespec="seconds")


def _next_check(frequency: str, now: datetime | None = None) -> str | None:
    current = now or _now()
    if frequency == "daily":
        return _stamp(current + timedelta(days=1))
    if frequency == "weekly":
        return _stamp(current + timedelta(days=7))
    return None


def _connect() -> sqlite3.Connection:
    db_path = get_settings().database_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def init_storage() -> None:
    with _connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS monitored_pages (
                id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                official_domain TEXT NOT NULL,
                page_url TEXT NOT NULL,
                frequency TEXT NOT NULL CHECK (frequency IN ('manual','daily','weekly')),
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_checked_at TEXT,
                next_check_at TEXT
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                monitored_page_id TEXT NOT NULL REFERENCES monitored_pages(id) ON DELETE CASCADE,
                retrieved_at TEXT NOT NULL,
                source_url TEXT NOT NULL,
                page_title TEXT NOT NULL DEFAULT '',
                page_text TEXT NOT NULL,
                normalized_hash TEXT NOT NULL,
                etag TEXT,
                last_modified TEXT
            );
            CREATE INDEX IF NOT EXISTS snapshots_by_page_time
                ON snapshots(monitored_page_id, retrieved_at DESC);
            CREATE TABLE IF NOT EXISTS check_runs (
                id TEXT PRIMARY KEY,
                monitored_page_id TEXT NOT NULL REFERENCES monitored_pages(id) ON DELETE CASCADE,
                snapshot_id TEXT REFERENCES snapshots(id) ON DELETE SET NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('baseline','changed','unchanged','failed')),
                error_code TEXT
            );
            CREATE INDEX IF NOT EXISTS checks_by_page_time
                ON check_runs(monitored_page_id, started_at DESC);
            CREATE TABLE IF NOT EXISTS change_events (
                id TEXT PRIMARY KEY,
                monitored_page_id TEXT NOT NULL REFERENCES monitored_pages(id) ON DELETE CASCADE,
                old_snapshot_id TEXT NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
                new_snapshot_id TEXT NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
                detected_at TEXT NOT NULL,
                category TEXT NOT NULL,
                category_confidence REAL NOT NULL DEFAULT 0,
                category_method TEXT NOT NULL DEFAULT 'keyword_fallback',
                old_excerpt TEXT NOT NULL,
                new_excerpt TEXT NOT NULL
            );
            """
        )
        columns = {row[1] for row in db.execute("PRAGMA table_info(change_events)")}
        if "category_confidence" not in columns:
            db.execute("ALTER TABLE change_events ADD COLUMN category_confidence REAL NOT NULL DEFAULT 0")
        if "category_method" not in columns:
            db.execute("ALTER TABLE change_events ADD COLUMN category_method TEXT NOT NULL DEFAULT 'keyword_fallback'")


def create_monitor(
    *, company_name: str, domain: str, page_url: str, frequency: str,
    page_title: str, page_text: str, normalized_hash: str,
    etag: str | None = None, last_modified: str | None = None,
) -> dict[str, Any]:
    monitor_id = uuid.uuid4().hex
    snapshot_id = uuid.uuid4().hex
    now = _stamp()
    with _connect() as db:
        db.execute(
            "INSERT INTO monitored_pages (id,company_name,official_domain,page_url,frequency,active,created_at,last_checked_at,next_check_at) VALUES (?,?,?,?,?,1,?,?,?)",
            (monitor_id, company_name, domain, page_url, frequency, now, now, _next_check(frequency)),
        )
        db.execute(
            "INSERT INTO snapshots (id,monitored_page_id,retrieved_at,source_url,page_title,page_text,normalized_hash,etag,last_modified) VALUES (?,?,?,?,?,?,?,?,?)",
            (snapshot_id, monitor_id, now, page_url, page_title, page_text, normalized_hash, etag, last_modified),
        )
        db.execute(
            "INSERT INTO check_runs (id,monitored_page_id,snapshot_id,started_at,finished_at,status) VALUES (?,?,?,?,?,'baseline')",
            (uuid.uuid4().hex, monitor_id, snapshot_id, now, now),
        )
        row = db.execute("SELECT * FROM monitored_pages WHERE id=?", (monitor_id,)).fetchone()
    return dict(row)


def get_monitor(monitor_id: str) -> dict[str, Any] | None:
    with _connect() as db:
        row = db.execute("SELECT * FROM monitored_pages WHERE id=?", (monitor_id,)).fetchone()
    return dict(row) if row else None


def list_monitors(limit: int = 100) -> list[dict[str, Any]]:
    with _connect() as db:
        rows = db.execute("SELECT * FROM monitored_pages ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def active_monitor_count() -> int:
    with _connect() as db:
        row = db.execute("SELECT COUNT(*) AS count FROM monitored_pages WHERE active=1").fetchone()
    return int(row["count"])


def get_latest_snapshot(monitor_id: str) -> dict[str, Any] | None:
    with _connect() as db:
        row = db.execute(
            "SELECT * FROM snapshots WHERE monitored_page_id=? ORDER BY retrieved_at DESC,id DESC LIMIT 1",
            (monitor_id,),
        ).fetchone()
    return dict(row) if row else None


def record_successful_check(
    *, monitor_id: str, page_url: str, page_title: str, page_text: str,
    normalized_hash: str, etag: str | None, last_modified: str | None,
    changed: bool, category: str, old_excerpt: str, new_excerpt: str,
    category_confidence: float = 0, category_method: str = "keyword_fallback",
) -> dict[str, Any]:
    now = _stamp()
    check_id = uuid.uuid4().hex
    with _connect() as db:
        monitor = db.execute("SELECT * FROM monitored_pages WHERE id=?", (monitor_id,)).fetchone()
        if not monitor:
            raise KeyError("monitor_not_found")
        latest = db.execute(
            "SELECT * FROM snapshots WHERE monitored_page_id=? ORDER BY retrieved_at DESC,id DESC LIMIT 1",
            (monitor_id,),
        ).fetchone()
        snapshot_id = latest["id"] if latest else None
        status = "unchanged"
        if changed or latest is None:
            snapshot_id = uuid.uuid4().hex
            db.execute(
                "INSERT INTO snapshots (id,monitored_page_id,retrieved_at,source_url,page_title,page_text,normalized_hash,etag,last_modified) VALUES (?,?,?,?,?,?,?,?,?)",
                (snapshot_id, monitor_id, now, page_url, page_title, page_text, normalized_hash, etag, last_modified),
            )
            status = "changed" if latest else "baseline"
            if latest:
                db.execute(
                    "INSERT INTO change_events (id,monitored_page_id,old_snapshot_id,new_snapshot_id,detected_at,category,category_confidence,category_method,old_excerpt,new_excerpt) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (uuid.uuid4().hex, monitor_id, latest["id"], snapshot_id, now, category, category_confidence, category_method, old_excerpt, new_excerpt),
                )
        db.execute(
            "INSERT INTO check_runs (id,monitored_page_id,snapshot_id,started_at,finished_at,status) VALUES (?,?,?,?,?,?)",
            (check_id, monitor_id, snapshot_id, now, now, status),
        )
        db.execute(
            "UPDATE monitored_pages SET last_checked_at=?,next_check_at=? WHERE id=?",
            (now, _next_check(monitor["frequency"]), monitor_id),
        )
        event = db.execute(
            "SELECT * FROM change_events WHERE monitored_page_id=? ORDER BY detected_at DESC,id DESC LIMIT 1",
            (monitor_id,),
        ).fetchone() if status == "changed" else None
        updated = db.execute("SELECT * FROM monitored_pages WHERE id=?", (monitor_id,)).fetchone()
    return {"monitor": dict(updated), "status": status, "change": dict(event) if event else None, "check_id": check_id}


def record_failed_check(monitor_id: str, error_code: str) -> dict[str, Any] | None:
    now = _stamp()
    with _connect() as db:
        monitor = db.execute("SELECT * FROM monitored_pages WHERE id=?", (monitor_id,)).fetchone()
        if not monitor:
            return None
        db.execute(
            "INSERT INTO check_runs (id,monitored_page_id,snapshot_id,started_at,finished_at,status,error_code) VALUES (?,?,NULL,?,?, 'failed',?)",
            (uuid.uuid4().hex, monitor_id, now, now, error_code),
        )
        db.execute("UPDATE monitored_pages SET last_checked_at=?,next_check_at=? WHERE id=?", (now, _next_check(monitor["frequency"]), monitor_id))
        row = db.execute("SELECT * FROM monitored_pages WHERE id=?", (monitor_id,)).fetchone()
    return dict(row)


def due_monitors(now: datetime | None = None, limit: int = 20) -> list[dict[str, Any]]:
    with _connect() as db:
        rows = db.execute(
            "SELECT * FROM monitored_pages WHERE active=1 AND frequency!='manual' AND next_check_at IS NOT NULL AND next_check_at<=? ORDER BY next_check_at ASC LIMIT ?",
            (_stamp(now), limit),
        ).fetchall()
    return [dict(row) for row in rows]


def deactivate_monitor(monitor_id: str) -> bool:
    with _connect() as db:
        cursor = db.execute("UPDATE monitored_pages SET active=0,next_check_at=NULL WHERE id=?", (monitor_id,))
    return cursor.rowcount > 0


def monitor_history(monitor_id: str, limit: int = 100) -> dict[str, Any] | None:
    with _connect() as db:
        monitor = db.execute("SELECT * FROM monitored_pages WHERE id=?", (monitor_id,)).fetchone()
        if not monitor:
            return None
        snapshots = db.execute(
            "SELECT id,retrieved_at,source_url,page_title,normalized_hash FROM snapshots WHERE monitored_page_id=? ORDER BY retrieved_at DESC LIMIT ?",
            (monitor_id, limit),
        ).fetchall()
        checks = db.execute(
            "SELECT id,snapshot_id,started_at,finished_at,status,error_code FROM check_runs WHERE monitored_page_id=? ORDER BY started_at DESC LIMIT ?",
            (monitor_id, limit),
        ).fetchall()
        changes = db.execute(
            "SELECT id,old_snapshot_id,new_snapshot_id,detected_at,category,category_confidence,category_method,old_excerpt,new_excerpt FROM change_events WHERE monitored_page_id=? ORDER BY detected_at DESC LIMIT ?",
            (monitor_id, limit),
        ).fetchall()
    return {"monitor": dict(monitor), "snapshots": [dict(x) for x in snapshots], "checks": [dict(x) for x in checks], "changes": [dict(x) for x in changes]}
