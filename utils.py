# utils.py — Speech I/O helpers

import random
import time
import speech_recognition as sr

from config import WAKE_WORD, MIC_TIMEOUT, PHRASE_LIMIT, SR_LANGUAGE, RESPONSES
from voice import Speaker

_speaker    = Speaker()
_recognizer = sr.Recognizer()
_recognizer.dynamic_energy_threshold = True
_recognizer.pause_threshold          = 0.6   # end-of-phrase silence threshold (seconds)
_recognizer.non_speaking_duration    = 0.4   # min silence before phrase end is considered

_CY = "\033[96m"; _YE = "\033[93m"; _MA = "\033[95m"; _RE = "\033[91m"; _RS = "\033[0m"


def _calibrate() -> None:
    try:
        with sr.Microphone() as source:
            print(f"{_CY}[STATUS] Calibrating microphone...{_RS}", flush=True)
            _recognizer.adjust_for_ambient_noise(source, duration=1.0)
            print(f"{_CY}[STATUS] Microphone ready.{_RS}", flush=True)
    except Exception as e:
        print(f"{_RE}[ERROR]  Mic calibration failed: {e}{_RS}", flush=True)

_calibrate()


# ──────────────────────────────────────────────
# TEXT-TO-SPEECH
# ──────────────────────────────────────────────

def speak(text: str) -> None:
    print(f"{_MA}[SPEECH] {text}{_RS}", flush=True)
    _speaker.speak(text)


def ack() -> None:
    speak(random.choice(RESPONSES))


# ──────────────────────────────────────────────
# SPEECH RECOGNITION — two-phase API
# ──────────────────────────────────────────────

def listen_for_wake_word() -> bool:
    """Block until the wake word is detected. Returns True when heard."""
    try:
        with sr.Microphone() as source:
            audio = _recognizer.listen(source, timeout=None, phrase_time_limit=4)
        text = _recognizer.recognize_google(audio, language=SR_LANGUAGE).lower()
        if WAKE_WORD in text:
            print(f"{_CY}[STATUS] Wake word detected.{_RS}", flush=True)
            return True
    except sr.WaitTimeoutError:
        pass
    except sr.UnknownValueError:
        pass
    except sr.RequestError as e:
        print(f"{_RE}[ERROR]  STT service error: {e}{_RS}", flush=True)
    except Exception as e:
        print(f"{_RE}[ERROR]  Mic error: {e}{_RS}", flush=True)
        time.sleep(1)
    return False


def listen_for_command() -> str | None:
    """Capture one utterance after the wake word. Returns text or None."""
    time.sleep(0.5)  # keep mic closed until TTS audio has fully left the speakers
    try:
        with sr.Microphone() as source:
            audio = _recognizer.listen(
                source, timeout=MIC_TIMEOUT, phrase_time_limit=PHRASE_LIMIT
            )
        text = _recognizer.recognize_google(audio, language=SR_LANGUAGE)
        if text:
            print(f"{_YE}[INPUT]  {text}{_RS}", flush=True)
        return text or None
    except sr.WaitTimeoutError:
        print(f"{_CY}[STATUS] No command heard — timed out.{_RS}", flush=True)
    except sr.UnknownValueError:
        print(f"{_CY}[STATUS] Didn't catch that.{_RS}", flush=True)
    except sr.RequestError as e:
        print(f"{_RE}[ERROR]  STT service error: {e}{_RS}", flush=True)
    except Exception as e:
        print(f"{_RE}[ERROR]  Mic error: {e}{_RS}", flush=True)
    return None
