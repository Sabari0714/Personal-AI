"""
ROLEX AI — Device Management
Read device/system information and perform safe device actions.

On Android it uses pyjnius to read battery, storage, connectivity and to
trigger vibration / torch where permitted. On desktop it falls back to
stdlib (platform, shutil, os) so the module always works.
"""
from __future__ import annotations

import os
import platform
import shutil
import time
from typing import Dict, Optional

from modules.logger import get_logger

log = get_logger("rolex.device")


class DeviceManager:
    def __init__(self):
        self._android = self._detect_android()

    @staticmethod
    def _detect_android() -> bool:
        try:
            from modules.voice_android import is_android
            return is_android()
        except Exception:
            return "ANDROID_ARGUMENT" in os.environ

    # -- info ---------------------------------------------------------------
    def info(self) -> Dict:
        info = {
            "platform": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "android": self._android,
            "cpu_count": os.cpu_count(),
        }
        try:
            total, used, free = shutil.disk_usage("/")
            info["storage"] = {"total_gb": round(total / 1e9, 2),
                               "used_gb": round(used / 1e9, 2),
                               "free_gb": round(free / 1e9, 2),
                               "percent_used": round(used / total * 100, 1)}
        except Exception:
            pass
        if self._android:
            info.update(self._android_info())
        return info

    def _android_info(self) -> Dict:
        out: Dict = {}
        try:
            from jnius import autoclass  # type: ignore
            from modules.voice_android import _activity
            activity = _activity()
            if activity is None:
                return out
            # Battery
            try:
                Intent = autoclass("android.content.Intent")
                IntentFilter = autoclass("android.content.IntentFilter")
                BatteryManager = autoclass("android.os.BatteryManager")
                intent = activity.registerReceiver(None, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
                level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
                scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
                if level >= 0 and scale > 0:
                    out["battery_percent"] = round(level / scale * 100, 1)
            except Exception as e:
                log.debug("Battery read failed: %s", e)
            # Build info
            try:
                Build = autoclass("android.os.Build")
                out["model"] = str(Build.MODEL)
                out["manufacturer"] = str(Build.MANUFACTURER)
                out["android_version"] = str(Build.VERSION.RELEASE)
            except Exception:
                pass
        except Exception as e:
            log.debug("Android info unavailable: %s", e)
        return out

    # -- actions ------------------------------------------------------------
    def vibrate(self, ms: int = 300) -> Dict:
        if not self._android:
            return {"ok": False, "error": "Vibration is Android-only."}
        try:
            from jnius import autoclass  # type: ignore
            from modules.voice_android import _activity
            activity = _activity()
            Context = autoclass("android.content.Context")
            vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
            vibrator.vibrate(int(ms))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_torch(self, on: bool) -> Dict:
        if not self._android:
            return {"ok": False, "error": "Torch is Android-only."}
        try:
            from jnius import autoclass  # type: ignore
            from modules.voice_android import _activity
            activity = _activity()
            Context = autoclass("android.content.Context")
            camera_manager = activity.getSystemService(Context.CAMERA_SERVICE)
            cam_id = camera_manager.getCameraIdList()[0]
            camera_manager.setTorchMode(cam_id, bool(on))
            return {"ok": True, "on": bool(on)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def battery(self) -> Dict:
        return {"battery_percent": self._android_info().get("battery_percent")}

    def storage(self) -> Dict:
        try:
            total, used, free = shutil.disk_usage("/")
            return {"total_gb": round(total / 1e9, 2), "used_gb": round(used / 1e9, 2),
                    "free_gb": round(free / 1e9, 2)}
        except Exception as e:
            return {"error": str(e)}


_device: Optional[DeviceManager] = None


def get_device() -> DeviceManager:
    global _device
    if _device is None:
        _device = DeviceManager()
    return _device
