"""Integration tests: Router -> Tools -> Database, and app end-to-end."""
import os
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="rolex_itest_")

from router import Router
from app import RolexApp


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.r = Router()

    def test_intent_remember(self):
        self.assertEqual(self.r.detect_intent("remember that I prefer local AI"), "remember")

    def test_intent_calculate(self):
        self.assertEqual(self.r.detect_intent("calculate 25 * 4"), "calculate")

    def test_intent_task(self):
        self.assertEqual(self.r.detect_intent("remind me to study"), "task_create")

    def test_intent_weather(self):
        self.assertEqual(self.r.detect_intent("what is the weather in Chennai"), "weather")

    def test_intent_help(self):
        self.assertEqual(self.r.detect_intent("help"), "help")

    def test_route_calculate(self):
        res = self.r.route("calculate 25 * 4")
        self.assertTrue(res.handled)
        self.assertIn("100", res.text)

    def test_route_remember(self):
        res = self.r.route("remember that my favourite color is blue")
        self.assertTrue(res.handled)
        self.assertIn("remember", res.text.lower())

    def test_route_task_create(self):
        res = self.r.route("remind me to finish the report")
        self.assertTrue(res.handled)
        self.assertEqual(res.tool, "tasks")

    def test_route_unknown_falls_through(self):
        res = self.r.route("tell me a story about dragons")
        self.assertFalse(res.handled)


class TestAppEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = RolexApp()

    def test_process_math(self):
        resp = self.app.process("calculate 12 * 12")
        self.assertIn("144", resp.text)

    def test_process_remember(self):
        resp = self.app.process("remember that I use Termux")
        self.assertIn("remember", resp.text.lower())

    def test_process_help(self):
        resp = self.app.process("help")
        self.assertIn("ROLEX", resp.text)

    def test_process_status(self):
        resp = self.app.process("status")
        self.assertTrue(len(resp.text) > 0)

    def test_process_empty(self):
        resp = self.app.process("")
        self.assertTrue(len(resp.text) > 0)

    def test_status_dict(self):
        status = self.app.status()
        self.assertIn("version", status)
        self.assertIn("providers", status)

    def test_diagnostics(self):
        report = self.app.diagnostics_report()
        self.assertIn("summary", report)

    def test_process_convert(self):
        resp = self.app.process("convert 5 km to miles")
        self.assertIn("miles", resp.text.lower())
        self.assertEqual(resp.tool, "math")

    def test_process_convert_how_many(self):
        resp = self.app.process("how many miles in 10 km")
        self.assertIn("miles", resp.text.lower())

    def test_process_recall_specific(self):
        self.app.process("remember my wifi password is hunter2")
        resp = self.app.process("what is my wifi password")
        self.assertIn("hunter2", resp.text)


if __name__ == "__main__":
    unittest.main()
