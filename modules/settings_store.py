"""
ROLEX AI — Settings Store
Persists user-entered API keys and preferences to a local JSON file
(data/settings.json) and applies them to the running CONFIG.

Security notes:
  * Keys are stored locally only (never transmitted by this module).
  * Values are masked when displayed.
  * The file is created with 0600 permissions where the OS supports it.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Dict, Optional

from config import CONFIG, DATA_DIR
from modules.logger import get_logger

log = get_logger("rolex.settings")

SETTINGS_PATH = DATA_DIR / "settings.json"

# Capture the config defaults at import time so cleared fields can be reset.
_ORIGINAL_DEFAULTS = {
    attr: getattr(CONFIG, attr, None)
    for (attr, _label, _secret) in [
        ("openai_api_key", "", True), ("openai_model", "", False),
        ("gemini_api_key", "", True), ("gemini_model", "", False),
        ("ollama_base_url", "", False), ("ollama_model", "", False),
        ("huggingface_api_key", "", True), ("huggingface_model", "", False),
        ("elevenlabs_api_key", "", True), ("elevenlabs_voice_id", "", False),
        ("picovoice_access_key", "", True), ("openweather_api_key", "", True),
        ("default_location", "", False), ("wake_word", "", False),
        ("secret_key", "", True),
    ]
}

# Fields the user can edit from the Settings screen.
# key -> (config attribute, label, is_secret)
EDITABLE_FIELDS = {
    "OPENAI_API_KEY":        ("openai_api_key",        "OpenAI API Key",        True),
    "OPENAI_MODEL":          ("openai_model",          "OpenAI Model",          False),
    "GEMINI_API_KEY":        ("gemini_api_key",        "Gemini API Key",        True),
    "GEMINI_MODEL":          ("gemini_model",          "Gemini Model",          False),
    "OLLAMA_BASE_URL":       ("ollama_base_url",       "Ollama Base URL",       False),
    "OLLAMA_MODEL":          ("ollama_model",          "Ollama Model",          False),
    "HUGGINGFACE_API_KEY":   ("huggingface_api_key",   "HuggingFace API Key",   True),
    "HUGGINGFACE_MODEL":     ("huggingface_model",     "HuggingFace Model",     False),
    "ELEVENLABS_API_KEY":    ("elevenlabs_api_key",    "ElevenLabs API Key",    True),
    "ELEVENLABS_VOICE_ID":   ("elevenlabs_voice_id",   "ElevenLabs Voice ID",   False),
    "PICOVOICE_ACCESS_KEY":  ("picovoice_access_key",  "Picovoice Access Key",  True),
    "OPENWEATHER_API_KEY":   ("openweather_api_key",   "OpenWeather API Key",   True),
    "DEFAULT_LOCATION":      ("default_location",      "Default Location",      False),
    "WAKE_WORD":             ("wake_word",             "Wake Word",             False),
    "ROLEX_SECRET_KEY":      ("secret_key",            "Encryption Secret",     True),
}

# Grouping for the UI
FIELD_GROUPS = {
    "AI Providers": [
        "OPENAI_API_KEY", "OPENAI_MODEL",
        "GEMINI_API_KEY", "GEMINI_MODEL",
        "OLLAMA_BASE_URL", "OLLAMA_MODEL",
        "HUGGINGFACE_API_KEY", "HUGGINGFACE_MODEL",
    ],
    "Voice": [
        "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID",
        "PICOVOICE_ACCESS_KEY", "WAKE_WORD",
    ],
    "Services": [
        "OPENWEATHER_API_KEY", "DEFAULT_LOCATION",
    ],
    "Security": [
        "ROLEX_SECRET_KEY",
    ],
}


def _secure_write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except Exception:
        pass


def load_settings() -> Dict[str, str]:
    """Load saved settings from disk (returns {} if none)."""
    if not SETTINGS_PATH.exists():
        return {}
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: str(v) for k, v in data.items() if v is not None}
    except Exception as e:
        log.warning("Could not read settings: %s", e)
    return {}


def apply_settings(values: Optional[Dict[str, str]] = None) -> None:
    """Apply saved (or provided) settings onto the live CONFIG object.

    Keys absent from the store are reset to their original default.
    """
    values = values if values is not None else load_settings()
    for env_key, (attr, _label, _secret) in EDITABLE_FIELDS.items():
        if env_key in values and values[env_key] != "":
            try:
                setattr(CONFIG, attr, values[env_key])
            except Exception:
                pass
        else:
            # Reset to the value captured at import time (env default).
            if attr in _ORIGINAL_DEFAULTS:
                try:
                    setattr(CONFIG, attr, _ORIGINAL_DEFAULTS[attr])
                except Exception:
                    pass


def save_settings(values: Dict[str, str]) -> None:
    """Merge + persist settings, then apply them to CONFIG.

    Empty values remove the key so the environment default applies again.
    """
    current = load_settings()
    for k, v in values.items():
        if k not in EDITABLE_FIELDS:
            continue
        v = "" if v is None else str(v).strip()
        if v == "":
            current.pop(k, None)
        else:
            current[k] = v
    _secure_write(SETTINGS_PATH, json.dumps(current, indent=2))
    apply_settings(current)
    log.info("Settings saved (%d fields)", len(current))


def get_field(env_key: str) -> str:
    """Return the current value for a field (from CONFIG)."""
    attr = EDITABLE_FIELDS.get(env_key, (None, None, None))[0]
    if attr is None:
        return ""
    val = getattr(CONFIG, attr, "")
    return "" if val is None else str(val)


def mask(value: str, visible: int = 4) -> str:
    """Mask a secret for display: sk-1234...cdef -> '••••cdef'."""
    if not value:
        return ""
    if len(value) <= visible:
        return "•" * len(value)
    return "•" * 8 + value[-visible:]


def provider_summary() -> Dict[str, bool]:
    """Return which providers are configured (no secrets exposed)."""
    return CONFIG.provider_status()


# Apply any previously saved settings at import time.
apply_settings()
