"""
ROLEX AI — Desktop Voice Backend
================================
Speech-to-text and text-to-speech for PC / laptop / Termux using the classic
Python libraries. Every dependency is optional; missing pieces degrade
gracefully so the rest of the app keeps working.

  * TTS -> pyttsx3 (espeak / nsss / sapi5)
  * STT -> SpeechRecognition + PyAudio microphone
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from modules.logger import get_logger

log = get_logger("rolex.voice.desktop")


class DesktopTTS:
    """pyttsx3 wrapper with a speak()/stop() API mirroring the Android one."""

    def __init__(self, rate: int = 175):
        self._engine = None
        self._lock = threading.Lock()
        self._rate = rate
        self._init()

    def _init(self) -> None:
        try:
            import pyttsx3  # type: ignore
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._rate)
            # Prefer a female/neutral voice when available.
            try:
                voices = self._engine.getProperty("voices")
                if voices:
                    self._engine.setProperty("voice", voices[0].id)
            except Exception:
                pass
        except Exception as e:
            log.info("pyttsx3 unavailable: %s", e)
            self._engine = None

    def available(self) -> bool:
        return self._engine is not None

    def speak(self, text: str, blocking: bool = False) -> None:
        if not text or self._engine is None:
            return

        def _run():
            try:
                with self._lock:
                    self._engine.say(str(text))
                    self._engine.runAndWait()
            except Exception as e:
                log.error("Desktop TTS error: %s", e)

        if blocking:
            _run()
        else:
            threading.Thread(target=_run, daemon=True).start()

    def stop(self) -> None:
        try:
            if self._engine is not None:
                self._engine.stop()
        except Exception:
            pass

    def shutdown(self) -> None:
        self.stop()


class DesktopSTT:
    """SpeechRecognition wrapper. Uses Google Web Speech by default."""

    def __init__(self, on_partial: Optional[Callable[[str], None]] = None,
                 on_level: Optional[Callable[[float], None]] = None):
        self._recognizer = None
        self._mic = None
        self._on_partial = on_partial
        self._on_level = on_level
        self._init()

    def _init(self) -> None:
        try:
            import speech_recognition as sr  # type: ignore
            self._recognizer = sr.Recognizer()
            self._mic = sr.Microphone()
        except Exception as e:
            log.info("speech_recognition unavailable: %s", e)
            self._recognizer = None
            self._mic = None

    def available(self) -> bool:
        return self._recognizer is not None and self._mic is not None

    def listen(self, timeout: float = 8.0, phrase_limit: float = 8.0,
               language: str = "en-IN") -> Optional[str]:
        if not self.available():
            return None
        import speech_recognition as sr  # type: ignore
        try:
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_limit)
            # Simulate a level pulse for the UI while decoding.
            if self._on_level:
                try:
                    self._on_level(0.6)
                except Exception:
                    pass
            try:
                text = self._recognizer.recognize_google(audio, language=language)
            except Exception:
                # Fall back to the offline Sphinx engine if present.
                try:
                    text = self._recognizer.recognize_sphinx(audio)
                except Exception:
                    text = None
            if text and self._on_partial:
                try:
                    self._on_partial(text)
                except Exception:
                    pass
            return text
        except Exception as e:
            log.info("Desktop listen failed: %s", e)
            return None

    def shutdown(self) -> None:
        pass
