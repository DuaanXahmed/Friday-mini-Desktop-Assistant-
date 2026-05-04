# commands.py — FRIDAY Command Executor

import os
import re
import datetime
import glob
import subprocess
import webbrowser

import psutil
import pyautogui

from config import WORKSPACE, APPS, APP_PROCESS_NAMES, WEBSITES
from utils import speak, ack

os.makedirs(WORKSPACE, exist_ok=True)

_RE = "\033[91m"; _RS = "\033[0m"


class FridayShutdown(Exception):
    """Raised by shutdown_friday() to signal a clean exit."""


def _safe_path(filename: str) -> str:
    return os.path.join(WORKSPACE, os.path.basename(filename))


def _find_in_workspace(name: str) -> str | None:
    """Resolve a name (with or without extension) to an existing workspace path."""
    exact = _safe_path(name)
    if os.path.exists(exact):
        return exact
    for ext in (".txt", ".pdf", ".docx", ".py", ".csv", ".json", ".md"):
        p = _safe_path(name + ext)
        if os.path.exists(p):
            return p
    matches = [m for m in glob.glob(os.path.join(WORKSPACE, f"*{name}*")) if os.path.isfile(m)]
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# File Operations
# ---------------------------------------------------------------------------

_FILE_TYPE_KEYWORDS = {
    "docx": ("word", "docx", "word document", "word file"),
    "pdf":  ("pdf", "pdf file", "pdf document"),
    "txt":  ("text", "txt", "text file", "plain"),
}


def _spoken_ext(text: str) -> str:
    """Return '.docx', '.pdf', or '.txt' based on keywords in a spoken string."""
    t = text.lower()
    for ext, kws in _FILE_TYPE_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return f".{ext}"
    return ".txt"


def _spoken_stem(text: str) -> str:
    """Extract a clean filename stem from a spoken response."""
    t = text.lower().strip()
    for filler in ("call it ", "name it ", "called ", "named ", "name "):
        if filler in t:
            t = t.split(filler, 1)[1].strip()
    # drop any type keywords so we get a clean name
    for kws in _FILE_TYPE_KEYWORDS.values():
        for kw in kws:
            t = t.replace(kw, "").strip()
    stem = re.split(r"[\s,.]", t)[0]
    return stem or "untitled"


def generate_file(entities: dict):
    topic    = entities.get("topic", "").strip()
    filename = entities.get("filename", "")

    if not topic:
        speak(
            "What should I write about, sir? "
            "Say something like: write a file about the solar system."
        )
        return

    if not filename:
        slug     = topic[:30].replace(" ", "_")
        filename = f"{slug}.txt"

    path = _safe_path(filename)
    ack()
    speak(f"Generating content on '{topic}', sir. One moment.")

    try:
        from fallback import generate_content
        content = generate_content(topic)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        speak(f"Done, sir. I've written the document and saved it as {filename} in your workspace.")
    except Exception as e:
        speak(f"I ran into a problem generating the file, sir. {e}")


def create_file(entities: dict):
    filename  = entities.get("filename", "")
    name_hint = entities.get("name_hint", "")
    file_type = entities.get("file_type", "")

    # Build filename from parts when we don't have a full one already
    if not filename:
        stem = name_hint
        ext  = f".{file_type}" if file_type else ""

        if not stem:
            # Ask user for the filename / type
            if ext:
                type_label = {"txt": "text", "pdf": "PDF", "docx": "Word"}.get(file_type, file_type)
                speak(f"What should I name the {type_label} file, sir?")
            else:
                speak(
                    "What should I name the file, sir? "
                    "You can also tell me the type — text, PDF, or Word."
                )
            from utils import listen_for_command
            raw = listen_for_command()
            if not raw:
                speak("Didn't catch a name, sir. Cancelled.")
                return
            stem = _spoken_stem(raw)
            if not ext:
                ext = _spoken_ext(raw)

        filename = f"{stem}{ext or '.txt'}"

    path = _safe_path(filename)
    ext  = os.path.splitext(filename)[1].lower()
    try:
        if ext == ".docx":
            from docx import Document
            Document().save(path)
        elif ext == ".pdf":
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(path)
            c.drawString(100, 750, "Created by FRIDAY")
            c.save()
        else:
            open(path, "w").close()
        speak(f"Done, sir. {filename} has been created in your workspace.")
    except Exception as e:
        speak(f"I couldn't create {filename}, sir. {e}")


def create_multiple_files(entities: dict):
    filenames = entities.get("filenames", [])
    if not filenames:
        speak(
            "Please name the files you'd like me to create, sir. "
            "For example: create files report dot txt and notes dot pdf."
        )
        return

    created = []
    failed  = []
    for filename in filenames:
        path = _safe_path(filename)
        ext  = os.path.splitext(filename)[1].lower()
        try:
            if ext == ".docx":
                from docx import Document
                Document().save(path)
            elif ext == ".pdf":
                from reportlab.pdfgen import canvas
                c = canvas.Canvas(path)
                c.drawString(100, 750, "Created by FRIDAY")
                c.save()
            else:
                open(path, "w").close()
            created.append(filename)
        except Exception:
            failed.append(filename)

    if created:
        speak(f"Done, sir. I've created {len(created)} files: {', '.join(created)}.")
    if failed:
        speak(f"I couldn't create the following files, sir: {', '.join(failed)}.")


def delete_file(entities: dict):
    name = entities.get("filename") or entities.get("query", "")
    if not name:
        speak("Which file should I delete, sir?")
        return
    path = _find_in_workspace(name)
    if path:
        fname = os.path.basename(path)
        os.remove(path)
        speak(f"Done, sir. {fname} has been deleted.")
    else:
        speak(f"I couldn't find a file named '{name}' in your workspace, sir.")


def delete_multiple_files(entities: dict):
    filenames = entities.get("filenames", [])
    if not filenames:
        speak(
            "Please name the files you'd like me to delete, sir. "
            "For example: delete files report dot txt and notes dot pdf."
        )
        return

    deleted = []
    missing = []
    for filename in filenames:
        path = _safe_path(filename)
        if os.path.exists(path):
            os.remove(path)
            deleted.append(filename)
        else:
            missing.append(filename)

    if deleted:
        speak(f"Done, sir. Deleted {len(deleted)} files: {', '.join(deleted)}.")
    if missing:
        speak(f"I couldn't find these files in your workspace, sir: {', '.join(missing)}.")


def delete_all_files(entities: dict):
    files = glob.glob(os.path.join(WORKSPACE, "*"))
    files = [f for f in files if os.path.isfile(f)]

    if not files:
        speak("Your workspace is already empty, sir. There's nothing to delete.")
        return

    count = len(files)
    for f in files:
        try:
            os.remove(f)
        except Exception:
            pass

    speak(f"Done, sir. I've cleared your workspace — {count} {'file' if count == 1 else 'files'} deleted.")


def rename_file(entities: dict):
    old_name = entities.get("filename") or ""
    new_name = entities.get("new_name") or ""
    if not old_name or not new_name:
        speak("I need both the current name and the new name, sir. Try: rename report to summary.")
        return
    old_path = _find_in_workspace(old_name)
    if not old_path:
        speak(f"I couldn't find a file named '{old_name}' in your workspace, sir.")
        return
    old_ext = os.path.splitext(old_path)[1]
    if "." not in new_name:
        new_name += old_ext
    new_path = _safe_path(new_name)
    os.rename(old_path, new_path)
    speak(f"Done, sir. {os.path.basename(old_path)} has been renamed to {new_name}.")


def search_file(entities: dict):
    query = entities.get("query") or entities.get("filename", "")
    if not query:
        speak("What should I search for, sir? Just say the name.")
        return
    matches = [m for m in glob.glob(os.path.join(WORKSPACE, f"*{query}*")) if os.path.isfile(m)]
    if matches:
        names  = [os.path.basename(m) for m in matches]
        noun   = "file" if len(names) == 1 else "files"
        speak(f"I found {len(names)} {noun} matching '{query}', sir: {', '.join(names)}.")
    else:
        speak(f"No files matching '{query}' were found in your workspace, sir.")


def open_file(entities: dict):
    name = entities.get("filename") or entities.get("query", "")
    if not name:
        speak("Which file should I open, sir?")
        return
    path = _find_in_workspace(name)
    if path:
        os.startfile(path) if os.name == "nt" else subprocess.Popen(["xdg-open", path])
        speak(f"Opening {os.path.basename(path)}, sir.")
    else:
        speak(f"I couldn't find a file named '{name}' in your workspace, sir.")


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

def take_screenshot(entities: dict):
    ack()
    path = _safe_path(f"screenshot_{datetime.datetime.now().strftime('%H%M%S')}.png")
    try:
        pyautogui.screenshot(path)
        speak(f"Screenshot saved to your workspace, sir.")
    except Exception as e:
        speak(f"I couldn't take the screenshot, sir. {e}")


# ---------------------------------------------------------------------------
# Websites & Apps
# ---------------------------------------------------------------------------

def open_website(entities: dict):
    site_key = entities.get("website") or ""
    if not site_key:
        speak(
            "Which website should I open, sir? "
            "I can open YouTube, ChatGPT, GitHub, Google, Upwork, Supabase, and Siteground."
        )
        return
    url = WEBSITES.get(site_key, site_key if site_key.startswith("http") else f"https://{site_key}")
    webbrowser.open(url)
    speak(f"Opening {site_key} for you, sir.")


def open_app(entities: dict):
    app_name = (entities.get("app") or "").lower()
    if not app_name:
        speak(
            "Which application should I open, sir? "
            "I can launch Chrome, Notepad, Calculator, Camera, Spotify, Cursor, and more."
        )
        return
    path = APPS.get(app_name)
    if path:
        try:
            subprocess.Popen(path, shell=True)
            speak(f"Launching {app_name} for you, sir.")
        except Exception:
            speak(f"I found {app_name} in my list but couldn't launch it, sir. Please check the path in settings.")
    else:
        try:
            subprocess.Popen(app_name, shell=True)
            speak(f"Trying to launch {app_name}, sir.")
        except Exception:
            speak(
                f"I'm not sure how to open {app_name}, sir. "
                "I can open Chrome, Notepad, Calculator, Camera, Spotify, Cursor, VS Code, Word, Excel, and more."
            )


def close_app(entities: dict):
    app_name = entities.get("app") or ""
    if not app_name:
        speak(
            "Which application should I close, sir? "
            "Just say close followed by the app name."
        )
        return

    proc_name = APP_PROCESS_NAMES.get(app_name.lower(), "").lower()
    killed = 0

    for proc in psutil.process_iter(["name", "pid"]):
        try:
            pname = proc.info["name"].lower()
            match = (proc_name and pname == proc_name) or \
                    (not proc_name and app_name.lower() in pname)
            if match:
                proc.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed:
        speak(f"Closed {app_name}, sir.")
    else:
        speak(
            f"{app_name} doesn't appear to be running, sir. "
            "If it is open, make sure you said the name clearly."
        )


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def study_mode(entities: dict):
    speak("Activating study mode, sir. Opening ChatGPT and YouTube for you.")
    for site in entities.get("sites", []):
        webbrowser.open(WEBSITES[site])


def work_mode(entities: dict):
    speak("Activating work mode, sir. Setting up Upwork, Supabase, GitHub, and Siteground.")
    for site in entities.get("sites", []):
        webbrowser.open(WEBSITES[site])


# ---------------------------------------------------------------------------
# System Info
# ---------------------------------------------------------------------------

def tell_time(entities: dict):
    now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"It's {now}, sir.")


def tell_date(entities: dict):
    today = datetime.datetime.now().strftime("%A, %B %d, %Y")
    speak(f"Today is {today}, sir.")


def tell_datetime(entities: dict):
    now   = datetime.datetime.now()
    time_ = now.strftime("%I:%M %p")
    date_ = now.strftime("%A, %B %d, %Y")
    speak(f"It's {time_} on {date_}, sir.")


def battery(entities: dict):
    try:
        batt = psutil.sensors_battery()
    except Exception:
        batt = None
    if batt is None:
        speak("No battery sensor was detected, sir. This appears to be a desktop machine.")
        return
    pct    = int(batt.percent)
    status = "charging" if batt.power_plugged else "on battery"
    if pct < 20 and not batt.power_plugged:
        note = " I'd recommend plugging in soon, sir."
    elif batt.power_plugged and pct >= 95:
        note = " Your battery is almost fully charged, sir."
    else:
        note = ""
    speak(f"Battery is at {pct} percent and {status}, sir.{note}")


def cpu(entities: dict):
    usage = psutil.cpu_percent(interval=1)
    if usage > 80:
        note = " That's quite high, sir. You may want to close some applications."
    elif usage < 20:
        note = " Your system is running smoothly, sir."
    else:
        note = ""
    speak(f"CPU usage is at {usage} percent.{note}")


def system_status(entities: dict):
    cpu_usage = psutil.cpu_percent(interval=1)

    try:
        batt = psutil.sensors_battery()
    except Exception:
        batt = None

    cpu_note = (
        "running quite high" if cpu_usage > 80
        else "running smoothly" if cpu_usage < 20
        else "at a moderate level"
    )

    if batt is None:
        batt_line = "No battery sensor detected — likely a desktop machine."
    else:
        pct    = int(batt.percent)
        status = "charging" if batt.power_plugged else "on battery"
        batt_line = f"Battery is at {pct} percent and {status}."

    speak(
        f"System report, sir: CPU is at {cpu_usage} percent, {cpu_note}. "
        f"{batt_line}"
    )


# ---------------------------------------------------------------------------
# Introduction
# ---------------------------------------------------------------------------

def shutdown_friday(entities: dict):
    speak("Shutting down, sir. It was a pleasure. Goodbye.")
    raise FridayShutdown()


def introduce(entities: dict):
    speak(
        "I'm FRIDAY, your personal AI voice assistant, sir. "
        "Say Friday to wake me, then give your command. "
        "I can create, generate, delete, rename, search, and open files in your workspace. "
        "I can open and close apps like Chrome, Notepad, Calculator, and Camera. "
        "I can open websites, take screenshots, check battery and CPU status, "
        "tell you the time and date, and activate study or work mode. "
        "For anything else, just ask and I'll look it up for you, sir."
    )


# ---------------------------------------------------------------------------
# General Query  (answer comes from OpenAI fallback)
# ---------------------------------------------------------------------------

def general_query(entities: dict):
    answer = entities.get("answer", "")
    if answer:
        speak(answer)
    else:
        speak(
            "I wasn't able to get an answer for that, sir. "
            "Please check your internet connection and try again."
        )


# ---------------------------------------------------------------------------
# Intent → Function Router
# ---------------------------------------------------------------------------

COMMAND_MAP = {
    "shutdown_friday":        shutdown_friday,
    "introduce":              introduce,
    "generate_file":          generate_file,
    "create_file":            create_file,
    "create_multiple_files":  create_multiple_files,
    "delete_file":            delete_file,
    "delete_multiple_files":  delete_multiple_files,
    "delete_all_files":       delete_all_files,
    "rename_file":            rename_file,
    "search_file":            search_file,
    "open_file":              open_file,
    "screenshot":             take_screenshot,
    "open_website":           open_website,
    "open_app":               open_app,
    "close_app":              close_app,
    "study_mode":             study_mode,
    "work_mode":              work_mode,
    "tell_time":              tell_time,
    "tell_date":              tell_date,
    "tell_datetime":          tell_datetime,
    "battery":                battery,
    "cpu":                    cpu,
    "system_status":          system_status,
    "general_query":          general_query,
}


def execute(parsed: dict):
    intent   = parsed.get("intent")
    entities = parsed.get("entities", {})
    fn = COMMAND_MAP.get(intent)
    if fn:
        try:
            fn(entities)
        except FridayShutdown:
            raise
        except Exception as e:
            print(f"{_RE}[ERROR]  {intent} failed: {e}{_RS}")
            speak("I ran into a problem with that command, sir. Please try again.")
    else:
        speak(
            "I'm not sure how to handle that, sir. "
            "Try asking me to open an app, manage a file, check system info, or ask me a question."
        )
