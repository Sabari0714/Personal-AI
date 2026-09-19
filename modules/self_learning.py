"""
ROLEX AI — Self-Learning Engine
Daily learning routines that turn conversations, memories and knowledge into
durable, structured understanding.

The engine is conservative: it never invents facts. It distils what the user
has explicitly told it, extracts entities/relations into the knowledge graph,
promotes frequently-used facts, and records a learning journal so progress is
auditable and reversible.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from data.database import get_db
from modules.logger import get_logger
from modules.memory import get_memory
from modules.knowledge_graph import get_knowledge_graph

log = get_logger("rolex.self_learning")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS learning_journal (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT NOT NULL,
    summary    TEXT NOT NULL,
    detail     TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS learned_facts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    subject    TEXT NOT NULL,
    relation   TEXT NOT NULL,
    object     TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.6,
    hits       INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(subject, relation, object)
);
"""

# Simple relation cues (English + Tanglish) used to mine facts from sentences.
_RELATION_CUES = [
    (r"\b(?:is|are|was|were)\s+(?:a|an|the)?\s*", "is_a"),
    (r"\b(?:works at|works for|working at|velai)\b", "works_at"),
    (r"\b(?:lives in|stays in|from|ooru)\b", "lives_in"),
    (r"\b(?:likes|likes to|loves|prefers|istam)\b", "likes"),
    (r"\b(?:owns|has|have|kitta)\b", "has"),
    (r"\b(?:uses|using|use pannuvaan)\b", "uses"),
    (r"\b(?:wants|needs|venum)\b", "wants"),
]


@dataclass
class LearnedFact:
    subject: str
    relation: str
    object: str
    confidence: float = 0.6
    hits: int = 1


class SelfLearningEngine:
    def __init__(self):
        self.db = get_db()
        self.memory = get_memory()
        self.kg = get_knowledge_graph()
        try:
            self.db._conn.executescript(_SCHEMA)
            self.db._conn.commit()
        except Exception as e:  # pragma: no cover
            log.warning("Self-learning schema init issue: %s", e)

    # -- journal ------------------------------------------------------------
    def journal(self, kind: str, summary: str, detail: Optional[dict] = None) -> None:
        self.db.execute(
            "INSERT INTO learning_journal(kind, summary, detail, created_at) VALUES(?,?,?,?)",
            (kind, summary, json.dumps(detail or {}), time.time()),
        )

    def recent_journal(self, limit: int = 20) -> List[Dict]:
        rows = self.db.query(
            "SELECT * FROM learning_journal ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [{"id": r["id"], "kind": r["kind"], "summary": r["summary"],
                 "detail": json.loads(r["detail"]) if r["detail"] else {},
                 "created_at": r["created_at"]} for r in rows]

    # -- fact mining --------------------------------------------------------
    def mine_facts(self, text: str) -> List[LearnedFact]:
        """Extract simple subject-relation-object facts from a sentence."""
        text = (text or "").strip()
        if not text:
            return []
        facts: List[LearnedFact] = []
        # Split into clauses for cleaner extraction.
        for clause in re.split(r"[.;\n]|\band\b|\bmatrum\b|,\s*(?=[A-Z])", text, flags=re.I):
            clause = clause.strip()
            if len(clause) < 6:
                continue
            for pattern, relation in _RELATION_CUES:
                m = re.search(pattern, clause, re.I)
                if not m:
                    continue
                subj = clause[:m.start()].strip(" ,")
                obj = clause[m.end():].strip(" ,")
                subj = re.sub(r"^(my|the|a|an|i|en|enoda)\s+", "", subj, flags=re.I).strip()
                if subj and obj and len(subj) < 60 and len(obj) < 120:
                    facts.append(LearnedFact(subj, relation, obj))
                break
        return facts

    def learn_from_text(self, text: str, source: str = "conversation") -> int:
        """Mine facts, persist them, and mirror into the knowledge graph."""
        facts = self.mine_facts(text)
        stored = 0
        for f in facts:
            self._store_fact(f)
            try:
                self.kg.relate(f.subject, f.relation, f.object, weight=f.confidence)
            except Exception:
                pass
            stored += 1
        if stored:
            self.journal("mine", f"Learned {stored} fact(s) from {source}",
                         {"facts": [f.__dict__ for f in facts]})
        return stored

    def _store_fact(self, f: LearnedFact) -> None:
        now = time.time()
        self.db.execute(
            "INSERT INTO learned_facts(subject, relation, object, confidence, hits, "
            "created_at, updated_at) VALUES(?,?,?,?,?,?,?) "
            "ON CONFLICT(subject, relation, object) DO UPDATE SET "
            "hits=hits+1, confidence=MIN(1.0, confidence+0.05), updated_at=excluded.updated_at",
            (f.subject, f.relation, f.object, f.confidence, 1, now, now),
        )

    def facts(self, limit: int = 100) -> List[LearnedFact]:
        rows = self.db.query(
            "SELECT * FROM learned_facts ORDER BY hits DESC, confidence DESC LIMIT ?", (limit,)
        )
        return [LearnedFact(r["subject"], r["relation"], r["object"],
                            r["confidence"], r["hits"]) for r in rows]

    # -- daily routine ------------------------------------------------------
    def daily_learning_cycle(self) -> Dict:
        """Run the daily consolidation routine. Safe to call repeatedly."""
        t0 = time.time()
        # 1) Re-mine recent memories into the graph.
        mined = 0
        for item in self.memory.all(limit=50):
            mined += self.learn_from_text(item.content, source="memory")
        # 2) Promote high-hit facts into long-term memory.
        promoted = 0
        for f in self.facts(limit=50):
            if f.hits >= 3 and f.confidence >= 0.7:
                try:
                    self.memory.remember(
                        f"{f.subject} {f.relation} {f.object}",
                        category="fact", importance=3,
                    )
                    promoted += 1
                except Exception:
                    pass
        # 3) Record the cycle.
        summary = f"Daily learning: mined {mined}, promoted {promoted}"
        self.journal("daily_cycle", summary,
                     {"mined": mined, "promoted": promoted,
                      "elapsed": round(time.time() - t0, 3)})
        log.info(summary)
        return {"mined": mined, "promoted": promoted,
                "elapsed": round(time.time() - t0, 3)}

    def stats(self) -> Dict:
        f = self.db.query_one("SELECT COUNT(*) AS c FROM learned_facts")
        j = self.db.query_one("SELECT COUNT(*) AS c FROM learning_journal")
        return {"facts": f["c"] if f else 0, "journal_entries": j["c"] if j else 0,
                "graph": self.kg.stats()}


_engine: Optional[SelfLearningEngine] = None


def get_self_learning() -> SelfLearningEngine:
    global _engine
    if _engine is None:
        _engine = SelfLearningEngine()
    return _engine
