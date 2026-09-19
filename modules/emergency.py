"""
ROLEX AI — Emergency Stop
A global kill-switch that halts all autonomous activity immediately.

When engaged:
  * automation jobs are paused,
  * voice listening/speaking is stopped,
  * the router refuses to execute tools,
  * an audit entry is written.

It can only be released with an explicit ``release()`` call (optionally
requiring a passphrase via the biometrics module).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional

from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.emergency")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS emergency_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    action     TEXT NOT NULL,
    reason     TEXT,
    created_at REAL NOT NULL
);
"""


@dataclass
class EmergencyState:
    engaged: bool = False
    reason: str = ""
    since: float = 0.0

    def to_dict(self) -> dict:
        return {"engaged": self.engaged, "reason": self.reason, "since": self.since}


class EmergencyStop:
    def __init__(self):
        self.db = get_db()
        self._state = EmergencyState()
        try:
            self.db._conn.executescript(_SCHEMA)
            self.db._conn.commit()
        except Exception as e:  # pragma: no cover
            log.warning("Emergency schema init issue: %s", e)

    def engage(self, reason: str = "manual") -> Dict:
        self._state = EmergencyState(True, reason, time.time())
        self._record("engage", reason)
        log.warning("EMERGENCY STOP engaged: %s", reason)
        # Best-effort: stop automation + voice.
        try:
            from modules.automation import get_automation
            get_automation().stop()
        except Exception:
            pass
        try:
            from modules.voice import get_voice
            get_voice().stop_speaking()
        except Exception:
            pass
        return self._state.to_dict()

    def release(self, passphrase: Optional[str] = None) -> Dict:
        if passphrase is not None:
            try:
                from modules.biometrics import get_biometrics
                res = get_biometrics().verify_secret("emergency", passphrase)
                if not res.ok:
                    return {"ok": False, "error": "Invalid passphrase."}
            except Exception:
                pass
        self._state = EmergencyState(False, "", 0.0)
        self._record("release", "manual")
        log.info("Emergency stop released.")
        return {"ok": True, **self._state.to_dict()}

    def is_engaged(self) -> bool:
        return self._state.engaged

    def status(self) -> Dict:
        return self._state.to_dict()

    def _record(self, action: str, reason: str) -> None:
        self.db.execute(
            "INSERT INTO emergency_events(action, reason, created_at) VALUES(?,?,?)",
            (action, reason, time.time()),
        )

    def history(self, limit: int = 20) -> list:
        rows = self.db.query("SELECT * FROM emergency_events ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]


_estop: Optional[EmergencyStop] = None


def get_emergency() -> EmergencyStop:
    global _estop
    if _estop is None:
        _estop = EmergencyStop()
    return _estop
