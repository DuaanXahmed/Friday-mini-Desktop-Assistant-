# fallback.py — OpenAI integration (intent classification + general LLM calls)

import json
import re
from config import OPENAI_API_KEY, OPENAI_MODEL

_RE = "\033[91m"; _RS = "\033[0m"

# ---------------------------------------------------------------------------
# Intent classification system prompt
# ---------------------------------------------------------------------------

_INTENT_SYSTEM = """
You are FRIDAY, a sharp and capable AI voice assistant. Your user is your boss.
Given a user utterance, return ONLY a valid JSON object with exactly two keys:
  "intent"   — one of the valid intent names below
  "entities" — an object with the fields for that intent (can be {})

No explanation. No markdown. No code fences. Just raw JSON.

Valid intents and their entity fields:
  generate_file         — { "topic": "<what to write about>", "filename": "<optional>" }
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
  general_query         — { "answer": "<your answer, spoken naturally, addressed to boss>" }

Disambiguation rules:
- generate_file: user wants AI to WRITE content and save it. ("write a file about X", "create a doc on X")
- create_file: blank file only — no content generation. User gives a specific name.
- delete_all_files: "delete all", "clear everything", "wipe workspace", "fresh start".
- delete_multiple_files: user names 2+ specific files.
- close_app: user wants an app CLOSED. Never route "close X" to open_app.
- open_app: user wants an app LAUNCHED.
- tell_datetime: user asks for BOTH date AND time.
- system_status: user wants full CPU + battery report.
- general_query: anything factual, conversational, analytical, creative, or definitional.
  Write the answer as FRIDAY speaking directly to boss. Be confident, natural, and clear.
  Simple questions get one punchy sentence. Complex topics can use 3-4 sentences.
  Never say "I don't know" — always give the best informed answer.
  Do NOT add preamble like "Great question" or "Of course". Just answer.
""".strip()

# ---------------------------------------------------------------------------
# Direct Q&A system prompt (used when intent routing fails or for rich queries)
# ---------------------------------------------------------------------------

_QA_SYSTEM = (
    "You are FRIDAY, a sharp and capable personal AI voice assistant. "
    "Your user is your boss — address them as 'boss' naturally in your replies. "
    "Answer questions directly, confidently, and conversationally. "
    "Match answer length to the question: one sentence for simple facts, "
    "a few sentences for complex topics. "
    "No markdown, no bullet points, no numbered lists — clean spoken language only. "
    "Never start with 'Great question' or 'Of course'. Just answer."
)

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

def ask_llm(prompt: str, system: str = _QA_SYSTEM) -> str:
    """Send a prompt to the LLM and return the plain-text reply."""
    client = _get_client()
    if client is None:
        return "My AI module is offline, boss. Please check your OpenAI API key."
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
        return f"I couldn't reach the AI, boss: {e}"


def generate_content(topic: str) -> str:
    """Ask the LLM to write a document on *topic* and return the body text."""
    return ask_llm(topic, system=_CONTENT_SYSTEM)


def fallback(text: str) -> dict | None:
    """
    Classify *text* into a structured intent dict via OpenAI.

    Always returns {"intent": ..., "entities": {...}} or None on total failure.
    If intent classification produces malformed JSON, falls back to a direct
    Q&A call so the user still gets a useful answer.
    """
    client = _get_client()
    if client is None:
        return None

    # ── Step 1: attempt intent classification ────────────────────────────────
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
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)

        intent   = data.get("intent")
        entities = data.get("entities", {})

        if not intent:
            raise ValueError("LLM returned JSON without an intent key")

        # Normalise: if the LLM put entity keys at the top level instead of
        # nesting them under "entities", lift them out properly.
        if not isinstance(entities, dict):
            entities = {}
        if not entities:
            entities = {k: v for k, v in data.items() if k != "intent"}

        return {"intent": intent, "entities": entities}

    except json.JSONDecodeError as e:
        print(f"{_RE}[WARN]   Fallback JSON parse failed ({e}) — trying direct Q&A{_RS}")

    except ValueError as e:
        print(f"{_RE}[WARN]   Fallback intent missing ({e}) — trying direct Q&A{_RS}")

    except Exception as e:
        print(f"{_RE}[ERROR]  Fallback API: {e}{_RS}")
        return None

    # ── Step 2: direct Q&A as last resort ────────────────────────────────────
    try:
        answer = ask_llm(text)
        return {"intent": "general_query", "entities": {"answer": answer}}
    except Exception as e:
        print(f"{_RE}[ERROR]  Direct Q&A fallback: {e}{_RS}")

    return None
