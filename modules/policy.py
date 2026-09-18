"""
ROLEX AI — Policy Engine
Enforces the Rolex-only policy: external LLM providers must never silently
receive user prompts. Also handles approval gating for sensitive operations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from config import CONFIG
from modules.logger import get_logger

log = get_logger("rolex.policy")


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    requires_approval: bool = False


class PolicyEngine:
    def __init__(self):
        self.rolex_only = CONFIG.rolex_only_mode
        self.allow_external = CONFIG.allow_external_ai
        self.require_approval = CONFIG.require_approval

    def set_rolex_only(self, enabled: bool) -> None:
        self.rolex_only = bool(enabled)
        CONFIG.rolex_only_mode = bool(enabled)
        log.info("Rolex-only mode set to %s", self.rolex_only)

    def can_use_external_ai(self) -> bool:
        return self.allow_external and not self.rolex_only

    def check_external_ai(self) -> PolicyDecision:
        if self.rolex_only:
            return PolicyDecision(False, "Rolex-only mode is enabled; external AI is blocked.")
        if not self.allow_external:
            return PolicyDecision(False, "External AI is disabled in configuration.")
        return PolicyDecision(True, "External AI permitted.")

    def check_sensitive(self, action: str) -> PolicyDecision:
        sensitive = {"delete", "format", "install", "uninstall", "modify_system",
                     "send_message", "payment", "self_modify"}
        if action in sensitive and self.require_approval:
            return PolicyDecision(True, f"'{action}' requires human approval.", requires_approval=True)
        return PolicyDecision(True, "Allowed.")

    def describe(self) -> str:
        mode = "ROLEX-ONLY (local intelligence only)" if self.rolex_only else "External AI allowed"
        return (f"Policy: {mode}. "
                f"External AI: {'enabled' if self.allow_external else 'disabled'}. "
                f"Approval required for sensitive actions: {self.require_approval}.")


_policy: Optional[PolicyEngine] = None


def get_policy() -> PolicyEngine:
    global _policy
    if _policy is None:
        _policy = PolicyEngine()
    return _policy
