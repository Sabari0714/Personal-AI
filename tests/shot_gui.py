"""Render GUI screenshots headlessly for visual verification."""
import os
os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_CONSOLELOG"] = "1"
import sys
sys.path.insert(0, ".")

from kivy.config import Config
Config.set("graphics", "width", "420")
Config.set("graphics", "height", "860")

from kivy.clock import Clock
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout

import gui.rolex_gui as g
from app import get_app

OUT = "tests/shots"
os.makedirs(OUT, exist_ok=True)


class ShotApp(App):
    def build(self):
        self.rolex = get_app()
        self.container = FloatLayout()
        self.shell = g.MainShell(self.rolex)
        self.container.add_widget(g.GradientBackground())
        self.container.add_widget(self.shell)
        self._order = ["home", "chat", "voice", "memory", "tasks", "settings", "system"]
        self._i = 0
        Clock.schedule_once(self._next, 1.0)
        return self.container

    def _next(self, dt):
        if self._i >= len(self._order):
            self.stop()
            return
        name = self._order[self._i]
        self.shell._nav(name)
        Clock.schedule_once(self._shot, 0.6)

    def _shot(self, dt):
        name = self._order[self._i]
        from kivy.core.window import Window
        Window.screenshot(name=os.path.join(OUT, f"{name}.png"))
        print("shot:", name)
        self._i += 1
        Clock.schedule_once(self._next, 0.4)


ShotApp().run()
print("DONE")
