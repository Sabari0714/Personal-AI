"""
ROLEX AI — Android Native Voice Backend
=======================================
Real speech-to-text and text-to-speech on Android using the platform APIs
through pyjnius. This is what makes voice actually work inside the APK.

  * TTS  -> android.speech.tts.TextToSpeech
  * STT  -> android.speech.SpeechRecognizer + RecognizerIntent

Everything is defensive: if any Java class is missing we degrade gracefully
instead of crashing the app.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, List, Optional

from modules.logger import get_logger

log = get_logger("rolex.voice.android")

# ---------------------------------------------------------------------------
# Lazy jnius imports (only valid on Android / python-for-android)
# ---------------------------------------------------------------------------
_JNIUS_OK = False
try:  # pragma: no cover - only importable on device
    from jnius import autoclass, PythonJavaClass, java_method  # type: ignore
    _JNIUS_OK = True
except Exception as e:  # desktop / CI
    log.info("pyjnius unavailable: %s", e)


def is_android() -> bool:
    """Best-effort detection of an Android runtime."""
    import os
    if "ANDROID_ARGUMENT" in os.environ or "ANDROID_PRIVATE" in os.environ:
        return True
    if "ANDROID_ROOT" in os.environ and "ANDROID_DATA" in os.environ:
        return True
    try:
        import android  # noqa: F401  # type: ignore
        return True
    except Exception:
        return False


def _activity():
    """Return the current Android Activity (or None)."""
    if not _JNIUS_OK:
        return None
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        return PythonActivity.mActivity
    except Exception:
        try:
            from android import mActivity  # type: ignore
            return mActivity
        except Exception:
            return None


# ===========================================================================
# Text To Speech
# ===========================================================================
if _JNIUS_OK:

    class _TTSInitListener(PythonJavaClass):
        __javainterfaces__ = ["android/speech/tts/TextToSpeech$OnInitListener"]
        __javacontext__ = "app"

        def __init__(self, on_ready: Callable[[bool], None]):
            super().__init__()
            self._on_ready = on_ready

        @java_method("(I)V")
        def onInit(self, status):  # noqa: N802 (Java naming)
            try:
                self._on_ready(status == 0)  # 0 == SUCCESS
            except Exception as e:
                log.error("TTS onInit handler error: %s", e)


class AndroidTTS:
    """Android TextToSpeech wrapper with a simple speak()/stop() API."""

    def __init__(self, rate: int = 175):
        self._tts = None
        self._ready = False
        self._lock = threading.Lock()
        self._rate = rate
        self._init()

    def _init(self) -> None:
        if not _JNIUS_OK:
            return
        activity = _activity()
        if activity is None:
            log.info("No Android activity; TTS disabled.")
            return
        try:
            TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
            listener = _TTSInitListener(self._on_ready)
            self._tts = TextToSpeech(activity, listener)
        except Exception as e:
            log.error("Android TTS init failed: %s", e)
            self._tts = None

    def _on_ready(self, ok: bool) -> None:
        self._ready = ok
        if not ok:
            log.warning("Android TTS engine failed to initialise.")
            return
        try:
            Locale = autoclass("java.util.Locale")
            # Prefer Indian English for Tamil/Tanglish friendliness, fall back to US.
            try:
                self._tts.setLanguage(Locale("en", "IN"))
            except Exception:
                self._tts.setLanguage(Locale.US)
            # Map our 0-300 rate onto Android's 0.1-2.0 float scale.
            try:
                self._tts.setSpeechRate(max(0.1, min(2.0, self._rate / 175.0)))
                self._tts.setPitch(1.0)
            except Exception:
                pass
        except Exception as e:
            log.error("Android TTS configure failed: %s", e)

    def available(self) -> bool:
        return self._tts is not None

    def speak(self, text: str, blocking: bool = False) -> None:
        if not text or self._tts is None:
            return

        def _run():
            # Wait briefly for the engine to finish initialising.
            for _ in range(40):
                if self._ready:
                    break
                time.sleep(0.05)
            try:
                with self._lock:
                    self._tts.speak(str(text), 0, None, "rolex-utterance")
            except Exception as e:
                log.error("Android TTS speak failed: %s", e)

        if blocking:
            _run()
        else:
            threading.Thread(target=_run, daemon=True).start()

    def stop(self) -> None:
        try:
            if self._tts is not None:
                self._tts.stop()
        except Exception:
            pass

    def shutdown(self) -> None:
        try:
            if self._tts is not None:
                self._tts.stop()
                self._tts.shutdown()
        except Exception:
            pass


# ===========================================================================
# Speech To Text
# ===========================================================================
if _JNIUS_OK:

    class _RecognitionListener(PythonJavaClass):
        __javainterfaces__ = ["android/speech/RecognitionListener"]
        __javacontext__ = "app"

        def __init__(self, engine: "AndroidSTT"):
            super().__init__()
            self._engine = engine

        @java_method("(Landroid/os/Bundle;)V")
        def onReadyForSpeech(self, params):  # noqa: N802
            self._engine._on_ready()

        @java_method("()V")
        def onBeginningOfSpeech(self):  # noqa: N802
            self._engine._on_speech_start()

        @java_method("(F)V")
        def onRmsChanged(self, rmsdB):  # noqa: N802
            # rmsdB is roughly -2..10; normalise to 0..1 for the eye glow.
            try:
                level = max(0.0, min(1.0, (float(rmsdB) + 2.0) / 12.0))
                self._engine._on_level(level)
            except Exception:
                pass

        @java_method("([B)V")
        def onBufferReceived(self, buffer):  # noqa: N802
            pass

        @java_method("()V")
        def onEndOfSpeech(self):  # noqa: N802
            self._engine._on_speech_end()

        @java_method("(I)V")
        def onError(self, error):  # noqa: N802
            self._engine._on_error(int(error))

        @java_method("(Landroid/os/Bundle;)V")
        def onResults(self, results):  # noqa: N802
            self._engine._on_results(results)

        @java_method("(Landroid/os/Bundle;)V")
        def onPartialResults(self, partialResults):  # noqa: N802
            self._engine._on_partial(partialResults)

        @java_method("(ILandroid/os/Bundle;)V")
        def onEvent(self, eventType, params):  # noqa: N802
            pass


class AndroidSTT:
    """
    Android SpeechRecognizer wrapper.

    listen() blocks until a final result, an error, or a timeout, and returns
    the recognised text (or None). Partial results are streamed through the
    optional ``on_partial`` callback so the UI can show live transcription.
    """

    # SpeechRecognizer error codes
    ERROR_NO_MATCH = 7
    ERROR_SPEECH_TIMEOUT = 6
    ERROR_RECOGNIZER_BUSY = 8
    ERROR_INSUFFICIENT_PERMISSIONS = 9

    def __init__(self, on_partial: Optional[Callable[[str], None]] = None,
                 on_level: Optional[Callable[[float], None]] = None):
        self._recognizer = None
        self._listener = None
        self._on_partial = on_partial
        self._on_level = on_level
        self._result: Optional[str] = None
        self._error: Optional[int] = None
        self._done = threading.Event()
        self._ready = threading.Event()
        self._speaking = threading.Event()
        self._init()

    def _init(self) -> None:
        if not _JNIUS_OK:
            return
        try:
            SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
            activity = _activity()
            if activity is None:
                return
            if not SpeechRecognizer.isRecognitionAvailable(activity):
                log.info("Speech recognition not available on this device.")
                return
            self._recognizer = SpeechRecognizer.createSpeechRecognizer(activity)
            self._listener = _RecognitionListener(self)
            self._recognizer.setRecognitionListener(self._listener)
        except Exception as e:
            log.error("Android STT init failed: %s", e)
            self._recognizer = None

    # -- callbacks from the Java listener ----------------------------------
    def _on_ready(self) -> None:
        self._ready.set()

    def _on_speech_start(self) -> None:
        self._speaking.set()

    def _on_speech_end(self) -> None:
        self._speaking.clear()

    def _on_level(self, level: float) -> None:
        if self._on_level:
            try:
                self._on_level(level)
            except Exception:
                pass

    def _on_error(self, code: int) -> None:
        self._error = code
        self._done.set()

    def _on_partial(self, bundle) -> None:
        text = self._extract(bundle)
        if text and self._on_partial:
            try:
                self._on_partial(text)
            except Exception:
                pass

    def _on_results(self, bundle) -> None:
        self._result = self._extract(bundle)
        self._done.set()

    @staticmethod
    def _extract(bundle) -> Optional[str]:
        try:
            SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
            key = SpeechRecognizer.RESULTS_RECOGNITION
            matches = bundle.getStringArrayList(key)
            if matches is not None and matches.size() > 0:
                return str(matches.get(0))
        except Exception as e:
            log.debug("Result extraction failed: %s", e)
        return None

    # -- public API ---------------------------------------------------------
    def available(self) -> bool:
        return self._recognizer is not None

    def listen(self, timeout: float = 8.0, phrase_limit: float = 8.0,
               language: str = "en-IN") -> Optional[str]:
        if self._recognizer is None:
            return None
        self._result = None
        self._error = None
        self._done.clear()
        self._ready.clear()
        try:
            Intent = autoclass("android.content.Intent")
            RecognizerIntent = autoclass("android.speech.RecognizerIntent")
            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, language)
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, True)
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
            intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS,
                            int(phrase_limit * 1000))
            self._recognizer.startListening(intent)
        except Exception as e:
            log.error("startListening failed: %s", e)
            return None

        # Wait for a result / error / timeout.
        deadline = time.time() + max(timeout, phrase_limit) + 2.0
        while time.time() < deadline:
            if self._done.wait(0.1):
                break
        try:
            self._recognizer.stopListening()
        except Exception:
            pass

        if self._result:
            return self._result
        if self._error is not None:
            log.info("STT error code: %s", self._error)
        return None

    def shutdown(self) -> None:
        try:
            if self._recognizer is not None:
                self._recognizer.destroy()
        except Exception:
            pass
