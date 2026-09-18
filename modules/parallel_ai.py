"""
ROLEX AI — Parallel AI Architecture
Multiple provider orchestration, parallel execution, timeouts, failure handling,
result collection, comparison and fallback routing.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from config import CONFIG
from modules.logger import get_logger
from modules.providers import AIResponse, all_providers, available_providers, get_provider

log = get_logger("rolex.parallel_ai")


class ParallelAI:
    """Orchestrates multiple AI providers in parallel with graceful fallback."""

    def __init__(self, max_workers: int = 4, timeout: float = 30.0):
        self.max_workers = max_workers
        self.timeout = timeout

    def _select_providers(self, providers: Optional[List[str]] = None,
                          include_external: bool = True) -> List[str]:
        if providers:
            return [p for p in providers if get_provider(p)]
        return available_providers(include_external=include_external)

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
        try:
            return prov.generate(prompt, system)
        except Exception as e:
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
