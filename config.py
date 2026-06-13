#!/usr/bin/python
# -*- coding: utf-8 -*-
##
## Copyright (C) 2025 Henry Kroll III <nospam@thenerdshow.com>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
## MA 02110-1301, USA.
##
"""
Configuration loader for whisper_dictation.

Stores settings in ~/.config/whisper_dictation/config.json.
On first run, prompts interactively for missing values.
Environment variables override file values at runtime.

Config file path is printed whenever it is created or modified.
"""

import json
import os
import sys
import urllib.request
from urllib.parse import urlparse

CONFIG_DIR = os.path.expanduser("~/.config/whisper_dictation")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "whisper_url": "http://127.0.0.1:7777/inference",
    "chat_url": "http://127.0.0.1:8888/v1/chat",
    "embed_url": "http://127.0.0.1:8888/v1/embeddings",
    "openai_api_key": "",
    "openai_base_url": "",
    "gemini_api_key": "",
    "conversation_length": 9,
    "audio_format": ".wav",
    "debug": False,
    "threshold": 0.45,
    "piper_model": "",
    "piper_binary": "",
    "piper_voice": "en_US-libritts_r-medium",
    "embed_model": "",
}


def _prompt(label, default=""):
    """Prompt the user for a value, returning the default if left blank."""
    if not sys.stdin.isatty():
        return default
    try:
        val = input(f"{label} [{default}]: ").strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        return default


def _first_run_setup():
    """Interactive first-run configuration prompts."""
    config = dict(DEFAULT_CONFIG)

    print()
    print("=" * 60)
    print("  whisper_dictation — First Run Setup")
    print("=" * 60)
    print(f"  Config file: {CONFIG_PATH}")
    print("  Press Enter to accept defaults.")
    print()

    config["whisper_url"] = _prompt("  Whisper.cpp server URL", config["whisper_url"])
    config["chat_url"] = _prompt(
        "  Local chat server URL (llama.cpp)", config["chat_url"]
    )
    config["openai_api_key"] = _prompt("  OpenAI API key (leave blank to skip)", "")
    if config["openai_api_key"]:
        config["openai_base_url"] = _prompt(
            "  OpenAI base URL (leave blank for default)", ""
        )
    config["gemini_api_key"] = _prompt(
        "  Google Gemini API key (leave blank to skip)", ""
    )

    # ── Embeddings server ────────────────────────────────────────────
    config["embed_url"] = _prompt(
        "  Embeddings server URL (semantic matching)", config["embed_url"]
    )

    # Same port as chat? Then we need a model name for router-mode.
    chat_port = urlparse(config["chat_url"]).port
    embed_port = urlparse(config["embed_url"]).port
    if chat_port and embed_port and chat_port == embed_port:
        config["embed_model"] = _prompt(
            "  Embedding model name (same port as chat; e.g. all-MiniLM-L6-v2)",
            config.get("embed_model", ""),
        )

    # ── Piper TTS voice ──────────────────────────────────────────────
    pip_cache = os.path.join(
        os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")),
        "piper",
    )
    voice = config.get("piper_voice", "en_US-libritts_r-medium") or "en_US-libritts_r-medium"
    onnx_path = os.path.join(pip_cache, f"{voice}.onnx")
    json_path = os.path.join(pip_cache, f"{voice}.onnx.json")
    if not os.path.isfile(onnx_path) or not os.path.isfile(json_path):
        print()
        print(f"  Piper TTS voice '{voice}' not found in {pip_cache}.")
        ans = input("  Download it now from HuggingFace? [Y/n] ").strip().lower()
        if ans in ("", "y", "yes"):
            os.makedirs(pip_cache, exist_ok=True)
            base = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
            # Derive HF path from voice name (e.g. en_US-libritts_r-medium)
            lang_region = voice.split("-", 1)[0]  # en_US
            lang = lang_region[:2]  # en
            size = voice.rsplit("-", 1)[-1]  # medium
            name = voice[len(lang_region) + 1 : -(len(size) + 1)]  # libritts_r
            model_dir = f"{lang}/{lang_region}/{name}/{size}"
            print(f"  Downloading {voice}.onnx (may take a minute)...")
            try:
                urllib.request.urlretrieve(
                    f"{base}/{model_dir}/{voice}.onnx", onnx_path
                )
                print(f"  Downloaded ({os.path.getsize(onnx_path)} bytes)")
                urllib.request.urlretrieve(
                    f"{base}/{model_dir}/{voice}.onnx.json", json_path
                )
                print(f"  Voice saved to {pip_cache}/")
            except Exception as e:
                print(f"  Download failed: {e}")

    print()

    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Configuration saved to {CONFIG_PATH}")
    print("  You can edit this file directly to change settings.")
    print()

    return config


# Track whether get_config() triggered first-run setup this session.
first_run = False


def _load_from_file():
    """Load config from file, or run first-run setup if missing."""
    global first_run
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        config = dict(DEFAULT_CONFIG)
        config.update(data)
        return config
    first_run = True
    return _first_run_setup()


def get_config():
    """
    Return the merged configuration.

    Priority (highest wins):
      1. Environment variables
      2. Config file (~/.config/whisper_dictation/config.json)
      3. Built-in defaults
    """
    config = _load_from_file()

    # Environment variable overrides (highest priority)
    env_overrides = {
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "gemini_api_key": os.getenv("GENAI_TOKEN"),
        "whisper_url": os.getenv("WHISPER_URL"),
        "chat_url": os.getenv("CHAT_URL"),
        "embed_url": os.getenv("EMBED_URL"),
        "embed_model": os.getenv("EMBED_MODEL"),
        "piper_model": os.getenv("PIPER_MODEL"),
        "piper_binary": os.getenv("PIPER_BINARY"),
        "piper_voice": os.getenv("PIPER_VOICE"),
        "debug": (os.getenv("DEBUG", "").lower() in ("1", "true", "yes")),
    }
    for key, val in env_overrides.items():
        if val is not None and val != "":
            if key == "debug":
                config[key] = val
            else:
                config[key] = val
            # True not in booleans... check properly
        if key == "debug" and val == "":
            pass  # env not set, keep file value

    return config


def update_config(updates):
    """
    Merge `updates` into the saved config and write it back.

    Prints the config file path so the user knows where it lives.
    """
    config = _load_from_file()
    config.update(updates)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Updated configuration: {CONFIG_PATH}")
