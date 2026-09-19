"""
ROLEX AI — Tool Manager
Central registry of every capability (tool) ROLEX can invoke.

Tools declare a name, description, category, a callable, and whether they
require approval. The manager provides discovery, lookup, safe invocation
(with audit logging) and a capability manifest used by the brain/router.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from modules.logger import get_logger

log = get_logger("rolex.tool_manager")


@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., Any]
    category: str = "general"
    requires_approval: bool = False
    dangerous: bool = False
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name, "description": self.description,
                "category": self.category, "requires_approval": self.requires_approval,
                "dangerous": self.dangerous, "tags": self.tags}


class ToolManager:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._audit: Optional[Callable[[str, str], None]] = None

    def set_audit(self, fn: Callable[[str, str], None]) -> None:
        self._audit = fn

    # -- registration -------------------------------------------------------
    def register(self, name: str, description: str, func: Callable[..., Any],
                 category: str = "general", requires_approval: bool = False,
                 dangerous: bool = False, tags: Optional[List[str]] = None) -> Tool:
        tool = Tool(name, description, func, category, requires_approval,
                    dangerous, tags or [])
        self._tools[name] = tool
        log.debug("Registered tool: %s", name)
        return tool

    def unregister(self, name: str) -> bool:
        return self._tools.pop(name, None) is not None

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def all(self) -> List[Tool]:
        return list(self._tools.values())

    def by_category(self, category: str) -> List[Tool]:
        return [t for t in self._tools.values() if t.category == category]

    def categories(self) -> List[str]:
        return sorted({t.category for t in self._tools.values()})

    def search(self, term: str) -> List[Tool]:
        term = (term or "").lower()
        out = []
        for t in self._tools.values():
            hay = f"{t.name} {t.description} {' '.join(t.tags)}".lower()
            if term in hay:
                out.append(t)
        return out

    # -- invocation ---------------------------------------------------------
    def invoke(self, name: str, *args, approved: bool = False, **kwargs) -> Dict:
        tool = self._tools.get(name)
        if tool is None:
            return {"ok": False, "error": f"Unknown tool: {name}"}
        if tool.requires_approval and not approved:
            return {"ok": False, "error": f"Tool '{name}' requires approval."}
        t0 = time.time()
        try:
            result = tool.func(*args, **kwargs)
            ok = True
            err = None
        except Exception as e:
            result = None
            ok = False
            err = str(e)
            log.error("Tool %s failed: %s", name, e)
        if self._audit:
            try:
                self._audit("tool_invoke",
                            f"{name} ok={ok} {round(time.time()-t0,3)}s")
            except Exception:
                pass
        return {"ok": ok, "result": result, "error": err,
                "elapsed": round(time.time() - t0, 3)}

    def manifest(self) -> List[dict]:
        return [t.to_dict() for t in self._tools.values()]

    def summary(self) -> str:
        lines = [f"• {t.name} [{t.category}] — {t.description}" for t in self._tools.values()]
        return f"{len(self._tools)} tools available:\n" + "\n".join(lines)


_manager: Optional[ToolManager] = None


def get_tool_manager() -> ToolManager:
    global _manager
    if _manager is None:
        _manager = ToolManager()
    return _manager
