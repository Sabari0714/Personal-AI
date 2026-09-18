"""
ROLEX AI — Plugin Architecture
Extensible connectors (Gmail, Calendar, Drive, GitHub, WhatsApp, Smart Home,
Finance, Travel, Coding, IoT, Instagram, Telegram) with declared permissions.
Plugins are isolated and optional; failures never crash the core.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from modules.logger import get_logger

log = get_logger("rolex.plugins")


@dataclass
class PluginManifest:
    name: str
    description: str
    permissions: List[str] = field(default_factory=list)
    data_access: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    credentials: List[str] = field(default_factory=list)
    network: bool = False
    enabled: bool = False


class Plugin:
    manifest: PluginManifest

    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest

    def execute(self, action: str, params: dict) -> dict:
        return {"ok": False, "error": f"Plugin '{self.manifest.name}' action '{action}' not implemented."}


class PluginManager:
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._register_builtin_manifests()

    def _register_builtin_manifests(self) -> None:
        builtins = [
            PluginManifest("gmail", "Read/send email", ["read", "send"], ["email"],
                           ["list", "read", "send"], ["oauth"], True),
            PluginManifest("calendar", "Calendar events", ["read", "write"], ["events"],
                           ["list", "create"], ["oauth"], True),
            PluginManifest("drive", "Google Drive files", ["read", "write"], ["files"],
                           ["list", "upload", "download"], ["oauth"], True),
            PluginManifest("github", "GitHub repositories", ["read", "write"], ["repos"],
                           ["list_repos", "create_issue", "push"], ["token"], True),
            PluginManifest("whatsapp", "WhatsApp messaging", ["send"], ["messages"],
                           ["send"], ["session"], True),
            PluginManifest("telegram", "Telegram messaging", ["send"], ["messages"],
                           ["send"], ["bot_token"], True),
            PluginManifest("instagram", "Instagram", ["read"], ["posts"], ["feed"], ["oauth"], True),
            PluginManifest("smart_home", "Smart home / IoT control", ["control"], ["devices"],
                           ["turn_on", "turn_off", "set"], ["token"], True),
            PluginManifest("finance", "Finance tracking", ["read", "write"], ["transactions"],
                           ["balance", "add"], [], False),
            PluginManifest("travel", "Travel planning", ["read"], ["trips"], ["plan"], [], True),
            PluginManifest("coding", "Coding assistance", ["read", "write"], ["code"],
                           ["generate", "review"], [], False),
        ]
        for m in builtins:
            self._plugins[m.name] = Plugin(m)

    def register(self, plugin: Plugin) -> None:
        self._plugins[plugin.manifest.name] = plugin
        log.info("Plugin registered: %s", plugin.manifest.name)

    def get(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[PluginManifest]:
        return [p.manifest for p in self._plugins.values()]

    def enable(self, name: str, enabled: bool = True) -> bool:
        p = self._plugins.get(name)
        if not p:
            return False
        p.manifest.enabled = enabled
        return True

    def execute(self, name: str, action: str, params: Optional[dict] = None) -> dict:
        p = self._plugins.get(name)
        if not p:
            return {"ok": False, "error": f"Unknown plugin: {name}"}
        if not p.manifest.enabled:
            return {"ok": False, "error": f"Plugin '{name}' is disabled."}
        try:
            return p.execute(action, params or {})
        except Exception as e:
            log.error("Plugin %s failed: %s", name, e)
            return {"ok": False, "error": str(e)}


_plugins: Optional[PluginManager] = None


def get_plugins() -> PluginManager:
    global _plugins
    if _plugins is None:
        _plugins = PluginManager()
    return _plugins
