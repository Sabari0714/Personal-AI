"""Render the full ROLEX AI GUI (Home + Optimus) to PNGs for verification."""
import os
os.environ["KIVY_NO_ARGS"] = "1"
# Use the PIL text provider for headless rendering: the SDL2 text provider
# cannot encode some BMP symbol glyphs (●, ✓, •, …) on headless builds.
os.environ.setdefault("KIVY_TEXT", "pil")
# console log enabled
import sys
sys.path.insert(0, ".")

from kivy.config import Config
Config.set("graphics", "width", "420")
Config.set("graphics", "height", "820")
Config.set("graphics", "resizable", "0")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout

import gui.rolex_gui as g
from gui.theme import COLORS
from app import get_app


class Shot(App):
    def build(self):
        Window.clearcolor = COLORS["bg"]
        self.rolex = get_app()
        self.container = FloatLayout()
        self.shell = g.MainShell(self.rolex)
        self.container.add_widget(g.GradientBackground())
        self.container.add_widget(self.shell)
        Clock.schedule_once(self._home, 1.0)
        return self.container

    def _home(self, *_):
        self.shell._nav("home")
        Clock.schedule_once(self._snap_home, 0.8)

    def _snap_home(self, *_):
        Window.screenshot(name="gui_home.png")
        print("saved gui_home.png")
        self.shell._nav("optimus")
        Clock.schedule_once(self._snap_optimus, 0.8)

    def _snap_optimus(self, *_):
        Window.screenshot(name="gui_optimus.png")
        print("saved gui_optimus.png")
        self.shell._nav("capabilities")
        Clock.schedule_once(self._snap_caps, 0.8)

    def _snap_caps(self, *_):
        Window.screenshot(name="gui_capabilities.png")
        print("saved gui_capabilities.png")
        Clock.schedule_once(lambda *_: self.stop(), 0.3)


if __name__ == "__main__":
    Shot().run()
