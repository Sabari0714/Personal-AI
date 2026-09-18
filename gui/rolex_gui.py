"""
ROLEX AI — Kivy GUI
Dark futuristic Rolex interface: Home/Chat, Voice, Memory, Tasks, System.
Designed to run on Android and PC. Fails gracefully if Kivy is unavailable.
"""
from __future__ import annotations

import threading
from typing import Optional

from modules.logger import get_logger

log = get_logger("rolex.gui")

try:
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.graphics import Color, RoundedRectangle
    from kivy.metrics import dp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
    from kivy.uix.textinput import TextInput
    from kivy.uix.widget import Widget
    KIVY_AVAILABLE = True
except Exception as e:  # pragma: no cover
    KIVY_AVAILABLE = False
    log.warning("Kivy not available: %s", e)

from gui.theme import COLORS


if KIVY_AVAILABLE:

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
            lbl.bind(width=lambda *_: setattr(lbl, "text_size", (lbl.width - dp(24), None)))
            lbl.bind(texture_size=lambda *_: setattr(self, "height", lbl.texture_size[1] + dp(20)))

            with lbl.canvas.before:
                Color(*bubble_color)
                lbl._bg = RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[dp(10)])
                Color(*accent)
                lbl._bar = RoundedRectangle(pos=lbl.pos, size=(dp(3), lbl.height), radius=[dp(2)])

            def _update(*_):
                lbl._bg.pos = lbl.pos
                lbl._bg.size = lbl.size
                lbl._bar.pos = lbl.pos
                lbl._bar.size = (dp(3), lbl.height)
            lbl.bind(pos=_update, size=_update)

            if is_user:
                self.add_widget(Widget(size_hint_x=0.15))
                self.add_widget(lbl)
            else:
                self.add_widget(lbl)
                self.add_widget(Widget(size_hint_x=0.15))

    class RolexRoot(BoxLayout):
        def __init__(self, app_ref, **kwargs):
            super().__init__(**kwargs)
            self.orientation = "vertical"
            self.app_ref = app_ref
            self._build_header()
            self._build_tabs()

        def _build_header(self):
            header = BoxLayout(size_hint_y=None, height=dp(56), padding=(dp(12), dp(6)))
            with header.canvas.before:
                Color(*COLORS["panel"])
                header._bg = RoundedRectangle(pos=header.pos, size=header.size)
            header.bind(pos=lambda *_: setattr(header._bg, "pos", header.pos),
                        size=lambda *_: setattr(header._bg, "size", header.size))
            title = Label(text="[b][color=D4AF37]ROLEX[/color] [color=00E5E5]AI[/color][/b]",
                          markup=True, font_size="22sp", halign="left", valign="middle")
            title.bind(size=lambda *_: setattr(title, "text_size", title.size))
            self.status_lbl = Label(text="● local", color=COLORS["success"],
                                    font_size="12sp", halign="right", valign="middle")
            self.status_lbl.bind(size=lambda *_: setattr(self.status_lbl, "text_size", self.status_lbl.size))
            header.add_widget(title)
            header.add_widget(self.status_lbl)
            self.add_widget(header)

        def _build_tabs(self):
            self.tabs = TabbedPanel(do_default_tab=False, tab_width=dp(90))
            self.tabs.background_color = COLORS["bg"]

            self.tabs.add_widget(self._chat_tab())
            self.tabs.add_widget(self._voice_tab())
            self.tabs.add_widget(self._memory_tab())
            self.tabs.add_widget(self._tasks_tab())
            self.tabs.add_widget(self._system_tab())
            self.tabs.default_tab = self.tabs.tab_list[0]
            self.add_widget(self.tabs)

        # -- Chat ----------------------------------------------------------
        def _chat_tab(self):
            tab = TabbedPanelItem(text="Chat")
            root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))

            self.chat_scroll = ScrollView()
            self.chat_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
            self.chat_box.bind(minimum_height=self.chat_box.setter("height"))
            self.chat_scroll.add_widget(self.chat_box)
            root.add_widget(self.chat_scroll)

            input_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
            self.chat_input = TextInput(hint_text="Ask Rolex anything...", multiline=False,
                                        background_color=COLORS["panel_light"],
                                        foreground_color=COLORS["text"],
                                        cursor_color=COLORS["gold"])
            self.chat_input.bind(on_text_validate=self._send)
            send_btn = Button(text="Send", size_hint_x=None, width=dp(80),
                              background_normal="", background_color=COLORS["gold"],
                              color=COLORS["bg"], bold=True)
            send_btn.bind(on_release=self._send)
            input_row.add_widget(self.chat_input)
            input_row.add_widget(send_btn)
            root.add_widget(input_row)

            tab.add_widget(root)
            self._add_bubble("Vanakkam! I am ROLEX AI. How can I help you today?", is_user=False)
            return tab

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
            self._add_bubble("...", is_user=False)
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

        # -- Voice ---------------------------------------------------------
        def _voice_tab(self):
            tab = TabbedPanelItem(text="Voice")
            root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
            self.voice_status = Label(text="[color=00E5E5]●[/color] Ready",
                                      markup=True, font_size="18sp")
            self.voice_transcript = Label(text="", font_size="14sp", color=COLORS["text_dim"])
            listen_btn = Button(text="🎙  Listen", size_hint_y=None, height=dp(60),
                                background_normal="", background_color=COLORS["cyan_dim"],
                                color=COLORS["text"], bold=True, font_size="18sp")
            listen_btn.bind(on_release=self._listen)
            root.add_widget(self.voice_status)
            root.add_widget(listen_btn)
            root.add_widget(self.voice_transcript)
            root.add_widget(Widget())
            tab.add_widget(root)
            return tab

        def _listen(self, *_):
            self.voice_status.text = "[color=D4AF37]● Listening...[/color]"
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
            self.voice_transcript.text = text

        # -- Memory --------------------------------------------------------
        def _memory_tab(self):
            tab = TabbedPanelItem(text="Memory")
            root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
            self.memory_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
            self.memory_box.bind(minimum_height=self.memory_box.setter("height"))
            scroll = ScrollView()
            scroll.add_widget(self.memory_box)
            refresh = Button(text="Refresh memories", size_hint_y=None, height=dp(44),
                             background_normal="", background_color=COLORS["panel_light"],
                             color=COLORS["text"])
            refresh.bind(on_release=lambda *_: self._load_memory())
            root.add_widget(scroll)
            root.add_widget(refresh)
            tab.add_widget(root)
            Clock.schedule_once(lambda *_: self._load_memory(), 0.5)
            return tab

        def _load_memory(self):
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

        # -- Tasks ---------------------------------------------------------
        def _tasks_tab(self):
            tab = TabbedPanelItem(text="Tasks")
            root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
            self.tasks_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
            self.tasks_box.bind(minimum_height=self.tasks_box.setter("height"))
            scroll = ScrollView()
            scroll.add_widget(self.tasks_box)
            refresh = Button(text="Refresh tasks", size_hint_y=None, height=dp(44),
                             background_normal="", background_color=COLORS["panel_light"],
                             color=COLORS["text"])
            refresh.bind(on_release=lambda *_: self._load_tasks())
            root.add_widget(scroll)
            root.add_widget(refresh)
            tab.add_widget(root)
            Clock.schedule_once(lambda *_: self._load_tasks(), 0.5)
            return tab

        def _load_tasks(self):
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

        # -- System --------------------------------------------------------
        def _system_tab(self):
            tab = TabbedPanelItem(text="System")
            root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
            self.system_lbl = Label(text="Loading...", color=COLORS["text"],
                                    size_hint_y=None, halign="left", valign="top")
            self.system_lbl.bind(width=lambda *_: setattr(self.system_lbl, "text_size",
                                                          (self.system_lbl.width, None)))
            self.system_lbl.bind(texture_size=lambda *_: setattr(self.system_lbl, "height",
                                                                 self.system_lbl.texture_size[1]))
            scroll = ScrollView()
            scroll.add_widget(self.system_lbl)
            refresh = Button(text="Run diagnostics", size_hint_y=None, height=dp(44),
                             background_normal="", background_color=COLORS["gold"],
                             color=COLORS["bg"], bold=True)
            refresh.bind(on_release=lambda *_: self._load_system())
            root.add_widget(scroll)
            root.add_widget(refresh)
            tab.add_widget(root)
            Clock.schedule_once(lambda *_: self._load_system(), 0.5)
            return tab

        def _load_system(self):
            try:
                report = self.app_ref.diagnostics_report()
                self.system_lbl.text = report["summary"]
            except Exception as e:
                self.system_lbl.text = f"Diagnostics unavailable: {e}"

    class RolexApp(App):
        title = "ROLEX AI"

        def build(self):
            Window.clearcolor = COLORS["bg"]
            from app import get_app
            self.rolex = get_app()
            self.root_widget = RolexRoot(self.rolex)
            Clock.schedule_interval(self._update_status, 5)
            return self.root_widget

        def _update_status(self, *_):
            try:
                online = self.rolex.web.is_online()
                self.root_widget.status_lbl.text = "● online" if online else "● local"
                self.root_widget.status_lbl.color = COLORS["success"] if online else COLORS["warning"]
            except Exception:
                pass

        def on_stop(self):
            try:
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
