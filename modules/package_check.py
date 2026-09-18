"""
ROLEX AI — Package / Dependency Check
Validates optional dependencies and reports what is available.
Optional dependencies must fail gracefully.
"""
from __future__ import annotations

import importlib
from typing import Dict, List

from modules.logger import get_logger

log = get_logger("rolex.package_check")

# name -> (import_name, purpose, required)
OPTIONAL_PACKAGES = {
    "kivy": ("kivy", "GUI framework", False),
    "pypdf": ("pypdf", "PDF reading", False),
    "PyPDF2": ("PyPDF2", "PDF reading (legacy)", False),
    "python-docx": ("docx", "DOCX reading", False),
    "openpyxl": ("openpyxl", "XLSX reading", False),
    "python-pptx": ("pptx", "PPTX reading", False),
    "requests": ("requests", "HTTP (optional)", False),
    "speech_recognition": ("speech_recognition", "Voice input", False),
    "pyttsx3": ("pyttsx3", "Text-to-speech", False),
    "pvporcupine": ("pvporcupine", "Wake word", False),
    "openwakeword": ("openwakeword", "Wake word (open)", False),
    "Pillow": ("PIL", "Image processing", False),
    "pytesseract": ("pytesseract", "OCR", False),
    "plyer": ("plyer", "Android platform APIs", False),
    "cryptography": ("cryptography", "Encryption", False),
}


def check_package(import_name: str) -> bool:
    try:
        importlib.import_module(import_name)
        return True
    except Exception:
        return False


def check_all() -> Dict[str, Dict]:
    results = {}
    for name, (imp, purpose, required) in OPTIONAL_PACKAGES.items():
        available = check_package(imp)
        results[name] = {"available": available, "purpose": purpose, "required": required}
    return results


def missing_optional() -> List[str]:
    return [name for name, info in check_all().items() if not info["available"]]


def summary() -> str:
    results = check_all()
    avail = sum(1 for v in results.values() if v["available"])
    lines = [f"{'✓' if v['available'] else '✗'} {k} — {v['purpose']}"
             for k, v in results.items()]
    return f"Optional packages: {avail}/{len(results)} available\n" + "\n".join(lines)
