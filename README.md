# FRIDAY — AI Voice Assistant

**F**ast **R**esponsive **I**ntelligent **D**igital **A**ssistant for **Y**ou

A voice-controlled Python assistant that wakes on a wake word, understands natural language, and executes commands — locally and through OpenAI.

---

## Architecture

```
Microphone
    │
    ▼
Wake Word Detection  ("friday")
    │
    ▼
Command Capture
    │
    ▼
Multi-Command Splitter  (splits on "and")
    │
    ├──► Keyword Parser  ──► Intent + Entities ──► Execute
    │         │
    │      No Match
    │         │
    └──► OpenAI Fallback ──► Intent + Entities ──► Execute
```

**Parser (fast path)** — zero-latency, zero API cost. Keyword + regex matching against a curated intent map.

**Fallback (smart path)** — only fires when the parser misses. Sends the raw command to OpenAI, which returns a structured `{ intent, entities }` JSON response.

---

## File Structure

```
friday/
├── main.py          # Entry point — two-phase voice loop
├── parser.py        # Keyword + regex intent parser
├── commands.py      # All command functions + router
├── fallback.py      # OpenAI intent classifier + content generator
├── utils.py         # Mic input, TTS output
├── config.py        # Apps, websites, workspace, voice settings
├── voice/
│   ├── __init__.py
│   └── speaker.py   # PiperTTS (local) + PowerShell TTS fallback
├── requirements.txt
├── .env             # OPENAI_API_KEY — never commit this
└── .gitignore
```

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env with your OpenAI key
echo OPENAI_API_KEY=your-key-here > .env

# 3. Run
python main.py
```

The workspace folder (`~/friday_workspace/`) is created automatically on first run. All file operations are sandboxed there.

---

## Wake Word

Say **"Friday"** to activate. FRIDAY responds and waits for your command. After each command it stays active — no need to repeat the wake word. After 3 missed commands it returns to standby.

Say **"Goodbye Friday"** (or any shutdown phrase) to exit cleanly.

---

## Commands

### File Operations

| What you say | What happens |
|---|---|
| `create file` | Asks for name and type (text / PDF / Word) |
| `create a PDF called invoice` | Creates `invoice.pdf` |
| `create a text file called report` | Creates `report.txt` |
| `create files a.txt and b.pdf` | Creates both files |
| `delete report` | Finds and deletes any file named report |
| `delete files a.txt and b.pdf` | Deletes both |
| `delete all files` / `clear workspace` | Wipes the entire workspace |
| `rename report to summary` | Renames, preserves extension |
| `find report` / `search report` | Searches workspace by name |
| `open report` | Opens the file (by name, no extension needed) |

File names can be said with or without extension — FRIDAY resolves them automatically.

### AI File Generation

| What you say | What happens |
|---|---|
| `write a file about machine learning` | AI writes a document, saves to workspace |
| `create a PDF file about finance` | AI generates content, saves as PDF |
| `generate document about solar system` | AI writes, saves as .txt |

### Apps

| What you say | What happens |
|---|---|
| `open chrome` / `launch chrome` | Opens Chrome |
| `open notepad` / `open calculator` | Opens the app |
| `close chrome` / `quit chrome` | Closes all Chrome processes |
| `kill spotify` / `terminate notepad` | Force-closes the app |

Supported apps: Chrome, Cursor, Notepad, Calculator, Camera, Explorer, Task Manager, Spotify, VS Code, Upwork, Paint, Word, Excel.

### Websites

| What you say | What happens |
|---|---|
| `open youtube` / `go to youtube` | Opens in browser |
| `browse to github` / `visit chatgpt` | Opens in browser |

Supported: YouTube, ChatGPT, GitHub, Google, Upwork, Supabase, Siteground.

### Modes

| What you say | What happens |
|---|---|
| `study mode` / `activate study` | Opens ChatGPT + YouTube |
| `work mode` / `activate work` | Opens Upwork, Supabase, GitHub, Siteground |

### System Info

| What you say | What happens |
|---|---|
| `what time` / `tell me the time` | Current time |
| `what date` / `today's date` | Today's date |
| `date and time` | Both together |
| `battery` / `battery percentage` | Battery level + charging status |
| `cpu` / `cpu usage` | CPU usage with health note |
| `system status` / `full system check` | CPU + battery report |

### Screenshot

| What you say | What happens |
|---|---|
| `take screenshot` / `screenshot` | Saves PNG to workspace |

### General Questions

Anything not matching a specific command is sent to OpenAI for a direct answer.

```
"what is quantum computing"
"who invented the internet"
"how do I sort a list in Python"
```

### Shutdown

```
"goodbye Friday"   "bye Friday"   "goodnight"   "go to sleep"
"shut down Friday" "exit Friday"  "that will be all"   "we're done"
```

---

## Multi-Command

Chain commands with **"and"**:

```
"create file notes and open youtube"
"delete report and take a screenshot"
```

---

## Configuration

Edit `config.py` to:
- Add apps to `APPS` and `APP_PROCESS_NAMES`
- Add websites to `WEBSITES`
- Change `WAKE_WORD`
- Adjust mic timeouts (`MIC_TIMEOUT`, `PHRASE_LIMIT`)
- Toggle workspace auto-open (`AUTO_OPEN_WORKSPACE`)

---

## Dependencies

| Package | Purpose |
|---|---|
| `speechrecognition` + `pyaudio` | Microphone input |
| `openai` | Intent classification + content generation |
| `psutil` | CPU, battery, process management |
| `pyautogui` | Screenshots |
| `python-docx` | Word file creation |
| `reportlab` | PDF file creation |
| `sounddevice` + `numpy` | PiperTTS audio playback |
| `python-dotenv` | Loads `.env` |

---

*Built with Python 3.11+ · SpeechRecognition · OpenAI · PiperTTS*
