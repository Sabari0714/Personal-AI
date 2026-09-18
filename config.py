"""
ROLEX AI — Central Configuration
Local-first personal AI operating system.

All configuration is loaded from environment variables (.env) with safe defaults.
No secrets are ever hard-coded here.
"""
from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"
DOCS_DIR = BASE_DIR / "docs"
BUILD_DIR = BASE_DIR / "build"

for _d in (DATA_DIR, LOGS_DIR, ASSETS_DIR, DOCS_DIR, BUILD_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "rolex.db"


# ---------------------------------------------------------------------------
# Minimal .env loader (no external dependency required)
# ---------------------------------------------------------------------------
def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # Do not overwrite already-set environment variables
            os.environ.setdefault(key, value)
    except Exception:
        # Never crash on a malformed .env
        pass


_load_dotenv(BASE_DIR / ".env")


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    val = os.environ.get(key)
    if val is None or val == "":
        return default
    return val


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on", "y")


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------
@dataclass
class RolexConfig:
    # Identity
    app_name: str = "ROLEX AI"
    version: str = "1.0.0"
    codename: str = "Rolex"

    # Policy
    # When True, external LLM providers are NEVER called silently.
    rolex_only_mode: bool = field(default_factory=lambda: _env_bool("ROLEX_ONLY_MODE", False))
    # When True, external providers may be used (still requires explicit keys).
    allow_external_ai: bool = field(default_factory=lambda: _env_bool("ALLOW_EXTERNAL_AI", True))
    # Require human approval for sensitive operations.
    require_approval: bool = field(default_factory=lambda: _env_bool("REQUIRE_APPROVAL", True))

    # AI Providers
    openai_api_key: Optional[str] = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: _env("OPENAI_MODEL", "gpt-4o-mini"))
    openai_base_url: str = field(default_factory=lambda: _env("OPENAI_BASE_URL", "https://api.openai.com/v1"))

    gemini_api_key: Optional[str] = field(default_factory=lambda: _env("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: _env("GEMINI_MODEL", "gemini-1.5-flash"))
    gemini_base_url: str = field(
        default_factory=lambda: _env("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
    )

    ollama_base_url: str = field(default_factory=lambda: _env("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: _env("OLLAMA_MODEL", "llama3"))

    huggingface_api_key: Optional[str] = field(default_factory=lambda: _env("HUGGINGFACE_API_KEY"))
    huggingface_model: str = field(
        default_factory=lambda: _env("HUGGINGFACE_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
    )

    elevenlabs_api_key: Optional[str] = field(default_factory=lambda: _env("ELEVENLABS_API_KEY"))
    elevenlabs_voice_id: str = field(default_factory=lambda: _env("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"))

    picovoice_access_key: Optional[str] = field(default_factory=lambda: _env("PICOVOICE_ACCESS_KEY"))

    # Weather
    openweather_api_key: Optional[str] = field(default_factory=lambda: _env("OPENWEATHER_API_KEY"))
    default_location: str = field(default_factory=lambda: _env("DEFAULT_LOCATION", "Chennai"))

    # Network
    http_timeout: float = field(default_factory=lambda: _env_float("HTTP_TIMEOUT", 20.0))
    http_retries: int = field(default_factory=lambda: _env_int("HTTP_RETRIES", 2))

    # Voice
    wake_word: str = field(default_factory=lambda: _env("WAKE_WORD", "hey rolex"))
    voice_enabled: bool = field(default_factory=lambda: _env_bool("VOICE_ENABLED", True))
    tts_rate: int = field(default_factory=lambda: _env_int("TTS_RATE", 175))

    # Security
    secret_key: Optional[str] = field(default_factory=lambda: _env("ROLEX_SECRET_KEY"))

    # Logging
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))

    # Database
    db_path: Path = field(default_factory=lambda: DB_PATH)

    def provider_status(self) -> dict:
        """Return which providers are configured (without exposing secrets)."""
        return {
            "local": True,
            "openai": bool(self.openai_api_key),
            "gemini": bool(self.gemini_api_key),
            "ollama": bool(self.ollama_base_url),
            "huggingface": bool(self.huggingface_api_key),
            "elevenlabs": bool(self.elevenlabs_api_key),
            "picovoice": bool(self.picovoice_access_key),
            "openweather": bool(self.openweather_api_key),
        }


CONFIG = RolexConfig()
