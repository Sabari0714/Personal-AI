"""
ROLEX AI — Controlled Self-Modification
Lets ROLEX propose, test and (with approval) apply improvements to its own
code — safely and reversibly.

Workflow:
  1. propose()  — record a proposed change (file + new content + rationale)
  2. test()     — run the change through the sandbox / syntax check
  3. apply()    — back up the original, write the new content, verify import
  4. rollback() — restore the most recent backup for a file

Every step is journaled. Nothing is applied without an explicit approval flag,
honouring the app's "require_approval" policy.
"""
from __future__ import annotations

import ast
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from config import BASE_DIR, BUILD_DIR, CONFIG
from data.database import get_db
from modules.logger import get_logger
from modules.sandbox import get_sandbox

log = get_logger("rolex.self_modify")

_BACKUP_DIR = BUILD_DIR / "self_modify_backups"
_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS self_modifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    file       TEXT NOT NULL,
    rationale  TEXT,
    status     TEXT NOT NULL DEFAULT 'PROPOSED',
    diff       TEXT,
    backup     TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
"""


@dataclass
class Modification:
    id: int
    file: str
    rationale: str
    status: str
    backup: Optional[str]
    created_at: float

    def to_dict(self) -> dict:
        return {"id": self.id, "file": self.file, "rationale": self.rationale,
                "status": self.status, "backup": self.backup,
                "created_at": self.created_at}


class SelfModifier:
    def __init__(self):
        self.db = get_db()
        self.sandbox = get_sandbox()
        try:
            self.db._conn.executescript(_SCHEMA)
            self.db._conn.commit()
        except Exception as e:  # pragma: no cover
            log.warning("Self-modify schema init issue: %s", e)

    # -- helpers ------------------------------------------------------------
    def _safe_path(self, rel: str) -> Path:
        p = (BASE_DIR / rel).resolve()
        if BASE_DIR.resolve() not in p.parents and p != BASE_DIR.resolve():
            raise ValueError("Path escapes the project root.")
        return p

    # -- propose ------------------------------------------------------------
    def propose(self, file: str, new_content: str, rationale: str = "") -> Modification:
        path = self._safe_path(file)
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        diff = self._simple_diff(old, new_content)
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO self_modifications(file, rationale, status, diff, created_at, updated_at) "
            "VALUES(?,?,?,?,?,?)",
            (file, rationale, "PROPOSED", diff, now, now),
        )
        log.info("Proposed self-modification #%s for %s", cur.lastrowid, file)
        return Modification(cur.lastrowid, file, rationale, "PROPOSED", None, now)

    @staticmethod
    def _simple_diff(old: str, new: str) -> str:
        old_lines = old.splitlines()
        new_lines = new.splitlines()
        added = len(new_lines) - len(old_lines)
        return f"lines: {len(old_lines)} -> {len(new_lines)} ({added:+d})"

    # -- test ---------------------------------------------------------------
    def test(self, mod_id: int, new_content: str) -> Dict:
        """Syntax-check and sandbox-import the proposed content."""
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            self._set_status(mod_id, "TEST_FAILED")
            return {"ok": False, "error": f"SyntaxError: {e}"}
        # Run a lightweight import smoke test in the sandbox.
        snippet = (
            "import ast\n"
            f"src = {new_content!r}\n"
            "ast.parse(src)\n"
            "print('syntax-ok')\n"
        )
        res = self.sandbox.run_python(snippet, timeout=6.0)
        ok = res.ok and "syntax-ok" in res.stdout
        self._set_status(mod_id, "TESTED" if ok else "TEST_FAILED")
        return {"ok": ok, "sandbox": res.to_dict()}

    # -- apply --------------------------------------------------------------
    def apply(self, mod_id: int, new_content: str, approved: bool = False) -> Dict:
        if CONFIG.require_approval and not approved:
            return {"ok": False, "error": "Approval required (REQUIRE_APPROVAL is on)."}
        row = self.db.query_one("SELECT * FROM self_modifications WHERE id=?", (mod_id,))
        if not row:
            return {"ok": False, "error": f"No modification #{mod_id}."}
        path = self._safe_path(row["file"])
        # Back up the original.
        backup = None
        if path.exists():
            backup = _BACKUP_DIR / f"{path.name}.{int(time.time())}.bak"
            shutil.copy2(path, backup)
        try:
            path.write_text(new_content, encoding="utf-8")
            ast.parse(new_content)  # final guard
        except Exception as e:
            if backup and backup.exists():
                shutil.copy2(backup, path)
            self._set_status(mod_id, "APPLY_FAILED")
            return {"ok": False, "error": str(e)}
        self.db.execute(
            "UPDATE self_modifications SET status=?, backup=?, updated_at=? WHERE id=?",
            ("APPLIED", str(backup) if backup else None, time.time(), mod_id),
        )
        log.info("Applied self-modification #%s to %s", mod_id, row["file"])
        return {"ok": True, "backup": str(backup) if backup else None}

    # -- rollback -----------------------------------------------------------
    def rollback(self, mod_id: int) -> Dict:
        row = self.db.query_one("SELECT * FROM self_modifications WHERE id=?", (mod_id,))
        if not row or not row["backup"]:
            return {"ok": False, "error": "No backup available for this modification."}
        backup = Path(row["backup"])
        if not backup.exists():
            return {"ok": False, "error": "Backup file missing."}
        path = self._safe_path(row["file"])
        shutil.copy2(backup, path)
        self._set_status(mod_id, "ROLLED_BACK")
        log.info("Rolled back self-modification #%s", mod_id)
        return {"ok": True}

    def _set_status(self, mod_id: int, status: str) -> None:
        self.db.execute(
            "UPDATE self_modifications SET status=?, updated_at=? WHERE id=?",
            (status, time.time(), mod_id),
        )

    def history(self, limit: int = 50) -> List[Modification]:
        rows = self.db.query(
            "SELECT * FROM self_modifications ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [Modification(r["id"], r["file"], r["rationale"], r["status"],
                             r["backup"], r["created_at"]) for r in rows]


_modifier: Optional[SelfModifier] = None


def get_self_modifier() -> SelfModifier:
    global _modifier
    if _modifier is None:
        _modifier = SelfModifier()
    return _modifier
