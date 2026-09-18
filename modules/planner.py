"""
ROLEX AI — Planning Engine
Convert goals into ordered steps, store plans, track step status and dependencies.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.planner")


@dataclass
class PlanStep:
    id: int
    plan_id: int
    step_no: int
    description: str
    status: str
    depends_on: Optional[int]
    result: Optional[str]


@dataclass
class Plan:
    id: int
    goal: str
    status: str
    created_at: float
    updated_at: float
    steps: List[PlanStep] = field(default_factory=list)


class Planner:
    def __init__(self):
        self.db = get_db()

    def create_plan(self, goal: str, steps: List[str]) -> Plan:
        goal = (goal or "").strip()
        if not goal:
            raise ValueError("Plan goal cannot be empty.")
        steps = [s.strip() for s in steps if s and s.strip()]
        if not steps:
            raise ValueError("A plan needs at least one step.")
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO plans(goal, status, created_at, updated_at) VALUES(?,?,?,?)",
            (goal, "ACTIVE", now, now),
        )
        plan_id = cur.lastrowid
        for i, desc in enumerate(steps, start=1):
            self.db.execute(
                "INSERT INTO plan_steps(plan_id, step_no, description, status, depends_on) "
                "VALUES(?,?,?,?,?)",
                (plan_id, i, desc, "PENDING", i - 1 if i > 1 else None),
            )
        log.info("Plan created: %s (%d steps)", goal, len(steps))
        return self.get_plan(plan_id)

    def get_plan(self, plan_id: int) -> Optional[Plan]:
        row = self.db.query_one("SELECT * FROM plans WHERE id=?", (plan_id,))
        if not row:
            return None
        step_rows = self.db.query(
            "SELECT * FROM plan_steps WHERE plan_id=? ORDER BY step_no ASC", (plan_id,)
        )
        steps = [
            PlanStep(r["id"], r["plan_id"], r["step_no"], r["description"],
                     r["status"], r["depends_on"], r["result"])
            for r in step_rows
        ]
        return Plan(row["id"], row["goal"], row["status"], row["created_at"], row["updated_at"], steps)

    def list_plans(self, limit: int = 50) -> List[Plan]:
        rows = self.db.query("SELECT id FROM plans ORDER BY updated_at DESC LIMIT ?", (limit,))
        return [self.get_plan(r["id"]) for r in rows]

    def set_step_status(self, step_id: int, status: str, result: Optional[str] = None) -> bool:
        status = status.upper()
        if status not in ("PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "SKIPPED"):
            return False
        self.db.execute(
            "UPDATE plan_steps SET status=?, result=? WHERE id=?", (status, result, step_id)
        )
        row = self.db.query_one("SELECT plan_id FROM plan_steps WHERE id=?", (step_id,))
        if row:
            self.db.execute("UPDATE plans SET updated_at=? WHERE id=?", (time.time(), row["plan_id"]))
            self._maybe_complete(row["plan_id"])
        return True

    def _maybe_complete(self, plan_id: int) -> None:
        rows = self.db.query("SELECT status FROM plan_steps WHERE plan_id=?", (plan_id,))
        if rows and all(r["status"] in ("COMPLETED", "SKIPPED") for r in rows):
            self.db.execute("UPDATE plans SET status='COMPLETED', updated_at=? WHERE id=?",
                            (time.time(), plan_id))

    def progress(self, plan_id: int) -> dict:
        plan = self.get_plan(plan_id)
        if not plan:
            return {}
        total = len(plan.steps)
        done = sum(1 for s in plan.steps if s.status in ("COMPLETED", "SKIPPED"))
        return {"plan_id": plan_id, "goal": plan.goal, "total": total, "done": done,
                "percent": round(100 * done / total, 1) if total else 0.0, "status": plan.status}

    # -- goal decomposition (local heuristic) -------------------------------
    def decompose_goal(self, goal: str) -> List[str]:
        """Local heuristic decomposition for common goals."""
        g = goal.lower()
        if "apk" in g or "android" in g or "build" in g:
            return [
                "Validate source code",
                "Run unit and integration tests",
                "Fix dependencies",
                "Configure Buildozer",
                "Build APK",
                "Install on device",
                "Runtime test",
                "Regression test",
                "Release",
            ]
        if "rolex" in g:
            return [
                "Define requirements",
                "Design architecture",
                "Implement core modules",
                "Implement intelligence layer",
                "Implement GUI and voice",
                "Add security",
                "Add automation",
                "Test everything",
                "Build and release",
            ]
        # Generic decomposition
        return [
            f"Clarify the goal: {goal}",
            "Gather required information",
            "Break into concrete tasks",
            "Execute tasks",
            "Validate results",
            "Finalize and report",
        ]


_planner: Optional[Planner] = None


def get_planner() -> Planner:
    global _planner
    if _planner is None:
        _planner = Planner()
    return _planner
