# config.py — FRIDAY Settings

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Wake word
WAKE_WORD = "friday"

# Workspace folder (all file ops restricted here)
WORKSPACE = os.path.join(os.path.expanduser("~"), "friday_workspace")

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# OpenAI model for fallback
OPENAI_MODEL = "gpt-4o-mini"

# Speech recognition settings
MIC_TIMEOUT  = 6           # seconds to wait for speech to start
PHRASE_LIMIT = 20        # max seconds per phrase
SR_LANGUAGE  = "en-US"

# Text-to-speech settings
TTS_RATE   = 195           # words per minute
TTS_VOLUME = 0.95          # 0.0 – 1.0
INTERRUPT_WORD = "cancel"

# Auto-open workspace folder in Explorer at startup
AUTO_OPEN_WORKSPACE = True

# ──────────────────────────────────────────────
# APP LAUNCHER  (Windows)
# ──────────────────────────────────────────────

_user = os.getenv("USERNAME", "User")

APPS = {
    "chrome":        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "cursor":        rf"C:\Users\{_user}\AppData\Local\Programs\cursor\Cursor.exe",
    "notepad":       "notepad",
    "calculator":    "calc",
    "camera":        "start microsoft.windows.camera:",
    "explorer":      "explorer",
    "task manager":  "taskmgr",
    "spotify":       rf"C:\Users\{_user}\AppData\Roaming\Spotify\Spotify.exe",
    "vscode":        rf"C:\Users\{_user}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vs code":       rf"C:\Users\{_user}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "upwork":        rf"C:\Users\{_user}\AppData\Local\Upwork\Upwork.exe",
    "paint":         "mspaint",
    "word":          r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":         r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
}

APP_PROCESS_NAMES = {
    "chrome":        "chrome.exe",
    "cursor":        "Cursor.exe",
    "notepad":       "notepad.exe",
    "calculator":    "CalculatorApp.exe",
    "camera":        "WindowsCamera.exe",
    "explorer":      "explorer.exe",
    "task manager":  "Taskmgr.exe",
    "spotify":       "Spotify.exe",
    "vscode":        "Code.exe",
    "vs code":       "Code.exe",
    "upwork":        "Upwork.exe",
    "paint":         "mspaint.exe",
    "word":          "WINWORD.EXE",
    "excel":         "EXCEL.EXE",
}

# ──────────────────────────────────────────────
# WEBSITES
# ──────────────────────────────────────────────

WEBSITES = {
    "youtube":     "https://youtube.com",
    "upwork":      "https://upwork.com",
    "chatgpt":     "https://chat.openai.com",
    "supabase":    "https://supabase.com",
    "github":      "https://github.com",
    "siteground":  "https://siteground.com",
    "google":      "https://google.com",
}

# ──────────────────────────────────────────────
# MODES
# ──────────────────────────────────────────────

MODES = {
    "study": ["chatgpt", "youtube"],
    "work":  ["upwork", "supabase", "github", "siteground"],
}

# ──────────────────────────────────────────────
# ACKNOWLEDGEMENT PHRASES
# ──────────────────────────────────────────────

RESPONSES = [
    "On it, sir.",
    "Right away, boss.",
    "Consider it done, sir.",
    "Of course, boss.",
    "Understood, sir.",
]
