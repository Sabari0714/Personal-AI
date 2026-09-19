"""
ROLEX AI — Optimus Prime Hero Widget
A futuristic Autobots-themed centerpiece. Displays the Optimus Prime hero
image with animated, voice-synced glowing eyes and an energy aura.

The eye glow intensity is driven by the live voice amplitude (0..1) exposed
by modules.voice.VoiceState.amplitude, so the eyes pulse in sync with the
bass of ROLEX's spoken replies.

Fails gracefully if Kivy is unavailable.
"""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Optional

from modules.logger import get_logger

log = get_logger("rolex.optimus")

try:
    from kivy.clock import Clock
    from kivy.graphics import (
        Color, Ellipse, Line, Rectangle, RoundedRectangle,
    )
    from kivy.metrics import dp
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.image import Image
    from kivy.uix.widget import Widget
    KIVY_AVAILABLE = True
except Exception as e:  # pragma: no cover
    KIVY_AVAILABLE = False
    log.warning("Kivy not available for Optimus widget: %s", e)

from config import BASE_DIR
from gui.theme import COLORS

OPTIMUS_IMAGE = BASE_DIR / "assets" / "optimus_prime.jpg"


if KIVY_AVAILABLE:

    class OptimusPrime(Widget):
        """Optimus Prime hero with voice-synced glowing eyes + energy aura.

        Public API:
            set_amplitude(value)  -> drive eye glow from voice amplitude (0..1)
            set_speaking(bool)    -> enable/disable the live pulse
            set_state(str)        -> 'idle' | 'listening' | 'thinking' | 'speaking'
        """

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._amplitude = 0.0          # target amplitude from voice
            self._display = 0.0            # smoothed amplitude for rendering
            self._speaking = False
            self._state = "idle"
            self._phase = 0.0
            self._pulse = 0.0
            self._eye_glow = 0.35
            self._event = None
            self.bind(pos=self._redraw, size=self._redraw)
            self._event = Clock.schedule_interval(self._tick, 1 / 60.0)

        # -------------------------------------------------------------- #
        # Public API
        # -------------------------------------------------------------- #
        def set_amplitude(self, value: float) -> None:
            try:
                self._amplitude = max(0.0, min(1.0, float(value)))
            except Exception:
                self._amplitude = 0.0

        def set_speaking(self, speaking: bool) -> None:
            self._speaking = bool(speaking)
            if speaking:
                self._state = "speaking"

        def set_state(self, state: str) -> None:
            self._state = state or "idle"

        def stop(self) -> None:
            if self._event is not None:
                try:
                    self._event.cancel()
                except Exception:
                    pass
                self._event = None

        # -------------------------------------------------------------- #
        # Animation loop
        # -------------------------------------------------------------- #
        def _tick(self, dt: float) -> None:
            self._phase += dt * 2.4
            self._pulse = (math.sin(self._phase) + 1.0) / 2.0  # 0..1

            # Smoothly approach the target amplitude (attack/decay).
            target = self._amplitude
            if self._speaking and target < 0.12:
                # Idle breathing pulse while speaking but silent moment.
                target = 0.12 + 0.10 * self._pulse
            rate = 0.35 if target > self._display else 0.12
            self._display += (target - self._display) * rate

            # Eye glow combines amplitude + gentle breathing.
            base = 0.30 if self._state == "idle" else 0.45
            self._eye_glow = min(1.0, base + self._display * 0.9 + 0.08 * self._pulse)
            self._redraw()

        # -------------------------------------------------------------- #
        # Rendering
        # -------------------------------------------------------------- #
        def _redraw(self, *args) -> None:
            self.canvas.clear()
            if self.width <= 1 or self.height <= 1:
                return
            cx, cy = self.center_x, self.center_y
            w, h = self.width, self.height
            glow = self._eye_glow

            with self.canvas:
                # --- Energy aura rings behind Optimus -------------------
                for i, (scale, alpha) in enumerate(
                        ((1.05, 0.10), (0.92, 0.16), (0.80, 0.22))):
                    Color(COLORS["cyan"][0], COLORS["cyan"][1],
                          COLORS["cyan"][2], alpha * (0.5 + glow * 0.5))
                    Line(circle=(cx, cy, min(w, h) * 0.5 * scale), width=dp(1.2))

                # --- Rotating energy spokes -----------------------------
                Color(COLORS["gold"][0], COLORS["gold"][1],
                      COLORS["gold"][2], 0.18 + glow * 0.25)
                r = min(w, h) * 0.46
                for k in range(12):
                    ang = self._phase * 0.6 + k * (math.pi / 6)
                    x1 = cx + math.cos(ang) * r * 0.82
                    y1 = cy + math.sin(ang) * r * 0.82
                    x2 = cx + math.cos(ang) * r
                    y2 = cy + math.sin(ang) * r
                    Line(points=[x1, y1, x2, y2], width=dp(1))

                # --- Hero image -----------------------------------------
                if OPTIMUS_IMAGE.exists():
                    Color(1, 1, 1, 1)
                    Rectangle(source=str(OPTIMUS_IMAGE),
                              pos=self.pos, size=self.size)

                # --- Voice-synced glowing eyes --------------------------
                # Eye positions are proportional to the hero image framing.
                eye_y = cy + h * 0.10
                eye_dx = w * 0.11
                eye_r = min(w, h) * (0.045 + 0.030 * glow)
                for ex in (cx - eye_dx, cx + eye_dx):
                    # Outer bloom
                    Color(COLORS["cyan_hi"][0], COLORS["cyan_hi"][1],
                          COLORS["cyan_hi"][2], 0.20 + 0.55 * glow)
                    Ellipse(pos=(ex - eye_r * 1.9, eye_y - eye_r * 1.9),
                            size=(eye_r * 3.8, eye_r * 3.8))
                    # Mid glow
                    Color(COLORS["cyan"][0], COLORS["cyan"][1],
                          COLORS["cyan"][2], 0.45 + 0.5 * glow)
                    Ellipse(pos=(ex - eye_r * 1.25, eye_y - eye_r * 1.25),
                            size=(eye_r * 2.5, eye_r * 2.5))
                    # Core
                    Color(1, 1, 1, 0.75 + 0.25 * glow)
                    Ellipse(pos=(ex - eye_r * 0.55, eye_y - eye_r * 0.55),
                            size=(eye_r * 1.1, eye_r * 1.1))

                # --- Bass-reactive ground glow --------------------------
                Color(COLORS["gold"][0], COLORS["gold"][1],
                      COLORS["gold"][2], 0.10 + 0.30 * self._display)
                Ellipse(pos=(cx - w * 0.42, self.y - h * 0.02),
                        size=(w * 0.84, h * 0.10))

    class OptimusHero(FloatLayout):
        """Container that frames the Optimus widget with a status caption."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.optimus = OptimusPrime(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
            self.add_widget(self.optimus)

        def set_amplitude(self, value: float) -> None:
            self.optimus.set_amplitude(value)

        def set_speaking(self, speaking: bool) -> None:
            self.optimus.set_speaking(speaking)

        def set_state(self, state: str) -> None:
            self.optimus.set_state(state)

        def stop(self) -> None:
            self.optimus.stop()


def create_optimus_hero():
    """Factory that returns an OptimusHero or None if Kivy is unavailable."""
    if not KIVY_AVAILABLE:
        return None
    return OptimusHero()
