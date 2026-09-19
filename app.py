"""
ROLEX AI — Application Core
Ties together brain, router, memory, tools, voice, automation and security.
This is the single entry point used by both the CLI and the GUI.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config import CONFIG
from modules.logger import get_logger, user_safe_error
from modules.memory import get_memory
from modules.tasks import get_tasks
from modules.planner import get_planner
from modules.documents import get_documents
from modules.knowledge import get_knowledge
from modules.web import get_web
from modules.diagnostics import get_diagnostics
from modules.security import get_security
from modules.policy import get_policy
from modules.automation import get_automation
from modules.plugins import get_plugins
from modules.sync import get_sync
from modules.voice import get_voice
from modules.vision import get_vision
from modules.package_check import summary as pkg_summary
from modules.finance import get_finance
from modules.health import get_health
from modules.device import get_device
from modules.smarthome import get_smarthome
from modules.messaging import get_messaging
from modules.coding import get_coding
from modules.computer_knowledge import get_computer_knowledge
from modules.emergency import get_emergency
from modules.recovery import get_recovery
from modules.self_tests import get_self_tests
from modules.knowledge_graph import get_knowledge_graph
from modules.self_learning import get_self_learning
from modules.tool_manager import get_tool_manager
from modules.package_manager import get_package_manager
from modules.remote_lab import get_remote_lab
from modules.parallel_ai import get_parallel_ai
from modules.biometrics import get_biometrics
from brain import get_brain
from router import get_router

log = get_logger("rolex.app")


@dataclass
class RolexResponse:
    text: str
    intent: str = "chat"
    provider: str = "local"
    confidence: float = 0.0
    tool: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    flags: List[str] = field(default_factory=list)
    elapsed: float = 0.0

    def to_dict(self) -> dict:
        return {"text": self.text, "intent": self.intent, "provider": self.provider,
                "confidence": self.confidence, "tool": self.tool, "data": self.data,
                "flags": self.flags, "elapsed": self.elapsed}


class RolexApp:
    """The ROLEX AI application facade."""

    def __init__(self):
        self.config = CONFIG
        self.memory = get_memory()
        self.tasks = get_tasks()
        self.planner = get_planner()
        self.documents = get_documents()
        self.knowledge = get_knowledge()
        self.web = get_web()
        self.diagnostics = get_diagnostics()
        self.security = get_security()
        self.policy = get_policy()
        self.automation = get_automation()
        self.plugins = get_plugins()
        self.sync = get_sync()
        self.voice = get_voice()
        self.vision = get_vision()
        self.finance = get_finance()
        self.health = get_health()
        self.device = get_device()
        self.smarthome = get_smarthome()
        self.messaging = get_messaging()
        self.coding = get_coding()
        self.computer = get_computer_knowledge()
        self.emergency = get_emergency()
        self.recovery = get_recovery()
        self.self_tests = get_self_tests()
        self.kg = get_knowledge_graph()
        self.learning = get_self_learning()
        self.tools = get_tool_manager()
        self.packages = get_package_manager()
        self.remote_lab = get_remote_lab()
        self.parallel_ai = get_parallel_ai()
        self.biometrics = get_biometrics()
        self.brain = get_brain()
        self.router = get_router()
        self._register_automation_actions()
        self._register_tools()
        self.security.audit("app_start", detail=f"v{CONFIG.version}")

    def _register_tools(self) -> None:
        """Expose core capabilities through the tool manager."""
        try:
            self.tools.register("calculate", "math", "Solve a math expression",
                                lambda expr: self.router.route(f"calculate {expr}").text)
            self.tools.register("remember", "memory", "Store a memory",
                                lambda text: self.memory.remember(text).to_dict())
            self.tools.register("web_search", "web", "Search the web",
                                lambda q: self.web.search(q))
            self.tools.register("finance_sip", "finance", "SIP future value",
                                lambda a, r, y: self.finance and __import__("modules.finance", fromlist=["sip"]).sip(a, r, y))
            self.tools.register("health_bmi", "health", "Compute BMI",
                                lambda w, h: self.health.bmi(w, h))
            self.tools.register("device_info", "device", "Device information",
                                lambda: self.device.info())
            self.tools.register("self_test", "system", "Run self-tests",
                                lambda: self.self_tests.run_all())
            self.tools.register("snapshot", "recovery", "Create a recovery snapshot",
                                lambda: self.recovery.snapshot())
        except Exception as e:
            log.debug("Tool registration issue: %s", e)

    def _register_automation_actions(self) -> None:
        self.automation.register_action("notify", lambda payload: log.info("Reminder: %s", payload))
        self.automation.register_action("speak", lambda payload: self.voice.speak(payload))

    # ------------------------------------------------------------------ #
    # Primary interaction
    # ------------------------------------------------------------------ #
    def process(self, user_text: str, speak: bool = False) -> RolexResponse:
        """Process a user message end-to-end."""
        t0 = time.time()
        user_text = (user_text or "").strip()
        if not user_text:
            return RolexResponse("Please say or type something.", elapsed=time.time() - t0)

        # Persist conversation
        try:
            self._log_conversation("user", user_text)
        except Exception:
            pass

        # 1) Route to a deterministic tool if possible (local-first)
        try:
            route = self.router.route(user_text)
        except Exception as e:
            log.error("Router error: %s", e)
            route = None

        if route and route.handled and route.text:
            resp = RolexResponse(
                text=route.text, intent=route.intent, provider="local",
                confidence=0.95, tool=route.tool, data=route.data,
                elapsed=time.time() - t0,
            )
        else:
            # 2) Fall back to the brain (AI providers, respecting policy)
            try:
                brain_result = self.brain.reason(user_text, intent="chat")
                resp = RolexResponse(
                    text=brain_result.text, intent=brain_result.intent,
                    provider=brain_result.provider, confidence=brain_result.confidence,
                    flags=brain_result.flags, data=brain_result.data,
                    elapsed=time.time() - t0,
                )
            except Exception as e:
                log.error("Brain error: %s", e)
                resp = RolexResponse(user_safe_error(e), elapsed=time.time() - t0)

        # Persist assistant response
        try:
            self._log_conversation("assistant", resp.text, provider=resp.provider)
        except Exception:
            pass

        if speak:
            try:
                self.voice.speak(resp.text)
            except Exception:
                pass
        return resp

    def _log_conversation(self, role: str, content: str, provider: Optional[str] = None) -> None:
        from data.database import get_db
        get_db().execute(
            "INSERT INTO conversations(role, content, provider, created_at) VALUES(?,?,?,?)",
            (role, content, provider, time.time()),
        )

    # ------------------------------------------------------------------ #
    # Voice interaction
    # ------------------------------------------------------------------ #
    def voice_turn(self) -> Optional[RolexResponse]:
        text = self.voice.listen()
        if not text:
            return None
        if self.voice.detect_wake_word(text):
            text = self.voice.strip_wake_word(text)
        return self.process(text, speak=True)

    # ------------------------------------------------------------------ #
    # Status / info
    # ------------------------------------------------------------------ #
    def status(self) -> Dict:
        return {
            "name": CONFIG.app_name,
            "version": CONFIG.version,
            "online": self.web.is_online(),
            "rolex_only": self.policy.rolex_only,
            "providers": CONFIG.provider_status(),
            "memory_count": self.memory.count(),
            "task_stats": self.tasks.stats(),
            "knowledge_count": self.knowledge.count(),
            "voice": {"stt": self.voice.stt_available(), "tts": self.voice.tts_available(),
                      "backend": self.voice.backend_name()},
            "vision_ocr": self.vision.ocr_available(),
            "vision_camera": self.vision.camera_available(),
            "emergency": self.emergency.is_engaged(),
            "biometrics": self.biometrics.biometric_available(),
            "tools": len(self.tools.all()),
            "kg_nodes": self.kg.stats().get("nodes", 0),
            "remote_lab": self.remote_lab.is_running(),
        }

    def diagnostics_report(self) -> Dict:
        return self.diagnostics.report()

    def packages(self) -> str:
        return pkg_summary()

    def shutdown(self) -> None:
        try:
            self.automation.stop()
        except Exception:
            pass
        try:
            from data.database import get_db
            get_db().close()
        except Exception:
            pass
        self.security.audit("app_stop")


_app: Optional[RolexApp] = None


def get_app() -> RolexApp:
    global _app
    if _app is None:
        _app = RolexApp()
    return _app
