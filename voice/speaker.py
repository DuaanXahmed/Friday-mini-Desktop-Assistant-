from __future__ import annotations

import os
import platform
import subprocess
import threading
from pathlib import Path

from config import TTS_RATE, TTS_VOLUME

_ON_WINDOWS = platform.system() == "Windows"

# ---------------------------------------------------------------------------
# Piper model paths
# ---------------------------------------------------------------------------

PIPER_VOICE      = "en_US-hfc_female-medium"
PIPER_VOICE_URL  = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
PIPER_MODELS_DIR = Path.home() / ".local" / "share" / "friday" / "models" / "piper"


def _piper_paths() -> tuple[Path, Path]:
    PIPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return (
        PIPER_MODELS_DIR / f"{PIPER_VOICE}.onnx",
        PIPER_MODELS_DIR / f"{PIPER_VOICE}.onnx.json",
    )


def _download_piper_model() -> bool:
    import requests

    onnx_path, json_path = _piper_paths()
    parts = PIPER_VOICE.split("-")
    lang_region, name, quality = parts[0], parts[1], parts[2]
    lang = lang_region.split("_")[0]
    base = f"{lang}/{lang_region}/{name}/{quality}/{PIPER_VOICE}"

    for url, target in [
        (f"{PIPER_VOICE_URL}/{base}.onnx",      onnx_path),
        (f"{PIPER_VOICE_URL}/{base}.onnx.json", json_path),
    ]:
        if target.exists():
            continue
        print(f"[FRIDAY] Downloading {target.name}...", flush=True)
        try:
            r = requests.get(url, stream=True, timeout=120)
            r.raise_for_status()
            tmp = target.with_suffix(".tmp")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            tmp.rename(target)
        except Exception as e:
            print(f"[FRIDAY] Download failed: {e}", flush=True)
            return False
    return True


# ---------------------------------------------------------------------------
# Speaker
# ---------------------------------------------------------------------------

def _rate_to_length_scale(wpm: int) -> float:
    return round(175 / max(wpm, 1), 3)


class Speaker:
    """Thread-safe TTS. Tries PiperTTS first, falls back to PowerShell on Windows."""

    def __init__(self) -> None:
        self._lock        = threading.Lock()
        self._voice       = None
        self._sample_rate = 22050
        self._init_piper()

    # ── initialisation ────────────────────────────────────────────────────

    def _init_piper(self) -> None:
        print("[FRIDAY] Loading voice engine...", flush=True)
        try:
            onnx, cfg = _piper_paths()
            if not onnx.exists() or not cfg.exists():
                if not _download_piper_model():
                    print("[FRIDAY] Using system TTS fallback.", flush=True)
                    return
                onnx, cfg = _piper_paths()

            from piper.voice import PiperVoice
            self._voice = PiperVoice.load(str(onnx), str(cfg))
            self._sample_rate = self._voice.config.sample_rate
            print("[FRIDAY] Voice engine ready.", flush=True)

        except ImportError:
            print("[FRIDAY] piper-tts not installed — using system TTS.", flush=True)
        except Exception as e:
            print(f"[FRIDAY] Piper init failed ({e}) — using system TTS.", flush=True)

    # ── public ────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        with self._lock:
            if self._voice is not None:
                try:
                    self._speak_piper(text)
                    return
                except Exception as e:
                    print(f"[Speaker] Piper speak error: {e}", flush=True)
            if _ON_WINDOWS:
                self._speak_ps(text)

    # ── piper path ────────────────────────────────────────────────────────

    def _speak_piper(self, text: str) -> None:
        import sounddevice as sd
        import numpy as np
        from piper.config import SynthesisConfig

        cfg = SynthesisConfig(length_scale=_rate_to_length_scale(TTS_RATE))
        chunks = [chunk.audio_int16_array
                  for chunk in self._voice.synthesize(text, cfg)]
        if not chunks:
            return
        audio = np.concatenate(chunks)
        sd.play(audio, samplerate=self._sample_rate, blocking=True)

    # ── powershell fallback ───────────────────────────────────────────────

    def _speak_ps(self, text: str) -> None:
        rate = max(-10, min(10, (TTS_RATE - 185) // 20))
        safe = text.replace("'", "''")
        cmd  = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = {rate}; $s.Volume = {int(TTS_VOLUME * 100)}; "
            f"$s.Speak('{safe}')"
        )
        try:
            proc = subprocess.Popen(
                ["powershell", "-NonInteractive", "-Command", cmd],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            proc.wait()
        except Exception as e:
            print(f"[Speaker] PowerShell TTS error: {e}", flush=True)
