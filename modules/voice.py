"""
ROLEX AI — Voice Interaction (platform-aware facade)
====================================================
Speech-to-text, text-to-speech and wake-word handling ("Hey Rolex" / "Hey Guru").

This module is the single entry point used by the rest of the app. It
automatically selects the correct backend:

  * Android  -> modules.voice_android  (native TextToSpeech / SpeechRecognizer)
  * Desktop  -> modules.voice_desktop  (pyttsx3 / SpeechRecognition)

It also exposes a live ``amplitude`` value (0..1) that the GUI uses to make
Optimus Prime's eyes glow in sync with the voice.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from config import CONFIG
from modules.logger import get_logger

log = get_logger("rolex.voice")

WAKE_WORDS = ("hey rolex", "hey guru", "hey rolex ai", "rolex", "guru")


@dataclass
class VoiceState:
    listening: bool = False
    processing: bool = False
    speaking: bool = False
    last_text: str = ""
    amplitude: float = 0.0          # 0..1 live mic/voice level for the UI
    backend: str = "none"           # "android" | "desktop" | "none"
    last_error: str = ""


class VoiceEngine:
    """Voice input/output with automatic platform backend selection."""

    def __init__(self):
        self.state = VoiceState()
        self._tts = None
        self._stt = None
        self._on_partial: Optional[Callable[[str], None]] = None
        self._init_backends()

    # ------------------------------------------------------------------ #
    # Backend selection
    # ------------------------------------------------------------------ #
    def _init_backends(self) -> None:
        from modules.voice_android import is_android
        android = is_android()

        if android:
            try:
                from modules.voice_android import AndroidTTS, AndroidSTT
                self._tts = AndroidTTS(rate=CONFIG.tts_rate)
                self._stt = AndroidSTT(on_partial=self._partial_cb,
                                       on_level=self._level_cb)
                self.state.backend = "android"
                log.info("Voice backend: Android native (TTS=%s, STT=%s)",
                         self._tts.available(), self._stt.available())
                return
            except Exception as e:
                log.error("Android voice backend failed: %s", e)
                self.state.last_error = str(e)

        # Desktop / fallback
        try:
            from modules.voice_desktop import DesktopTTS, DesktopSTT
            self._tts = DesktopTTS(rate=CONFIG.tts_rate)
            self._stt = DesktopSTT(on_partial=self._partial_cb,
                                   on_level=self._level_cb)
            self.state.backend = "desktop"
            log.info("Voice backend: Desktop (TTS=%s, STT=%s)",
                     self._tts.available(), self._stt.available())
        except Exception as e:
            log.error("Desktop voice backend failed: %s", e)
            self.state.last_error = str(e)
            self.state.backend = "none"

    # -- callbacks ---------------------------------------------------------
    def _partial_cb(self, text: str) -> None:
        self.state.last_text = text
        if self._on_partial:
            try:
                self._on_partial(text)
            except Exception:
                pass

    def _level_cb(self, level: float) -> None:
        self.state.amplitude = max(0.0, min(1.0, float(level)))

    def set_partial_callback(self, cb: Optional[Callable[[str], None]]) -> None:
        self._on_partial = cb

    # ------------------------------------------------------------------ #
    # Capabilities
    # ------------------------------------------------------------------ #
    def stt_available(self) -> bool:
        return self._stt is not None and self._stt.available()

    def tts_available(self) -> bool:
        return self._tts is not None and self._tts.available()

    def backend_name(self) -> str:
        return self.state.backend

    # ------------------------------------------------------------------ #
    # Speech to text
    # ------------------------------------------------------------------ #
    def listen(self, timeout: float = 8.0, phrase_limit: float = 8.0,
               language: str = "en-IN") -> Optional[str]:
        if not self.stt_available():
            log.warning("STT not available (backend=%s).", self.state.backend)
            return None
        self.state.listening = True
        self.state.amplitude = 0.0
        try:
            text = self._stt.listen(timeout=timeout, phrase_limit=phrase_limit,
                                    language=language)
            if text:
                self.state.last_text = text
            return text
        except Exception as e:
            log.info("Listen failed: %s", e)
            self.state.last_error = str(e)
            return None
        finally:
            self.state.listening = False
            self.state.amplitude = 0.0

    # ------------------------------------------------------------------ #
    # Text to speech
    # ------------------------------------------------------------------ #
    def speak(self, text: str, blocking: bool = False) -> None:
        if not text:
            return
        if not self.tts_available():
            log.info("TTS unavailable; would say: %s", text[:80])
            return

        def _run():
            self.state.speaking = True
            # Animate the amplitude while speaking so the eyes glow.
            stop = threading.Event()

            def _pulse():
                import math
                t = 0.0
                while not stop.is_set():
                    t += 0.08
                    self.state.amplitude = 0.35 + 0.45 * (0.5 + 0.5 * math.sin(t * 6))
                    time.sleep(0.05)
                self.state.amplitude = 0.0

            pulse = threading.Thread(target=_pulse, daemon=True)
            pulse.start()
            try:
                self._tts.speak(text, blocking=True)
            except Exception as e:
                log.error("TTS error: %s", e)
            finally:
                stop.set()
                self.state.speaking = False
                self.state.amplitude = 0.0

        if blocking:
            _run()
        else:
            threading.Thread(target=_run, daemon=True).start()

    def stop_speaking(self) -> None:
        try:
            if self._tts:
                self._tts.stop()
        except Exception:
            pass
        self.state.speaking = False
        self.state.amplitude = 0.0

    # ------------------------------------------------------------------ #
    # Wake word
    # ------------------------------------------------------------------ #
    def detect_wake_word(self, text: str) -> bool:
        low = (text or "").lower()
        return any(w in low for w in WAKE_WORDS)

    def strip_wake_word(self, text: str) -> str:
        low = (text or "").lower()
        for w in WAKE_WORDS:
            idx = low.find(w)
            if idx != -1:
                return text[idx + len(w):].strip(" ,.")
        return text

    def wake_word_available(self) -> bool:
        try:
            import pvporcupine  # type: ignore  # noqa: F401
            return bool(CONFIG.picovoice_access_key)
        except Exception:
            return False

    def shutdown(self) -> None:
        try:
            if self._tts:
                self._tts.shutdown()
            if self._stt:
                self._stt.shutdown()
        except Exception:
            pass


_voice: Optional[VoiceEngine] = None


def get_voice() -> VoiceEngine:
    global _voice
    if _voice is None:
        _voice = VoiceEngine()
    return _voice
