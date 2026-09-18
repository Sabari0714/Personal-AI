"""
ROLEX AI — Knowledge System
Structured personal knowledge base with keyword retrieval.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.knowledge")


@dataclass
class KnowledgeItem:
    id: int
    topic: str
    content: str
    tags: Optional[str]
    source: Optional[str]
    created_at: float
    updated_at: float


class KnowledgeBase:
    def __init__(self):
        self.db = get_db()

    def add(self, topic: str, content: str, tags: Optional[str] = None,
            source: Optional[str] = None) -> KnowledgeItem:
        topic = (topic or "").strip()
        content = (content or "").strip()
        if not topic or not content:
            raise ValueError("Knowledge requires a topic and content.")
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO knowledge(topic, content, tags, source, created_at, updated_at) "
            "VALUES(?,?,?,?,?,?)",
            (topic, content, tags, source, now, now),
        )
        return self.get(cur.lastrowid)

    def get(self, kid: int) -> Optional[KnowledgeItem]:
        row = self.db.query_one("SELECT * FROM knowledge WHERE id=?", (kid,))
        if not row:
            return None
        return KnowledgeItem(row["id"], row["topic"], row["content"], row["tags"],
                             row["source"], row["created_at"], row["updated_at"])

    def search(self, term: str, limit: int = 20) -> List[KnowledgeItem]:
        like = f"%{term}%"
        rows = self.db.query(
            "SELECT * FROM knowledge WHERE topic LIKE ? OR content LIKE ? OR tags LIKE ? "
            "ORDER BY updated_at DESC LIMIT ?", (like, like, like, limit),
        )
        return [KnowledgeItem(r["id"], r["topic"], r["content"], r["tags"], r["source"],
                              r["created_at"], r["updated_at"]) for r in rows]

    def all(self, limit: int = 100) -> List[KnowledgeItem]:
        rows = self.db.query("SELECT * FROM knowledge ORDER BY updated_at DESC LIMIT ?", (limit,))
        return [KnowledgeItem(r["id"], r["topic"], r["content"], r["tags"], r["source"],
                              r["created_at"], r["updated_at"]) for r in rows]

    def update(self, kid: int, content: Optional[str] = None,
               tags: Optional[str] = None) -> bool:
        row = self.db.query_one("SELECT * FROM knowledge WHERE id=?", (kid,))
        if not row:
            return False
        self.db.execute(
            "UPDATE knowledge SET content=?, tags=?, updated_at=? WHERE id=?",
            (content if content is not None else row["content"],
             tags if tags is not None else row["tags"], time.time(), kid),
        )
        return True

    def delete(self, kid: int) -> bool:
        cur = self.db.execute("DELETE FROM knowledge WHERE id=?", (kid,))
        return cur.rowcount > 0

    def count(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS c FROM knowledge")
        return row["c"] if row else 0


_kb: Optional[KnowledgeBase] = None


def get_knowledge() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
