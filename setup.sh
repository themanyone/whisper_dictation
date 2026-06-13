#!/usr/bin/env bash
# -*- coding: utf-8 -*-
##
## setup.sh — one-command setup for whisper_dictation
##
## Downloads pre-built whisper-server and llama-server binaries, downloads
## the recommended models (whisper tiny + Qwen2.5-7B-Q4_K_S), installs
## Python dependencies, and optionally creates a systemd user service.
##
## Usage:  ./setup.sh
##

# ── Configurable options ────────────────────────────────────────────
#    Change these to match your network, GPU, and preferences.

# Server ports
WHISPER_PORT="${WHISPER_PORT:-7777}"
LLAMA_PORT="${LLAMA_PORT:-8888}"
LLAMA_HOST="${LLAMA_HOST:-127.0.0.1}"

# GPU offload layers (-ngl). Set to 0 for CPU-only, 99 for full offload.
LLAMA_NGL="${LLAMA_NGL:-99}"

# Context window size (input + output tokens)
LLAMA_CONTEXT="${LLAMA_CONTEXT:-4096}"

# Whisper model (speech recognition)
WHISPER_MODEL="${WHISPER_MODEL:-ggml-tiny.en.bin}"
WHISPER_MODEL_URL="${WHISPER_MODEL_URL:-https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin}"

# LLM model (agent)
LLM_MODEL="${LLM_MODEL:-qwen2.5-7b-q4_k_s.gguf}"
LLM_MODEL_URL="${LLM_MODEL_URL:-https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_S.gguf}"

# Embedding model (semantic command matching, optional)
EMBED_MODEL="${EMBED_MODEL:-all-MiniLM-L6-v2.Q8_0.gguf}"
EMBED_MODEL_URL="${EMBED_MODEL_URL:-https://huggingface.co/ChristianAzinn/all-MiniLM-L6-v2-Q8_0-GGUF/resolve/main/all-MiniLM-L6-v2.Q8_0.gguf}"

# Pre-built binary versions
WHISPER_VER="${WHISPER_VER:-v1.8.6}"
LLAMA_VER="${LLAMA_VER:-b9585}"

# Whisper binary variant: "whisper-blas-bin-x64" (CPU BLAS) or
# "whisper-cublas-12.4.0-bin-x64" (CUDA) or "whisper-bin-x64" (plain CPU)
WHISPER_BIN="${WHISPER_BIN:-whisper-blas-bin-x64}"

# Llama binary variant: "llama-${LLAMA_VER}-bin-ubuntu-x64" (CPU) or
# "llama-${LLAMA_VER}-bin-ubuntu-vulkan-x64" (Vulkan)
LLAMA_BIN="${LLAMA_BIN:-llama-${LLAMA_VER}-bin-ubuntu-x64}"

set -euo pipefail

# ── Sanity checks ────────────────────────────────────────────────────
for cmd in wget unzip tar python3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd is required but not found."
        echo "Install it with your package manager first."
        exit 1
    fi
done

# ── Paths ────────────────────────────────────────────────────────────
BIN_DIR="${HOME}/.local/bin"
MODELS_DIR="${MODELS_DIR:-${HOME}/models}"
CONFIG_DIR="${HOME}/.config/whisper_dictation"

# Create directories
mkdir -p "$BIN_DIR" "$MODELS_DIR" "$CONFIG_DIR"

echo ""
echo "================================================"
echo "  whisper_dictation — Automated Setup"
echo "================================================"
echo "  Binaries:   $BIN_DIR"
echo "  Models:     $MODELS_DIR"
echo "  Config:     $CONFIG_DIR"
echo ""

# ── 1. Install system dependencies ───────────────────────────────────
echo "── [1/5] Installing system dependencies ──"

# Detect distro and show install hint (actual check at end of script)
if command -v pacman &>/dev/null; then
    echo "  (Arch)  sudo pacman -S --needed gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad swh-plugins python-pip"
elif command -v dnf &>/dev/null; then
    echo "  (Fedora)  sudo dnf install gstreamer1 gstreamer1-plugins-base gstreamer1-plugins-good gstreamer1-plugins-bad-free-extras"
elif command -v apt &>/dev/null; then
    echo "  (Debian/Ubuntu)  sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad swh-plugins python3-gi python3-pip gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0"
else
    echo "  Please install GStreamer and LADSPA delay plugin via your package manager."
fi
echo "  (Verified at the end of this script.)"

# ── 2. Install Python dependencies ───────────────────────────────────
echo ""
echo "── [2/5] Installing Python dependencies ──"
pip3 install --user -r requirements.txt 2>/dev/null || \
    pip3 install --user -r requirements.txt --break-system-packages 2>/dev/null || {
    echo "  pip install failed. Try: pip install -r requirements.txt"
    echo "  (You may need a virtual environment on newer distros.)"
}

# ── 3. Download whisper-server binary ────────────────────────────────
echo ""
echo "── [3/5] Downloading whisper-server ──"
# Use version from configurable options at top of file
if ! command -v whisper-server &>/dev/null && [ ! -x "$BIN_DIR/whisper-server" ]; then
    echo "  Downloading whisper-server ${WHISPER_VER} (BLAS x64)..."
    wget -q --show-progress \
        "https://github.com/ggml-org/whisper.cpp/releases/download/${WHISPER_VER}/${WHISPER_BIN}.zip" \
        -O /tmp/whisper-bin.zip
    unzip -qo /tmp/whisper-bin.zip -d /tmp/whisper-bin/
    cp /tmp/whisper-bin/whisper-server "$BIN_DIR/whisper-server"
    cp /tmp/whisper-bin/whisper-cli "$BIN_DIR/whisper-cli"
    chmod +x "$BIN_DIR/whisper-server" "$BIN_DIR/whisper-cli"
    rm -rf /tmp/whisper-bin.zip /tmp/whisper-bin/
    echo "  → Installed whisper-server and whisper-cli to $BIN_DIR"
else
    echo "  whisper-server already present, skipping."
fi

# ── 4. Download llama-server binary ─────────────────────────────────
echo ""
echo "── [4/5] Downloading llama-server ──"
# Use version from configurable options at top of file
if ! command -v llama-server &>/dev/null && [ ! -x "$BIN_DIR/llama-server" ]; then
    echo "  Downloading llama-server ${LLAMA_VER} (Ubuntu x64 CPU)..."
    wget -q --show-progress \
        "https://github.com/ggml-org/llama.cpp/releases/download/${LLAMA_VER}/${LLAMA_BIN}.tar.gz" \
        -O /tmp/llama-bin.tar.gz
    tar -xzf /tmp/llama-bin.tar.gz -C /tmp/llama-bin/
    cp /tmp/llama-bin/llama-server "$BIN_DIR/llama-server"
    cp /tmp/llama-bin/llama-cli "$BIN_DIR/llama-cli"
    chmod +x "$BIN_DIR/llama-server" "$BIN_DIR/llama-cli"
    rm -rf /tmp/llama-bin.tar.gz /tmp/llama-bin/
    echo "  → Installed llama-server and llama-cli to $BIN_DIR"
else
    echo "  llama-server already present, skipping."
fi

# ── 5. Download models ───────────────────────────────────────────────
echo ""
echo "── [5/5] Downloading models ──"

# Whisper model (tiny.en)
if [ ! -f "$MODELS_DIR/$WHISPER_MODEL" ]; then
    echo "  Downloading $WHISPER_MODEL..."
    wget -q --show-progress \
        "${WHISPER_MODEL_URL}" \
        -O "$MODELS_DIR/$WHISPER_MODEL"
    echo "  → $MODELS_DIR/$WHISPER_MODEL"
else
    echo "  $WHISPER_MODEL already present, skipping."
fi

# LLM model (Qwen2.5-7B-Instruct Q4_K_S)
if [ ! -f "$MODELS_DIR/$LLM_MODEL" ]; then
    echo "  Downloading $LLM_MODEL..."
    echo "  This may take a while depending on your connection."
    wget -q --show-progress \
        "${LLM_MODEL_URL}" \
        -O "$MODELS_DIR/$LLM_MODEL"
    echo "  → $MODELS_DIR/$LLM_MODEL"
else
    echo "  $LLM_MODEL already present, skipping."
fi

# Embedding model (optional, for semantic command matching)
echo ""
echo -n "  Download embedding model ${EMBED_MODEL} (~23 MB)? [y/N] "
read -r dl_embed
if [[ "$dl_embed" =~ ^(y|Y|yes)$ ]]; then
    if [ ! -f "$MODELS_DIR/$EMBED_MODEL" ]; then
        wget -q --show-progress \
            "${EMBED_MODEL_URL}" \
            -O "$MODELS_DIR/$EMBED_MODEL"
        echo "  → $MODELS_DIR/$EMBED_MODEL"
    else
        echo "  $EMBED_MODEL already present, skipping."
    fi
fi

# ── Write config.json ────────────────────────────────────────────────
echo ""
echo "── Writing config ──"
EMBED_MODE="same-server"  # or "router"
if [[ "$dl_embed" =~ ^(y|Y|yes)$ ]]; then
    # We have a dedicated embedding model; ask how to serve it
    echo ""
    echo "  How would you like to serve the embedding model?"
    echo "    1) Same server as chat (llama-server --embeddings — works with any model)"
    echo "    2) Router mode (llama-server with models.ini — dedicated embed model)"
    echo -n "  Choose [1]: "
    read -r embed_choice
    if [[ "$embed_choice" == "2" ]]; then
        EMBED_MODE="router"
    fi
fi

cat > "$CONFIG_DIR/config.json" <<-CONFIG
{
    "whisper_url": "http://${LLAMA_HOST}:${WHISPER_PORT}/inference",
    "chat_url": "http://${LLAMA_HOST}:${LLAMA_PORT}/v1/chat",
    "embed_url": "http://${LLAMA_HOST}:${LLAMA_PORT}/v1/embeddings",
    "openai_api_key": "",
    "openai_base_url": "",
    "gemini_api_key": "",
    "conversation_length": 9,
    "audio_format": ".wav",
    "debug": false,
    "threshold": 0.45,
    "piper_model": "",
    "piper_binary": "",
    "piper_voice": "en_US-libritts_r-medium",
    "embed_model": "$([ "$EMBED_MODE" == "router" ] && echo "$EMBED_MODEL" || echo "")"
}
CONFIG
echo "  → $CONFIG_DIR/config.json"

# ── Optional: systemd service ────────────────────────────────────────
echo ""
echo "── Setup complete ──"
echo ""
echo "  Environment:"
echo "    export MODELS_DIR=\"$MODELS_DIR\""
echo "    export PATH=\"\$PATH:$BIN_DIR\""
echo ""
echo "  Run whisper-server:"
echo "    whisper-server -l en -m \"$MODELS_DIR/$WHISPER_MODEL\" --convert --port $WHISPER_PORT"
echo ""
if [[ "$EMBED_MODE" == "router" ]]; then
    echo "  Create models.ini for router mode:"
    echo "    cat > ${CONFIG_DIR}/models.ini << 'EOF'"
    echo "    [*]"
    echo "    jinja = true"
    echo ""
    echo "    [${EMBED_MODEL}]"
    echo "    embedding = true"
    echo "    load-on-startup = true"
    echo "    sleep-idle-seconds = -1"
    echo ""
    echo "    [${LLM_MODEL}]"
    echo "    fa = off"
    echo "    ctx-size = ${LLAMA_CONTEXT}"
    echo "    ub = ${LLAMA_CONTEXT}"
    echo "    EOF"
    echo ""
    echo "  Run llama-server (router mode):"
    echo "    llama-server --port ${LLAMA_PORT} --host ${LLAMA_HOST} \\"
    echo "      --model \"${MODELS_DIR}/${LLM_MODEL}\" \\"
    echo "      --model \"${MODELS_DIR}/${EMBED_MODEL}\""
    echo ""
else
    echo "  Run llama-server (embeddings enabled):"
    echo "    llama-server -m \"$MODELS_DIR/$LLM_MODEL\" -ngl $LLAMA_NGL -c $LLAMA_CONTEXT \\"
    echo "      --port $LLAMA_PORT --host $LLAMA_HOST --embeddings"
    echo ""
fi
echo "  Run the dictation client:"
echo "    cd $(pwd) && ./whisper_cpp_client.py"
echo ""

# Offer systemd service setup for whisper-server
if command -v systemctl &>/dev/null; then
    echo -n "  Install whisper-server as a systemd user service? [Y/n] "
    read -r resp
    if [[ "$resp" =~ ^(y|Y|)$ ]]; then
        UNIT_DIR="${HOME}/.config/systemd/user"
        mkdir -p "$UNIT_DIR"
        cat > "$UNIT_DIR/whisper.service" <<-SERVICE
[Unit]
Description=Run Whisper server

[Service]
ExecStart=whisper-server -l en -m \
 "${MODELS_DIR}/${WHISPER_MODEL}" \
 --convert --port ${WHISPER_PORT}

[Install]
WantedBy=default.target
SERVICE
        systemctl --user daemon-reload
        echo "  Created $UNIT_DIR/whisper.service"
        echo "  The client will auto-start/stop this service."
        echo "  To keep it always running: systemctl --user enable whisper"
    fi
fi

echo ""
echo "  Done! Add this to your ~/.bashrc:"
echo "    export MODELS_DIR=\"$MODELS_DIR\""
echo "    export PATH=\"\$PATH:$BIN_DIR\""
echo ""

# ── GStreamer check ───────────────────────────────────────────────────
echo "── Checking GStreamer installation ──"

GSTREAMER_OK=true

if ! command -v gst-launch-1.0 &>/dev/null; then
    GSTREAMER_OK=false
    echo "  gst-launch-1.0 not found."
fi

# Check for LADSPA delay plugin used by the pre-recording buffer
LADSPA_FOUND=false
for dir in /usr/lib/ladspa /usr/lib64/ladspa /usr/lib/x86_64-linux-gnu/ladspa; do
    if [ -f "$dir/delay_1898.so" ]; then
        LADSPA_FOUND=true
        break
    fi
done

if ! $LADSPA_FOUND; then
    GSTREAMER_OK=false
    echo "  LADSPA delay plugin (delay_1898.so) not found."
fi

if ! $GSTREAMER_OK; then
    echo ""
    echo "  GStreamer components are missing. See README Preparation:"
    echo ""

    if command -v apt &>/dev/null; then
        echo "  ** Ubuntu / Debian **"
        echo "  sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-base \\"
        echo "    gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \\"
        echo "    swh-plugins python3-gi python3-pip \\"
        echo "    gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0"
    elif command -v pacman &>/dev/null; then
        echo "  ** Arch Linux **"
        echo "  sudo pacman -S gstreamer gst-plugins-base gst-plugins-good \\"
        echo "    gst-plugins-bad swh-plugins"
    elif command -v dnf &>/dev/null; then
        echo "  ** Fedora **"
        echo "  Get the Rpmfusion repos (http://rpmfusion.org) then:"
        echo "  sudo dnf install gstreamer1 gstreamer1-plugins-base \\"
        echo "    gstreamer1-plugins-good gstreamer1-plugins-bad-free-extras"
    else
        echo "  Please install GStreamer and the LADSPA delay plugin"
        echo "  via your package manager. See README.md for details."
    fi
    echo ""
    echo "  Recording will not work until these are installed."
else
    echo "  GStreamer components found."
fi
