# Whisper Dictation

Private voice keyboard, AI chat, images, webcam, recordings, voice control in >= 4 GiB VRAM.

<img src="img/ss.png" alt="Dictation anywhere, even social media." width="300" align="right">

- **Dictation mode** — transcribed speech goes straight to text output (fast, no LLM)
- **Agent mode** — speech routed through the LLM for chat, tool calling, or learning new commands
- **Semantic fast-path** — embedding-based matcher (`all-MiniLM-L6-v2`) recognizes common commands in ~50ms with no LLM round trip
- **Voice-prompted agent learning** — say *"Computer, record a 30 second video"* and the LLM proposes a shell command, asks for confirmation, then remembers it so next time it can run directly (with permission).

```
Transcript → semantic matcher → matched? → run tool (fast path)
                              → no match, wake word? → LLM proposes command → approved? → save & run
                              → no match, dictation mode? → write text
```

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

# Terminal 2 — LLM agent
llama-server -m ~/models/qwen2.5-7b-q4_k_s.gguf -ngl 99 -c 4096 --port 8888

# Terminal 3 — dictation client
./whisper_cpp_client.py
```

## Default configuration

On first run, the client prompts for server URLs and API keys — press Enter to accept defaults. Settings are saved to `~/.config/whisper_dictation/config.json`. Environment variables override file values at runtime:

- `WHISPER_URL` — whisper.cpp server (default `http://127.0.0.1:7777`)
- `CHAT_URL` — LLM server (default `http://127.0.0.1:8888/v1`)
- `OPENAI_API_KEY` — optional OpenAI ChatGPT
- `GENAI_TOKEN` — optional Google Gemini

Edit or delete `~/.config/whisper_dictation/config.json` to reset.

## Building from source (GPU acceleration)

The pre-built binaries are CPU-only. For GPU acceleration (recommended), compile from source. Here we are using CUDA. Your options may vary. See below:

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

## Wayland

The app auto-detects `XDG_SESSION_TYPE` and uses `python-evdev` on Wayland or `PyAutoGUI` on X11.

For Wayland, install `python-evdev` and set up uinput permissions:
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
| `mimic3_client.py` | Text-to-speech client for Mimic3 |
| `sdapi.py` | Stable Diffusion image generation client |
| `input_backend.py` | Wayland input simulation (evdev) |

## Optional services

- **ChatGPT** — `export OPENAI_API_KEY=<key>`
- **Google Gemini** — `export GENAI_TOKEN=<key>`; `pip install google-generativeai`
- **Mimic3 TTS** — run `mimic3-server` on the network for spoken answers
- **Stable Diffusion** — start `webui.sh --api --medvram` on the server for image generation

## Troubleshooting

- If whisper-server is slow or refuses VRAM, try `sudo modprobe -r nvidia_uvm && sudo modprobe nvidia_uvm`
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
