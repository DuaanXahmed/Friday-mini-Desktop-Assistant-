# fallback.py — OpenAI integration (intent classification + general LLM calls)

import json
import re
from config import OPENAI_API_KEY, OPENAI_MODEL

_RE = "\033[91m"; _RS = "\033[0m"

# ---------------------------------------------------------------------------
# Intent classification system prompt
# ---------------------------------------------------------------------------

_INTENT_SYSTEM = """
You are an intent extraction engine for a voice assistant called FRIDAY.
Given a user utterance, return ONLY a valid JSON object. No explanation. No markdown. No code fences.

Valid intents and their entity fields:
  generate_file         — { "topic": "<what to write about>", "filename": "<optional, e.g. notes.txt>" }
  create_file           — { "filename": "<name.ext>" }
  create_multiple_files — { "filenames": ["a.txt", "b.pdf", ...] }
  delete_all_files      — {}
  delete_multiple_files — { "filenames": ["a.txt", "b.pdf", ...] }
  delete_file           — { "filename": "<name.ext>" }
  rename_file           — { "filename": "<old.ext>", "new_name": "<new.ext>" }
  search_file           — { "query": "<search term>" }
  open_file             — { "filename": "<name.ext>" }
  screenshot            — {}
  open_website          — { "website": "<youtube|chatgpt|github|google|upwork|supabase|siteground|or full URL>" }
  open_app              — { "app": "<app name as spoken>" }
  close_app             — { "app": "<app name as spoken>" }
  study_mode            — {}
  work_mode             — {}
  tell_datetime         — {}
  tell_time             — {}
  tell_date             — {}
  system_status         — {}
  battery               — {}
  cpu                   — {}
  general_query         — { "answer": "<direct, conversational answer in 1-2 sentences>" }

Disambiguation rules:
- generate_file: user wants content WRITTEN and SAVED (e.g. "write a file about X", "create a document on X").
- create_file: user wants a blank file created with a specific name. No content generation.
- delete_all_files: user says "delete all", "clear everything", "wipe workspace", "fresh start".
- delete_multiple_files: user names 2+ specific files for deletion.
- close_app: user wants an app CLOSED/QUIT. Never route "close X" to open_app.
- open_app: user wants an app LAUNCHED/OPENED.
- tell_datetime: user asks for BOTH date AND time together.
- system_status: user wants a full CPU + battery report.
- general_query: anything factual, conversational, or definitional. Answer directly and naturally.
  Good general_query answers are short, clear, and sound like a knowledgeable assistant speaking.
  Do not say "I don't know" — give the best answer you can in 1-2 sentences.
""".strip()

# ---------------------------------------------------------------------------
# Content generation system prompt
# ---------------------------------------------------------------------------

_CONTENT_SYSTEM = (
    "You are a professional writing assistant. Write a clear, informative, and well-structured document "
    "on the topic provided by the user. "
    "Use plain text only — absolutely no markdown, no bullet symbols, no asterisks, no headers with #. "
    "Write in flowing paragraphs. "
    "Aim for 250 to 400 words. Be factual, engaging, and easy to read. "
    "Output only the document body — no title, no preamble, no closing remarks."
)


# ---------------------------------------------------------------------------
# OpenAI client (lazy — never created at import time)
# ---------------------------------------------------------------------------

def _get_client():
    try:
        from openai import OpenAI
        if not OPENAI_API_KEY:
            return None
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ask_llm(prompt: str, system: str = "You are a helpful assistant. Be concise.") -> str:
    """Send a prompt to the LLM and return the plain-text reply."""
    client = _get_client()
    if client is None:
        return "My AI module is offline. Please check your OpenAI API key."
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"I couldn't reach the AI: {e}"


def generate_content(topic: str) -> str:
    """Ask the LLM to write a document on *topic* and return the body text."""
    return ask_llm(topic, system=_CONTENT_SYSTEM)


def fallback(text: str) -> dict | None:
    """
    Classify *text* into a structured intent dict via OpenAI.
    Returns a dict with at least an 'intent' key, or None on failure.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": _INTENT_SYSTEM},
                {"role": "user",   "content": text},
            ],
        )
        raw = response.choices[0].message.content.strip()
        # Strip any accidental markdown code fences
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"{_RE}[ERROR]  Fallback JSON parse: {e}{_RS}")
    except Exception as e:
        print(f"{_RE}[ERROR]  Fallback API: {e}{_RS}")

    return None
