"""
ROLEX AI — Knowledge Graph
A lightweight, local-first semantic graph of entities and relationships.

Nodes are concepts/entities; edges are typed relations. The graph supports
add/query/traverse, path finding, and a compact text export used to enrich
prompts. It persists to SQLite so knowledge survives restarts.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.knowledge_graph")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kg_nodes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    kind       TEXT NOT NULL DEFAULT 'concept',
    data       TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS kg_edges (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    src        TEXT NOT NULL,
    relation   TEXT NOT NULL,
    dst        TEXT NOT NULL,
    weight     REAL NOT NULL DEFAULT 1.0,
    created_at REAL NOT NULL,
    UNIQUE(src, relation, dst)
);
CREATE INDEX IF NOT EXISTS idx_kg_edges_src ON kg_edges(src);
CREATE INDEX IF NOT EXISTS idx_kg_edges_dst ON kg_edges(dst);
"""


@dataclass
class Node:
    name: str
    kind: str = "concept"
    data: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "data": self.data}


class KnowledgeGraph:
    def __init__(self):
        self.db = get_db()
        try:
            self.db._conn.executescript(_SCHEMA)
            self.db._conn.commit()
        except Exception as e:  # pragma: no cover
            log.warning("Knowledge graph schema init issue: %s", e)

    # -- nodes --------------------------------------------------------------
    def add_node(self, name: str, kind: str = "concept", **data) -> Node:
        name = (name or "").strip()
        if not name:
            raise ValueError("Node name required.")
        now = time.time()
        self.db.execute(
            "INSERT INTO kg_nodes(name, kind, data, created_at, updated_at) "
            "VALUES(?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET "
            "kind=excluded.kind, data=excluded.data, updated_at=excluded.updated_at",
            (name, kind, json.dumps(data), now, now),
        )
        return Node(name, kind, data)

    def get_node(self, name: str) -> Optional[Node]:
        row = self.db.query_one("SELECT * FROM kg_nodes WHERE name=?", (name,))
        if not row:
            return None
        try:
            data = json.loads(row["data"]) if row["data"] else {}
        except Exception:
            data = {}
        return Node(row["name"], row["kind"], data)

    def nodes(self, kind: Optional[str] = None, limit: int = 500) -> List[Node]:
        if kind:
            rows = self.db.query("SELECT * FROM kg_nodes WHERE kind=? LIMIT ?", (kind, limit))
        else:
            rows = self.db.query("SELECT * FROM kg_nodes LIMIT ?", (limit,))
        out = []
        for r in rows:
            try:
                data = json.loads(r["data"]) if r["data"] else {}
            except Exception:
                data = {}
            out.append(Node(r["name"], r["kind"], data))
        return out

    # -- edges --------------------------------------------------------------
    def relate(self, src: str, relation: str, dst: str, weight: float = 1.0) -> None:
        src, dst, relation = src.strip(), dst.strip(), relation.strip()
        if not (src and dst and relation):
            raise ValueError("src, relation and dst are required.")
        # Auto-create nodes so the graph stays consistent.
        if not self.get_node(src):
            self.add_node(src)
        if not self.get_node(dst):
            self.add_node(dst)
        self.db.execute(
            "INSERT INTO kg_edges(src, relation, dst, weight, created_at) "
            "VALUES(?,?,?,?,?) ON CONFLICT(src, relation, dst) DO UPDATE SET "
            "weight=excluded.weight",
            (src, relation, dst, float(weight), time.time()),
        )

    def neighbors(self, name: str, relation: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """Return (src, relation, dst) triples touching ``name``."""
        if relation:
            rows = self.db.query(
                "SELECT src, relation, dst FROM kg_edges WHERE (src=? OR dst=?) AND relation=?",
                (name, name, relation),
            )
        else:
            rows = self.db.query(
                "SELECT src, relation, dst FROM kg_edges WHERE src=? OR dst=?", (name, name)
            )
        return [(r["src"], r["relation"], r["dst"]) for r in rows]

    def query(self, name: str) -> Dict:
        node = self.get_node(name)
        return {"node": node.to_dict() if node else None,
                "edges": self.neighbors(name)}

    def path(self, src: str, dst: str, max_depth: int = 4) -> Optional[List[str]]:
        """Breadth-first shortest path between two nodes."""
        if src == dst:
            return [src]
        frontier = [(src, [src])]
        seen = {src}
        depth = 0
        while frontier and depth < max_depth:
            nxt = []
            for node, trail in frontier:
                for s, _rel, d in self.neighbors(node):
                    other = d if s == node else s
                    if other in seen:
                        continue
                    if other == dst:
                        return trail + [other]
                    seen.add(other)
                    nxt.append((other, trail + [other]))
            frontier = nxt
            depth += 1
        return None

    def context_block(self, limit: int = 20) -> str:
        rows = self.db.query(
            "SELECT src, relation, dst FROM kg_edges ORDER BY id DESC LIMIT ?", (limit,)
        )
        if not rows:
            return ""
        lines = [f"- {r['src']} {r['relation']} {r['dst']}" for r in rows]
        return "Knowledge graph facts:\n" + "\n".join(lines)

    def stats(self) -> Dict:
        n = self.db.query_one("SELECT COUNT(*) AS c FROM kg_nodes")
        e = self.db.query_one("SELECT COUNT(*) AS c FROM kg_edges")
        return {"nodes": n["c"] if n else 0, "edges": e["c"] if e else 0}


_kg: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _kg
    if _kg is None:
        _kg = KnowledgeGraph()
    return _kg
