"""
ROLEX AI — Vision / Camera
Local-first image analysis, OCR, barcode/QR detection, document scanning and
camera capture (Android via pyjnius, desktop via OpenCV/PIL). Optional
dependencies degrade gracefully.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Optional

from config import DATA_DIR
from modules.logger import get_logger

log = get_logger("rolex.vision")

CAPTURE_DIR = DATA_DIR / "captures"


def _is_android() -> bool:
    try:
        from kivy.utils import platform  # type: ignore
        return platform == "android"
    except Exception:
        return False


class VisionEngine:
    def __init__(self):
        self._ocr_available = self._check_ocr()
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Capability probes
    # ------------------------------------------------------------------ #
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

    def camera_available(self) -> bool:
        if _is_android():
            try:
                from jnius import autoclass  # type: ignore  # noqa: F401
                return True
            except Exception:
                return False
        try:
            import cv2  # type: ignore  # noqa: F401
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # Camera capture
    # ------------------------------------------------------------------ #
    def capture(self, filename: Optional[str] = None) -> Dict:
        """Capture a still image from the device camera.

        Android: uses the native Camera intent via pyjnius.
        Desktop: uses OpenCV VideoCapture (first frame).
        """
        filename = filename or f"capture_{int(time.time())}.jpg"
        dest = CAPTURE_DIR / filename
        if _is_android():
            return self._capture_android(dest)
        return self._capture_desktop(dest)

    def _capture_android(self, dest: Path) -> Dict:
        try:
            from jnius import autoclass  # type: ignore
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            MediaStore = autoclass("android.provider.MediaStore")
            activity_obj = PythonActivity.mActivity
            intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
            activity_obj.startActivity(intent)
            return {"ok": True, "path": str(dest),
                    "note": "Android camera intent launched; image saved by system."}
        except Exception as e:
            log.error("Android capture failed: %s", e)
            return {"ok": False, "error": str(e)}

    def _capture_desktop(self, dest: Path) -> Dict:
        try:
            import cv2  # type: ignore
            cam = cv2.VideoCapture(0)
            if not cam.isOpened():
                return {"ok": False, "error": "No camera device found."}
            ok, frame = cam.read()
            cam.release()
            if not ok:
                return {"ok": False, "error": "Failed to read frame."}
            cv2.imwrite(str(dest), frame)
            return {"ok": True, "path": str(dest)}
        except Exception as e:
            return {"ok": False, "error": f"Camera capture requires 'opencv-python'. ({e})"}

    # ------------------------------------------------------------------ #
    # Analysis
    # ------------------------------------------------------------------ #
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
        """QR/barcode detection (requires optional 'pyzbar')."""
        try:
            from pyzbar.pyzbar import decode  # type: ignore
            from PIL import Image  # type: ignore
            codes = decode(Image.open(image_path))
            return {"ok": True, "codes": [c.data.decode("utf-8", "ignore") for c in codes]}
        except Exception as e:
            return {"ok": False, "error": f"QR detection requires 'pyzbar'. ({e})"}

    def scan_document(self, image_path: str) -> Dict:
        """Document scan: OCR + basic metadata, ready for the documents module."""
        result = self.analyze(image_path)
        if result.get("ok") and self._ocr_available:
            text = result.get("ocr", {}).get("text", "")
            result["document_text"] = text
            result["word_count"] = len(text.split())
        return result


_vision: Optional[VisionEngine] = None


def get_vision() -> VisionEngine:
    global _vision
    if _vision is None:
        _vision = VisionEngine()
    return _vision
