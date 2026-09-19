"""Smoke test for the new router intents."""
import sys
sys.path.insert(0, ".")
from router import get_router

r = get_router()
CASES = [
    "SIP 5000 12 10",
    "EMI 500000 8.5 20",
    "compound 10000 8 5",
    "my spending",
    "bmi 70 1.75",
    "device info",
    "battery",
    "smart home devices",
    "inbox",
    "explain code def f(): return 1",
    "what is a cpu",
    "backup now",
    "run self test",
    "knowledge graph stats",
    "daily learning",
    "available tools",
    "list packages",
    "remote lab status",
    "camera available",
    "best ai for coding",
    "emergency stop",
    "release emergency stop",
]
for c in CASES:
    try:
        res = r.route(c)
        txt = (res.text or "").replace("\n", " ")[:90]
        print(f"[{res.intent:16}] {c[:32]:32} -> {txt}")
    except Exception as e:
        print(f"[ERROR] {c}: {e}")
