"""
ROLEX AI — Automation / Scheduling
One-time, scheduled, recurring and conditional tasks; background routines.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.automation")


@dataclass
class ScheduledJob:
    id: int
    name: str
    kind: str
    payload: Optional[str]
    run_at: Optional[float]
    interval: Optional[float]
    enabled: bool
    last_run: Optional[float]
    next_run: Optional[float]


class AutomationEngine:
    def __init__(self):
        self.db = get_db()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, Callable[[str], None]] = {}

    def register_action(self, name: str, fn: Callable[[str], None]) -> None:
        self._callbacks[name] = fn

    # -- job management -----------------------------------------------------
    def schedule_once(self, name: str, action: str, run_at: float,
                      payload: Optional[str] = None) -> int:
        cur = self.db.execute(
            "INSERT INTO scheduled_jobs(name, kind, payload, run_at, enabled, next_run, created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (name, "once", json.dumps({"action": action, "payload": payload}),
             run_at, 1, run_at, time.time()),
        )
        return cur.lastrowid

    def schedule_recurring(self, name: str, action: str, interval: float,
                           payload: Optional[str] = None) -> int:
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO scheduled_jobs(name, kind, payload, interval, enabled, next_run, created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (name, "recurring", json.dumps({"action": action, "payload": payload}),
             interval, 1, now + interval, now),
        )
        return cur.lastrowid

    def list_jobs(self) -> List[ScheduledJob]:
        rows = self.db.query("SELECT * FROM scheduled_jobs ORDER BY next_run ASC")
        return [ScheduledJob(r["id"], r["name"], r["kind"], r["payload"], r["run_at"],
                             r["interval"], bool(r["enabled"]), r["last_run"], r["next_run"])
                for r in rows]

    def cancel(self, job_id: int) -> bool:
        cur = self.db.execute("DELETE FROM scheduled_jobs WHERE id=?", (job_id,))
        return cur.rowcount > 0

    def enable(self, job_id: int, enabled: bool = True) -> bool:
        cur = self.db.execute("UPDATE scheduled_jobs SET enabled=? WHERE id=?",
                              (1 if enabled else 0, job_id))
        return cur.rowcount > 0

    # -- execution ----------------------------------------------------------
    def _run_due(self) -> int:
        now = time.time()
        rows = self.db.query(
            "SELECT * FROM scheduled_jobs WHERE enabled=1 AND next_run IS NOT NULL AND next_run<=?",
            (now,),
        )
        count = 0
        for r in rows:
            try:
                payload = json.loads(r["payload"]) if r["payload"] else {}
                action = payload.get("action", "")
                cb = self._callbacks.get(action)
                if cb:
                    cb(payload.get("payload", ""))
                else:
                    log.info("No callback for action '%s' (job %s)", action, r["name"])
                if r["kind"] == "recurring" and r["interval"]:
                    self.db.execute(
                        "UPDATE scheduled_jobs SET last_run=?, next_run=? WHERE id=?",
                        (now, now + r["interval"], r["id"]),
                    )
                else:
                    self.db.execute(
                        "UPDATE scheduled_jobs SET last_run=?, enabled=0, next_run=NULL WHERE id=?",
                        (now, r["id"]),
                    )
                count += 1
            except Exception as e:
                log.error("Job %s failed: %s", r["id"], e)
        return count

    def tick(self) -> int:
        return self._run_due()

    def start(self, poll_interval: float = 30.0) -> None:
        if self._running:
            return
        self._running = True

        def _loop():
            while self._running:
                try:
                    self._run_due()
                except Exception as e:
                    log.error("Automation loop error: %s", e)
                time.sleep(poll_interval)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        log.info("Automation engine started.")

    def stop(self) -> None:
        self._running = False
        log.info("Automation engine stopped.")


_auto: Optional[AutomationEngine] = None


def get_automation() -> AutomationEngine:
    global _auto
    if _auto is None:
        _auto = AutomationEngine()
    return _auto
