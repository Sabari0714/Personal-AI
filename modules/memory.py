"""
ROLEX AI — Personal Memory System
Save / retrieve / search / update / forget / validate.
Memory remains under user control.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple

from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.memory")

CATEGORIES = ("preference", "project", "instruction", "context", "fact", "general")


@dataclass
class MemoryItem:
    id: int
    category: str
    key: Optional[str]
    content: str
    importance: int
    created_at: float
    updated_at: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "key": self.key,
            "content": self.content,
            "importance": self.importance,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class MemoryManager:
    def __init__(self):
        self.db = get_db()
        # Short-term (working) memory: recent turns, in-process only.
        self._short_term: Deque[Tuple[str, str, float]] = deque(maxlen=40)

    # -- short-term (working) memory ---------------------------------------
    def add_turn(self, role: str, content: str) -> None:
        """Record a recent conversation turn in short-term memory."""
        self._short_term.append((role, (content or "").strip(), time.time()))

    def short_term(self, limit: int = 10) -> List[Tuple[str, str, float]]:
        return list(self._short_term)[-limit:]

    def short_term_block(self, limit: int = 8) -> str:
        turns = self.short_term(limit)
        if not turns:
            return ""
        lines = [f"{role}: {content}" for role, content, _t in turns]
        return "Recent conversation:\n" + "\n".join(lines)

    def clear_short_term(self) -> None:
        self._short_term.clear()

    # -- long-term consolidation -------------------------------------------
    def consolidate(self) -> int:
        """Promote important short-term turns into long-term memory.

        Heuristic: turns that contain durable cues (preferences, instructions,
        facts) are saved. Returns the number of items promoted.
        """
        cues = ("i prefer", "i like", "i always", "i never", "remember",
                "my name is", "call me", "istam", "enoda", "always use",
                "don't forget", "important")
        promoted = 0
        for role, content, _t in list(self._short_term):
            if role != "user" or len(content) < 8:
                continue
            low = content.lower()
            if any(c in low for c in cues):
                try:
                    self.remember(content, category="context", importance=2)
                    promoted += 1
                except Exception:
                    pass
        if promoted:
            log.info("Consolidated %d short-term turn(s) into long-term memory.", promoted)
        return promoted

    # -- write --------------------------------------------------------------
    def remember(self, content: str, category: str = "general",
                 key: Optional[str] = None, importance: int = 1) -> MemoryItem:
        content = (content or "").strip()
        if not content:
            raise ValueError("Cannot remember empty content.")
        if category not in CATEGORIES:
            category = "general"
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO memory(category, key, content, importance, created_at, updated_at) "
            "VALUES(?,?,?,?,?,?)",
            (category, key, content, int(importance), now, now),
        )
        log.info("Memory saved [%s]: %s", category, content[:60])
        return MemoryItem(cur.lastrowid, category, key, content, int(importance), now, now)

    def update(self, mem_id: int, content: Optional[str] = None,
               category: Optional[str] = None, importance: Optional[int] = None) -> bool:
        row = self.db.query_one("SELECT * FROM memory WHERE id=?", (mem_id,))
        if not row:
            return False
        self.db.execute(
            "UPDATE memory SET content=?, category=?, importance=?, updated_at=? WHERE id=?",
            (
                content if content is not None else row["content"],
                category if category is not None else row["category"],
                importance if importance is not None else row["importance"],
                time.time(),
                mem_id,
            ),
        )
        return True

    def forget(self, mem_id: int) -> bool:
        cur = self.db.execute("DELETE FROM memory WHERE id=?", (mem_id,))
        return cur.rowcount > 0

    def forget_by_key(self, key: str) -> int:
        cur = self.db.execute("DELETE FROM memory WHERE key=?", (key,))
        return cur.rowcount

    # -- read ---------------------------------------------------------------
    def _row_to_item(self, row) -> MemoryItem:
        return MemoryItem(row["id"], row["category"], row["key"], row["content"],
                          row["importance"], row["created_at"], row["updated_at"])

    def get(self, mem_id: int) -> Optional[MemoryItem]:
        row = self.db.query_one("SELECT * FROM memory WHERE id=?", (mem_id,))
        return self._row_to_item(row) if row else None

    def all(self, category: Optional[str] = None, limit: int = 200) -> List[MemoryItem]:
        if category:
            rows = self.db.query(
                "SELECT * FROM memory WHERE category=? ORDER BY importance DESC, updated_at DESC LIMIT ?",
                (category, limit),
            )
        else:
            rows = self.db.query(
                "SELECT * FROM memory ORDER BY importance DESC, updated_at DESC LIMIT ?", (limit,)
            )
        return [self._row_to_item(r) for r in rows]

    def search(self, term: str, limit: int = 50) -> List[MemoryItem]:
        term = (term or "").strip()
        if not term:
            return []
        like = f"%{term}%"
        rows = self.db.query(
            "SELECT * FROM memory WHERE content LIKE ? OR key LIKE ? OR category LIKE ? "
            "ORDER BY importance DESC, updated_at DESC LIMIT ?",
            (like, like, like, limit),
        )
        return [self._row_to_item(r) for r in rows]

    def context_block(self, limit: int = 12) -> str:
        """Return a compact memory block for prompt context (long + short term)."""
        parts = []
        short = self.short_term_block(limit=6)
        if short:
            parts.append(short)
        items = self.all(limit=limit)
        if items:
            lines = [f"- [{m.category}] {m.content}" for m in items]
            parts.append("Known user memory:\n" + "\n".join(lines))
        return "\n\n".join(parts)

    def count(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS c FROM memory")
        return row["c"] if row else 0


_memory: Optional[MemoryManager] = None


def get_memory() -> MemoryManager:
    global _memory
    if _memory is None:
        _memory = MemoryManager()
    return _memory
