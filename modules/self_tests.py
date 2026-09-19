"""
ROLEX AI — Automated Self-Tests
A built-in test harness that verifies core subsystems are healthy.

Each check returns pass/fail with a short detail. The suite is safe to run at
startup, on a schedule, or on demand, and never mutates user data.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, List

from modules.logger import get_logger

log = get_logger("rolex.self_tests")


@dataclass
class TestResult:
    name: str
    ok: bool
    detail: str = ""
    elapsed: float = 0.0

    def to_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "detail": self.detail,
                "elapsed": round(self.elapsed, 3)}


class SelfTestSuite:
    def __init__(self):
        self._tests: List[Callable[[], TestResult]] = []
        self._register_defaults()

    def register(self, fn: Callable[[], TestResult]) -> None:
        self._tests.append(fn)

    def _register_defaults(self) -> None:
        self.register(self._test_database)
        self.register(self._test_memory)
        self.register(self._test_math)
        self.register(self._test_knowledge_graph)
        self.register(self._test_sandbox)
        self.register(self._test_voice)
        self.register(self._test_finance)

    # -- individual tests ---------------------------------------------------
    def _test_database(self) -> TestResult:
        t0 = time.time()
        try:
            from data.database import get_db
            ok = get_db().integrity_check()
            return TestResult("database", ok, "integrity ok" if ok else "integrity failed",
                              time.time() - t0)
        except Exception as e:
            return TestResult("database", False, str(e), time.time() - t0)

    def _test_memory(self) -> TestResult:
        t0 = time.time()
        try:
            from modules.memory import get_memory
            m = get_memory()
            item = m.remember("__selftest__ ping", category="general")
            found = any(x.id == item.id for x in m.search("__selftest__"))
            m.forget(item.id)
            return TestResult("memory", found, "write/read/delete ok" if found else "roundtrip failed",
                              time.time() - t0)
        except Exception as e:
            return TestResult("memory", False, str(e), time.time() - t0)

    def _test_math(self) -> TestResult:
        t0 = time.time()
        try:
            from modules.math_engine import solve
            out = solve("2 + 2")
            ok = "4" in out
            return TestResult("math", ok, out[:60], time.time() - t0)
        except Exception as e:
            return TestResult("math", False, str(e), time.time() - t0)

    def _test_knowledge_graph(self) -> TestResult:
        t0 = time.time()
        try:
            from modules.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()
            kg.relate("__selftest_a__", "links", "__selftest_b__")
            path = kg.path("__selftest_a__", "__selftest_b__")
            ok = path is not None
            return TestResult("knowledge_graph", ok, str(path), time.time() - t0)
        except Exception as e:
            return TestResult("knowledge_graph", False, str(e), time.time() - t0)

    def _test_sandbox(self) -> TestResult:
        t0 = time.time()
        try:
            from modules.sandbox import get_sandbox
            res = get_sandbox().run_python("print(6*7)")
            ok = res.ok and "42" in res.stdout
            return TestResult("sandbox", ok, res.stdout.strip() or res.error or "",
                              time.time() - t0)
        except Exception as e:
            return TestResult("sandbox", False, str(e), time.time() - t0)

    def _test_voice(self) -> TestResult:
        t0 = time.time()
        try:
            from modules.voice import get_voice
            v = get_voice()
            detail = f"backend={v.backend_name()} stt={v.stt_available()} tts={v.tts_available()}"
            return TestResult("voice", True, detail, time.time() - t0)
        except Exception as e:
            return TestResult("voice", False, str(e), time.time() - t0)

    def _test_finance(self) -> TestResult:
        t0 = time.time()
        try:
            from modules.finance import emi
            r = emi(100000, 10, 1)
            ok = r["emi"] > 0
            return TestResult("finance", ok, f"emi={r['emi']}", time.time() - t0)
        except Exception as e:
            return TestResult("finance", False, str(e), time.time() - t0)

    # -- runner -------------------------------------------------------------
    def run_all(self) -> Dict:
        results = []
        for test in self._tests:
            try:
                results.append(test())
            except Exception as e:
                results.append(TestResult(getattr(test, "__name__", "test"), False, str(e)))
        passed = sum(1 for r in results if r.ok)
        return {"total": len(results), "passed": passed,
                "failed": len(results) - passed,
                "results": [r.to_dict() for r in results],
                "ok": passed == len(results)}

    def summary(self) -> str:
        report = self.run_all()
        lines = [f"{'✓' if r['ok'] else '✗'} {r['name']}: {r['detail']}"
                 for r in report["results"]]
        return (f"Self-tests: {report['passed']}/{report['total']} passed\n"
                + "\n".join(lines))


_suite: SelfTestSuite = SelfTestSuite()


def get_self_tests() -> SelfTestSuite:
    return _suite
