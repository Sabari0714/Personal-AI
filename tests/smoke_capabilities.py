"""Smoke test for ROLEX AI capability modules (Section 4)."""
import sys, traceback
sys.path.insert(0, ".")

MODULES = [
    "tool_manager", "package_manager", "device", "smarthome", "messaging",
    "finance", "health", "biometrics", "emergency", "remote_lab", "coding",
    "computer_knowledge", "self_tests", "recovery", "vision",
]

ok, fail = [], []
for m in MODULES:
    try:
        __import__(f"modules.{m}")
        ok.append(m)
    except Exception as e:
        fail.append((m, str(e)))

print("IMPORT OK :", ", ".join(ok))
print("IMPORT FAIL:", fail or "none")

# Functional checks
def check(name, fn):
    try:
        r = fn()
        print(f"[PASS] {name}: {r}")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        traceback.print_exc()

from modules.finance import get_finance, sip, emi
from modules.health import get_health
from modules.coding import get_coding
from modules.computer_knowledge import get_computer_knowledge
from modules.tool_manager import get_tool_manager
from modules.package_manager import get_package_manager
from modules.device import get_device
from modules.smarthome import get_smarthome
from modules.messaging import get_messaging
from modules.biometrics import get_biometrics
from modules.emergency import get_emergency
from modules.remote_lab import get_remote_lab
from modules.self_tests import get_self_tests
from modules.recovery import get_recovery

check("finance.sip", lambda: sip(5000, 12, 10))
check("finance.emi", lambda: emi(500000, 8.5, 20))
check("health.bmi", lambda: get_health().bmi(70, 1.75))
check("coding.detect_language", lambda: get_coding().detect_language("def f():\n    return 1"))
check("computer_knowledge.topics", lambda: len(get_computer_knowledge().topics()))
check("tool_manager.summary", lambda: get_tool_manager().summary())
check("package_manager.list_known", lambda: len(get_package_manager().list_known()))
check("device.info", lambda: get_device().info())
check("smarthome.devices", lambda: len(get_smarthome().devices()))
check("messaging.inbox", lambda: len(get_messaging().inbox()))
check("biometrics.biometric_available", lambda: get_biometrics().biometric_available())
check("emergency.status", lambda: get_emergency().status())
check("remote_lab.is_running", lambda: get_remote_lab().is_running())
check("self_tests.summary", lambda: get_self_tests().summary())
check("recovery.integrity_check", lambda: get_recovery().integrity_check())
check("vision.camera_available", lambda: get_vision().camera_available() if False else __import__("modules.vision", fromlist=["get_vision"]).get_vision().camera_available())

print("\nDONE")
