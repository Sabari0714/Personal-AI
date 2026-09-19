"""
ROLEX AI — Messaging & Social Integrations
A unified messaging layer with an auto-answer engine.

Design:
  * ``Connector`` — a pluggable adapter for a channel (email, whatsapp,
    telegram, sms, generic webhook). Real sending is delegated to the
    connector; a ``local`` connector just records outbound messages.
  * ``AutoResponder`` — rule-based automatic replies. Rules match incoming
    text and produce a reply, optionally only when the user is away.
  * ``Inbox`` — a local store of messages (in/out) for auditing and context.

This gives ROLEX a working, testable messaging core that can be wired to real
providers (SMTP, Twilio, Telegram Bot API, WhatsApp Cloud API) by adding a
connector — without changing the rest of the app.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.messaging")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    channel    TEXT NOT NULL,
    direction  TEXT NOT NULL,
    sender     TEXT,
    recipient  TEXT,
    body       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'recorded',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel);
CREATE TABLE IF NOT EXISTS auto_rules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    channel    TEXT NOT NULL DEFAULT '*',
    pattern    TEXT NOT NULL,
    reply      TEXT NOT NULL,
    enabled    INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);
"""


@dataclass
class Message:
    id: int
    channel: str
    direction: str
    sender: Optional[str]
    recipient: Optional[str]
    body: str
    status: str
    created_at: float

    def to_dict(self) -> dict:
        return {"id": self.id, "channel": self.channel, "direction": self.direction,
                "sender": self.sender, "recipient": self.recipient, "body": self.body,
                "status": self.status, "created_at": self.created_at}


class Connector:
    """Base connector. Subclass and override ``send`` for real channels."""
    name = "local"

    def send(self, recipient: str, body: str) -> Dict:
        return {"ok": True, "channel": self.name, "recipient": recipient,
                "status": "recorded"}


class LocalConnector(Connector):
    name = "local"


class WebhookConnector(Connector):
    """POSTs JSON to a webhook URL (e.g. Zapier, n8n, custom bot)."""
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

    def send(self, recipient: str, body: str) -> Dict:
        import urllib.request
        try:
            payload = json.dumps({"to": recipient, "text": body}).encode()
            req = urllib.request.Request(self.url, data=payload,
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=8)
            return {"ok": True, "channel": self.name, "status": "sent"}
        except Exception as e:
            return {"ok": False, "channel": self.name, "error": str(e)}


class MessagingHub:
    def __init__(self):
        self.db = get_db()
        self._connectors: Dict[str, Connector] = {"local": LocalConnector()}
        self._away = False
        try:
            self.db._connects = None  # noqa
            self.db._conn.executescript(_SCHEMA)
            self.db._conn.commit()
        except Exception as e:  # pragma: no cover
            log.warning("Messaging schema init issue: %s", e)

    # -- connectors ---------------------------------------------------------
    def register_connector(self, connector: Connector) -> None:
        self._connectors[connector.name] = connector

    def channels(self) -> List[str]:
        return list(self._connectors.keys())

    def set_away(self, away: bool) -> None:
        self._away = away

    # -- sending ------------------------------------------------------------
    def send(self, channel: str, recipient: str, body: str) -> Dict:
        conn = self._connectors.get(channel, self._connectors["local"])
        result = conn.send(recipient, body)
        self._store(channel, "out", None, recipient, body,
                    "sent" if result.get("ok") else "failed")
        return result

    def _store(self, channel: str, direction: str, sender: Optional[str],
               recipient: Optional[str], body: str, status: str) -> int:
        cur = self.db.execute(
            "INSERT INTO messages(channel, direction, sender, recipient, body, status, "
            "created_at) VALUES(?,?,?,?,?,?,?)",
            (channel, direction, sender, recipient, body, status, time.time()),
        )
        return cur.lastrowid

    # -- auto-answer rules --------------------------------------------------
    def add_rule(self, pattern: str, reply: str, channel: str = "*") -> int:
        cur = self.db.execute(
            "INSERT INTO auto_rules(channel, pattern, reply, enabled, created_at) "
            "VALUES(?,?,?,?,?)",
            (channel, pattern, reply, 1, time.time()),
        )
        return cur.lastrowid

    def rules(self) -> List[Dict]:
        rows = self.db.query("SELECT * FROM auto_rules ORDER BY id DESC")
        return [dict(r) for r in rows]

    def remove_rule(self, rule_id: int) -> bool:
        cur = self.db.execute("DELETE FROM auto_rules WHERE id=?", (rule_id,))
        return cur.rowcount > 0

    def auto_reply(self, channel: str, sender: str, body: str) -> Optional[str]:
        """Return an automatic reply for an incoming message, if a rule matches."""
        rows = self.db.query(
            "SELECT * FROM auto_rules WHERE enabled=1 AND (channel=? OR channel='*') "
            "ORDER BY id DESC", (channel,),
        )
        for r in rows:
            try:
                if re.search(r["pattern"], body, re.I):
                    reply = r["reply"]
                    self._store(channel, "in", sender, None, body, "received")
                    self.send(channel, sender, reply)
                    return reply
            except re.error:
                continue
        self._store(channel, "in", sender, None, body, "received")
        return None

    # -- inbox --------------------------------------------------------------
    def inbox(self, channel: Optional[str] = None, limit: int = 50) -> List[Message]:
        if channel:
            rows = self.db.query(
                "SELECT * FROM messages WHERE channel=? ORDER BY id DESC LIMIT ?",
                (channel, limit))
        else:
            rows = self.db.query("SELECT * FROM messages ORDER BY id DESC LIMIT ?", (limit,))
        return [Message(r["id"], r["channel"], r["direction"], r["sender"],
                        r["recipient"], r["body"], r["status"], r["created_at"])
                for r in rows]


_hub: Optional[MessagingHub] = None


def get_messaging() -> MessagingHub:
    global _hub
    if _hub is None:
        _hub = MessagingHub()
    return _hub
