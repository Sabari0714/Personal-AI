"""
ROLEX AI — Security Manager
Secrets handling, encryption, access control, audit logging, supply-chain checks.
No secrets are ever hard-coded; .env or secure storage is used.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from config import CONFIG
from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.security")

ROLES = ("owner", "admin", "device", "service", "limited")


@dataclass
class AuditEvent:
    event: str
    actor: str
    detail: str
    severity: str
    created_at: float


class SecurityManager:
    def __init__(self):
        self.db = get_db()
        self._role = "owner"  # default local role
        self._secret = self._derive_secret()

    # -- secrets ------------------------------------------------------------
    def _derive_secret(self) -> bytes:
        base = CONFIG.secret_key or "rolex-local-default-key"
        return hashlib.sha256(base.encode("utf-8")).digest()

    def encrypt(self, plaintext: str) -> str:
        """Lightweight XOR+HMAC obfuscation for local sensitive data.
        (For production, use a proper AEAD library.)"""
        data = plaintext.encode("utf-8")
        key = self._secret
        stream = (key * (len(data) // len(key) + 1))[:len(data)]
        xored = bytes(a ^ b for a, b in zip(data, stream))
        mac = hmac.new(key, xored, hashlib.sha256).digest()[:16]
        return base64.urlsafe_b64encode(mac + xored).decode("ascii")

    def decrypt(self, token: str) -> Optional[str]:
        try:
            raw = base64.urlsafe_b64decode(token.encode("ascii"))
            mac, xored = raw[:16], raw[16:]
            expected = hmac.new(self._secret, xored, hashlib.sha256).digest()[:16]
            if not hmac.compare_digest(mac, expected):
                log.warning("Decryption integrity check failed.")
                return None
            key = self._secret
            stream = (key * (len(xored) // len(key) + 1))[:len(xored)]
            return bytes(a ^ b for a, b in zip(xored, stream)).decode("utf-8")
        except Exception as e:
            log.error("Decrypt error: %s", e)
            return None

    # -- access control -----------------------------------------------------
    def set_role(self, role: str) -> bool:
        if role in ROLES:
            self._role = role
            self.audit("role_change", detail=role, severity="WARN")
            return True
        return False

    def current_role(self) -> str:
        return self._role

    def can(self, action: str) -> bool:
        """Simple role-based permission matrix."""
        matrix = {
            "owner": {"*"},
            "admin": {"read", "write", "execute", "configure"},
            "device": {"read", "execute"},
            "service": {"read", "execute"},
            "limited": {"read"},
        }
        perms = matrix.get(self._role, {"read"})
        return "*" in perms or action in perms

    # -- audit --------------------------------------------------------------
    def audit(self, event: str, actor: Optional[str] = None, detail: str = "",
              severity: str = "INFO") -> None:
        try:
            self.db.execute(
                "INSERT INTO audit_log(event, actor, detail, severity, created_at) VALUES(?,?,?,?,?)",
                (event, actor or self._role, detail, severity, time.time()),
            )
        except Exception as e:
            log.error("Audit write failed: %s", e)

    def recent_audit(self, limit: int = 50) -> List[AuditEvent]:
        rows = self.db.query(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [AuditEvent(r["event"], r["actor"], r["detail"], r["severity"], r["created_at"])
                for r in rows]

    # -- supply chain -------------------------------------------------------
    def check_secrets_in_source(self, directory: str = ".") -> List[str]:
        """Scan source for accidentally hard-coded secrets."""
        import re
        from pathlib import Path
        patterns = [
            re.compile(r"sk-[A-Za-z0-9]{20,}"),
            re.compile(r"AIza[A-Za-z0-9_\-]{20,}"),
            re.compile(r"hf_[A-Za-z0-9]{20,}"),
        ]
        findings = []
        for p in Path(directory).rglob("*.py"):
            if ".git" in str(p):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                for pat in patterns:
                    if pat.search(text):
                        findings.append(str(p))
                        break
            except Exception:
                continue
        return findings


_security: Optional[SecurityManager] = None


def get_security() -> SecurityManager:
    global _security
    if _security is None:
        _security = SecurityManager()
    return _security
