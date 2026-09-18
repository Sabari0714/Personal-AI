"""Unit tests for database, memory, tasks, planner, knowledge, security, policy."""
import os
import tempfile
import unittest
from pathlib import Path

# Use an isolated temp DB for tests
_TMP = tempfile.mkdtemp(prefix="rolex_test_")
os.environ["ROLEX_TEST_DB"] = str(Path(_TMP) / "test.db")

from data.database import Database
from modules.memory import MemoryManager
from modules.tasks import TaskManager
from modules.planner import Planner
from modules.knowledge import KnowledgeBase
from modules.security import SecurityManager
from modules.policy import PolicyEngine


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = Database(Path(_TMP) / "db_test.db")

    def test_integrity(self):
        self.assertTrue(self.db.integrity_check())

    def test_backup_restore(self):
        self.db.execute("INSERT INTO memory(category, content, importance, created_at, updated_at) "
                        "VALUES('general','hello',1,0,0)")
        backup = self.db.backup(Path(_TMP) / "backup.db")
        self.assertTrue(backup.exists())
        self.assertTrue(self.db.restore(backup))

    def test_transaction_rollback(self):
        try:
            with self.db.transaction() as conn:
                conn.execute("INSERT INTO memory(category, content, importance, created_at, updated_at) "
                             "VALUES('general','tx',1,0,0)")
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass
        rows = self.db.query("SELECT * FROM memory WHERE content='tx'")
        self.assertEqual(len(rows), 0)


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.m = MemoryManager()

    def test_remember_and_get(self):
        item = self.m.remember("I prefer local AI", category="preference")
        self.assertIsNotNone(self.m.get(item.id))

    def test_search(self):
        self.m.remember("unique_marker_xyz", category="general")
        self.assertTrue(len(self.m.search("unique_marker_xyz")) >= 1)

    def test_forget(self):
        item = self.m.remember("to be forgotten")
        self.assertTrue(self.m.forget(item.id))
        self.assertIsNone(self.m.get(item.id))

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            self.m.remember("")


class TestTasks(unittest.TestCase):
    def setUp(self):
        self.t = TaskManager()

    def test_create_and_complete(self):
        task = self.t.create("Test task", priority=1)
        self.assertEqual(task.status, "PENDING")
        self.assertTrue(self.t.complete(task.id))
        self.assertEqual(self.t.get(task.id).status, "COMPLETED")

    def test_delete(self):
        task = self.t.create("Delete me")
        self.assertTrue(self.t.delete(task.id))

    def test_empty_title(self):
        with self.assertRaises(ValueError):
            self.t.create("")

    def test_stats(self):
        self.t.create("stat task")
        stats = self.t.stats()
        self.assertIn("total", stats)


class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.p = Planner()

    def test_create_plan(self):
        plan = self.p.create_plan("Build APK", ["step1", "step2"])
        self.assertEqual(len(plan.steps), 2)

    def test_progress(self):
        plan = self.p.create_plan("Goal", ["a", "b"])
        self.p.set_step_status(plan.steps[0].id, "COMPLETED")
        prog = self.p.progress(plan.id)
        self.assertEqual(prog["done"], 1)

    def test_decompose(self):
        steps = self.p.decompose_goal("build the apk")
        self.assertTrue(len(steps) > 3)


class TestKnowledge(unittest.TestCase):
    def setUp(self):
        self.k = KnowledgeBase()

    def test_add_search(self):
        self.k.add("python", "Python is a programming language", tags="lang")
        self.assertTrue(len(self.k.search("programming")) >= 1)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            self.k.add("", "")


class TestSecurity(unittest.TestCase):
    def setUp(self):
        self.s = SecurityManager()

    def test_encrypt_decrypt(self):
        token = self.s.encrypt("secret data")
        self.assertEqual(self.s.decrypt(token), "secret data")

    def test_tamper_detection(self):
        token = self.s.encrypt("secret")
        tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
        self.assertIsNone(self.s.decrypt(tampered))

    def test_roles(self):
        self.assertTrue(self.s.set_role("admin"))
        self.assertTrue(self.s.can("read"))
        self.assertFalse(self.s.set_role("hacker"))

    def test_audit(self):
        self.s.audit("test_event")
        self.assertTrue(len(self.s.recent_audit()) >= 1)


class TestPolicy(unittest.TestCase):
    def test_rolex_only_blocks_external(self):
        p = PolicyEngine()
        p.set_rolex_only(True)
        self.assertFalse(p.can_use_external_ai())
        p.set_rolex_only(False)

    def test_sensitive_requires_approval(self):
        p = PolicyEngine()
        decision = p.check_sensitive("delete")
        self.assertTrue(decision.requires_approval)


if __name__ == "__main__":
    unittest.main()
