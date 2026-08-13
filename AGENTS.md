# Whisper Dictation — Agent Guide

## Project Overview

Voice-controlled keyboard, AI agent chat, webcam, image generation, and voice control system for Linux. Designed to run on low-end hardware (>= 4 GiB VRAM). With the right models, all features can run concurrently on an old laptop from 2013.

**License:** GNU GPL v2 — all files carry the standard GPL header with `Henry Kroll III <nospam@thenerdshow.com>` copyright.

## Essential Commands

```bash
# Run the main dictation client (requires whisper-server running)
./ship_commander.py

# Record audio (standalone voice recorder with VU meter)
./modules/record.py [file_name.wav] [-options]

# Start the whisper.cpp STT server (prerequisite)
whisper-server -l en -m $MODELS_DIR/ggml-tiny.en.bin --convert --port 7777

# Install dependencies
pip install -r requirements.txt
```

No build system, Makefile, or test framework — pure Python scripts with a `requirements.txt`.

## Service Dependencies

The system depends on **external servers running in background** (not included in this repo):

| Service | Binary | Purpose | Default Port |
|---|---|---|---|
| [whisper.cpp](https://github.com/ggerganov/whisper.cpp) | `whisper-server` | Speech-to-text | 7777 |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | `llama-server` | Local LLM chat & embeddings | 8080 |
| [stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | `webui.sh --api` | Image generation | 7860 |

`whisper_server` and `llama.cpp` are compiled from source (CUDA optional). The Python scripts are stateless clients that POST/GET to these HTTP APIs.

## Architecture & File Layout

```
whisper_dictation/
├── ship_commander.py        # MAIN ENTRY POINT: dictation + agent loop (two-mode routing)
├── modules/
│   ├── record.py            # Hands-free GStreamer audio recorder with VU meter
│   ├── on_screen.py         # Webcam viewer using GStreamer + PIL
│   ├── input_backend.py     # Wayland input simulation (evdev, PyAutoGUI-compatible API)
│   ├── sdapi.py             # Stable Diffusion image generation client
│   ├── browse_webcam.py     # Flask web gallery for webcam images
│   ├── commands_table.py    # User-editable command definitions (intent → handler)
│   ├── matcher.py           # Semantic command matching engine (all-MiniLM-L6-v2)
│   ├── config.py            # Config loader, first-run prompts, provider discovery
│   ├── tui.py               # Rich-based terminal UI (transcription log + status bar + VU meter)
│   ├── tool_manager.py      # Claude/OpenAI-format tool loading, normalization, dispatch
│   ├── skill_manager.py     # Agent Skills standard loader & injector
│   ├── project_scanner.py   # Scan project directory and generate AGENTS.md
│   ├── system_info.py       # OS/platform detection utility
│   └── __init__.py          # Package marker
├── tools/
│   ├── search_web.json      # Example tool — web search via browser
│   └── write_file.json      # Example tool — create or write files
├── camera-shutter.oga       # Shutter sound effect for webcam
├── noise.prof               # Noise profile (likely from audio processing)
├── requirements.txt         # Pip dependencies
├── AGENTS.md                # This file
├── README.md                # Full user-facing documentation
├── webcam/                  # Captured webcam images
├── extras/
│   ├── ad.md                # Advertisement/gallery pitch
│   ├── say                  # Alternative TTS client (appsrc-based, standalone)
│   └── print_pipeline.py    # GStreamer pipeline debugging utility
└── tests/
    ├── test.py              # Chat completion test (calls localhost:5000)
    ├── test_cuda.py         # CUDA/cuDNN/onnxruntime availability check
    ├── testv.py             # Vision API test (llava-phi-3 via OpenAI-compatible API)
    ├── chopt.py             # HuggingFace text generation test
    ├── dummy_server.py      # Flask dummy server for chat testing
    └── simple_recorder.py   # Simplified GStreamer recorder (educational/reference)
```

## Control Flow — two-mode routing cascade

1. **`ship_commander.py`** is the main entry point. It:
   - Starts a background thread (`record_to_queue`) that continuously runs `delayRecord` (from `modules/record.py`)
   - Each completed recording file is pushed onto `audio_queue`
   - The main thread (`transcribe()`) reads files from the queue, sends them to `whisper-server` via HTTP POST, then routes the recognized text through a **three-stage cascade**:

```
Transcript → semantic matcher → matched? → run handler (fast path)
                              → no match, in agent mode (chatting=True)? → LLM with tool fallthrough
                              → no match, in dictation mode (listening=True)? → pyautogui.write()
```

2. **Two modes**
   - **Dictation mode** (`listening=True`, `chatting=False`): text is written directly via `pyautogui.write()`. No LLM involved — the fast path.
   - **Agent mode** (`chatting=True`): text goes to the LLM (OpenAI → Gemini → local llama.cpp), which can chat or trigger tools. A "resume dictation" command switches back to dictation mode.

3. **Semantic fast-path** sits between them: common commands (open terminal, copy that, search the web) are matched by the embedding-based `Matcher` in ~50ms, bypassing the LLM entirely. Commands are defined in `modules/commands_table.py` as `{intent, handler}` pairs — no regex, no `eval()`.

4. **Record → Queue → Transcribe pipeline:**
   - `delayRecord` (in `modules/record.py`) uses GStreamer to listen for sound above threshold, pre-records into a delay buffer, and saves audio when sustained sound is detected
   - `audio_queue` (Python `queue.Queue`) buffers recordings for the transcription thread
   - Transcription happens via HTTP POST to `whisper_cpp` server at `http://127.0.0.1:7777/inference`

5. **AI Chat fallback chain:**
   - OpenAI (requires `OPENAI_API_KEY`)
   - Google Gemini (requires `GENAI_TOKEN`)
   - Local llama.cpp server (`http://127.0.0.1:8080/v1`)

## Command Routing System — semantic matching + LLM fallthrough

Voice commands are routed through a semantic matching engine (`modules/matcher.py`) instead of regex or `eval()`. The engine converts spoken text to an embedding vector and finds the closest command by cosine similarity.

**How it works:**

1. **`modules/commands_table.py`** defines all commands as `{intent, handler, argument}` entries. Intents are plain English phrases like "open terminal" or "copy selection".
2. **`modules/matcher.py`** pre-computes embeddings for all intent phrases (via llama.cpp's `/v1/embeddings` endpoint) and caches them to disk. At match time, it embeds the spoken text and picks the best match above a threshold (default 0.45).
3. **`HANDLER_MAP`** in `ship_commander.py` maps handler names (e.g., `"open_terminal"`, `"hotkey_copy"`) to actual Python functions.
4. If nothing matches and `chatting=True`, the text is sent to the LLM (OpenAI → Gemini → local llama.cpp).

## Tool System — LLM function calling from Claude/OpenAI tool definitions

Tools let the LLM perform actions (search, generate images, run scripts) via structured function calling. The system supports both **Claude-format** (`name`/`description`/`input_schema`) and **OpenAI-format** (`type: "function"`/`function: {name, parameters}`) tool definitions.

**How it works:**

1. **`modules/tool_manager.py`** scans `~/.config/whisper_dictation/tools/*.json` at startup, normalizes each file to an internal format, and passes the definitions to the LLM via the `tools` parameter in the API call.
2. **Built-in tools** are registered in code (e.g., `image_gen` → `draw_picture()`). User-installed tool JSON files can include a `handler_code` field with inline Python that gets compiled on load.
3. **In `generate_text()`**, when the LLM returns a `msg.tool_calls`, the tool manager routes each call to its registered handler. Results are spoken via TTS.
4. **Text-mode LLMs** that can't do real function calling can still invoke image generation by returning `{"action": "image_gen", "action_input": {"prompt": "..."}}` as text.

**Adding tools:**

Drop a `.json` file in `~/.config/whisper_dictation/tools/`:

```json
{
  "name": "tool_name",
  "description": "What the tool does",
  "input_schema": {
    "type": "object",
    "properties": {
      "param": {"type": "string", "description": "The parameter"}
    },
    "required": ["param"]
  },
  "handler_code": "def handler(args):\n    import webbrowser\n    webbrowser.open('https://example.com?q=' + args['param'])"
}
```

The `handler_code` Python source can define `handler(args: dict) -> str | None`. The return value is spoken aloud. Symlinking existing Claude/OpenAI tool definition files into the tools directory works as long as the format is recognized.

**Key design decisions:**
- **No regex, no `eval()`** — the old regex/eval approach was replaced by semantic embeddings. Commands match by meaning, not exact phrasing.
- **Fast path for common actions** — commands like "new paragraph", "copy that", "open terminal" are handled in ~50ms without any LLM round trip.
- **LLM as general-purpose agent** — when the matcher doesn't find a match, the LLM handles it. This covers chat, research questions, and anything not in the command table.
- **Wake words** are "Peter", "Samantha", or "Computer" (e.g., "Computer, open terminal"). They're stripped before matching by `modules/matcher._strip_wake_words()`.
- **User-editable** — add or change commands by editing `modules/commands_table.py`. No main program changes needed.

**The `generate_text` function** handles tool calls from the LLM: if the response includes `tool_calls`, each one is dispatched via `exec_tool()`, results are appended as tool-role messages, and the LLM is re-called with the full context.

## Embeddings & Router Mode

Semantic command matching requires llama.cpp's `/v1/embeddings` endpoint (default port 8080). Two setups:

- **Same-server** — chat model handles embeddings too. Start `llama-server` with `--embeddings`. `embed_model` stays `""` (no model name sent in request).

- **Router mode** — dedicated embedding model (e.g. `all-MiniLM-L6-v2.Q8_0.gguf`) on the same server, defined in `models.ini`. Set `embed_model` to the model name so the matcher sends it in every `/v1/embeddings` request.

See `~/.config/whisper_dictation/config.json` for `embed_url` / `embed_model`, or override at runtime: `export EMBED_URL=...` / `export EMBED_MODEL=...`.

## Input Backends

- **Wayland** (`XDG_SESSION_TYPE=wayland`): Uses `modules/input_backend.py` (`InputSimulator` class via `python-evdev`). Requires udev rule for `/dev/uinput` and `input` group membership.
- **X11** (default): Uses `PyAutoGUI`.

The backend is selected at import time in `ship_commander.py` (lines 26-30):
```python
if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
    from modules.input_backend import InputSimulator
    pyautogui = InputSimulator()
else:
    import pyautogui
```

`modules/input_backend.py` mirrors PyAutoGUI's API (`write`, `hotkey`, `click`, `rightClick`, `middleClick`, `prompt`).

## Code Conventions

- **Shebang:** `#!/usr/bin/python` (NOT `#!/usr/bin/env python3`)
- **Encoding:** `# -*- coding: utf-8 -*-` on all `.py` files
- **Comment style:** Block headers use `##` (double hash), inline comments use `#`
- **Copyright header:** Every `.py` file has the full GPL boilerplate with Henry Kroll III copyright
- **Naming:** `snake_case` for functions and variables, `CamelCase` for classes, `UPPER_CASE` for string constants
- **Type hints:** Sparse but present on some function signatures (e.g., `def match(text: str, threshold=None)`)
- **Imports:** Standard library first, then third-party, then local. Within-file conditional imports for optional dependencies (e.g., `google.generativeai`, `evdev`)
- **Indentation:** Tabs (width 4). `logging.basicConfig` blocks use tabs. Pipeline strings use spaces.
- **Error handling:** Generally exception-catch-and-log, rarely re-raises. Uses `logging` module throughout (INFO level by default). Optional file handlers are commented out.
- **`__name__ == '__main__'` guards:** Present on all modules that can run standalone

## Testing

No formal test framework (no pytest, unittest, etc.). The `tests/` directory contains:
- **Manual/integration test scripts** that require running services (whisper-server, llama.cpp, etc.)
- **`test_cuda.py`** — Quick CUDA availability check
- **`testv.py`** — Vision/LLaVA model test via OpenAI-compatible API
- **`simple_recorder.py`** — Simplified version of `delayRecord` for learning/reference

To validate changes: run the script directly and verify behavior. There are no automated CI tests in this repo.

## Logging Convention

All modules use the same pattern:
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(lineno)d %(message)s",
    handlers=[
        # logging.FileHandler('/tmp/some_name.log'),
        logging.StreamHandler()
    ]
)
```

The `bs` variable (`ANSI_clear_line()` return value) is used as a prefix in log messages to clear the terminal line before printing.

## GStreamer Patterns

The project uses GStreamer extensively via `gi.repository` (PyGObject):

- **Audio recording** (`modules/record.py`): Pipeline like `autoaudiosrc ! tee ! ladspa-delay ! valve ! audioconvert ! queue ! audioresample ! encoder ! filesink`. The valve controls when audio is actually written. Sound level monitoring uses the `level` element.
- **Webcam** (`modules/on_screen.py`): `autovideosrc ! tee ! videoconvert ! autovideosink` with valve-controlled JPEG capture

The LADSPA delay plugin (`ladspa-delay-1898-so-delay-l`) is critical for pre-recording — it keeps a rolling buffer so no speech is lost while the VU meter detects sustained sound. Without it (or the `swh-plugins` package), recording won't work.

## Terminal UI (Rich)

`modules/tui.py` provides a live Rich-based interface (`TUI` class) that replaces bare `print()` calls. It auto-degrades to plain `print()` when `rich` is not installed, so the app works either way.

**What it shows:**

- **Transcription Log panel** — timestamped, color-coded entries for dictation (white), commands (yellow), LLM replies (cyan), errors (red), system messages (dim), and voice prompts (green).
- **Status bar** — mode indicator (🟢 dictating / 🟡 agent/paused), active model name, live VU bar from the GStreamer recorder, and last command match score.
- **Numbered tables** — providers, models, custom commands, and skills display as formatted Rich tables instead of raw `print()` lines.

**VU meter wiring** — `delayRecord.__init__()` accepts an optional `vu_callback(rms_normalised_0to1, rms_db)` parameter. `ship_commander.py` passes `tui.set_vu` so the status bar shows a live audio level bar during recording.

```python
# ship_commander.py
from modules.tui import TUI
tui = TUI()
tui.start()                        # starts Live display thread
tui.dictation("hello world")       # log entry, white
tui.command("open_terminal", 0.87) # log entry, yellow + sets match
tui.set_mode("agent")              # updates status dot
tui.llm("How do I...")             # log entry, cyan
tui.table("Items", ["a", "b"])     # standalone numbered table
tui.stop()                         # stop Live on shutdown
```

## Non-Obvious Details & Gotchas

1. **`conversation_length`** (default 9) controls how many user+assistant message pairs are kept in the LLM chat history. When exceeded, the oldest pair is removed (messages[1] and the new messages[1] after that removal). This is fragile — if you change how messages are structured, this logic breaks.

2. **`manage_whisper_service()`** auto-starts/stops `whisper-server` (via systemd) when the service unit is installed — no manual uncommenting needed.

3. **`audio_format`** (default `.wav`) can be changed to `.ogg` to save network bandwidth when whisper-server is on a different machine.

4. **Wake words** are "Peter", "Samantha", or "Computer" — stripped by `modules/matcher._strip_wake_words()` using `re.compile(r"^(peter|samantha|computer)[,\s]*", re.IGNORECASE)` before semantic matching. This `|` is proper regex alternation, not literal pipe.


5. **`discard_input()`** at shutdown uses `termios.tcflush` or `fcntl` nonblocking reads to drain any buffered terminal input. This prevents stray keystrokes from executing after the program exits.

6. **`shutup()`** in `ship_commander.py` terminates the piper-tts audio player subprocess (`paplay`/`aplay`/`pw-play`) with `.terminate()`, falling back to `.kill()` on timeout. The global `_piper_player` tracks the active process.

7. **`delayRecord.process_options()`** uses `exec()` on dynamically constructed strings to set options via flags. This is a refactoring risk — option processing uses `exec(f"self.{oj}")` where `oj` comes from the `options` dict.

8. **File cleanup safety** — `record_to_queue` generates temp files via `tempfile.mktemp()+.wav`. In `quit()`, files are only deleted if they start with `/tmp/` (safety check).
