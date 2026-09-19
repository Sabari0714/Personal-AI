"""
ROLEX AI — Sandbox
A safe execution environment for testing generated code and proposed
self-modifications before they touch the live system.

The sandbox:
  * runs Python snippets in a subprocess with a hard timeout,
  * captures stdout/stderr/exit code,
  * blocks obviously dangerous operations (network, subprocess, file writes
    outside a scratch dir) via an AST guard,
  * never imports the snippet into the host process.

This is intentionally conservative — it is a guardrail, not a jail.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from config import BUILD_DIR
from modules.logger import get_logger

log = get_logger("rolex.sandbox")

# Modules that generated code may import.
_ALLOWED_IMPORTS = {
    "math", "cmath", "statistics", "random", "json", "re", "datetime",
    "itertools", "functools", "collections", "decimal", "fractions",
    "string", "textwrap", "typing", "dataclasses", "enum", "heapq",
    "bisect", "copy", "uuid", "hashlib", "base64", "time", "ast",
}

# Names that are never allowed in sandboxed code.
_FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "__import__", "open", "input",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "memoryview", "breakpoint", "exit", "quit",
}

_FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "pathlib", "ctypes",
    "importlib", "pickle", "marshal", "multiprocessing", "threading",
    "requests", "urllib", "http", "ftplib", "smtplib", "telnetlib",
}


@dataclass
class SandboxResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    elapsed: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {"ok": self.ok, "stdout": self.stdout, "stderr": self.stderr,
                "exit_code": self.exit_code, "elapsed": self.elapsed,
                "error": self.error}


class Sandbox:
    def __init__(self, scratch_dir: Optional[Path] = None):
        self.scratch = Path(scratch_dir) if scratch_dir else (BUILD_DIR / "sandbox")
        self.scratch.mkdir(parents=True, exist_ok=True)

    # -- static safety analysis --------------------------------------------
    def check_code(self, code: str) -> List[str]:
        """Return a list of policy violations (empty == safe)."""
        violations: List[str] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"SyntaxError: {e}"]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in _FORBIDDEN_MODULES:
                        violations.append(f"forbidden import: {alias.name}")
                    elif root not in _ALLOWED_IMPORTS:
                        violations.append(f"unlisted import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in _FORBIDDEN_MODULES:
                    violations.append(f"forbidden import: {node.module}")
                elif root and root not in _ALLOWED_IMPORTS:
                    violations.append(f"unlisted import: {node.module}")
            elif isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
                violations.append(f"forbidden name: {node.id}")
            elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                violations.append(f"dunder access: {node.attr}")
        return violations

    # -- execution ----------------------------------------------------------
    def run_python(self, code: str, timeout: float = 8.0,
                   allow_unsafe: bool = False) -> SandboxResult:
        """Execute a Python snippet in an isolated subprocess."""
        if not allow_unsafe:
            violations = self.check_code(code)
            if violations:
                return SandboxResult(False, error="Policy violation: " + "; ".join(violations))

        fd, path = tempfile.mkstemp(suffix=".py", dir=str(self.scratch))
        os.close(fd)
        Path(path).write_text(code, encoding="utf-8")
        t0 = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, "-I", path],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(self.scratch),
            )
            return SandboxResult(
                ok=(proc.returncode == 0),
                stdout=proc.stdout[-8000:],
                stderr=proc.stderr[-8000:],
                exit_code=proc.returncode,
                elapsed=round(time.time() - t0, 3),
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(False, error=f"Timed out after {timeout}s",
                                 elapsed=round(time.time() - t0, 3))
        except Exception as e:
            return SandboxResult(False, error=str(e), elapsed=round(time.time() - t0, 3))
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def run_tests(self, test_code: str, timeout: float = 15.0) -> SandboxResult:
        """Run a unittest-style test snippet."""
        return self.run_python(test_code, timeout=timeout)


_sandbox: Optional[Sandbox] = None


def get_sandbox() -> Sandbox:
    global _sandbox
    if _sandbox is None:
        _sandbox = Sandbox()
    return _sandbox
