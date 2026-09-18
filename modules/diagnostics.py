"""
ROLEX AI — Diagnostics
System health: network, storage, CPU, memory, version, module status.
"""
from __future__ import annotations

import os
import platform
import shutil
import sys
import time
from typing import Dict

from config import CONFIG, BASE_DIR
from modules.logger import get_logger

log = get_logger("rolex.diagnostics")


class Diagnostics:
    def __init__(self):
        self._start = time.time()

    def system_info(self) -> Dict:
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
            "processor": platform.processor() or "unknown",
            "uptime_seconds": round(time.time() - self._start, 1),
        }
        return info

    def storage_info(self) -> Dict:
        try:
            total, used, free = shutil.disk_usage(str(BASE_DIR))
            return {
                "total_gb": round(total / 1e9, 2),
                "used_gb": round(used / 1e9, 2),
                "free_gb": round(free / 1e9, 2),
                "percent_used": round(100 * used / total, 1) if total else 0,
            }
        except Exception as e:
            return {"error": str(e)}

    def memory_info(self) -> Dict:
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {"max_rss_mb": round(usage.ru_maxrss / 1024, 2)}
        except Exception:
            return {"max_rss_mb": "unavailable"}

    def cpu_info(self) -> Dict:
        return {"cpu_count": os.cpu_count() or 1, "load_avg": self._load_avg()}

    @staticmethod
    def _load_avg():
        try:
            return [round(x, 2) for x in os.getloadavg()]
        except Exception:
            return "unavailable"

    def network_info(self) -> Dict:
        try:
            from modules.web import get_web
            online = get_web().is_online()
        except Exception:
            online = False
        return {"online": online}

    def module_status(self) -> Dict[str, bool]:
        modules = ["memory", "math_engine", "tasks", "planner", "documents",
                   "knowledge", "providers", "parallel_ai", "verification",
                   "web", "voice", "security", "policy", "automation",
                   "diagnostics", "package_check", "plugins", "sync", "vision"]
        status = {}
        for m in modules:
            try:
                __import__(f"modules.{m}")
                status[m] = True
            except Exception:
                status[m] = False
        return status

    def report(self) -> Dict:
        sysinfo = self.system_info()
        storage = self.storage_info()
        net = self.network_info()
        mods = self.module_status()
        ok_mods = sum(1 for v in mods.values() if v)
        summary = (
            f"ROLEX AI {CONFIG.version} diagnostics\n"
            f"Platform: {sysinfo['system']} {sysinfo['machine']} | Python {sysinfo['python']}\n"
            f"Network: {'online' if net['online'] else 'offline'}\n"
            f"Storage: {storage.get('free_gb', '?')} GB free of {storage.get('total_gb', '?')} GB\n"
            f"Modules: {ok_mods}/{len(mods)} loaded"
        )
        return {
            "summary": summary,
            "system": sysinfo,
            "storage": storage,
            "memory": self.memory_info(),
            "cpu": self.cpu_info(),
            "network": net,
            "modules": mods,
        }


_diag = None


def get_diagnostics() -> Diagnostics:
    global _diag
    if _diag is None:
        _diag = Diagnostics()
    return _diag
