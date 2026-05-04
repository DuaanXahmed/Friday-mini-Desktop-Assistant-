# parser.py — Keyword + Pattern Intent Parser

import re
from config import WEBSITES, MODES, APPS

# ---------------------------------------------------------------------------
# Intent map: each intent → list of trigger keywords/phrases
#
# ORDER MATTERS — _match_intent returns the FIRST match found.
# Critical ordering rules:
#   - generate_file   before create_multiple_files before create_file
#   - delete_all      before delete_multiple       before delete_file
#   - close_app       before open_app  (APPS.keys() are open_app triggers;
#                     "close chrome" would match "chrome" and reopen it otherwise)
#   - tell_datetime   before tell_date and tell_time
#   - system_status   before battery and cpu
# ---------------------------------------------------------------------------

INTENT_MAP = {

    # ── Generate file (AI-written content) ─────────────────────────────────
    "generate_file": [
        "generate file", "write a file", "write file",
        "generate a file", "write me a file", "ai write",
        "write a document", "generate document",
        "create a document about", "make a file about",
        "create file about", "generate file about",
        "write about", "write me a document",
        "compose a document", "compose a file",
        "draft a document", "draft a file",
        "write something about", "create content about",
        "make a document about", "a file about",
    ],

    # ── Create multiple files ── before create_file ─────────────────────────
    "create_multiple_files": [
        "create files", "make files", "new files",
        "create multiple files", "make multiple files",
        "create several files", "make several files",
        "add multiple files", "add files", "create these files",
        "make these files", "create a bunch of files",
    ],

    # ── Create single file ──────────────────────────────────────────────────
    "create_file": [
        "create file", "make file", "new file", "create a file",
        "add file", "new document", "make a new file",
        "create new file", "make a document", "make me a file",
        "create blank file", "start a new file", "create an empty file",
        "make an empty file",
        # typed creation shortcuts
        "create a text file", "make a text file", "new text file",
        "create a pdf", "make a pdf", "new pdf",
        "create a pdf file", "make a pdf file", "new pdf file",
        "create a word file", "make a word file",
        "create a word document", "make a word document",
        "create a docx", "make a docx", "new word document",
    ],

    # ── Delete all files ── before delete_multiple and delete_file ──────────
    "delete_all_files": [
        "delete all files", "remove all files", "erase all files",
        "delete all", "clear workspace", "wipe everything",
        "clear all files", "wipe workspace", "delete everything",
        "clean workspace", "purge workspace", "clean up workspace",
        "remove everything", "empty the workspace", "clear everything",
        "fresh start workspace",
    ],

    # ── Delete multiple files ── before delete_file ─────────────────────────
    "delete_multiple_files": [
        "delete files", "remove files", "erase files",
        "delete multiple files", "remove multiple files",
        "delete these files", "get rid of these files",
        "remove these files",
    ],

    # ── Delete single file ──────────────────────────────────────────────────
    "delete_file": [
        "delete file", "remove file", "delete a file",
        "erase file", "trash file", "remove the file",
        "get rid of file", "throw away file", "discard file",
        "delete this file",
        # bare verb fallbacks (delete_all and delete_multiple are checked first)
        "delete", "remove", "erase", "trash",
    ],

    # ── Rename file ─────────────────────────────────────────────────────────
    "rename_file": [
        "rename file", "rename", "change name",
        "rename the file", "rename it to",
        "change filename", "change file name",
        "change the name of", "rename this file",
    ],

    # ── Search file ─────────────────────────────────────────────────────────
    "search_file": [
        "search file", "find file", "look for file",
        "search for file", "find the file", "locate file",
        "where is file", "search for", "find my file",
        "look up file", "do i have a file", "is there a file",
        "find me a file", "look for my file", "search my files",
        "find", "search", "locate",
    ],

    # ── Open file ───────────────────────────────────────────────────────────
    "open_file": [
        "open file", "read file", "view file", "show file",
        "display file", "open the file", "launch file",
        "show me the file", "pull up file",
        "load file", "access file",
    ],

    # ── Screenshot ──────────────────────────────────────────────────────────
    "screenshot": [
        "take screenshot", "screenshot", "capture screen",
        "take a snap", "take ss", "grab screenshot",
        "snap screen", "take a screen capture",
        "capture screenshot", "screen grab",
        "take a picture of the screen",
        "capture the screen", "snap the screen",
    ],

    # ── Shutdown FRIDAY ── before close_app and open_website (ordering!) ────
    "shutdown_friday": [
        "goodbye friday", "bye friday", "goodbye", "bye bye",
        "shut down friday", "shutdown friday", "turn off friday",
        "exit friday", "quit friday", "stop friday",
        "go to sleep", "sleep friday",
        "that's all friday", "that's all for now", "dismiss friday",
        "goodnight friday", "good night friday", "goodnight",
        "see you later friday", "see ya friday", "farewell friday",
        "power off friday", "close friday", "terminate friday",
        "you can go", "you're dismissed", "we're done",
        "that will be all", "i'm done", "enough for now",
        
        "go away friday","You can sleep now"
    ],

    # ── Close app ── before open_app (APPS.keys() conflict) ─────────────────
    "close_app": [
        "close", "quit", "kill", "shut down",
        "terminate", "force close", "exit app",
        "close out", "close the app", "close the program",
        "exit the app", "stop the app", "stop running",
        "get rid of the app", "shut the app",
    ],

    # ── Open app ────────────────────────────────────────────────────────────
    "open_app": [
        "open app", "open", "launch", "start", "run",
        "fire up", "pull up", "open the app",
        "start the app", "boot up", "load up",
        "open up the app", "open program",
    ] + list(APPS.keys()),

    # ── Open website ────────────────────────────────────────────────────────
    "open_website": [
        "open website", "go to", "browse to",
        "navigate to", "visit", "open the website",
        "take me to", "head to", "open up",
        "open the site", "pull up the website",
    ] + list(WEBSITES.keys()),

    # ── Modes ───────────────────────────────────────────────────────────────
    "study_mode": [
        "study mode", "study", "focus mode", "study time",
        "learning mode", "enter study", "activate study",
        "switch to study", "start study mode",
    ],
    "work_mode": [
        "work mode", "work", "office mode", "productivity mode",
        "work time", "enter work", "activate work",
        "switch to work", "start work mode",
    ],

    # ── Date & time ── tell_datetime before tell_date and tell_time ─────────
    "tell_datetime": [
        "date and time", "time and date",
        "current date and time", "what's the date and time",
        "tell date and time", "date time",
        "what's today's date and time",
        "tell me the date and time",
        "what's the time and date",
        "give me the date and time",
    ],
    "tell_time": [
        "what time", "current time", "what's the time",
        "tell time", "clock", "time now",
        "tell me the time", "what hour",
        "time please", "what is the time",
        "what's the hour", "give me the time",
        "check the time",
    ],
    "tell_date": [
        "what date", "today's date", "what's the date",
        "tell date", "what day is it", "current date",
        "what's today", "what is today",
        "tell me the date", "what's the day",
        "which day is it", "what day is today",
        "give me the date",
    ],

    # ── System status ── before battery and cpu ─────────────────────────────
    "system_status": [
        "system status", "full system", "system report",
        "system check", "how's my system", "how is my system",
        "full status", "system health", "overall status",
        "check my system", "full system check",
        "complete system check", "run diagnostics",
        "status report", "how's everything running",
        "full report",
    ],
    "battery": [
        "battery", "battery percentage", "battery level",
        "power level", "charging status", "battery status",
        "battery life", "how much battery", "check battery",
        "how much charge", "power status", "charge level",
        "am i charging",
    ],
    "cpu": [
        "cpu", "cpu usage", "processor",
        "processor load", "system load", "system performance",
        "how is my cpu", "check cpu", "cpu load",
        "processor usage", "how's the cpu",
        "how's the processor",
    ],

    # ── Introduction ────────────────────────────────────────────────────────
    "introduce": [
        "who are you", "introduce yourself", "what can you do",
        "your name", "about you", "what are you",
        "tell me about yourself", "what do you know",
        "what are your features", "how do you work",
        "what commands do you know",
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _match_intent(text: str) -> str | None:
    for intent, keywords in INTENT_MAP.items():
        for kw in keywords:
            if kw in text:
                return intent
    return None


def _extract_filename(text: str) -> str | None:
    match = re.search(r"\b[\w\-]+\.(txt|pdf|docx|py|csv|json|md)\b", text)
    return match.group(0) if match else None


def _extract_filenames_list(text: str) -> list[str]:
    return re.findall(r"\b[\w\-]+\.(txt|pdf|docx|py|csv|json|md)\b", text)


def _extract_action_target(text: str) -> str | None:
    """Extract the word immediately after an action verb as a fallback file target."""
    match = re.search(
        r"\b(?:delete|remove|erase|trash|open|read|view|show|find|locate|rename|search)\s+([\w\-]+)",
        text,
    )
    if match:
        word = match.group(1)
        if word not in _NOISE:
            return word
    return None


def _extract_name_hint(text: str) -> str | None:
    """Extract a bare filename stem from 'called X', 'named X', 'name it X'."""
    for phrase in ("called ", "named ", "name it ", "call it "):
        if phrase in text:
            after = text.split(phrase, 1)[1].strip()
            word = re.split(r"[\s,.]", after)[0]
            if word and word not in _NOISE:
                return word.rsplit(".", 1)[0] if "." in word else word
    return None


def _extract_file_type(text: str) -> str | None:
    """Return 'txt', 'pdf', or 'docx' based on type keywords in the utterance."""
    if any(kw in text for kw in ("word document", "word file", "word doc", "docx")):
        return "docx"
    if any(kw in text for kw in ("pdf file", "pdf document", "pdf")):
        return "pdf"
    if any(kw in text for kw in ("text file", "txt file", "text document")):
        return "txt"
    return None


def _extract_topic(text: str) -> str:
    """Strip command prefix and return the topic the user wants written about."""
    for phrase in (
        "write a document about", "create a document about",
        "generate document about", "generate file about",
        "write a file about", "make a file about",
        "create file about", "write about",
        "write file about", "compose a document on",
        "compose a document about", "draft a document on",
        "draft a document about", "write something about",
        "create content about", "make a document about",
        "write me a document about", "write me a file about",
        "file about",
    ):
        if phrase in text:
            after = text.split(phrase, 1)[1].strip()
            return after if after else text
    return text


def _extract_new_name(text: str) -> str | None:
    match = re.search(r"\bto\s+([\w\-]+(?:\.\w+)?)", text)
    return match.group(1) if match else None


def _extract_target_word(text: str, after_kw: str) -> str | None:
    pattern = rf"{re.escape(after_kw)}\s+([\w\-]+)"
    match = re.search(pattern, text)
    return match.group(1) if match else None


def _extract_website(text: str) -> str | None:
    for site in WEBSITES:
        if site in text:
            return site
    return None


def _extract_app_name(text: str, skip_words: set) -> str | None:
    for app in sorted(APPS.keys(), key=len, reverse=True):
        if app in text:
            return app
    match = re.search(
        r"\b(?:open|close|launch|start|run|quit|kill|terminate|exit|fire up|pull up|boot up|load up)\s+([\w]+(?:\.[\w]+)?)",
        text,
    )
    if match:
        word = match.group(1)
        if word not in skip_words:
            return word
    return None


_NOISE = {"app", "application", "the", "a", "an", "file", "website", "mode", "program"}


# ---------------------------------------------------------------------------
# Multi-command splitter
# ---------------------------------------------------------------------------

def split_commands(text: str) -> list[str]:
    parts = re.split(r"\band\b", text)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------

def parse(text: str) -> dict | None:
    text   = text.lower().strip()
    intent = _match_intent(text)

    if intent is None:
        return None

    entities = {}

    # ── Generate file (AI-written content) ────────────────────────────────
    if intent == "generate_file":
        topic = _extract_topic(text)
        fn    = _extract_filename(text)
        entities["topic"] = topic
        if fn:
            entities["filename"] = fn

    # ── Multiple file creation ─────────────────────────────────────────────
    elif intent == "create_multiple_files":
        entities["filenames"] = _extract_filenames_list(text)

    # ── Create single file ────────────────────────────────────────────────
    elif intent == "create_file":
        fn = _extract_filename(text)
        if fn:
            entities["filename"] = fn
        elif " about " in text:
            # "create a text file about X" → generate content, not blank file
            intent = "generate_file"
            entities["topic"] = _extract_topic(text)
            ft = _extract_file_type(text)
            if ft:
                entities["file_type"] = ft
        else:
            name_hint = _extract_name_hint(text)
            file_type = _extract_file_type(text)
            if name_hint:
                entities["name_hint"] = name_hint
            if file_type:
                entities["file_type"] = file_type
            # fallback: bare word after "file" keyword
            if not name_hint:
                word = _extract_target_word(text, "file")
                if word and word not in _NOISE:
                    entities["name_hint"] = word

    # ── Other single file ops ─────────────────────────────────────────────
    elif intent in ("delete_file", "open_file", "search_file"):
        fn = _extract_filename(text)
        if fn:
            entities["filename"] = fn
        else:
            # Try bare name after action verb first, then keyword fallbacks
            target = _extract_action_target(text)
            if not target:
                for kw in (["for", "file"] if intent == "search_file" else ["file"]):
                    word = _extract_target_word(text, kw)
                    if word and word not in _NOISE:
                        target = word
                        break
            if target:
                entities["filename"] = target   # _find_in_workspace resolves ext later

    # ── Multiple file deletion ─────────────────────────────────────────────
    elif intent == "delete_multiple_files":
        entities["filenames"] = _extract_filenames_list(text)

    # ── Rename ────────────────────────────────────────────────────────────
    elif intent == "rename_file":
        fn = _extract_filename(text)
        if fn:
            entities["filename"] = fn
        else:
            target = _extract_action_target(text)
            if target:
                entities["filename"] = target
        entities["new_name"] = _extract_new_name(text)

    # ── App control ───────────────────────────────────────────────────────
    elif intent == "open_app":
        name = _extract_app_name(text, _NOISE)
        if name and name in WEBSITES:
            intent = "open_website"
            entities["website"] = name
        elif name and name in APPS:
            entities["app"] = name
        else:
            # Not a known app/site — could be a file ("open summary", "open notes.pdf")
            fn     = _extract_filename(text)
            target = fn or _extract_action_target(text) or name
            if target and target not in _NOISE:
                intent = "open_file"
                entities["filename"] = target
            else:
                entities["app"] = name

    elif intent == "close_app":
        entities["app"] = _extract_app_name(text, _NOISE)

    # ── Website ───────────────────────────────────────────────────────────
    elif intent == "open_website":
        site = _extract_website(text)
        if site:
            entities["website"] = site
        else:
            match = re.search(r"\b([\w]+\.[\w]+)\b", text)
            if match:
                entities["website"] = match.group(1)

    # ── Modes ─────────────────────────────────────────────────────────────
    elif intent == "study_mode":
        entities["sites"] = MODES["study"]

    elif intent == "work_mode":
        entities["sites"] = MODES["work"]

    # screenshot, delete_all_files, tell_time, tell_date, tell_datetime,
    # system_status, battery, cpu, introduce → no entities needed

    return {"intent": intent, "entities": entities}
