"""
ROLEX AI — Vision / Camera
Local-first image analysis, OCR, barcode/QR detection, document scanning.
Optional dependencies degrade gracefully.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from modules.logger import get_logger

log = get_logger("rolex.vision")


class VisionEngine:
    def __init__(self):
        self._ocr_available = self._check_ocr()

    @staticmethod
    def _check_ocr() -> bool:
        try:
            import pytesseract  # type: ignore  # noqa: F401
            from PIL import Image  # type: ignore  # noqa: F401
            return True
        except Exception:
            return False

    def ocr_available(self) -> bool:
        return self._ocr_available

    def extract_text(self, image_path: str) -> Dict:
        p = Path(image_path)
        if not p.exists():
            return {"ok": False, "error": f"Image not found: {image_path}"}
        if not self._ocr_available:
            return {"ok": False, "error": "OCR requires 'pytesseract' and 'Pillow'."}
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
            text = pytesseract.image_to_string(Image.open(str(p)))
            return {"ok": True, "text": text.strip(), "path": str(p)}
        except Exception as e:
            log.error("OCR failed: %s", e)
            return {"ok": False, "error": str(e)}

    def analyze(self, image_path: str) -> Dict:
        p = Path(image_path)
        if not p.exists():
            return {"ok": False, "error": f"Image not found: {image_path}"}
        info = {"ok": True, "path": str(p), "size_kb": round(p.stat().st_size / 1024, 1)}
        try:
            from PIL import Image  # type: ignore
            with Image.open(str(p)) as img:
                info["width"], info["height"] = img.size
                info["mode"] = img.mode
        except Exception:
            pass
        if self._ocr_available:
            info["ocr"] = self.extract_text(image_path)
        return info

    def detect_qr(self, image_path: str) -> Dict:
        """QR/barcode detection placeholder (requires optional libs)."""
        try:
            from pyzbar.pyzbar import decode  # type: ignore
            from PIL import Image  # type: ignore
            codes = decode(Image.open(image_path))
            return {"ok": True, "codes": [c.data.decode("utf-8", "ignore") for c in codes]}
        except Exception as e:
            return {"ok": False, "error": f"QR detection requires 'pyzbar'. ({e})"}


_vision: Optional[VisionEngine] = None


def get_vision() -> VisionEngine:
    global _vision
    if _vision is None:
        _vision = VisionEngine()
    return _vision
