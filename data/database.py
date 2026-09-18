"""
ROLEX AI — Database System
SQLite-based local-first storage with schema validation, migrations,
transactions, backup/restore and corruption detection.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from config import CONFIG, DB_PATH
from modules.logger import get_logger

log = get_logger("rolex.db")

SCHEMA_VERSION = 3

# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    category   TEXT NOT NULL DEFAULT 'general',
    key        TEXT,
    content    TEXT NOT NULL,
    importance INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_category ON memory(category);
CREATE INDEX IF NOT EXISTS idx_memory_key ON memory(key);

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'PENDING',
    priority    INTEGER NOT NULL DEFAULT 2,
    due_date    REAL,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL,
    completed_at REAL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

CREATE TABLE IF NOT EXISTS plans (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    goal       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_steps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id     INTEGER NOT NULL,
    step_no     INTEGER NOT NULL,
    description TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'PENDING',
    depends_on  INTEGER,
    result      TEXT,
    FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_plan_steps_plan ON plan_steps(plan_id);

CREATE TABLE IF NOT EXISTS cache (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    expires_at REAL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    path       TEXT NOT NULL,
    name       TEXT NOT NULL,
    doc_type   TEXT,
    size       INTEGER,
    content    TEXT,
    meta       TEXT,
    indexed_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documents_name ON documents(name);

CREATE TABLE IF NOT EXISTS knowledge (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    topic      TEXT NOT NULL,
    content    TEXT NOT NULL,
    tags       TEXT,
    source     TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge(topic);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event      TEXT NOT NULL,
    actor      TEXT,
    detail     TEXT,
    severity   TEXT NOT NULL DEFAULT 'INFO',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event);

CREATE TABLE IF NOT EXISTS conversations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    provider   TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at);

CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'once',
    payload     TEXT,
    run_at      REAL,
    interval    REAL,
    enabled     INTEGER NOT NULL DEFAULT 1,
    last_run    REAL,
    next_run    REAL,
    created_at  REAL NOT NULL
);
"""


class Database:
    """Thread-safe SQLite wrapper for ROLEX AI."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else Path(CONFIG.db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_schema()

    # -- connection ---------------------------------------------------------
    def _connect(self) -> None:
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False, timeout=30)
        self._conn.row_factory = sqlite3.Row
        try:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
        except sqlite3.Error as e:
            log.warning("PRAGMA setup issue: %s", e)

    def _init_schema(self) -> None:
        with self._lock:
            try:
                self._conn.executescript(SCHEMA)
                self._conn.commit()
                self._set_meta("schema_version", str(SCHEMA_VERSION))
                log.info("Database ready at %s (schema v%s)", self.path, SCHEMA_VERSION)
            except sqlite3.Error as e:
                log.error("Schema init failed: %s", e)
                raise

    # -- meta ---------------------------------------------------------------
    def _set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO schema_meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self._conn.commit()

    def get_meta(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self._conn.execute("SELECT value FROM schema_meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    # -- generic helpers ----------------------------------------------------
    @contextmanager
    def transaction(self):
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, tuple(params))
            self._conn.commit()
            return cur

    def query(self, sql: str, params: Iterable[Any] = ()) -> List[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, tuple(params)).fetchall()

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    # -- integrity ----------------------------------------------------------
    def integrity_check(self) -> bool:
        try:
            row = self._conn.execute("PRAGMA integrity_check;").fetchone()
            ok = row and row[0] == "ok"
            if not ok:
                log.error("Integrity check failed: %s", row[0] if row else "unknown")
            return bool(ok)
        except sqlite3.Error as e:
            log.error("Integrity check error: %s", e)
            return False

    def backup(self, dest: Optional[Path] = None) -> Path:
        dest = Path(dest) if dest else self.path.with_suffix(f".backup.{int(time.time())}.db")
        with self._lock:
            try:
                bconn = sqlite3.connect(str(dest))
                self._conn.backup(bconn)
                bconn.close()
                log.info("Backup created: %s", dest)
            except sqlite3.Error as e:
                log.error("Backup failed: %s", e)
                raise
        return dest

    def restore(self, src: Path) -> bool:
        src = Path(src)
        if not src.exists():
            log.error("Restore source missing: %s", src)
            return False
        with self._lock:
            try:
                self._conn.close()
                shutil.copy2(src, self.path)
                self._connect()
                self._init_schema()
                log.info("Restored database from %s", src)
                return True
            except Exception as e:
                log.error("Restore failed: %s", e)
                self._connect()
                return False

    def close(self) -> None:
        with self._lock:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------
_db: Optional[Database] = None
_db_lock = threading.Lock()


def get_db() -> Database:
    global _db
    if _db is None:
        with _db_lock:
            if _db is None:
                _db = Database()
    return _db
