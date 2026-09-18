"""
ROLEX AI — AI Provider Architecture
Local engine + optional OpenAI, Gemini, Ollama, HuggingFace connectors.
External providers are NEVER called silently (Rolex-only policy enforced upstream).
All connectors use only the standard library (urllib) so they work on Android/Termux.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional

from config import CONFIG
from modules.logger import get_logger

log = get_logger("rolex.providers")


@dataclass
class AIResponse:
    provider: str
    text: str
    ok: bool
    error: Optional[str] = None
    latency: float = 0.0

    def to_dict(self) -> dict:
        return {"provider": self.provider, "text": self.text, "ok": self.ok,
                "error": self.error, "latency": self.latency}


def _post_json(url: str, payload: dict, headers: Dict[str, str], timeout: float) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str, headers: Dict[str, str], timeout: float) -> dict:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Base provider
# ---------------------------------------------------------------------------
class BaseProvider:
    name = "base"

    def available(self) -> bool:
        return False

    def generate(self, prompt: str, system: Optional[str] = None) -> AIResponse:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Local provider (offline heuristic engine)
# ---------------------------------------------------------------------------
class LocalProvider(BaseProvider):
    name = "local"

    def available(self) -> bool:
        return True

    def generate(self, prompt: str, system: Optional[str] = None) -> AIResponse:
        import time
        t0 = time.time()
        text = self._respond(prompt)
        return AIResponse(self.name, text, True, latency=time.time() - t0)

    def _respond(self, prompt: str) -> str:
        p = (prompt or "").strip()
        low = p.lower()
        if not p:
            return "I'm here. Ask me anything, or say 'help' to see what I can do."
        if any(g in low for g in ("hello", "hi ", "hey", "vanakkam", "hai")):
            return "Vanakkam! I am Rolex, your personal AI assistant. How can I help you today?"
        if "who are you" in low or "your name" in low:
            return "I am Rolex AI — a local-first personal assistant running on your device."
        if "help" in low:
            return ("I can: remember things, manage tasks, do math, read documents, "
                    "plan goals, check weather, search the web, and run diagnostics. "
                    "Try: 'remember that I prefer local AI' or 'calculate 25*4'.")
        # Offline fallback: acknowledge and offer local tools
        return ("I'm running in local mode right now. I can still help with math, memory, "
                "tasks, plans, documents and diagnostics. For open-ended questions, "
                "enable an AI provider (OpenAI/Gemini/Ollama) in settings.")


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------
class OpenAIProvider(BaseProvider):
    name = "openai"

    def available(self) -> bool:
        return bool(CONFIG.openai_api_key)

    def generate(self, prompt: str, system: Optional[str] = None) -> AIResponse:
        import time
        if not self.available():
            return AIResponse(self.name, "", False, "OpenAI API key not configured.")
        t0 = time.time()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": CONFIG.openai_model, "messages": messages, "temperature": 0.7}
        headers = {"Authorization": f"Bearer {CONFIG.openai_api_key}",
                   "Content-Type": "application/json"}
        try:
            data = _post_json(f"{CONFIG.openai_base_url}/chat/completions",
                              payload, headers, CONFIG.http_timeout)
            text = data["choices"][0]["message"]["content"]
            return AIResponse(self.name, text, True, latency=time.time() - t0)
        except urllib.error.HTTPError as e:
            return AIResponse(self.name, "", False, f"HTTP {e.code}", time.time() - t0)
        except Exception as e:
            return AIResponse(self.name, "", False, str(e), time.time() - t0)


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------
class GeminiProvider(BaseProvider):
    name = "gemini"

    def available(self) -> bool:
        return bool(CONFIG.gemini_api_key)

    def generate(self, prompt: str, system: Optional[str] = None) -> AIResponse:
        import time
        if not self.available():
            return AIResponse(self.name, "", False, "Gemini API key not configured.")
        t0 = time.time()
        url = (f"{CONFIG.gemini_base_url}/models/{CONFIG.gemini_model}:generateContent"
               f"?key={CONFIG.gemini_api_key}")
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        headers = {"Content-Type": "application/json"}
        try:
            data = _post_json(url, payload, headers, CONFIG.http_timeout)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return AIResponse(self.name, text, True, latency=time.time() - t0)
        except urllib.error.HTTPError as e:
            return AIResponse(self.name, "", False, f"HTTP {e.code}", time.time() - t0)
        except Exception as e:
            return AIResponse(self.name, "", False, str(e), time.time() - t0)


# ---------------------------------------------------------------------------
# Ollama (local server)
# ---------------------------------------------------------------------------
class OllamaProvider(BaseProvider):
    name = "ollama"

    def available(self) -> bool:
        return bool(CONFIG.ollama_base_url)

    def generate(self, prompt: str, system: Optional[str] = None) -> AIResponse:
        import time
        t0 = time.time()
        payload = {"model": CONFIG.ollama_model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        headers = {"Content-Type": "application/json"}
        try:
            data = _post_json(f"{CONFIG.ollama_base_url}/api/generate",
                              payload, headers, CONFIG.http_timeout)
            return AIResponse(self.name, data.get("response", ""), True, latency=time.time() - t0)
        except Exception as e:
            return AIResponse(self.name, "", False, str(e), time.time() - t0)


# ---------------------------------------------------------------------------
# HuggingFace Inference API
# ---------------------------------------------------------------------------
class HuggingFaceProvider(BaseProvider):
    name = "huggingface"

    def available(self) -> bool:
        return bool(CONFIG.huggingface_api_key)

    def generate(self, prompt: str, system: Optional[str] = None) -> AIResponse:
        import time
        if not self.available():
            return AIResponse(self.name, "", False, "HuggingFace API key not configured.")
        t0 = time.time()
        url = f"https://api-inference.huggingface.co/models/{CONFIG.huggingface_model}"
        full = f"{system}\n\n{prompt}" if system else prompt
        payload = {"inputs": full, "parameters": {"max_new_tokens": 512}}
        headers = {"Authorization": f"Bearer {CONFIG.huggingface_api_key}",
                   "Content-Type": "application/json"}
        try:
            data = _post_json(url, payload, headers, CONFIG.http_timeout)
            if isinstance(data, list) and data:
                text = data[0].get("generated_text", "")
            elif isinstance(data, dict):
                text = data.get("generated_text", str(data))
            else:
                text = str(data)
            return AIResponse(self.name, text, True, latency=time.time() - t0)
        except Exception as e:
            return AIResponse(self.name, "", False, str(e), time.time() - t0)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
_PROVIDERS: Dict[str, BaseProvider] = {
    "local": LocalProvider(),
    "openai": OpenAIProvider(),
    "gemini": GeminiProvider(),
    "ollama": OllamaProvider(),
    "huggingface": HuggingFaceProvider(),
}


def get_provider(name: str) -> Optional[BaseProvider]:
    return _PROVIDERS.get(name)


def all_providers() -> Dict[str, BaseProvider]:
    return dict(_PROVIDERS)


def available_providers(include_external: bool = True) -> List[str]:
    out = ["local"]
    if include_external:
        for name, prov in _PROVIDERS.items():
            if name != "local" and prov.available():
                out.append(name)
    return out
