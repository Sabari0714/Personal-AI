"""
ROLEX AI — Logging System
Detailed for developers, safe for users (no secrets in logs).
"""
from __future__ import annotations

import logging
import logging.handlers
import re
from pathlib import Path

from config import LOGS_DIR, CONFIG

_SECRET_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9_\-]{10,})"),
    re.compile(r"(AIza[A-Za-z0-9_\-]{10,})"),
    re.compile(r"(hf_[A-Za-z0-9]{10,})"),
    re.compile(r"(?i)(api[_-]?key['\"]?\s*[:=]\s*['\"]?)([A-Za-z0-9_\-]{8,})"),
    re.compile(r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?)([A-Za-z0-9_\-\.]{8,})"),
]


class SecretRedactor(logging.Filter):
    """Redacts anything that looks like a secret from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            for pat in _SECRET_PATTERNS:
                msg = pat.sub(lambda m: (m.group(1) if m.lastindex and m.lastindex > 1 else "") + "***REDACTED***", msg)
            record.msg = msg
            record.args = ()
        except Exception:
            pass
        return True


_configured = False


def get_logger(name: str = "rolex") -> logging.Logger:
    global _configured
    logger = logging.getLogger(name)
    if _configured:
        return logger

    logger.setLevel(getattr(logging, str(CONFIG.log_level).upper(), logging.INFO))
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.addFilter(SecretRedactor())
    logger.addHandler(ch)

    # Rotating file handler
    try:
        fh = logging.handlers.RotatingFileHandler(
            LOGS_DIR / "rolex.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        fh.addFilter(SecretRedactor())
        logger.addHandler(fh)
    except Exception:
        pass

    _configured = True
    return logger


def user_safe_error(exc: Exception) -> str:
    """Convert an exception into a user-friendly message (no traceback)."""
    return (
        "I couldn't complete that because the required module is unavailable "
        f"({type(exc).__name__}). Please check the developer logs for details."
    )
