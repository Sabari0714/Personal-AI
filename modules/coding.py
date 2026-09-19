"""
ROLEX AI — Coding & Development Assistant
Offline helpers for writing, explaining, reviewing and running code.

Capabilities:
  * explain_code()   — heuristic explanation of a snippet
  * review_code()    — static checks (long lines, TODOs, bare excepts, etc.)
  * generate_snippet() — small templates for common tasks
  * run_python()     — execute a snippet safely via the sandbox
  * detect_language() — guess the language of a snippet
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from modules.logger import get_logger
from modules.sandbox import get_sandbox

log = get_logger("rolex.coding")

_LANG_HINTS = {
    "python": [r"\bdef\s+\w+\(", r"\bimport\s+\w+", r"\bprint\(", r":\s*$"],
    "javascript": [r"\bfunction\s+\w+\(", r"\bconst\s+\w+", r"=>", r"console\.log"],
    "java": [r"\bpublic\s+class\b", r"\bSystem\.out\.println"],
    "c": [r"#include\s*<", r"\bprintf\("],
    "html": [r"<html", r"<div", r"<!DOCTYPE"],
    "sql": [r"\bSELECT\b.*\bFROM\b", r"\bINSERT\s+INTO\b"],
    "bash": [r"^#!", r"\becho\b", r"\$\("],
}

_TEMPLATES = {
    "python_http": (
        "import urllib.request\n\n"
        "def fetch(url):\n"
        "    with urllib.request.urlopen(url, timeout=10) as r:\n"
        "        return r.read().decode('utf-8')\n"
    ),
    "python_class": (
        "class MyClass:\n"
        "    def __init__(self, value):\n"
        "        self.value = value\n\n"
        "    def describe(self):\n"
        "        return f'value={self.value}'\n"
    ),
    "python_file": (
        "def read_lines(path):\n"
        "    with open(path, 'r', encoding='utf-8') as f:\n"
        "        return [line.rstrip('\\n') for line in f]\n"
    ),
    "python_sort": (
        "def sort_records(records, key):\n"
        "    return sorted(records, key=lambda r: r[key])\n"
    ),
}


class CodingAssistant:
    def __init__(self):
        self.sandbox = get_sandbox()

    def detect_language(self, code: str) -> str:
        scores = {}
        for lang, patterns in _LANG_HINTS.items():
            scores[lang] = sum(1 for p in patterns if re.search(p, code, re.M))
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "unknown"

    def explain_code(self, code: str) -> Dict:
        lang = self.detect_language(code)
        lines = code.splitlines()
        funcs = re.findall(r"def\s+(\w+)\s*\(", code)
        classes = re.findall(r"class\s+(\w+)", code)
        imports = re.findall(r"^\s*(?:import|from)\s+([\w\.]+)", code, re.M)
        loops = len(re.findall(r"\b(for|while)\b", code))
        conds = len(re.findall(r"\bif\b", code))
        summary = (f"This looks like {lang} code with {len(lines)} lines, "
                   f"{len(funcs)} function(s), {len(classes)} class(es), "
                   f"{loops} loop(s) and {conds} conditional(s).")
        return {"ok": True, "language": lang, "lines": len(lines),
                "functions": funcs, "classes": classes, "imports": imports,
                "summary": summary}

    def review_code(self, code: str) -> Dict:
        issues: List[str] = []
        for i, line in enumerate(code.splitlines(), 1):
            if len(line) > 100:
                issues.append(f"Line {i}: exceeds 100 characters.")
            if "TODO" in line or "FIXME" in line:
                issues.append(f"Line {i}: contains TODO/FIXME.")
            if re.search(r"except\s*:", line):
                issues.append(f"Line {i}: bare 'except:' — catch specific exceptions.")
            if re.search(r"\beval\s*\(", line):
                issues.append(f"Line {i}: use of eval() is unsafe.")
            if re.search(r"\bprint\s*\(", line) and self.detect_language(code) == "python":
                issues.append(f"Line {i}: print() — consider logging in production.")
        return {"ok": True, "issues": issues, "count": len(issues),
                "clean": len(issues) == 0}

    def generate_snippet(self, template: str) -> Dict:
        code = _TEMPLATES.get(template)
        if not code:
            return {"ok": False, "error": f"Unknown template '{template}'.",
                    "available": list(_TEMPLATES.keys())}
        return {"ok": True, "template": template, "code": code}

    def templates(self) -> List[str]:
        return list(_TEMPLATES.keys())

    def run_python(self, code: str, timeout: float = 8.0) -> Dict:
        return self.sandbox.run_python(code, timeout=timeout).to_dict()


_coding: Optional[CodingAssistant] = None


def get_coding() -> CodingAssistant:
    global _coding
    if _coding is None:
        _coding = CodingAssistant()
    return _coding
