"""
ROLEX AI — Task Manager
Create / list / complete / delete / update tasks with priority, due date, status.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.tasks")

STATES = ("PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED", "FAILED")
PRIORITY_LABELS = {1: "HIGH", 2: "MEDIUM", 3: "LOW"}


@dataclass
class Task:
    id: int
    title: str
    description: Optional[str]
    status: str
    priority: int
    due_date: Optional[float]
    created_at: float
    updated_at: float
    completed_at: Optional[float]

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "status": self.status, "priority": self.priority,
            "priority_label": PRIORITY_LABELS.get(self.priority, "MEDIUM"),
            "due_date": self.due_date, "created_at": self.created_at,
            "updated_at": self.updated_at, "completed_at": self.completed_at,
        }


class TaskManager:
    def __init__(self):
        self.db = get_db()

    def _row(self, row) -> Task:
        return Task(row["id"], row["title"], row["description"], row["status"],
                    row["priority"], row["due_date"], row["created_at"],
                    row["updated_at"], row["completed_at"])

    def create(self, title: str, description: Optional[str] = None,
               priority: int = 2, due_date: Optional[float] = None) -> Task:
        title = (title or "").strip()
        if not title:
            raise ValueError("Task title cannot be empty.")
        priority = priority if priority in (1, 2, 3) else 2
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO tasks(title, description, status, priority, due_date, created_at, updated_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (title, description, "PENDING", priority, due_date, now, now),
        )
        log.info("Task created: %s", title)
        return self.get(cur.lastrowid)

    def get(self, task_id: int) -> Optional[Task]:
        row = self.db.query_one("SELECT * FROM tasks WHERE id=?", (task_id,))
        return self._row(row) if row else None

    def list(self, status: Optional[str] = None, limit: int = 100) -> List[Task]:
        if status:
            rows = self.db.query(
                "SELECT * FROM tasks WHERE status=? ORDER BY priority ASC, due_date IS NULL, due_date ASC LIMIT ?",
                (status.upper(), limit),
            )
        else:
            rows = self.db.query(
                "SELECT * FROM tasks ORDER BY status='COMPLETED', priority ASC, "
                "due_date IS NULL, due_date ASC LIMIT ?", (limit,),
            )
        return [self._row(r) for r in rows]

    def pending(self) -> List[Task]:
        return self.list(status="PENDING")

    def update(self, task_id: int, **fields) -> bool:
        task = self.get(task_id)
        if not task:
            return False
        allowed = {"title", "description", "status", "priority", "due_date"}
        sets, params = [], []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k}=?")
                params.append(v)
        if not sets:
            return False
        sets.append("updated_at=?")
        params.append(time.time())
        params.append(task_id)
        self.db.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id=?", params)
        return True

    def complete(self, task_id: int) -> bool:
        return self.update(task_id, status="COMPLETED") and self._set_completed(task_id)

    def _set_completed(self, task_id: int) -> bool:
        self.db.execute("UPDATE tasks SET completed_at=? WHERE id=?", (time.time(), task_id))
        return True

    def delete(self, task_id: int) -> bool:
        cur = self.db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        return cur.rowcount > 0

    def stats(self) -> dict:
        rows = self.db.query("SELECT status, COUNT(*) AS c FROM tasks GROUP BY status")
        out = {s: 0 for s in STATES}
        for r in rows:
            out[r["status"]] = r["c"]
        out["total"] = sum(out[s] for s in STATES)
        return out


_tasks: Optional[TaskManager] = None


def get_tasks() -> TaskManager:
    global _tasks
    if _tasks is None:
        _tasks = TaskManager()
    return _tasks
