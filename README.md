# Ship Commander

**The Ship's Computer** - Private voice keyboard, AI agent, images, webcam, recordings, voice control with as little as 4 GiB VRAM.

<img src="img/ss.png" alt="Voice dictation anywhere, even social media." width="300" align="right">

- **Dictation mode** — transcribed speech goes straight to text output (fast, no LLM)
- **Semantic fast-path** — tiny, 250MB embedding-based matcher (`all-MiniLM-L6-v2`) recognizes common commands in ~50ms with no LLM round trip
- **Agent mode** — speech routed through the LLM for chat, tool calling, or learning new commands
- **Updatesitself** — example; say *"Computer, record a 30 second video"* and the LLM proposes a shell command, asks for confirmation, then learns it. So next time you can just run it (with permission).

```
Transcript → semantic matcher → matched? → run tool (fast path)
                              → no match, wake word? → LLM proposes command → approved? → save & run
                              → no match, dictation mode? → write text
```

## Preparation

If setting up manually, run `pip install -r requirements.txt` with or without [optional venv setup](https://python.land/virtual-environments/virtualenv). We are using Python 3.14.5 but that shouldn't matter much.

**Ubuntu / Debian** Install GStreamer and required plugins:

```shell
sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
  swh-plugins python3-gi python3-pip \
  gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0
```

The `gst-plugins-good` package provides `souphttpsrc` required for mimic3 voice output.
The `gst-plugins-bad` package provides LADSPA plugin support for audio effects.
The `swh-plugins` package provides LADSPA delay plugins (`delay_1898.so`) for audio
recording.

**Arch Linux** Install GStreamer and required plugins:

```shell
sudo pacman -S gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad swh-plugins
```

The `gst-plugins-good` package provides `souphttpsrc` required for mimic3 voice output.
The `gst-plugins-bad` package provides LADSPA plugin support for audio effects.
The `swh-plugins` package provides LADSPA delay plugins (`delay_1898.so`) for audio
recording.

**Fedora** Get the [Rpmfusion repos]( http://rpmfusion.org) and install
[GStreamer](https://gstreamer.freedesktop.org/) using `dnf`. It is
necessary for recording temporary audio clips to send to your local `whisper.cpp` speech
to text (STT) server for decoding.
The required `ladspa-delay-so-delay-5s` may be found in the
`gstreamer1-plugins-bad-free-extras` package.

## Wayland

Some distros default to using Wayland now. The app auto-detects `XDG_SESSION_TYPE` and the voice keyboard uses `python-evdev` on Wayland or `PyAutoGUI` on X11. If you are curious about what your system uses, enter `echo $XDG_SESSION_TYPE` into a terminal.

For Wayland, install `python-evdev` to handle the keyboard and set up uinput permissions:
```shell
echo 'KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/99-input.rules
sudo usermod -aG input $USER
```
Then **logout and login** for group membership to take effect.

## Quick start

```shell
git clone -b nl --single-branch https://github.com/themanyone/whisper_dictation.git
cd whisper_dictation
./setup.sh
```

The script downloads pre-built `whisper-server` and `llama-server` binaries, the Whisper tiny model (74 MB), and the recommended **Qwen2.5-7B-Instruct Q4_K_S** (4 GB). It also installs Python deps and offers to create a systemd user service.

## Building from source (GPU acceleration)

The pre-built binaries are CPU-only. For GPU acceleration (recommended), compile from source. Here we are using CUDA. Your options may vary. Review project's build docs.

**whisper.cpp:**
```shell
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
cmake -B build -DGGML_CUDA=1
cmake --build build -j$(nproc) --config Release
cp build/bin/whisper-server build/bin/whisper-cli ~/.local/bin/
```

**llama.cpp:**
```shell
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
cmake -B build -DGGML_CUDA=1
cmake --build build -j$(nproc) --config Release
cp build/bin/llama-server build/bin/llama-cli ~/.local/bin/
```

For Vulkan backend, replace `-DGGML_CUDA=1` with `-DGGML_VULKAN=1`. See the [llama.cpp README](https://github.com/ggml-org/llama.cpp) for other backends.

## Sentence Transformer (semantic command matching)

Voice commands are matched semantically using `all-MiniLM-L6-v2` embeddings served by
`llama-server`'s OpenAI-compatible `/v1/embeddings` endpoint. No separate server needed.

**Option A — enable embeddings with llama.cpp** (works with any model):

```shell
llama-server -m ~/models/qwen2.5-7b-q4_k_s.gguf -ngl 99 -c 4096 --port 8080 --embeddings
```

Simply add `--embeddings` to your `llama-server` command. The embedding endpoint is
available at `http://127.0.0.1:8080/v1/embeddings` alongside the chat endpoint.

Then set `embed_url` to `http://127.0.0.1:8080/v1/embeddings` in
`~/.config/whisper_dictation/config.json` or export `EMBED_URL`.

The matcher pre-computes intent embeddings at startup and caches them to
`~/.config/whisper_dictation/embeddings_cache.json` — no round-trip cost on subsequent runs.

**Option B — router mode** (One server handles multiple LLM(s) + embeddings):

No need to add the `--embeddings` flag. The llama-server's router mode can launch the `/v1/embeddings` endpoint alongside other models by defining them in the `models.ini` file with `embedding=true`. Example `models.ini`:

```shell
[*]
jinja = true

[all-MiniLM-L6-v2.Q8_0]
embedding = true
load-on-startup = true
sleep-idle-seconds = -1

[Qwen2.5-Omni-7B-IQ4_XS]
fa = off
ctx-size = 16384
ub = 16384
```

To launch `llama-server` in router mode, see docs. Something like this might work. Change ports if you want. Just make sure they match your configuration.

```shell
llama-server --jinja --models-dir $MODELS_DIR --models-preset $MODELS_DIR/.models.ini --host 0.0.0.0 --port 8080 --no-warmup --models-max 1 --sleep-idle-seconds 420 -t 6 -fa on -np 1 --kv-unified --no-mmproj-offload
```

**Testing** Manually start servers. Model should support agentic tool calling if you want to use those capabilities.

```shell
# Terminal 1 — speech-to-text
whisper-server -l en -m ~/models/ggml-tiny.en.bin --convert --port 7777

# Terminal 2 — any model can test embeddings for semantic commands
llama-server -m ~/models/qwen2.5-7b-q4_k_s.gguf -ngl 99 -c 4096 --port 8080 --embeddings

# Terminal 3 — test dictation client
./ship_commander.py
```

Before blaming us, test embeddings, chat endpoints like so.

```shell
curl -X POST "http://localhost:8080/v1/embeddings" -H "Content-Type: application/json" -d '{
  "model": "all-MiniLM-L6-v2.Q8_0",
  "input": "This is some text to embed."
}'

curl -X POST "http://127.0.0.1:8080/v1/chat/completions" -H "Content-Type: application/json" -d '{
   "model": "gpt-3.5-turbo",
   "messages": [{
      "role":"user",
      "content":"What is the capital of France?"
   }],
   "temperature":0.1,"max_tokens":200
}'
```

## Provider configuration

The config file, `~/.config/whisper_dictation/config.json` stores available LLM backends and their API keys, embeddings endpoint, etc. You can edit `~/.config/whisper_dictation/config.json` or delete it and be prompted for new configurations. Switch providers any time by saying **"Switch provider"** — you'll be prompted to select one by number, then pick a model from that provider. You can also say, **"Switch model"**. This will modify your config.json for you.

Override the active provider with environment: `export PROVIDER=OpenAI`.

> **Editing defaults:** The provider list above ships as `default_config.json` in the repo root. Edit it freely to add your API keys — it's in `.gitignore` so you can't accidentally `git push` secrets. If the file doesn't exist it's auto-created from built-in defaults on first run.

The client auto-detects provider type from the URL and fixes the API path automatically. For example, `https://generativelanguage.googleapis.com` is corrected to `https://generativelanguage.googleapis.com/v1beta/openai/` (Gemini's OpenAI-compatible endpoint). When switching providers at runtime, the client probes the `/v1/models` endpoint to discover available models and sniffs the provider type from model IDs.

### Full config reference

Settings are saved to `~/.config/whisper_dictation/config.json`. Environment variables override file values at runtime:

| Key | Env var | Default | Description |
|---|---|---|---|
| `whisper_url` | `WHISPER_URL` | `http://127.0.0.1:7777/inference` | whisper.cpp STT endpoint |
| `provider` | `PROVIDER` | `llama.cpp` | Active provider name (must match `providers[].name`) |
| `chat_url` | `CHAT_URL` | *(from active provider)* | LLM server URL |
| `model` | `CHAT_MODEL` | `gpt-3.5-turbo` | Model name for LLM |
| `embed_url` | `EMBED_URL` | `http://127.0.0.1:8080/v1/embeddings` | Embeddings endpoint |
| `embed_model` | `EMBED_MODEL` | *(empty)* | Required only in router mode |
| `threshold` | — | `0.45` | Semantic match confidence (0.0–1.0) |
| `conversation_length` | — | `9` | Max user/assistant pairs in chat history |
| `audio_format` | — | `.wav` | Recording format (`.wav` or `.ogg`) |
| `debug` | `DEBUG` | `false` | Verbose debug logging |
| `piper_model` | `PIPER_MODEL` | *(auto-detect)* | Path to piper `.onnx` voice file |
| `piper_voice` | `PIPER_VOICE` | `en_US-libritts_r-medium` | Piper voice name |

Edit or delete `~/.config/whisper_dictation/config.json` to reset.

**Layout is subject to change** as development progresses. After updating, look to in `config.py` for `DEFAULT_CONFIG` or delete (regenerate) `default_config.json` from it to see what your `~/.config/whisper_dictation/config.json` should look like. Or delete `~/.config/whisper_dictation/config.json` and be prompted from the defaults.

## Spoken command usage

Say **"Computer"**, **"Samantha"**, or **"Peter"** as "wake words" to trigger the agent. Example commands:

- Computer, open terminal / open a web browser / go to *website*
- Computer, on screen / take a picture / off screen (webcam)
- Computer, record audio
- Computer, draw a picture of *subject* (stable-diffusion)
- Computer, add a command to launch Thunderbird when I say 'check email.'"
    Unnecessary. Saying launch [app name] already launches apps.
    But you can create other commands this way.

**Editing commands** do not require a wake word.
- Copy that / Paste it / Undo that
- Page up / Page down
- New paragraph / Pause dictation / Resume dictation
- Stop dictation (quits)

Types of built-in commands include
* Mouse actions (editing  no wake word)
* Launch apps (argument = which app to open)
* Terminal
* Navigation & window control
* Web search (argument = search query)
* Email (argument = recipient)
* Image generation (argument = prompt)
* Dictation control (no wake word)
* Recording
* Webcam
* Keyboard shortcuts (editing - no wake word)
* Provider / AI model selection
* AI chat - "Computer, what's the capital of Zimbabwe?"
* AI agent - "Computer, (perform some unknown command)"
    Asks AI agent what to do.
    Builds new command.
    Gets permissionto run it.

Commands are defined in [commands_table.py](commands_table.py) — add your own or change existing ones freely. New commands learned by the agent persist in [custom_commands.json](~/.config/whisper_dictation/custom_commands.json). To unlearn a command, say "Computer, remove command."

## Tool calling

"Tools do stuff. Skills know stuff." Tools let the LLM perform actions (search, generate images, run scripts) via structured function calling. The system supports both **Claude format** (`name`, `description`, `input_schema`) and **OpenAI format** (`type: "function"`, `function: {name, parameters}`).

**How it works**

1. At startup, `tool_manager.py` scans `~/.config/whisper_dictation/tools/*.json`
2. Each file is normalized and injected into the LLM's `tools` parameter
3. When the LLM returns a function call, the tool routes it to the registered handler
4. Results are spoken aloud via TTS

### Adding tools

Drop a `.json` file in `~/.config/whisper_dictation/tools/`:

```json
{
  "name": "search_web",
  "description": "Search the web for information",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "The search query"}
    },
    "required": ["query"]
  },
  "handler_code": "def handler(args):\n    import webbrowser\n    q = args['query'].replace(' ', '%20')\n    webbrowser.open('https://duckduckgo.com/?q=' + q)\n    return f'Searching for {args[\"query\"]}'"
}
```

### Download example tools

The repo ships with example tool definitions but you can put custom ones in `~/.config/whisper_dictation/tools/`

**Built-in tools** generate images via Stable Diffusion, search the web, edit files...

### Handler code

The optional `handler_code` field contains inline Python defining a `handler(args: dict) -> str | None`. The return value is spoken by TTS. If omitted, you must register a handler via `tool_manager.register_handler(name, callable)` elsewhere.

## Skills

Skills follow the [Agent Skills open standard](https://agentskills.io) — the same format used by Crush, Claude Code, and other agents. Skills give the LLM specialized instructions and domain knowledge on demand.

Unlike **tools** (callable functions), **skills** tell the agent how to do things. Just say what you want to do and if the intent matches a skill, the LLM will review it for the session.

### Progressive disclosure

1. **Catalog**: At startup, the LLM sees each skill's name + description (~50-100 tokens each)
2. **Activation**: When the LLM calls `load_skill("skill-name")`, the full SKILL.md body is loaded into context
3. **Resources**: Scripts, references, and assets in the skill directory are available when the instructions reference them

### Where skills live

Two scan paths are checked (first path wins for name collisions):

| Path | Purpose |
|---|---|
| `~/.agents/skills/` | Cross-client standard (shared with any Agent Skills-compatible client) |
| `~/.config/whisper_dictation/skills/` | Client-specific |

Each skill is a **subdirectory** containing a `SKILL.md` file:

```
~/.agents/skills/
├── pdf-processing/
│   ├── SKILL.md          ← YAML frontmatter + Markdown instructions
│   ├── scripts/          ← Optional executable code
│   ├── references/       ← Optional reference docs
│   └── assets/           ← Optional templates/resources
└── data-analysis/
    └── SKILL.md
```

### Installing skills

Symlink or copy existing Crush/Claude skills (their `SKILL.md` files work as-is):

```shell
mkdir -p ~/.agents/skills
ln -s ~/.config/crush/skills/claude-api ~/.agents/skills/
cp -r ~/.config/crush/skills/pdf ~/.agents/skills/
```

On startup you'll see:

```
Loaded 2 skill(s): claude-api, pdf
```

### SKILL.md format

Each `SKILL.md` has YAML frontmatter (between `---` delimiters) with at least `name` and `description`, followed by the Markdown instructions:

```yaml
---
name: pdf-processing
description: Extract PDF text, fill forms, merge files. Use when handling PDFs.
---

Full instructions for the LLM go here...
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Identifies the skill. Lowercase, hyphens, max 64 chars. |
| `description` | Yes | Non-empty, max 1024 chars. When to activate this skill. |
| `license` | No | License reference. |
| `compatibility` | No | Environment requirements. |
| `metadata` | No | Arbitrary key-value pairs. |

**File** | **Purpose**
---|---
`skill_manager.py` | Discover, parse, and activate skills via the Agent Skills standard

## Files

| File | Purpose |
|---|---|
| `ship_commander.py` | Main dictation loop, chat, voice commands |
| `commands_table.py` | User-editable command table (intent → handler) |
| `matcher.py` | Semantic matching engine (all-MiniLM-L6-v2) |
| `config.py` | Config loader, first-run prompts, provider discovery |
| `record.py` | Sound-activated GStreamer audio recorder |
| `on_screen.py` | Webcam viewer and capture |
| `sdapi.py` | Stable Diffusion image generation client |
| `browse_webcam.py` | Flask web gallery for captured webcam images |
| `input_backend.py` | Wayland input simulation (evdev) |
| `tool_manager.py` | Load and dispatch Claude/OpenAI-format tools |
| `skill_manager.py` | Load and inject skills into the LLM system prompt |
| `project_scanner.py` | Scan project directory and generate AGENTS.md |
| `system_info.py` | OS/platform detection utility |
| `setup.sh` | Quick-start installer (downloads binaries, creates service) |
| `tools/search_web.json` | Example tool — web search via browser |
| `tools/write_file.json` | Example tool — create or write files |

## Optional services

- **ChatGPT** — `export OPENAI_API_KEY=<key>`
- **Google Gemini** — `export GENAI_TOKEN=<key>`; `pip install google-generativeai`
- **Stable Diffusion** — start `webui.sh --api --medvram` on the server for image generation or set up [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp). Configure it by editing `sdapi.py` in this project (it's a small file).

## Voice responses

Samantha speaks answers using **Piper TTS** (`pip install piper-tts`). On first run you'll be prompted to download a voice (~15 MB). Configure in `~/.config/whisper_dictation/config.json`:

- `piper_model` — explicit path to a `.onnx` voice file (takes priority)
- `piper_voice` — voice name to look up in `$XDG_CACHE_HOME/piper/{voice}.onnx` (default `en_US-libritts_r-medium`)

Or override at runtime: `export PIPER_VOICE=en_US-amy-medium`.

## Troubleshooting

- If whisper-server is slow or refuses to use VRAM, try `sudo modprobe -r nvidia_uvm && sudo modprobe nvidia_uvm`
- The whisper-server must be started with `--convert` for .mp3 input support
- Edit `~/.config/whisper_dictation/config.json` to change server addresses/ports
- Test the pipeline: `curl http://localhost:7777/inference -F "file=@test.wav;type=audio/wav"`

## Thanks for trying out Whisper Dictation!

- GitHub https://github.com/themanyone
- YouTube https://www.youtube.com/themanyone
- Mastodon https://mastodon.social/@themanyone
- [TheNerdShow.com](http://thenerdshow.com/)

Copyright (C) 2023-2026 Henry Kroll III, www.thenerdshow.com.
See [LICENSE](LICENSE) for details.
