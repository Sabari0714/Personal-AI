"""Headless smoke test for the premium GUI — instantiates widgets without a window."""
import os
os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_CONSOLELOG"] = "1"

import sys
sys.path.insert(0, ".")

from kivy.config import Config
Config.set("graphics", "width", "400")
Config.set("graphics", "height", "800")

from kivy.clock import Clock
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout

import gui.rolex_gui as g
print("KIVY_AVAILABLE:", g.KIVY_AVAILABLE)

from app import get_app
rolex = get_app()
print("app OK")

# Build the shell
shell = g.MainShell(rolex)
print("MainShell OK, screens:", [s.name for s in shell.sm.screens])

# Exercise each screen's data loaders
for s in shell.sm.screens:
    if hasattr(s, "refresh"):
        s.refresh()
    if hasattr(s, "_load"):
        s._load()
    if hasattr(s, "_load_values"):
        s._load_values()
print("screen loaders OK")

# Settings save round-trip
ss = g.SettingsScreen(rolex)
ss._load_values()
ss.inputs["OPENAI_API_KEY"].text = "sk-test-1234567890"
ss._save()
from modules import settings_store as store
print("saved openai key present:", bool(store.get_field("OPENAI_API_KEY")))
print("mask:", store.mask(store.get_field("OPENAI_API_KEY")))

# Reset it back to empty so we don't ship a fake key
ss.inputs["OPENAI_API_KEY"].text = ""
ss._save()
print("reset openai key:", repr(store.get_field("OPENAI_API_KEY")))

# Splash
done = {"v": False}
sp = g.SplashScreen(on_done=lambda: done.__setitem__("v", True))
print("SplashScreen OK")

# Gradient background + widgets
bg = g.GradientBackground()
bg._redraw()
bg._pulse(0.05)
orb = g.VoiceOrb()
orb._tick(0.03)
orb.set_active(True)
orb._tick(0.03)
card = g.Card()
gb = g.GlowButton(text="x")
dot = g.StatusDot()
bubble = g.ChatBubble("hello", is_user=True)
bubble2 = g.ChatBubble("hi", is_user=False)
print("widgets OK")

print("SMOKE TEST PASSED")
