"""
ROLEX AI — Parallel AI Architecture
Multiple provider orchestration, parallel execution, timeouts, failure handling,
result collection, comparison and fallback routing.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from config import CONFIG
from modules.logger import get_logger
from modules.providers import AIResponse, all_providers, available_providers, get_provider

log = get_logger("rolex.parallel_ai")

# Task categories used for smart provider selection.
TASK_TYPES = ("chat", "code", "math", "reasoning", "creative", "vision", "fast")

# Preferred provider ordering per task type (best first).
_PREFERENCE = {
    "chat":      ["openai", "gemini", "ollama", "huggingface", "local"],
    "code":      ["openai", "gemini", "ollama", "local"],
    "math":      ["local", "openai", "gemini", "ollama"],
    "reasoning": ["openai", "gemini", "ollama", "local"],
    "creative":  ["openai", "gemini", "huggingface", "local"],
    "vision":    ["gemini", "openai", "local"],
    "fast":      ["local", "ollama", "gemini", "openai"],
}


class ParallelAI:
    """Orchestrates multiple AI providers in parallel with graceful fallback."""

    def __init__(self, max_workers: int = 4, timeout: float = 30.0):
        self.max_workers = max_workers
        self.timeout = timeout
        # Rolling latency history per provider for smart selection.
        self._latency: Dict[str, float] = {}
        self._success: Dict[str, int] = {}
        self._failure: Dict[str, int] = {}

    def _select_providers(self, providers: Optional[List[str]] = None,
                          include_external: bool = True) -> List[str]:
        if providers:
            return [p for p in providers if get_provider(p)]
        return available_providers(include_external=include_external)

    # -- smart selection ----------------------------------------------------
    def select_smart(self, task_type: str = "chat",
                     include_external: bool = True,
                     limit: int = 3) -> List[str]:
        """Pick the best providers for a task type using availability,
        historical latency and success rate."""
        available = set(available_providers(include_external=include_external))
        if not available:
            return ["local"]
        order = _PREFERENCE.get(task_type, _PREFERENCE["chat"])
        scored = []
        for rank, name in enumerate(order):
            if name not in available:
                continue
            lat = self._latency.get(name, 1.0)
            succ = self._success.get(name, 1)
            fail = self._failure.get(name, 0)
            reliability = succ / max(1, succ + fail)
            # Lower score is better: rank dominates, then latency, then reliability.
            score = rank * 10 + lat - reliability * 2
            scored.append((score, name))
        scored.sort()
        picked = [n for _s, n in scored[:limit]]
        return picked or ["local"]

    def _record(self, name: str, ok: bool, latency: float) -> None:
        if ok:
            self._success[name] = self._success.get(name, 0) + 1
            # Exponential moving average of latency.
            prev = self._latency.get(name, latency)
            self._latency[name] = 0.7 * prev + 0.3 * latency
        else:
            self._failure[name] = self._failure.get(name, 0) + 1

    def provider_health(self) -> Dict[str, dict]:
        names = set(list(self._latency) + list(self._success) + list(self._failure))
        out = {}
        for n in names:
            s = self._success.get(n, 0)
            f = self._failure.get(n, 0)
            out[n] = {"latency": round(self._latency.get(n, 0.0), 3),
                      "success": s, "failure": f,
                      "reliability": round(s / max(1, s + f), 3)}
        return out

    def query(self, prompt: str, system: Optional[str] = None,
              providers: Optional[List[str]] = None,
              include_external: bool = True) -> List[AIResponse]:
        """Query providers in parallel and collect all responses."""
        names = self._select_providers(providers, include_external)
        if not names:
            names = ["local"]

        results: List[AIResponse] = []
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(names))) as pool:
            futures = {}
            for name in names:
                prov = get_provider(name)
                if prov is None:
                    continue
                futures[pool.submit(self._safe_generate, prov, prompt, system)] = name
            for fut in as_completed(futures, timeout=self.timeout + 5):
                name = futures[fut]
                try:
                    results.append(fut.result(timeout=self.timeout))
                except Exception as e:
                    log.warning("Provider %s failed: %s", name, e)
                    results.append(AIResponse(name, "", False, str(e)))
        return results

    def _safe_generate(self, prov, prompt: str, system: Optional[str]) -> AIResponse:
        t0 = time.time()
        try:
            resp = prov.generate(prompt, system)
            self._record(prov.name, resp.ok, time.time() - t0)
            return resp
        except Exception as e:
            self._record(prov.name, False, time.time() - t0)
            return AIResponse(prov.name, "", False, str(e))

    def best(self, prompt: str, system: Optional[str] = None,
             providers: Optional[List[str]] = None,
             include_external: bool = True) -> AIResponse:
        """Return the best available response, with fallback to local."""
        results = self.query(prompt, system, providers, include_external)
        ok = [r for r in results if r.ok and r.text.strip()]
        if not ok:
            # Fallback to local
            local = get_provider("local")
            if local:
                return local.generate(prompt, system)
            return AIResponse("none", "", False, "No provider available.")
        # Prefer external providers with content, else local
        external = [r for r in ok if r.provider != "local"]
        if external:
            # Prefer fastest successful external response
            return min(external, key=lambda r: r.latency)
        return ok[0]

    def compare(self, prompt: str, system: Optional[str] = None,
                include_external: bool = True) -> Dict[str, dict]:
        """Return a comparison of provider responses."""
        results = self.query(prompt, system, include_external=include_external)
        return {r.provider: r.to_dict() for r in results}


_parallel: Optional[ParallelAI] = None


def get_parallel_ai() -> ParallelAI:
    global _parallel
    if _parallel is None:
        _parallel = ParallelAI()
    return _parallel
