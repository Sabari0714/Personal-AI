"""Render the Optimus hero widget to a PNG for visual verification."""
import os
os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_WINDOW", "sdl2")

from kivy.config import Config
Config.set("graphics", "width", "480")
Config.set("graphics", "height", "720")
Config.set("graphics", "resizable", "0")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle

from gui.theme import COLORS
from gui.optimus import create_optimus_hero


class Shot(App):
    def build(self):
        Window.clearcolor = COLORS["bg"]
        root = FloatLayout()
        with root.canvas.before:
            Color(*COLORS["bg"])
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *_: setattr(self._bg, "pos", root.pos),
                  size=lambda *_: setattr(self._bg, "size", root.size))
        self.hero = create_optimus_hero()
        self.hero.size_hint = (1, 1)
        root.add_widget(self.hero)
        # Drive a strong amplitude so the eyes glow brightly for the shot.
        self.hero.set_amplitude(0.85)
        self.hero.set_speaking(True)
        Clock.schedule_once(self._snap, 1.2)
        return root

    def _snap(self, *_):
        Window.screenshot(name="optimus_preview.png")
        print("saved optimus_preview.png")
        Clock.schedule_once(lambda *_: self.stop(), 0.3)


if __name__ == "__main__":
    Shot().run()
