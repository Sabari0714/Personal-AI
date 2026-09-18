"""
ROLEX AI — Brain / Reasoning System
Central reasoning layer: intent interpretation, context handling, tool routing,
memory retrieval, response synthesis, multi-step reasoning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config import CONFIG
from modules.logger import get_logger
from modules.memory import get_memory
from modules.parallel_ai import get_parallel_ai
from modules.providers import AIResponse
from modules.verification import verify, is_reliable

log = get_logger("rolex.brain")


@dataclass
class BrainResult:
    text: str
    intent: str = "chat"
    provider: str = "local"
    confidence: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"text": self.text, "intent": self.intent, "provider": self.provider,
                "confidence": self.confidence, "data": self.data, "flags": self.flags}


class Brain:
    """
    The reasoning pipeline:
    Input -> Normalize -> Intent Detection -> Context Retrieval -> Memory Retrieval
    -> Plan -> Tool Selection -> Execution -> Validation -> Response
    """

    def __init__(self):
        self.memory = get_memory()
        self.parallel = get_parallel_ai()

    # -- normalization ------------------------------------------------------
    def normalize(self, text: str) -> str:
        return " ".join((text or "").strip().split())

    # -- context ------------------------------------------------------------
    def build_context(self, user_text: str) -> str:
        mem_block = self.memory.context_block()
        return mem_block

    # -- reasoning ----------------------------------------------------------
    def reason(self, user_text: str, intent: str = "chat",
               tool_result: Optional[str] = None,
               include_external: Optional[bool] = None) -> BrainResult:
        """
        Produce a final response. If a tool already produced a result, synthesize
        around it; otherwise query AI providers (respecting Rolex-only policy).
        """
        text = self.normalize(user_text)
        if include_external is None:
            include_external = CONFIG.allow_external_ai and not CONFIG.rolex_only_mode

        # If a tool produced a deterministic result, prefer it (local-first).
        if tool_result is not None:
            return BrainResult(text=tool_result, intent=intent, provider="local",
                               confidence=0.95, data={"tool": True})

        system = self._system_prompt()
        context = self.build_context(text)
        if context:
            system = system + "\n\n" + context

        responses = self.parallel.query(text, system=system, include_external=include_external)
        report = verify(responses)

        if report.get("consensus"):
            best = max([r for r in responses if r.ok and r.text.strip()],
                       key=lambda r: len(r.text), default=None)
            return BrainResult(
                text=report["consensus"],
                intent=intent,
                provider=best.provider if best else "local",
                confidence=report.get("confidence", 0.0),
                flags=report.get("flags", []),
                data={"agreement": report.get("agreement", 0.0)},
            )

        # Fallback to local
        local = self.parallel.best(text, system=system, providers=["local"])
        return BrainResult(text=local.text, intent=intent, provider="local",
                           confidence=0.4, flags=["fallback_local"])

    def _system_prompt(self) -> str:
        return (
            "You are ROLEX AI, a local-first personal assistant. "
            "You support Tamil, English and Tanglish. Be concise, accurate and helpful. "
            "Never invent facts. If unsure, say so. Prefer local reasoning."
        )

    # -- multi-step reasoning ----------------------------------------------
    def decompose(self, goal: str) -> List[str]:
        from modules.planner import get_planner
        return get_planner().decompose_goal(goal)


_brain: Optional[Brain] = None


def get_brain() -> Brain:
    global _brain
    if _brain is None:
        _brain = Brain()
    return _brain
