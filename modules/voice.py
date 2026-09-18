"""
ROLEX AI — Voice Interaction
Speech-to-text, text-to-speech, wake word ("Hey Guru" / "Hey Rolex").
Gracefully degrades when optional voice libraries are unavailable.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

from config import CONFIG
from modules.logger import get_logger

log = get_logger("rolex.voice")

WAKE_WORDS = ("hey rolex", "hey guru", "rolex", "guru")


@dataclass
class VoiceState:
    listening: bool = False
    processing: bool = False
    speaking: bool = False
    last_text: str = ""


class VoiceEngine:
    """Voice input/output with optional backends."""

    def __init__(self):
        self.state = VoiceState()
        self._tts_engine = None
        self._recognizer = None
        self._mic = None
        self._init_backends()

    def _init_backends(self) -> None:
        # TTS
        try:
            import pyttsx3  # type: ignore
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", CONFIG.tts_rate)
        except Exception as e:
            log.info("pyttsx3 unavailable: %s", e)
        # STT
        try:
            import speech_recognition as sr  # type: ignore
            self._recognizer = sr.Recognizer()
            self._mic = sr.Microphone()
        except Exception as e:
            log.info("speech_recognition unavailable: %s", e)

    # -- capabilities -------------------------------------------------------
    def stt_available(self) -> bool:
        return self._recognizer is not None and self._mic is not None

    def tts_available(self) -> bool:
        return self._tts_engine is not None

    # -- speech to text -----------------------------------------------------
    def listen(self, timeout: float = 5.0, phrase_limit: float = 8.0) -> Optional[str]:
        if not self.stt_available():
            log.warning("STT not available.")
            return None
        import speech_recognition as sr  # type: ignore
        self.state.listening = True
        try:
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            self.state.processing = True
            text = self._recognizer.recognize_google(audio)
            self.state.last_text = text
            return text
        except Exception as e:
            log.info("Listen failed: %s", e)
            return None
        finally:
            self.state.listening = False
            self.state.processing = False

    # -- text to speech -----------------------------------------------------
    def speak(self, text: str, blocking: bool = False) -> None:
        if not text:
            return
        if not self.tts_available():
            log.info("TTS unavailable; would say: %s", text[:80])
            return

        def _run():
            self.state.speaking = True
            try:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
            except Exception as e:
                log.error("TTS error: %s", e)
            finally:
                self.state.speaking = False

        if blocking:
            _run()
        else:
            threading.Thread(target=_run, daemon=True).start()

    def stop_speaking(self) -> None:
        try:
            if self._tts_engine:
                self._tts_engine.stop()
        except Exception:
            pass
        self.state.speaking = False

    # -- wake word ----------------------------------------------------------
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


_voice: Optional[VoiceEngine] = None


def get_voice() -> VoiceEngine:
    global _voice
    if _voice is None:
        _voice = VoiceEngine()
    return _voice
