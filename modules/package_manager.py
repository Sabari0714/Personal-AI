"""
ROLEX AI — Controlled Package Management
Inspect, plan and (with approval) install Python packages.

Safety model:
  * ``list_installed`` / ``check`` are read-only and always safe.
  * ``plan_install`` produces a dry-run plan (never executes).
  * ``install`` requires explicit approval and is disabled on Android by
    default (pip is not available in a frozen APK).
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

from modules.logger import get_logger

log = get_logger("rolex.package_manager")

# Packages that are safe/known-good to suggest.
KNOWN_PACKAGES = {
    "kivy": "GUI framework (Android + PC)",
    "requests": "HTTP client",
    "pillow": "Image processing",
    "pypdf": "PDF reading",
    "python-docx": "Word documents",
    "openpyxl": "Excel spreadsheets",
    "python-pptx": "PowerPoint",
    "speechrecognition": "Speech-to-text",
    "pyttsx3": "Text-to-speech (desktop)",
    "pytesseract": "OCR",
    "cryptography": "Encryption",
    "numpy": "Numerical computing",
    "sympy": "Symbolic math",
}


@dataclass
class PackageInfo:
    name: str
    installed: bool
    description: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "installed": self.installed,
                "description": self.description}


class PackageManager:
    def __init__(self):
        self._is_android = self._detect_android()

    @staticmethod
    def _detect_android() -> bool:
        try:
            from modules.voice_android import is_android
            return is_android()
        except Exception:
            return "ANDROID_ARGUMENT" in __import__("os").environ

    def is_installed(self, name: str) -> bool:
        mod = name.replace("-", "_").lower()
        aliases = {"pillow": "PIL", "pypdf": "pypdf", "python-docx": "docx",
                   "python-pptx": "pptx", "speechrecognition": "speech_recognition",
                   "pyttsx3": "pyttsx3", "pytesseract": "pytesseract"}
        mod = aliases.get(name.lower(), mod)
        try:
            return importlib.util.find_spec(mod) is not None
        except Exception:
            return False

    def check(self, name: str) -> PackageInfo:
        return PackageInfo(name, self.is_installed(name),
                           KNOWN_PACKAGES.get(name.lower(), ""))

    def list_known(self) -> List[PackageInfo]:
        return [self.check(n) for n in KNOWN_PACKAGES]

    def list_installed(self) -> List[str]:
        try:
            out = subprocess.run([sys.executable, "-m", "pip", "list", "--format=freeze"],
                                 capture_output=True, text=True, timeout=20)
            if out.returncode == 0:
                return [line.split("==")[0] for line in out.stdout.splitlines() if line]
        except Exception as e:
            log.info("pip list unavailable: %s", e)
        return []

    def plan_install(self, name: str) -> Dict:
        """Dry-run plan — never installs."""
        return {
            "action": "install",
            "package": name,
            "command": f"{sys.executable} -m pip install {name}",
            "installed": self.is_installed(name),
            "android": self._is_android,
            "note": ("On Android, packages must be added to buildozer.spec "
                     "requirements and rebuilt — runtime pip is unavailable."
                     if self._is_android else "Run with approval to install."),
        }

    def install(self, name: str, approved: bool = False) -> Dict:
        if not approved:
            return {"ok": False, "error": "Approval required to install packages."}
        if self._is_android:
            return {"ok": False, "error": "Runtime installs are disabled on Android. "
                                          "Add the package to buildozer.spec and rebuild."}
        try:
            out = subprocess.run([sys.executable, "-m", "pip", "install", name],
                                 capture_output=True, text=True, timeout=180)
            return {"ok": out.returncode == 0, "stdout": out.stdout[-4000:],
                    "stderr": out.stderr[-2000:]}
        except Exception as e:
            return {"ok": False, "error": str(e)}


_pm: Optional[PackageManager] = None


def get_package_manager() -> PackageManager:
    global _pm
    if _pm is None:
        _pm = PackageManager()
    return _pm
