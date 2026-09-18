"""
ROLEX AI — Premium Kivy GUI
Dark futuristic Rolex interface with:
  * Animated gradient background + neon glow
  * Animated boot/splash screen
  * Bottom navigation shell
  * Home dashboard (status cards, quick actions)
  * Chat (premium bubbles + typing indicator)
  * Voice (animated orb)
  * Memory, Tasks
  * Settings (API keys for all providers)
  * System (permissions + provider status)

Runs on Android and PC. Fails gracefully if Kivy is unavailable.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from modules.logger import get_logger

log = get_logger("rolex.gui")

try:
    from kivy.app import App
    from kivy.animation import Animation
    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.graphics import (
        Color, RoundedRectangle, Rectangle, Ellipse, Line, Triangle,
    )
    from kivy.metrics import dp, sp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.image import Image
    from kivy.uix.label import Label
    from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, FadeTransition
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.textinput import TextInput
    from kivy.uix.widget import Widget
    from kivy.uix.popup import Popup
    from kivy.uix.spinner import Spinner
    from kivy.graphics.texture import Texture
    KIVY_AVAILABLE = True
except Exception as e:  # pragma: no cover
    KIVY_AVAILABLE = False
    log.warning("Kivy not available: %s", e)

from gui.theme import COLORS, BG_GRADIENT_TOP, BG_GRADIENT_BOT


if KIVY_AVAILABLE:

    # =====================================================================
    # Reusable premium widgets
    # =====================================================================
    class GradientBackground(Widget):
        """Vertical gradient background with a soft radial glow."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._glow_t = 0.0
            with self.canvas:
                self._c_top = Color(*BG_GRADIENT_TOP)
                self._top = Rectangle(pos=self.pos, size=self.size)
                self._c_bot = Color(*BG_GRADIENT_BOT)
                self._bot = Rectangle(pos=self.pos, size=self.size)
                # radial glow (approximated with a large soft ellipse)
                self._c_glow = Color(0.0, 0.898, 0.898, 0.06)
                self._glow = Ellipse(pos=self.pos, size=self.size)
            self.bind(pos=self._redraw, size=self._redraw)
            Clock.schedule_interval(self._pulse, 0.05)

        def _redraw(self, *_):
            w, h = self.size
            x, y = self.pos
            # top half lighter, bottom half darker
            self._top.pos = (x, y + h * 0.45)
            self._top.size = (w, h * 0.55)
            self._bot.pos = (x, y)
            self._bot.size = (w, h * 0.45)
            self._glow.pos = (x - w * 0.25, y + h * 0.35)
            self._glow.size = (w * 1.5, h * 0.9)

        def _pulse(self, dt):
            self._glow_t += dt
            a = 0.05 + 0.03 * (1 + __import__("math").sin(self._glow_t * 1.2)) / 2
            self._c_glow.a = a

    class Card(BoxLayout):
        """A rounded panel card with subtle border."""

        def __init__(self, bg=None, border=None, radius=14, **kwargs):
            super().__init__(**kwargs)
            bg = bg or COLORS["card"]
            border = border or COLORS["stroke"]
            with self.canvas.before:
                self._c = Color(*bg)
                self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(radius)])
                self._bc = Color(*border)
                self._brect = Line(
                    rounded_rectangle=(self.x, self.y, self.width, self.height, dp(radius)),
                    width=1.0,
                )
            self.bind(pos=self._redraw, size=self._redraw)

        def _redraw(self, *_):
            self._rect.pos = self.pos
            self._rect.size = self.size
            self._brect.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(14))

    class GlowButton(Button):
        """A button with a neon glow underline."""

        def __init__(self, accent=None, **kwargs):
            super().__init__(**kwargs)
            self.accent = accent or COLORS["gold"]
            self.background_normal = ""
            self.background_down = ""
            self.background_color = COLORS["card_hi"]
            self.color = COLORS["text"]
            self.bold = True
            with self.canvas.after:
                self._gc = Color(*self.accent)
                self._glow = RoundedRectangle(pos=self.pos, size=(self.width, dp(3)), radius=[dp(2)])
            self.bind(pos=self._redraw, size=self._redraw)

        def _redraw(self, *_):
            self._glow.pos = (self.x, self.y)
            self._glow.size = (self.width, dp(3))

    class StatusDot(Widget):
        """A small pulsing status dot."""

        def __init__(self, color=None, **kwargs):
            super().__init__(**kwargs)
            self.size_hint = (None, None)
            self.size = (dp(12), dp(12))
            self._color = color or COLORS["success"]
            with self.canvas:
                self._c = Color(*self._color)
                self._dot = Ellipse(pos=self.pos, size=self.size)
            self.bind(pos=self._redraw, size=self._redraw)

        def set_color(self, color):
            self._color = color
            self._c.rgba = color

        def _redraw(self, *_):
            self._dot.pos = self.pos
            self._dot.size = self.size

    class ChatBubble(BoxLayout):
        def __init__(self, text: str, is_user: bool = False, **kwargs):
            super().__init__(**kwargs)
            self.orientation = "horizontal"
            self.size_hint_y = None
            self.padding = (dp(8), dp(4))
            self.spacing = dp(6)

            bubble_color = COLORS["user_bubble"] if is_user else COLORS["ai_bubble"]
            accent = COLORS["gold"] if is_user else COLORS["cyan"]

            lbl = Label(
                text=text,
                color=COLORS["text"],
                font_size="14sp",
                size_hint_y=None,
                halign="left",
                valign="middle",
                markup=True,
            )
            lbl.bind(width=lambda *_: setattr(lbl, "text_size", (lbl.width - dp(28), None)))
            lbl.bind(texture_size=lambda *_: setattr(self, "height", lbl.texture_size[1] + dp(22)))

            with lbl.canvas.before:
                Color(*bubble_color)
                lbl._bg = RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[dp(12)])
                Color(*accent)
                lbl._bar = RoundedRectangle(pos=lbl.pos, size=(dp(3), lbl.height), radius=[dp(2)])

            def _update(*_):
                lbl._bg.pos = lbl.pos
                lbl._bg.size = lbl.size
                lbl._bar.pos = lbl.pos
                lbl._bar.size = (dp(3), lbl.height)
            lbl.bind(pos=_update, size=_update)

            if is_user:
                self.add_widget(Widget(size_hint_x=0.12))
                self.add_widget(lbl)
            else:
                self.add_widget(lbl)
                self.add_widget(Widget(size_hint_x=0.12))

    class VoiceOrb(Widget):
        """Animated concentric rings used on the Voice screen."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._t = 0.0
            self._active = False
            with self.canvas:
                self._c1 = Color(*COLORS["cyan"])
                self._ring1 = Line(circle=(0, 0, 0), width=1.4)
                self._c2 = Color(0.0, 0.898, 0.898, 0.5)
                self._ring2 = Line(circle=(0, 0, 0), width=1.2)
                self._c3 = Color(0.831, 0.686, 0.216, 0.7)
                self._core = Ellipse(pos=self.pos, size=(dp(90), dp(90)))
            self.bind(pos=self._redraw, size=self._redraw)
            Clock.schedule_interval(self._tick, 0.03)

        def set_active(self, active: bool):
            self._active = active

        def _redraw(self, *_):
            cx, cy = self.center
            self._core.pos = (cx - dp(45), cy - dp(45))
            self._core.size = (dp(90), dp(90))

        def _tick(self, dt):
            self._t += dt
            import math
            cx, cy = self.center
            base = dp(70)
            amp = dp(26) if self._active else dp(10)
            speed = 2.4 if self._active else 1.0
            r1 = base + amp * (0.5 + 0.5 * math.sin(self._t * speed))
            r2 = base + dp(22) + amp * (0.5 + 0.5 * math.sin(self._t * speed + 1.2))
            self._ring1.circle = (cx, cy, r1)
            self._ring2.circle = (cx, cy, r2)
            self._c2.a = 0.35 + 0.25 * (0.5 + 0.5 * math.sin(self._t * speed))

    # =====================================================================
    # Screens
    # =====================================================================
    class BaseScreen(Screen):
        title = ""

        def __init__(self, app_ref, **kwargs):
            super().__init__(**kwargs)
            self.app_ref = app_ref

    class HomeScreen(BaseScreen):
        title = "Home"

        def __init__(self, app_ref, **kwargs):
            super().__init__(app_ref, **kwargs)
            root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(12))

            # Greeting
            self.greet = Label(
                text="[b][color=D4AF37]ROLEX[/color] [color=00E5E5]AI[/color][/b]",
                markup=True, font_size="26sp", size_hint_y=None, height=dp(40),
                halign="left", valign="middle",
            )
            self.greet.bind(size=lambda *_: setattr(self.greet, "text_size", self.greet.size))
            root.add_widget(self.greet)

            self.sub = Label(
                text="Your local-first personal AI operating system.",
                color=COLORS["text_dim"], font_size="13sp", size_hint_y=None, height=dp(22),
                halign="left", valign="middle",
            )
            self.sub.bind(size=lambda *_: setattr(self.sub, "text_size", self.sub.size))
            root.add_widget(self.sub)

            # Status cards grid
            grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(190))
            self.card_providers = self._stat_card("Providers", "0/7", COLORS["cyan"])
            self.card_memory = self._stat_card("Memories", "0", COLORS["gold"])
            self.card_tasks = self._stat_card("Tasks", "0", COLORS["violet"])
            self.card_net = self._stat_card("Network", "local", COLORS["success"])
            for c in (self.card_providers, self.card_memory, self.card_tasks, self.card_net):
                grid.add_widget(c)
            root.add_widget(grid)

            # Quick actions
            qa = Label(text="[b]Quick Actions[/b]", markup=True, color=COLORS["text"],
                       size_hint_y=None, height=dp(28), halign="left", valign="middle")
            qa.bind(size=lambda *_: setattr(qa, "text_size", qa.size))
            root.add_widget(qa)

            actions = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(120))
            actions.add_widget(self._action("💬  Chat", "chat", COLORS["cyan"]))
            actions.add_widget(self._action("🎙  Voice", "voice", COLORS["gold"]))
            actions.add_widget(self._action("⚙  Settings", "settings", COLORS["violet"]))
            actions.add_widget(self._action("🖥  System", "system", COLORS["success"]))
            root.add_widget(actions)

            root.add_widget(Widget())
            self.add_widget(root)
            Clock.schedule_once(lambda *_: self.refresh(), 0.4)

        def _stat_card(self, label, value, accent):
            card = Card(orientation="vertical", padding=dp(12), spacing=dp(2))
            v = Label(text=f"[b]{value}[/b]", markup=True, font_size="24sp",
                      color=accent, halign="left", valign="middle")
            v.bind(size=lambda *_: setattr(v, "text_size", v.size))
            l = Label(text=label, font_size="12sp", color=COLORS["text_dim"],
                      halign="left", valign="middle")
            l.bind(size=lambda *_: setattr(l, "text_size", l.size))
            card.add_widget(v)
            card.add_widget(l)
            card._value_lbl = v
            return card

        def _action(self, text, target, accent):
            b = GlowButton(text=text, accent=accent, font_size="15sp")
            b.bind(on_release=lambda *_: self._go(target))
            return b

        def _go(self, target):
            try:
                self.manager.current = target
            except Exception:
                pass

        def refresh(self):
            try:
                st = self.app_ref.status()
                provs = st.get("providers", {})
                n = sum(1 for k, v in provs.items() if v and k != "local")
                self.card_providers._value_lbl.text = f"[b]{n}/7[/b]"
                self.card_memory._value_lbl.text = f"[b]{st.get('memory_count', 0)}[/b]"
                ts = st.get("task_stats", {}) or {}
                total = ts.get("total", ts.get("pending", 0)) if isinstance(ts, dict) else 0
                self.card_tasks._value_lbl.text = f"[b]{total}[/b]"
                online = st.get("online", False)
                self.card_net._value_lbl.text = "[b]online[/b]" if online else "[b]local[/b]"
                self.card_net._value_lbl.color = COLORS["success"] if online else COLORS["warning"]
            except Exception as e:
                log.debug("home refresh failed: %s", e)

    class ChatScreen(BaseScreen):
        title = "Chat"

        def __init__(self, app_ref, **kwargs):
            super().__init__(app_ref, **kwargs)
            root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))

            self.chat_scroll = ScrollView()
            self.chat_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
            self.chat_box.bind(minimum_height=self.chat_box.setter("height"))
            self.chat_scroll.add_widget(self.chat_box)
            root.add_widget(self.chat_scroll)

            input_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))
            self.chat_input = TextInput(
                hint_text="Ask Rolex anything...", multiline=False,
                background_color=COLORS["panel_light"], foreground_color=COLORS["text"],
                cursor_color=COLORS["gold"], padding=(dp(12), dp(12)),
            )
            self.chat_input.bind(on_text_validate=self._send)
            send_btn = GlowButton(text="Send", accent=COLORS["gold"],
                                  size_hint_x=None, width=dp(84))
            send_btn.bind(on_release=self._send)
            input_row.add_widget(self.chat_input)
            input_row.add_widget(send_btn)
            root.add_widget(input_row)

            self.add_widget(root)
            self._add_bubble("Vanakkam! I am ROLEX AI. How can I help you today?", is_user=False)

        def _add_bubble(self, text: str, is_user: bool):
            bubble = ChatBubble(text, is_user)
            self.chat_box.add_widget(bubble)
            Clock.schedule_once(lambda *_: setattr(self.chat_scroll, "scroll_y", 0), 0.1)

        def _send(self, *_):
            text = self.chat_input.text.strip()
            if not text:
                return
            self.chat_input.text = ""
            self._add_bubble(text, is_user=True)
            self._add_bubble("[i][color=8F9EB3]Rolex is thinking…[/color][/i]", is_user=False)
            threading.Thread(target=self._process_async, args=(text,), daemon=True).start()

        def _process_async(self, text: str):
            try:
                resp = self.app_ref.process(text)
                out = resp.text
            except Exception as e:
                log.error("GUI process error: %s", e)
                out = "I couldn't complete that because the required module is unavailable."
            Clock.schedule_once(lambda *_: self._replace_last(out), 0)

        def _replace_last(self, text: str):
            if self.chat_box.children:
                self.chat_box.remove_widget(self.chat_box.children[0])
            self._add_bubble(text, is_user=False)

    class VoiceScreen(BaseScreen):
        title = "Voice"

        def __init__(self, app_ref, **kwargs):
            super().__init__(app_ref, **kwargs)
            root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
            self.orb = VoiceOrb(size_hint_y=0.6)
            root.add_widget(self.orb)
            self.voice_status = Label(
                text="[color=00E5E5]●[/color] Ready", markup=True,
                font_size="18sp", size_hint_y=None, height=dp(30),
            )
            root.add_widget(self.voice_status)
            self.voice_transcript = Label(
                text="Tap Listen and speak. Say 'Hey Rolex' to wake me.",
                font_size="14sp", color=COLORS["text_dim"],
            )
            root.add_widget(self.voice_transcript)
            listen_btn = GlowButton(text="🎙  Listen", accent=COLORS["cyan"],
                                    size_hint_y=None, height=dp(60), font_size="18sp")
            listen_btn.bind(on_release=self._listen)
            root.add_widget(listen_btn)
            self.add_widget(root)

        def _listen(self, *_):
            self.voice_status.text = "[color=D4AF37]● Listening…[/color]"
            self.orb.set_active(True)
            threading.Thread(target=self._listen_async, daemon=True).start()

        def _listen_async(self):
            try:
                resp = self.app_ref.voice_turn()
                text = resp.text if resp else "I didn't catch that."
            except Exception as e:
                log.error("Voice error: %s", e)
                text = "Voice input is unavailable."
            Clock.schedule_once(lambda *_: self._voice_done(text), 0)

        def _voice_done(self, text: str):
            self.voice_status.text = "[color=00E5E5]●[/color] Ready"
            self.orb.set_active(False)
            self.voice_transcript.text = text

    class MemoryScreen(BaseScreen):
        title = "Memory"

        def __init__(self, app_ref, **kwargs):
            super().__init__(app_ref, **kwargs)
            root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
            self.memory_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
            self.memory_box.bind(minimum_height=self.memory_box.setter("height"))
            scroll = ScrollView()
            scroll.add_widget(self.memory_box)
            refresh = GlowButton(text="Refresh memories", accent=COLORS["gold"],
                                 size_hint_y=None, height=dp(46))
            refresh.bind(on_release=lambda *_: self._load())
            root.add_widget(scroll)
            root.add_widget(refresh)
            self.add_widget(root)
            Clock.schedule_once(lambda *_: self._load(), 0.5)

        def _load(self):
            self.memory_box.clear_widgets()
            try:
                items = self.app_ref.memory.all(limit=50)
            except Exception:
                items = []
            if not items:
                self.memory_box.add_widget(Label(text="No memories yet.", color=COLORS["text_dim"]))
                return
            for m in items:
                self.memory_box.add_widget(Label(
                    text=f"[color=D4AF37]#{m.id}[/color] [{m.category}] {m.content}",
                    markup=True, color=COLORS["text"], size_hint_y=None, height=dp(30),
                    halign="left", valign="middle"))

    class TasksScreen(BaseScreen):
        title = "Tasks"

        def __init__(self, app_ref, **kwargs):
            super().__init__(app_ref, **kwargs)
            root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
            self.tasks_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
            self.tasks_box.bind(minimum_height=self.tasks_box.setter("height"))
            scroll = ScrollView()
            scroll.add_widget(self.tasks_box)
            refresh = GlowButton(text="Refresh tasks", accent=COLORS["cyan"],
                                 size_hint_y=None, height=dp(46))
            refresh.bind(on_release=lambda *_: self._load())
            root.add_widget(scroll)
            root.add_widget(refresh)
            self.add_widget(root)
            Clock.schedule_once(lambda *_: self._load(), 0.5)

        def _load(self):
            self.tasks_box.clear_widgets()
            try:
                tasks = self.app_ref.tasks.list()
            except Exception:
                tasks = []
            if not tasks:
                self.tasks_box.add_widget(Label(text="No tasks yet.", color=COLORS["text_dim"]))
                return
            for t in tasks:
                mark = "✓" if t.status == "COMPLETED" else "•"
                self.tasks_box.add_widget(Label(
                    text=f"{mark} [color=00E5E5]#{t.id}[/color] [{t.status}] {t.title}",
                    markup=True, color=COLORS["text"], size_hint_y=None, height=dp(30),
                    halign="left", valign="middle"))

    class SettingsScreen(BaseScreen):
        title = "Settings"

        def __init__(self, app_ref, **kwargs):
            super().__init__(app_ref, **kwargs)
            from modules import settings_store as ss
            self.ss = ss

            outer = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

            head = Label(
                text="[b][color=D4AF37]API Keys & Settings[/color][/b]",
                markup=True, font_size="20sp", size_hint_y=None, height=dp(34),
                halign="left", valign="middle",
            )
            head.bind(size=lambda *_: setattr(head, "text_size", head.size))
            outer.add_widget(head)

            hint = Label(
                text="Enter your keys below. They are stored locally on this device only.",
                color=COLORS["text_dim"], font_size="12sp", size_hint_y=None, height=dp(20),
                halign="left", valign="middle",
            )
            hint.bind(size=lambda *_: setattr(hint, "text_size", hint.size))
            outer.add_widget(hint)

            scroll = ScrollView()
            form = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=(0, dp(6)))
            form.bind(minimum_height=form.setter("height"))

            self.inputs = {}
            for group, keys in ss.FIELD_GROUPS.items():
                g = Label(text=f"[b][color=00E5E5]{group}[/color][/b]", markup=True,
                          size_hint_y=None, height=dp(28), halign="left", valign="middle")
                g.bind(size=lambda *_: setattr(g, "text_size", g.size))
                form.add_widget(g)
                for env_key in keys:
                    form.add_widget(self._field(env_key))
            scroll.add_widget(form)
            outer.add_widget(scroll)

            btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
            save = GlowButton(text="💾  Save", accent=COLORS["gold"])
            save.bind(on_release=self._save)
            test = GlowButton(text="🔌  Test", accent=COLORS["cyan"])
            test.bind(on_release=self._test)
            btn_row.add_widget(save)
            btn_row.add_widget(test)
            outer.add_widget(btn_row)

            self.add_widget(outer)
            Clock.schedule_once(lambda *_: self._load_values(), 0.3)

        def _field(self, env_key):
            attr, label, secret = self.ss.EDITABLE_FIELDS[env_key]
            box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(64), spacing=dp(2))
            lbl = Label(text=label, color=COLORS["text_dim"], font_size="12sp",
                        size_hint_y=None, height=dp(18), halign="left", valign="middle")
            lbl.bind(size=lambda *_: setattr(lbl, "text_size", lbl.size))
            ti = TextInput(
                text="", multiline=False, password=secret,
                background_color=COLORS["panel_light"], foreground_color=COLORS["text"],
                cursor_color=COLORS["gold"], padding=(dp(10), dp(10)), font_size="14sp",
            )
            box.add_widget(lbl)
            box.add_widget(ti)
            self.inputs[env_key] = ti
            return box

        def _load_values(self):
            for env_key, ti in self.inputs.items():
                try:
                    ti.text = self.ss.get_field(env_key)
                except Exception:
                    ti.text = ""

        def _save(self, *_):
            values = {k: ti.text.strip() for k, ti in self.inputs.items()}
            try:
                self.ss.save_settings(values)
                self._toast("Settings saved ✓")
            except Exception as e:
                log.error("save settings failed: %s", e)
                self._toast("Could not save settings")

        def _test(self, *_):
            try:
                provs = self.ss.provider_summary()
                active = [k for k, v in provs.items() if v and k != "local"]
                msg = "Configured: " + (", ".join(active) if active else "none (local only)")
                self._toast(msg)
            except Exception as e:
                self._toast(f"Test failed: {e}")

        def _toast(self, msg):
            popup = Popup(
                title="ROLEX AI",
                content=Label(text=msg, color=COLORS["text"]),
                size_hint=(0.8, 0.3),
                background_color=COLORS["panel"],
                title_color=COLORS["gold"],
                separator_color=COLORS["gold"],
            )
            popup.open()
            Clock.schedule_once(lambda *_: popup.dismiss(), 1.8)

    class SystemScreen(BaseScreen):
        title = "System"

        def __init__(self, app_ref, **kwargs):
            super().__init__(app_ref, **kwargs)
            root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

            head = Label(text="[b][color=00E5E5]System & Permissions[/color][/b]",
                         markup=True, font_size="20sp", size_hint_y=None, height=dp(34),
                         halign="left", valign="middle")
            head.bind(size=lambda *_: setattr(head, "text_size", head.size))
            root.add_widget(head)

            self.body = Label(text="Loading…", color=COLORS["text"], markup=True,
                              size_hint_y=None, halign="left", valign="top")
            self.body.bind(width=lambda *_: setattr(self.body, "text_size", (self.body.width, None)))
            self.body.bind(texture_size=lambda *_: setattr(self.body, "height", self.body.texture_size[1]))
            scroll = ScrollView()
            scroll.add_widget(self.body)
            root.add_widget(scroll)

            refresh = GlowButton(text="Run diagnostics", accent=COLORS["gold"],
                                 size_hint_y=None, height=dp(48))
            refresh.bind(on_release=lambda *_: self._load())
            root.add_widget(refresh)
            self.add_widget(root)
            Clock.schedule_once(lambda *_: self._load(), 0.5)

        def _load(self):
            lines = []
            try:
                st = self.app_ref.status()
                lines.append("[b]Identity[/b]")
                lines.append(f"  Name: {st.get('name')}  v{st.get('version')}")
                lines.append(f"  Online: {'yes' if st.get('online') else 'no'}")
                lines.append(f"  Rolex-only mode: {'on' if st.get('rolex_only') else 'off'}")
                lines.append("")
                lines.append("[b]Providers[/b]")
                for k, v in (st.get("providers") or {}).items():
                    mark = "[color=4ADE80]●[/color]" if v else "[color=8F9EB3]○[/color]"
                    lines.append(f"  {mark} {k}")
                lines.append("")
                lines.append("[b]Data[/b]")
                lines.append(f"  Memories: {st.get('memory_count', 0)}")
                lines.append(f"  Knowledge: {st.get('knowledge_count', 0)}")
                v = st.get("voice", {}) or {}
                lines.append(f"  Voice STT: {'yes' if v.get('stt') else 'no'}  TTS: {'yes' if v.get('tts') else 'no'}")
                lines.append(f"  Vision OCR: {'yes' if st.get('vision_ocr') else 'no'}")
                lines.append("")
                lines.append("[b]Android Permissions[/b]")
                for p in ["INTERNET", "RECORD_AUDIO", "ACCESS_NETWORK_STATE",
                          "ACCESS_WIFI_STATE", "READ_EXTERNAL_STORAGE",
                          "WRITE_EXTERNAL_STORAGE", "VIBRATE", "WAKE_LOCK"]:
                    lines.append(f"  [color=4ADE80]✓[/color] {p}")
            except Exception as e:
                lines.append(f"Diagnostics unavailable: {e}")
            self.body.text = "\n".join(lines)

    # =====================================================================
    # Shell: header + screen manager + bottom nav
    # =====================================================================
    class MainShell(BoxLayout):
        def __init__(self, app_ref, **kwargs):
            super().__init__(orientation="vertical", **kwargs)
            self.app_ref = app_ref

            # Header
            header = BoxLayout(size_hint_y=None, height=dp(54), padding=(dp(14), dp(6)), spacing=dp(8))
            with header.canvas.before:
                Color(*COLORS["panel"])
                header._bg = RoundedRectangle(pos=header.pos, size=header.size)
            header.bind(pos=lambda *_: setattr(header._bg, "pos", header.pos),
                        size=lambda *_: setattr(header._bg, "size", header.size))
            title = Label(text="[b][color=D4AF37]ROLEX[/color] [color=00E5E5]AI[/color][/b]",
                          markup=True, font_size="22sp", halign="left", valign="middle")
            title.bind(size=lambda *_: setattr(title, "text_size", title.size))
            self.status_lbl = Label(text="● local", color=COLORS["warning"],
                                    font_size="12sp", halign="right", valign="middle")
            self.status_lbl.bind(size=lambda *_: setattr(self.status_lbl, "text_size", self.status_lbl.size))
            header.add_widget(title)
            header.add_widget(self.status_lbl)
            self.add_widget(header)

            # Screen manager
            self.sm = ScreenManager(transition=FadeTransition(duration=0.18))
            self.sm.add_widget(HomeScreen(app_ref, name="home"))
            self.sm.add_widget(ChatScreen(app_ref, name="chat"))
            self.sm.add_widget(VoiceScreen(app_ref, name="voice"))
            self.sm.add_widget(MemoryScreen(app_ref, name="memory"))
            self.sm.add_widget(TasksScreen(app_ref, name="tasks"))
            self.sm.add_widget(SettingsScreen(app_ref, name="settings"))
            self.sm.add_widget(SystemScreen(app_ref, name="system"))
            self.add_widget(self.sm)

            # Bottom navigation
            nav = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(2), padding=(dp(4), dp(4)))
            with nav.canvas.before:
                Color(*COLORS["panel"])
                nav._bg = RoundedRectangle(pos=nav.pos, size=nav.size)
            nav.bind(pos=lambda *_: setattr(nav._bg, "pos", nav.pos),
                     size=lambda *_: setattr(nav._bg, "size", nav.size))
            self._nav_buttons = {}
            for label, target in [("🏠", "home"), ("💬", "chat"), ("🎙", "voice"),
                                  ("🧠", "memory"), ("✅", "tasks"),
                                  ("⚙", "settings"), ("🖥", "system")]:
                b = Button(text=label, background_normal="", background_down="",
                           background_color=COLORS["panel"], font_size="20sp")
                b.bind(on_release=lambda inst, t=target: self._nav(t))
                nav.add_widget(b)
                self._nav_buttons[target] = b
            self.add_widget(nav)
            self._nav("home")

        def _nav(self, target):
            try:
                self.sm.current = target
            except Exception:
                return
            for t, b in self._nav_buttons.items():
                b.background_color = COLORS["card_hi"] if t == target else COLORS["panel"]

        def update_status(self):
            try:
                online = self.app_ref.web.is_online()
                self.status_lbl.text = "● online" if online else "● local"
                self.status_lbl.color = COLORS["success"] if online else COLORS["warning"]
            except Exception:
                pass

    # =====================================================================
    # Splash / boot screen
    # =====================================================================
    class SplashScreen(FloatLayout):
        def __init__(self, on_done, **kwargs):
            super().__init__(**kwargs)
            self.on_done = on_done
            self.add_widget(GradientBackground())

            center = BoxLayout(orientation="vertical", size_hint=(0.8, 0.5),
                               pos_hint={"center_x": 0.5, "center_y": 0.55}, spacing=dp(10))
            self.logo = Label(text="[b][color=D4AF37]ROLEX[/color] [color=00E5E5]AI[/color][/b]",
                              markup=True, font_size="40sp")
            self.tag = Label(text="Personal AI Operating System", color=COLORS["text_dim"],
                             font_size="14sp")
            self.bar_bg = Widget(size_hint_y=None, height=dp(6))
            with self.bar_bg.canvas:
                Color(*COLORS["panel_light"])
                self._bar_bg = RoundedRectangle(pos=self.bar_bg.pos, size=self.bar_bg.size, radius=[dp(3)])
                Color(*COLORS["gold"])
                self._bar = RoundedRectangle(pos=self.bar_bg.pos, size=(0, self.bar_bg.size[1]), radius=[dp(3)])
            self.bar_bg.bind(pos=self._redraw_bar, size=self._redraw_bar)
            self._progress = 0.0

            center.add_widget(Widget())
            center.add_widget(self.logo)
            center.add_widget(self.tag)
            center.add_widget(Widget())
            center.add_widget(self.bar_bg)
            self.add_widget(center)

            self.opacity = 0
            Animation(opacity=1, duration=0.5).start(self)
            Clock.schedule_interval(self._tick, 0.03)

        def _redraw_bar(self, *_):
            self._bar_bg.pos = self.bar_bg.pos
            self._bar_bg.size = self.bar_bg.size
            self._bar.pos = self.bar_bg.pos
            self._bar.size = (self.bar_bg.width * self._progress, self.bar_bg.height)

        def _tick(self, dt):
            self._progress = min(1.0, self._progress + dt * 0.7)
            self._redraw_bar()
            if self._progress >= 1.0:
                Clock.unschedule(self._tick)
                Clock.schedule_once(lambda *_: self.on_done(), 0.15)

    # =====================================================================
    # App
    # =====================================================================
    class RolexApp(App):
        title = "ROLEX AI"

        def build(self):
            Window.clearcolor = COLORS["bg"]
            self.rolex = None
            self.root_widget = None
            self._container = FloatLayout()
            self._splash = SplashScreen(on_done=self._boot)
            self._container.add_widget(self._splash)
            return self._container

        def _boot(self):
            try:
                from app import get_app
                self.rolex = get_app()
            except Exception as e:
                log.error("App init failed: %s", e)
                self.rolex = None
            self._container.clear_widgets()
            if self.rolex is not None:
                self.root_widget = MainShell(self.rolex)
                self._container.add_widget(GradientBackground())
                self._container.add_widget(self.root_widget)
                Clock.schedule_interval(self._update_status, 5)
            else:
                self._container.add_widget(GradientBackground())
                self._container.add_widget(Label(
                    text="ROLEX AI could not start.\nCheck logs for details.",
                    color=COLORS["error"], halign="center"))

        def _update_status(self, *_):
            if self.root_widget:
                self.root_widget.update_status()

        def on_stop(self):
            try:
                if self.rolex:
                    self.rolex.shutdown()
            except Exception:
                pass


def run_gui() -> int:
    if not KIVY_AVAILABLE:
        print("Kivy is not installed. Install it with: pip install kivy")
        return 1
    RolexApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_gui())
