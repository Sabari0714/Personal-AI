"""
ROLEX AI — Cloud Sync / Backup
Optional database, configuration and document backup. Local-first; cloud optional.
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

log = get_logger("rolex.sync")

BACKUP_DIR = DATA_DIR / "backups"


class SyncManager:
    def __init__(self):
        self.db = get_db()
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    def backup_local(self, label: Optional[str] = None) -> Path:
        label = label or time.strftime("%Y%m%d_%H%M%S")
        dest = BACKUP_DIR / f"rolex_{label}.db"
        self.db.backup(dest)
        return dest

    def list_backups(self) -> List[Dict]:
        out = []
        for p in sorted(BACKUP_DIR.glob("rolex_*.db"), reverse=True):
            out.append({"path": str(p), "size_kb": round(p.stat().st_size / 1024, 1),
                        "modified": p.stat().st_mtime})
        return out

    def restore(self, path: str) -> bool:
        return self.db.restore(Path(path))

    def export_config(self) -> Path:
        dest = BACKUP_DIR / f"config_{time.strftime('%Y%m%d_%H%M%S')}.json"
        safe = {
            "version": CONFIG.version,
            "rolex_only_mode": CONFIG.rolex_only_mode,
            "allow_external_ai": CONFIG.allow_external_ai,
            "default_location": CONFIG.default_location,
            "wake_word": CONFIG.wake_word,
            "providers": CONFIG.provider_status(),
        }
        dest.write_text(json.dumps(safe, indent=2), encoding="utf-8")
        return dest

    def cloud_sync(self, provider: str = "drive") -> Dict:
        """Placeholder for optional cloud sync (Google Drive etc.)."""
        return {"ok": False, "error": f"Cloud sync provider '{provider}' not configured. "
                                      "Local backup is available."}


_sync: Optional[SyncManager] = None


def get_sync() -> SyncManager:
    global _sync
    if _sync is None:
        _sync = SyncManager()
    return _sync
