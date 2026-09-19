"""
ROLEX AI — Recovery & Self-Healing
Backup/restore orchestration, integrity checks, self-heal routines and
diagnostic-driven recovery. Local-first; safe by default.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

from config import BASE_DIR, DATA_DIR, CONFIG
from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.recovery")

RECOVERY_DIR = DATA_DIR / "recovery"
SNAPSHOT_DIR = RECOVERY_DIR / "snapshots"


class RecoveryManager:
    """Coordinates backups, integrity checks and self-healing."""

    def __init__(self):
        self.db = get_db()
        RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Snapshots
    # ------------------------------------------------------------------ #
    def snapshot(self, label: Optional[str] = None) -> Dict:
        """Create a full recovery snapshot (database + config manifest)."""
        label = label or time.strftime("%Y%m%d_%H%M%S")
        folder = SNAPSHOT_DIR / label
        folder.mkdir(parents=True, exist_ok=True)
        try:
            db_copy = folder / "rolex.db"
            self.db.backup(db_copy)
            manifest = {
                "label": label,
                "created": time.time(),
                "version": CONFIG.version,
                "files": [db_copy.name],
            }
            (folder / "manifest.json").write_text(
                json.dumps(manifest, indent=2), encoding="utf-8")
            log.info("Recovery snapshot created: %s", label)
            return {"ok": True, "label": label, "path": str(folder)}
        except Exception as e:
            log.error("Snapshot failed: %s", e)
            return {"ok": False, "error": str(e)}

    def snapshots(self) -> List[Dict]:
        out = []
        for folder in sorted(SNAPSHOT_DIR.glob("*"), reverse=True):
            man = folder / "manifest.json"
            if not man.exists():
                continue
            try:
                data = json.loads(man.read_text(encoding="utf-8"))
                data["path"] = str(folder)
                out.append(data)
            except Exception:
                continue
        return out

    def restore_snapshot(self, label: str) -> Dict:
        folder = SNAPSHOT_DIR / label
        db_copy = folder / "rolex.db"
        if not db_copy.exists():
            return {"ok": False, "error": f"Snapshot '{label}' not found."}
        try:
            ok = self.db.restore(db_copy)
            return {"ok": bool(ok), "label": label}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------------------ #
    # Integrity
    # ------------------------------------------------------------------ #
    def integrity_check(self) -> Dict:
        """Run SQLite integrity check plus basic file checks."""
        result = {"ok": True, "issues": []}
        try:
            ok = self.db.integrity_check()
            result["database"] = "ok" if ok else "corrupt"
            if not ok:
                result["ok"] = False
                result["issues"].append("database integrity check failed")
        except Exception as e:
            result["ok"] = False
            result["issues"].append(f"database error: {e}")

        for name in ("config.py", "app.py", "main.py"):
            if not (BASE_DIR / name).exists():
                result["ok"] = False
                result["issues"].append(f"missing file: {name}")
        return result

    # ------------------------------------------------------------------ #
    # Self-heal
    # ------------------------------------------------------------------ #
    def self_heal(self) -> Dict:
        """Attempt automatic recovery of common problems."""
        actions = []
        # 1. Ensure core directories exist.
        for d in (DATA_DIR, DATA_DIR / "backups", RECOVERY_DIR, SNAPSHOT_DIR):
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
                actions.append(f"created {d.name}")
        # 2. Re-initialise database schema if integrity failed.
        check = self.integrity_check()
        if not check["ok"]:
            try:
                self.db._init_schema()
                actions.append("re-initialised database schema")
            except Exception as e:
                actions.append(f"schema re-init failed: {e}")
        # 3. Prune stale snapshots (keep newest 10).
        snaps = sorted(SNAPSHOT_DIR.glob("*"), reverse=True)
        for old in snaps[10:]:
            try:
                shutil.rmtree(old)
                actions.append(f"pruned snapshot {old.name}")
            except Exception:
                pass
        healed = bool(actions)
        log.info("Self-heal actions: %s", actions or "none")
        return {"ok": True, "healed": healed, "actions": actions,
                "integrity": check}

    # ------------------------------------------------------------------ #
    # Diagnostics bridge
    # ------------------------------------------------------------------ #
    def full_report(self) -> Dict:
        try:
            from modules.diagnostics import get_diagnostics
            diag = get_diagnostics().report()
        except Exception as e:
            diag = {"error": str(e)}
        return {
            "integrity": self.integrity_check(),
            "snapshots": len(self.snapshots()),
            "diagnostics": diag,
        }


_recovery: Optional[RecoveryManager] = None


def get_recovery() -> RecoveryManager:
    global _recovery
    if _recovery is None:
        _recovery = RecoveryManager()
    return _recovery
