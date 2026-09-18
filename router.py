"""
ROLEX AI — Command Router
Identify command -> select handler -> validate -> execute tool -> return result.
Supports natural language (Tamil / English / Tanglish) without exact syntax.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from config import CONFIG
from modules.logger import get_logger
from modules.memory import get_memory
from modules.tasks import get_tasks
from modules.planner import get_planner
from modules.math_engine import solve as math_solve, convert_units, MathError
from modules.documents import get_documents, DocumentError
from modules.knowledge import get_knowledge
from modules.web import get_web
from modules.diagnostics import get_diagnostics
from modules.security import get_security
from modules.policy import get_policy

log = get_logger("rolex.router")


@dataclass
class RouteResult:
    handled: bool
    intent: str
    text: str
    data: Dict[str, Any] = field(default_factory=dict)
    tool: Optional[str] = None

    def to_dict(self) -> dict:
        return {"handled": self.handled, "intent": self.intent, "text": self.text,
                "data": self.data, "tool": self.tool}


class Router:
    def __init__(self):
        self.memory = get_memory()
        self.tasks = get_tasks()
        self.planner = get_planner()
        self.docs = get_documents()
        self.knowledge = get_knowledge()
        self.web = get_web()
        self.diagnostics = get_diagnostics()
        self.security = get_security()
        self.policy = get_policy()
        self._handlers: Dict[str, Callable[[str], RouteResult]] = {
            "remember": self._h_remember,
            "forget": self._h_forget,
            "recall": self._h_recall,
            "calculate": self._h_calculate,
            "convert": self._h_convert,
            "task_create": self._h_task_create,
            "task_list": self._h_task_list,
            "task_complete": self._h_task_complete,
            "task_delete": self._h_task_delete,
            "plan": self._h_plan,
            "plan_list": self._h_plan_list,
            "document": self._h_document,
            "knowledge": self._h_knowledge,
            "weather": self._h_weather,
            "web_search": self._h_web_search,
            "status": self._h_status,
            "time": self._h_time,
            "diagnostics": self._h_diagnostics,
            "help": self._h_help,
            "providers": self._h_providers,
            "policy": self._h_policy,
        }

    # ------------------------------------------------------------------ #
    # Intent detection
    # ------------------------------------------------------------------ #
    def detect_intent(self, text: str) -> str:
        t = (text or "").strip().lower()
        if not t:
            return "chat"

        # Memory
        if re.search(r"\b(remember|note that|keep in mind|save this|nyabagam|gnyabagam)\b", t):
            return "remember"
        if re.search(r"\b(forget|delete memory|remove memory|marandhudu)\b", t):
            return "forget"
        if re.search(r"\b(what do you (know|remember)|recall|my memories|show memory|enaku theriyuma)\b", t):
            return "recall"
        # "what is my X" / "what's my X" -> recall from memory
        if re.search(r"\b(what('s| is| was)? my|who is my|where is my|enoda|en my)\b", t):
            return "recall"

        # Unit conversion (before generic math)
        if re.search(r"\b(convert|conversion|how many|in to|into)\b", t) and \
           re.search(r"\b(km|m|cm|mm|mile|miles|ft|feet|inch|inches|yard|yards|kg|g|mg|lb|lbs|pound|pounds|ounce|oz|"
                     r"l|litre|liter|litres|liters|ml|gallon|gallons|cup|cups|c|f|k|celsius|fahrenheit|kelvin|"
                     r"sec|secs|second|seconds|min|mins|minute|minutes|hour|hours|hr|hrs|day|days|week|weeks|"
                     r"byte|bytes|kb|mb|gb|tb)\b", t):
            return "convert"

        # Math
        if re.search(r"\b(calculate|compute|solve|what is|eval|enna|kanakku)\b", t) and re.search(r"[0-9]", t):
            return "calculate"
        if re.fullmatch(r"[\d\s\.\+\-\*/\(\)\^×÷%]+", t) and re.search(r"[0-9]", t):
            return "calculate"

        # Tasks
        if re.search(r"\b(remind me|add task|create task|new task|todo|task)\b", t) and \
           not re.search(r"\b(list|show|pending|complete|done|delete|remove)\b", t):
            return "task_create"
        if re.search(r"\b(show|list|pending|my tasks|what tasks|task list)\b", t) and "task" in t:
            return "task_list"
        if re.search(r"\b(complete|finish|done with|mark.*done)\b", t) and "task" in t:
            return "task_complete"
        if re.search(r"\b(delete|remove|cancel)\b", t) and "task" in t:
            return "task_delete"

        # Plans
        if re.search(r"\b(create a plan|make a plan|plan for|plan to|goal)\b", t):
            return "plan"
        if re.search(r"\b(show plans|list plans|my plans)\b", t):
            return "plan_list"

        # Documents
        if re.search(r"\b(read|open|summarize|analyse|analyze|index|search document|pdf|docx|xlsx|pptx)\b", t):
            return "document"

        # Knowledge
        if re.search(r"\b(learn that|add knowledge|knowledge base|teach you)\b", t):
            return "knowledge"

        # Weather
        if re.search(r"\b(weather|temperature|forecast|climate|mazhai|vaanilai)\b", t):
            return "weather"

        # Web search
        if re.search(r"\b(search|google|look up|find online|latest news|web)\b", t):
            return "web_search"

        # System
        if re.search(r"\b(status|system status|how are you|are you online)\b", t):
            return "status"
        if re.search(r"\b(time|date|what time|today|naalai|indha neram)\b", t):
            return "time"
        if re.search(r"\b(diagnostic|health|system info|device info|storage|cpu|memory usage)\b", t):
            return "diagnostics"
        if re.search(r"\b(help|what can you do|commands|capabilities)\b", t):
            return "help"
        if re.search(r"\b(providers|which ai|ai status|models)\b", t):
            return "providers"
        if re.search(r"\b(policy|rolex only|privacy mode)\b", t):
            return "policy"

        return "chat"

    # ------------------------------------------------------------------ #
    # Route
    # ------------------------------------------------------------------ #
    def route(self, text: str) -> RouteResult:
        intent = self.detect_intent(text)
        handler = self._handlers.get(intent)
        if handler is None:
            return RouteResult(False, "chat", "")
        try:
            result = handler(text)
            result.intent = intent
            return result
        except Exception as e:
            log.error("Handler %s failed: %s", intent, e)
            return RouteResult(True, intent,
                               "I couldn't complete that because the required module is unavailable.",
                               data={"error": str(e)})

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def _h_remember(self, text: str) -> RouteResult:
        content = re.sub(r"(?i)^.*?\b(remember|note that|keep in mind|save this|nyabagam|gnyabagam)\b",
                         "", text).strip(" :,-")
        if not content:
            return RouteResult(True, "remember", "What should I remember?")
        category = "general"
        low = content.lower()
        if any(w in low for w in ("prefer", "like", "favourite", "favorite", "istam")):
            category = "preference"
        elif any(w in low for w in ("project", "rolex", "app")):
            category = "project"
        elif any(w in low for w in ("always", "never", "instruction", "rule")):
            category = "instruction"
        item = self.memory.remember(content, category=category)
        self.security.audit("memory_write", detail=f"id={item.id}")
        return RouteResult(True, "remember", f"Got it. I'll remember: {content}",
                           data=item.to_dict(), tool="memory")

    def _h_forget(self, text: str) -> RouteResult:
        term = re.sub(r"(?i)^.*?\b(forget|delete memory|remove memory|marandhudu)\b", "", text).strip(" :,-")
        if not term:
            return RouteResult(True, "forget", "What should I forget?")
        matches = self.memory.search(term)
        if not matches:
            return RouteResult(True, "forget", f"I don't have a memory matching '{term}'.")
        for m in matches:
            self.memory.forget(m.id)
        return RouteResult(True, "forget", f"Forgotten {len(matches)} memory item(s) matching '{term}'.",
                           data={"count": len(matches)}, tool="memory")

    def _h_recall(self, text: str) -> RouteResult:
        # If the user asks about a specific thing ("what is my wifi password"),
        # search memory for the key terms first.
        low = text.lower()
        specific = re.search(r"\b(what('s| is| was)? my|who is my|where is my|enoda)\b", low)
        if specific:
            query = re.sub(r"(?i)^.*?\b(what('s| is| was)? my|who is my|where is my|enoda)\b", "", text)
            query = re.sub(r"(?i)\b(password|name|number|address|email|phone)\b", "", query)
            query = query.strip(" :?.-")
            if query:
                matches = self.memory.search(query, limit=5)
                if matches:
                    lines = [f"• [{m.category}] {m.content}" for m in matches]
                    return RouteResult(True, "recall",
                                       "Here's what I remember:\n" + "\n".join(lines),
                                       data={"count": len(matches)}, tool="memory")
        items = self.memory.all(limit=20)
        if not items:
            return RouteResult(True, "recall", "I don't have any saved memories yet.")
        lines = [f"{i+1}. [{m.category}] {m.content}" for i, m in enumerate(items)]
        return RouteResult(True, "recall", "Here's what I remember:\n" + "\n".join(lines),
                           data={"count": len(items)}, tool="memory")

    def _h_convert(self, text: str) -> RouteResult:
        # Patterns: "convert 5 km to miles", "5 km in miles", "how many miles in 5 km"
        m = re.search(
            r"(-?\d+(?:\.\d+)?)\s*([a-zA-Z]+)\s*(?:to|in|into|->|=)\s*([a-zA-Z]+)", text)
        if not m:
            m = re.search(
                r"how many\s+([a-zA-Z]+)\s+(?:in|are in|is)\s+(-?\d+(?:\.\d+)?)\s*([a-zA-Z]+)", text)
            if m:
                to_unit, value, from_unit = m.group(1), float(m.group(2)), m.group(3)
            else:
                return RouteResult(True, "convert",
                                   "Tell me like: convert 5 km to miles", tool="math")
        else:
            value, from_unit, to_unit = float(m.group(1)), m.group(2), m.group(3)
        try:
            result = convert_units(value, from_unit, to_unit)
            pretty = f"{result:.6g}"
            return RouteResult(True, "convert",
                               f"{value:g} {from_unit} = {pretty} {to_unit}",
                               data={"value": value, "from": from_unit,
                                     "to": to_unit, "result": result}, tool="math")
        except MathError as e:
            return RouteResult(True, "convert", f"I can't convert that: {e}", tool="math")

    def _h_calculate(self, text: str) -> RouteResult:
        expr = re.sub(r"(?i)^.*?\b(calculate|compute|solve|what is|eval|enna|kanakku)\b", "", text).strip(" :?=")
        if not expr:
            expr = text
        result = math_solve(expr)
        return RouteResult(True, "calculate", result, data={"expression": expr}, tool="math")

    def _h_task_create(self, text: str) -> RouteResult:
        title = re.sub(r"(?i)^.*?\b(remind me to|remind me|add task|create task|new task|todo|task)\b",
                       "", text).strip(" :,-")
        if not title:
            return RouteResult(True, "task_create", "What task should I create?")
        priority = 2
        low = text.lower()
        if any(w in low for w in ("urgent", "important", "high priority", "asap")):
            priority = 1
        elif any(w in low for w in ("low priority", "whenever", "someday")):
            priority = 3
        due = self._parse_due(text)
        task = self.tasks.create(title, priority=priority, due_date=due)
        return RouteResult(True, "task_create", f"Task created: {title}",
                           data=task.to_dict(), tool="tasks")

    def _h_task_list(self, text: str) -> RouteResult:
        tasks = self.tasks.list()
        if not tasks:
            return RouteResult(True, "task_list", "You have no tasks.", tool="tasks")
        lines = []
        for t in tasks:
            mark = "✓" if t.status == "COMPLETED" else "•"
            lines.append(f"{mark} #{t.id} [{t.status}] {t.title}")
        return RouteResult(True, "task_list", "Your tasks:\n" + "\n".join(lines),
                           data={"count": len(tasks)}, tool="tasks")

    def _h_task_complete(self, text: str) -> RouteResult:
        m = re.search(r"#?(\d+)", text)
        if not m:
            return RouteResult(True, "task_complete", "Which task number should I complete?")
        tid = int(m.group(1))
        if self.tasks.complete(tid):
            return RouteResult(True, "task_complete", f"Task #{tid} marked complete.", tool="tasks")
        return RouteResult(True, "task_complete", f"I couldn't find task #{tid}.", tool="tasks")

    def _h_task_delete(self, text: str) -> RouteResult:
        m = re.search(r"#?(\d+)", text)
        if not m:
            return RouteResult(True, "task_delete", "Which task number should I delete?")
        tid = int(m.group(1))
        if self.tasks.delete(tid):
            return RouteResult(True, "task_delete", f"Task #{tid} deleted.", tool="tasks")
        return RouteResult(True, "task_delete", f"I couldn't find task #{tid}.", tool="tasks")

    def _h_plan(self, text: str) -> RouteResult:
        goal = re.sub(r"(?i)^.*?\b(create a plan for|make a plan for|create a plan|make a plan|plan for|plan to|goal)\b",
                      "", text).strip(" :,-")
        if not goal:
            return RouteResult(True, "plan", "What goal should I plan for?")
        steps = self.planner.decompose_goal(goal)
        plan = self.planner.create_plan(goal, steps)
        lines = [f"{s.step_no}. {s.description}" for s in plan.steps]
        return RouteResult(True, "plan", f"Plan for '{goal}':\n" + "\n".join(lines),
                           data={"plan_id": plan.id, "steps": len(plan.steps)}, tool="planner")

    def _h_plan_list(self, text: str) -> RouteResult:
        plans = self.planner.list_plans()
        if not plans:
            return RouteResult(True, "plan_list", "You have no plans yet.", tool="planner")
        lines = []
        for p in plans:
            prog = self.planner.progress(p.id)
            lines.append(f"#{p.id} [{p.status}] {p.goal} ({prog.get('percent', 0)}%)")
        return RouteResult(True, "plan_list", "Your plans:\n" + "\n".join(lines), tool="planner")

    def _h_document(self, text: str) -> RouteResult:
        m = re.search(r"[\w\-/\\\.]+\.(txt|md|csv|json|pdf|docx|xlsx|pptx)", text, re.I)
        if not m:
            return RouteResult(True, "document", "Please provide a document path (e.g. report.pdf).")
        path = m.group(0)
        try:
            if re.search(r"(?i)\b(summarize|summary)\b", text):
                info = self.docs.analyze(path)
                return RouteResult(True, "document", f"Summary of {path}:\n{info['summary']}",
                                   data=info, tool="documents")
            if re.search(r"(?i)\b(index)\b", text):
                did = self.docs.index(path)
                return RouteResult(True, "document", f"Indexed {path} (id {did}).", tool="documents")
            info = self.docs.analyze(path)
            return RouteResult(True, "document",
                               f"{path}: {info['words']} words, {info['lines']} lines.\n{info['summary']}",
                               data=info, tool="documents")
        except DocumentError as e:
            return RouteResult(True, "document", f"Document error: {e}", tool="documents")

    def _h_knowledge(self, text: str) -> RouteResult:
        content = re.sub(r"(?i)^.*?\b(learn that|add knowledge|teach you|knowledge base)\b",
                         "", text).strip(" :,-")
        if not content:
            return RouteResult(True, "knowledge", "What should I learn?")
        item = self.knowledge.add(topic=content[:40], content=content)
        return RouteResult(True, "knowledge", f"Learned: {content}", data={"id": item.id}, tool="knowledge")

    def _h_weather(self, text: str) -> RouteResult:
        m = re.search(r"(?i)\b(?:in|at|for)\s+([A-Za-z\s]+)$", text.strip())
        location = m.group(1).strip() if m else None
        result = self.web.get_weather(location)
        if result.get("ok"):
            return RouteResult(True, "weather", result["summary"], data=result, tool="weather")
        return RouteResult(True, "weather", f"Weather unavailable: {result.get('error', 'unknown error')}",
                           tool="weather")

    def _h_web_search(self, text: str) -> RouteResult:
        query = re.sub(r"(?i)^.*?\b(search|google|look up|find online|latest news|web)\b",
                       "", text).strip(" :,-")
        if not query:
            return RouteResult(True, "web_search", "What should I search for?")
        results = self.web.search(query)
        if not results:
            return RouteResult(True, "web_search",
                               "I couldn't reach the internet. Try again when online.", tool="web")
        lines = [f"{i+1}. {r['title']}\n   {r['url']}" for i, r in enumerate(results)]
        return RouteResult(True, "web_search", f"Search results for '{query}':\n" + "\n".join(lines),
                           data={"results": results}, tool="web")

    def _h_status(self, text: str) -> RouteResult:
        stats = self.tasks.stats()
        mem = self.memory.count()
        online = self.web.is_online()
        text_out = (f"ROLEX AI {CONFIG.version} — {'online' if online else 'offline (local mode)'}\n"
                    f"Memories: {mem} | Tasks: {stats['total']} "
                    f"(pending {stats['PENDING']}, done {stats['COMPLETED']})")
        return RouteResult(True, "status", text_out, tool="system")

    def _h_time(self, text: str) -> RouteResult:
        now = time.localtime()
        return RouteResult(True, "time", time.strftime("It's %I:%M %p on %A, %d %B %Y.", now), tool="system")

    def _h_diagnostics(self, text: str) -> RouteResult:
        report = self.diagnostics.report()
        return RouteResult(True, "diagnostics", report["summary"], data=report, tool="diagnostics")

    def _h_help(self, text: str) -> RouteResult:
        help_text = (
            "I'm ROLEX AI. Here's what I can do:\n"
            "• remember that ... / forget ... / what do you remember\n"
            "• calculate 25 * 4\n"
            "• remind me to ... / show my tasks / complete task 3\n"
            "• create a plan for ...\n"
            "• read report.pdf / summarize notes.txt\n"
            "• weather in Chennai\n"
            "• search latest AI news\n"
            "• status / diagnostics / time / providers"
        )
        return RouteResult(True, "help", help_text, tool="system")

    def _h_providers(self, text: str) -> RouteResult:
        status = CONFIG.provider_status()
        lines = [f"{'✓' if v else '✗'} {k}" for k, v in status.items()]
        mode = "ROLEX-ONLY (local)" if CONFIG.rolex_only_mode else "external allowed"
        return RouteResult(True, "providers", f"AI providers ({mode}):\n" + "\n".join(lines), tool="system")

    def _h_policy(self, text: str) -> RouteResult:
        return RouteResult(True, "policy", self.policy.describe(), tool="policy")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _parse_due(self, text: str) -> Optional[float]:
        """Parse simple due dates: 'tomorrow', 'today', 'in N days'."""
        low = text.lower()
        now = time.time()
        if "tomorrow" in low or "naalai" in low:
            return now + 86400
        if "today" in low or "indru" in low:
            return now + 3600
        m = re.search(r"in (\d+) (day|days|hour|hours|week|weeks)", low)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            mult = {"day": 86400, "days": 86400, "hour": 3600, "hours": 3600,
                    "week": 604800, "weeks": 604800}[unit]
            return now + n * mult
        return None


_router: Optional[Router] = None


def get_router() -> Router:
    global _router
    if _router is None:
        _router = Router()
    return _router
