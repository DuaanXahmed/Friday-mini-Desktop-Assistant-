# main.py — FRIDAY Entry Point

import sys
import os
import platform
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

print("[FRIDAY] Starting up...", flush=True)

from config import WAKE_WORD, WORKSPACE, OPENAI_MODEL, AUTO_OPEN_WORKSPACE
from utils import listen_for_wake_word, listen_for_command, speak
from parser import parse, split_commands
from commands import execute, FridayShutdown

try:
    from fallback import fallback
except Exception:
    def fallback(text):
        return None


# ──────────────────────────────────────────────
# ANSI TERMINAL COLOURS
# ──────────────────────────────────────────────

_CY = "\033[96m"   # cyan    — status
_GR = "\033[92m"   # green   — action
_RE = "\033[91m"   # red     — error
_RS = "\033[0m"    # reset


def _log(colour: str, tag: str, msg: str) -> None:
    print(f"{colour}[{tag}] {msg}{_RS}", flush=True)

def log_status(msg: str) -> None: _log(_CY, "STATUS", msg)
def log_action(msg: str) -> None: _log(_GR, "ACTION", msg)
def log_error(msg: str)  -> None: _log(_RE, "ERROR",  msg)


# ──────────────────────────────────────────────
# STARTUP HELPERS
# ──────────────────────────────────────────────

def open_workspace() -> None:
    os.makedirs(WORKSPACE, exist_ok=True)
    try:
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", WORKSPACE])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", WORKSPACE])
        else:
            subprocess.Popen(["xdg-open", WORKSPACE])
    except Exception as e:
        log_error(f"Could not open workspace: {e}")


def boot_banner() -> None:
    print("\n" + "═" * 58)
    print("  FRIDAY  —  AI Voice Assistant")
    print("═" * 58)
    print(f"  Workspace : {WORKSPACE}")
    print(f"  AI model  : {OPENAI_MODEL}")
    print(f"  Wake word : '{WAKE_WORD}'  |  Ctrl+C to quit.")
    print(f"  Commands  : Speak naturally — AI understands you.")
    print("═" * 58 + "\n", flush=True)


# ──────────────────────────────────────────────
# COMMAND HANDLER
# ──────────────────────────────────────────────

def handle_command(raw: str) -> None:
    for cmd in split_commands(raw):
        try:
            parsed = parse(cmd)

            if parsed is None:
                log_status("Parser miss — asking AI...")
                parsed = fallback(cmd)

            if parsed:
                intent   = parsed.get("intent", "unknown")
                entities = parsed.get("entities", {})
                log_action(f"{intent}  args={entities}")
                execute(parsed)
            else:
                speak(
                    "I didn't quite understand that, sir. "
                    "Try saying something like: open Chrome, create file, "
                    "what's the time, or ask me a question."
                )

        except FridayShutdown:
            raise
        except Exception as e:
            log_error(f"Command failed: {e}")
            speak("Something went wrong with that command, sir. Please try again.")


# ──────────────────────────────────────────────
# MAIN LOOP
# ──────────────────────────────────────────────

# Max consecutive missed commands before returning to wake-word standby.
_MAX_MISSES = 3


def main() -> None:
    boot_banner()

    if AUTO_OPEN_WORKSPACE:
        open_workspace()

    speak("FRIDAY online, sir. Say Friday whenever you need me.")

    active = False
    misses = 0

    while True:
        try:
            # ── Phase 1: wait for wake word ───────────────────────────────
            if not active:
                misses = 0
                log_status(f"Listening for '{WAKE_WORD}'...")
                if not listen_for_wake_word():
                    continue
                speak("Yes, sir? What can I do for you?")
                active = True

            # ── Phase 2: capture command ──────────────────────────────────
            log_status("Listening for command...")
            raw = listen_for_command()

            if not raw:
                misses += 1
                if misses < _MAX_MISSES:
                    speak("Say again, sir.")
                else:
                    speak("Going to standby. Say Friday when ready.")
                    active = False
                    misses = 0
                continue

            misses = 0
            print(f"\033[93mYou said: {raw}\033[0m", flush=True)
            handle_command(raw)

            # Stay active — next command needs no wake word

        except (KeyboardInterrupt, FridayShutdown):
            raise
        except Exception as e:
            log_error(f"Loop error: {e}")
            active = False


if __name__ == "__main__":
    try:
        main()
    except FridayShutdown:
        print("\n[FRIDAY] Shutting down. Goodbye, sir.")
    except KeyboardInterrupt:
        try:
            speak("Friday shutting down. Goodbye, sir.")
        except Exception:
            pass
        print("\n[FRIDAY] Shutting down. Goodbye, sir.")
    except Exception:
        import traceback
        print("\n" + "═" * 58)
        print("  FRIDAY  —  STARTUP ERROR")
        print("═" * 58)
        traceback.print_exc()
        print("═" * 58)
        print("  Install missing packages:  pip install -r requirements.txt")
        print("═" * 58)
        input("\nPress Enter to exit...")
