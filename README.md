# Whisper Dictation

**The Ship's Computer** - Private voice keyboard, AI agent, images, webcam, recordings, voice control in >= 4 GiB VRAM.

<img src="img/ss.png" alt="Dictation anywhere, even social media." width="300" align="right">

- **Dictation mode** — transcribed speech goes straight to text output (fast, no LLM)
- **Agent mode** — speech routed through the LLM for chat, tool calling, or learning new commands
- **Semantic fast-path** — embedding-based matcher (`all-MiniLM-L6-v2`) recognizes common commands in ~50ms with no LLM round trip
- **Updatesitself** — example; say *"Computer, record a 30 second video"* and the LLM proposes a shell command, asks for confirmation, then learns it. So next time you can just run it (with permission).

```
Transcript → semantic matcher → matched? → run tool (fast path)
                              → no match, wake word? → LLM proposes command → approved? → save & run
                              → no match, dictation mode? → write text
```

## Preparation

If setting up manually, run `pip install -r requirements.txt`

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

## Quick start

```shell
git clone -b nl --single-branch https://github.com/themanyone/whisper_dictation.git
cd whisper_dictation
./setup.sh
```

The script downloads pre-built `whisper-server` and `llama-server` binaries, the Whisper tiny model (74 MB), and the recommended **Qwen2.5-7B-Instruct Q4_K_S** (4 GB). It also installs Python deps and offers to create a systemd user service.

Then start both servers and the client:

```shell
# Terminal 1 — speech-to-text
whisper-server -l en -m ~/models/ggml-tiny.en.bin --convert --port 7777

# Terminal 2 — LLM agent with embeddings for semantic commands
llama-server -m ~/models/qwen2.5-7b-q4_k_s.gguf -ngl 99 -c 4096 --port 8080 --embeddings

# Terminal 3 — dictation client
./whisper_cpp_client.py
```

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

Before blaming us, test your embeddings endpoint like so.

```shell
curl -X POST "http://localhost:8080/v1/embeddings" -H "Content-Type: application/json" -d '{
  "model": "all-MiniLM-L6-v2.Q8_0",
  "input": "This is some text to embed."
}'
```

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

## Provider configuration

The `providers` list in `~/.config/whisper_dictation/config.json` stores available LLM backends and their API keys. The active provider is selected by the `provider` key (name match). Defaults:

```json
{
  "provider": "llama.cpp",
  "providers": [
    {
      "name": "llama.cpp",
      "base_url": "http://127.0.0.1:8080/v1",
      "api_key": "sk-no-key-required",
      "provider_type": "llamacpp"
    },
    {
      "name": "OpenAI",
      "base_url": "https://api.openai.com/v1",
      "api_key": "",
      "provider_type": "openai"
    },
    {
      "name": "xAI Grok",
      "base_url": "https://api.x.ai/v1",
      "api_key": "",
      "provider_type": "openai"
    },
    {
      "name": "OpenRouter",
      "base_url": "https://openrouter.ai/api/v1",
      "api_key": "",
      "provider_type": "openai"
    },
    {
      "name": "Google Gemini",
      "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
      "api_key": "",
      "model": "gemini-2.0-flash",
      "provider_type": "gemini"
    },
    {
      "name": "Anthropic Claude",
      "base_url": "https://api.anthropic.com/v1",
      "api_key": "",
      "model": "claude-sonnet-4-20250514",
      "provider_type": "anthropic"
    },
    {
      "name": "Groq",
      "base_url": "https://api.groq.com/openai/v1",
      "api_key": "",
      "provider_type": "openai"
    },
    {
      "name": "Together AI",
      "base_url": "https://api.together.ai/v1",
      "api_key": "",
      "provider_type": "openai"
    },
    {
      "name": "DeepInfra",
      "base_url": "https://api.deepinfra.com/v1/openai",
      "api_key": "",
      "provider_type": "openai"
    },
    {
      "name": "DeepSeek",
      "base_url": "https://api.deepseek.com/v1",
      "api_key": "",
      "provider_type": "openai"
    },
    {
      "name": "Mistral AI",
      "base_url": "https://api.mistral.ai/v1",
      "api_key": "",
      "provider_type": "openai"
    },
    {
      "name": "Perplexity",
      "base_url": "https://api.perplexity.ai",
      "api_key": "",
      "provider_type": "openai"
    },
    {
      "name": "Fireworks AI",
      "base_url": "https://api.fireworks.ai/inference/v1",
      "api_key": "",
      "provider_type": "openai"
    },
    {
      "name": "AIHubMix",
      "base_url": "https://aihubmix.com/v1",
      "api_key": "",
      "provider_type": "openai"
    },
    {
      "name": "Ollama",
      "base_url": "http://127.0.0.1:11434/v1",
      "api_key": "sk-no-key-required",
      "provider_type": "ollama"
    }
  ]
}
```

Populate API keys in the `api_key` field of each provider entry. The active provider's `base_url` is used as `chat_url` on startup; if the entry has a `model` key it overrides `chat_model` automatically. Switch providers at runtime by saying **"Computer, switch provider"** — you'll be prompted to select one by number, then pick a model from that provider.

Override the active provider at runtime: `export PROVIDER=OpenAI`.

The client auto-detects provider type from the URL and fixes the API path automatically. For example, `https://generativelanguage.googleapis.com` is corrected to `https://generativelanguage.googleapis.com/v1beta/openai/` (Gemini's OpenAI-compatible endpoint). When switching providers at runtime, the client probes the `/v1/models` endpoint to discover available models and sniffs the provider type from model IDs.

### Full config reference

Settings are saved to `~/.config/whisper_dictation/config.json`. Environment variables override file values at runtime:

| Key | Env var | Default | Description |
|---|---|---|---|
| `whisper_url` | `WHISPER_URL` | `http://127.0.0.1:7777/inference` | whisper.cpp STT endpoint |
| `provider` | `PROVIDER` | `llama.cpp` | Active provider name (must match `providers[].name`) |
| `chat_url` | `CHAT_URL` | *(from active provider)* | LLM server URL |
| `chat_model` | `CHAT_MODEL` | `gpt-3.5-turbo` | Model name for LLM |
| `embed_url` | `EMBED_URL` | `http://127.0.0.1:8080/v1/embeddings` | Embeddings endpoint |
| `embed_model` | `EMBED_MODEL` | *(empty)* | Required only in router mode |
| `threshold` | — | `0.45` | Semantic match confidence (0.0–1.0) |
| `conversation_length` | — | `9` | Max user/assistant pairs in chat history |
| `audio_format` | — | `.wav` | Recording format (`.wav` or `.ogg`) |
| `debug` | `DEBUG` | `false` | Verbose debug logging |
| `piper_model` | `PIPER_MODEL` | *(auto-detect)* | Path to piper `.onnx` voice file |
| `piper_voice` | `PIPER_VOICE` | `en_US-libritts_r-medium` | Piper voice name |

Edit or delete `~/.config/whisper_dictation/config.json` to reset.

**Layout is subject to change** as development progresses. After updating, look in `config.py` for `DEFAULT_CONFIG` to see what your config file should look like.

## Wayland

Some distros default to using Wayland now. The app auto-detects `XDG_SESSION_TYPE` and uses `python-evdev` on Wayland or `PyAutoGUI` on X11. If you are curious about what your system uses, enter `echo $XDG_SESSION_TYPE` into a terminal.

For Wayland, install `python-evdev` to handle the keyboard and set up uinput permissions:
```shell
echo 'KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/99-input.rules
sudo usermod -aG input $USER
```
Then **logout and login** for group membership to take effect.

## Spoken commands

Say **"Computer"**, **"Samantha"**, or **"Peter"** to trigger the agent. Built-in commands include:

- Computer, open terminal / open a web browser / go to *website*
- Computer, on screen / take a picture / off screen (webcam)
- Computer, record audio
- Computer, draw a picture of *subject* (stable-diffusion)
- Copy that / Paste it / Undo that
- Page up / Page down
- New paragraph / Pause dictation / Resume dictation
- Stop dictation (quits)

Commands are defined in `commands_table.py` — add your own or change existing ones freely. Commands learned through the agent persist in `~/.config/whisper_dictation/custom_commands.json`.

## Files

| File | Purpose |
|---|---|
| `whisper_cpp_client.py` | Main dictation loop, chat, voice commands |
| `commands_table.py` | User-editable command table (intent → handler) |
| `matcher.py` | Semantic matching engine (all-MiniLM-L6-v2) |
| `config.py` | First-run configuration prompts |
| `record.py` | Sound-activated GStreamer audio recorder |
| `on_screen.py` | Webcam viewer and capture |
| `sdapi.py` | Stable Diffusion image generation client |
| `input_backend.py` | Wayland input simulation (evdev) |

## Optional services

- **ChatGPT** — `export OPENAI_API_KEY=<key>`
- **Google Gemini** — `export GENAI_TOKEN=<key>`; `pip install google-generativeai`
- **Stable Diffusion** — start `webui.sh --api --medvram` on the server for image generation

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
