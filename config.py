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
import logging
import os
import re
import requests
import sys
import urllib.request
from urllib.parse import urlparse

CONFIG_DIR = os.path.expanduser("~/.config/whisper_dictation")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
CUSTOM_COMMANDS_PATH = os.path.join(CONFIG_DIR, "custom_commands.json")

DEFAULT_CONFIG = {
    "whisper_url": "http://127.0.0.1:7777/inference",
    "chat_url": "http://127.0.0.1:8080/v1",
    "embed_url": "http://127.0.0.1:8080/v1/embeddings",
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
    "chat_model": "gpt-3.5-turbo",
    "provider": "llama.cpp",
    "providers": [
        {
            "name": "llama.cpp",
            "base_url": "http://127.0.0.1:8080/v1",
            "api_key": "sk-no-key-required",
            "provider_type": "llamacpp",
        },
        {
            "name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "provider_type": "openai",
        },
        {
            "name": "OpenRouter",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": "",
            "provider_type": "openai",
        },
        {
            "name": "xAI Grok",
            "base_url": "https://api.x.ai/v1",
            "api_key": "",
            "provider_type": "openai",
        },
        {
            "name": "Google Gemini",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "api_key": "",
            "model": "gemini-2.0-flash",
            "provider_type": "gemini",
        },
        {
            "name": "Anthropic Claude",
            "base_url": "https://api.anthropic.com/v1",
            "api_key": "",
            "model": "claude-sonnet-4-20250514",
            "provider_type": "anthropic",
        },
        {
            "name": "Groq",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": "",
            "provider_type": "openai",
        },
        {
            "name": "Together AI",
            "base_url": "https://api.together.ai/v1",
            "api_key": "",
            "provider_type": "openai",
        },
        {
            "name": "DeepInfra",
            "base_url": "https://api.deepinfra.com/v1/openai",
            "api_key": "",
            "provider_type": "openai",
        },
        {
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "",
            "provider_type": "openai",
        },
        {
            "name": "Mistral AI",
            "base_url": "https://api.mistral.ai/v1",
            "api_key": "",
            "provider_type": "openai",
        },
        {
            "name": "Perplexity",
            "base_url": "https://api.perplexity.ai",
            "api_key": "",
            "provider_type": "openai",
        },
        {
            "name": "Fireworks AI",
            "base_url": "https://api.fireworks.ai/inference/v1",
            "api_key": "",
            "provider_type": "openai",
        },
        {
            "name": "AIHubMix",
            "base_url": "https://aihubmix.com/v1",
            "api_key": "",
            "provider_type": "openai",
        },
        {
            "name": "Ollama",
            "base_url": "http://127.0.0.1:11434/v1",
            "api_key": "sk-no-key-required",
            "provider_type": "ollama",
        },
    ],
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
        "provider": os.getenv("PROVIDER"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "gemini_api_key": os.getenv("GENAI_TOKEN"),
        "whisper_url": os.getenv("WHISPER_URL"),
        "chat_url": os.getenv("CHAT_URL"),
        "embed_url": os.getenv("EMBED_URL"),
        "embed_model": os.getenv("EMBED_MODEL"),
        "chat_model": os.getenv("CHAT_MODEL"),
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

    # Resolve the active provider's base_url into chat_url (if not overridden by env)
    active = get_active_provider(config)
    if active and active.get("base_url"):
        # Only apply if CHAT_URL env var wasn't set
        if os.getenv("CHAT_URL") is None:
            ptype = active.get("provider_type") or detect_provider_type(
                active["base_url"]
            )
            config["chat_url"] = resolve_provider_url(
                active["base_url"], ptype
            )
        # Pull model from provider entry if present
        if active.get("model"):
            config["chat_model"] = active["model"]
        # Pull api_key into the provider's own entry (used by get_chat_api_key)
        # Already part of the provider entry

    return config


def get_active_provider(config):
    """Return the provider dict matching config['provider'], or None."""
    name = config.get("provider", "")
    if not name:
        return None
    for p in config.get("providers", []):
        if p.get("name") == name:
            return p
    return None


# ── Provider auto-detection & URL resolution ────────────────────────

_PROBE_PATHS = {
    "openai": "/v1",
    "llamacpp": "/v1",
    "ollama": "/v1",
    "gemini": "/v1beta/openai",
    "anthropic": "/v1",
}

_KNOWN_PROVIDER_PATTERNS = [
    (re.compile(r"generativelanguage\.googleapis\.com", re.I), "gemini"),
    (re.compile(r"anthropic\.com", re.I), "anthropic"),
    (re.compile(r"openai\.com", re.I), "openai"),
    (re.compile(r"x\.ai", re.I), "openai"),
    (re.compile(r"openrouter\.ai", re.I), "openai"),
    (re.compile(r"aihubmix\.com", re.I), "openai"),
    (re.compile(r"api\.groq\.com", re.I), "openai"),
    (re.compile(r"api\.together\.xyz|together\.ai", re.I), "openai"),
    (re.compile(r"deepinfra\.com", re.I), "openai"),
    (re.compile(r"deepseek\.com", re.I), "openai"),
    (re.compile(r"mistral\.ai", re.I), "openai"),
    (re.compile(r"perplexity\.ai", re.I), "openai"),
    (re.compile(r"fireworks\.ai", re.I), "openai"),
    (re.compile(r"127\.0\.0\.1:[89]\d{3}", re.I), "llamacpp"),
    (re.compile(r"localhost:[89]\d{3}", re.I), "llamacpp"),
    (re.compile(r"ollama", re.I), "ollama"),
    (re.compile(r":11434", re.I), "ollama"),
]


def detect_provider_type(base_url):
    """Return a provider_type string guessed from the base_url, or 'openai'."""
    for pattern, ptype in _KNOWN_PROVIDER_PATTERNS:
        if pattern.search(base_url):
            return ptype
    return "openai"


def resolve_provider_url(base_url, provider_type=None):
    """Auto-correct a base URL for the given provider_type.

    Ensures the URL ends with the correct API path suffix for the provider.
    """
    if not provider_type:
        provider_type = detect_provider_type(base_url)

    base = base_url.rstrip("/")

    # Strip known API path segments so we can re-add the correct one
    strip_suffixes = ["/v1", "/v1beta/openai", "/v1/openai",
                      "/openai", "/api"]
    for suf in strip_suffixes:
        if base.endswith(suf):
            base = base[: -len(suf)]
            break

    if provider_type == "gemini":
        # Gemini needs /v1beta/openai/ (trailing slash matters for some)
        resolved = base + "/v1beta/openai/"
    elif provider_type == "anthropic":
        # Anthropic native API isn't OpenAI-compatible; point at /v1
        # (user needs an OpenAI-compatible proxy for this to work)
        resolved = base + "/v1"
    else:
        resolved = base + "/v1"

    return resolved


def probe_endpoint(base_url, api_key=None, timeout=5):
    """Try to reach an OpenAI-compatible /models endpoint on *base_url*.

    Probes multiple path patterns and returns (resolved_url, provider_type)
    on success, or (None, None).
    """
    base = base_url.rstrip("/")
    # Strip any existing path segment so we can probe fresh
    for suf in ["/v1beta/openai", "/v1/openai", "/v1", "/openai", "/api"]:
        if base.endswith(suf):
            base = base[: -len(suf)]
            break

    candidates = [
        base + "/v1/models",
        base + "/v1beta/openai/models",
        base + "/openai/v1/models",
    ]
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    for url in candidates:
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                models = data.get("data", [])
                if models and isinstance(models, list) and "id" in models[0]:
                    # Sniff provider from model IDs
                    ids = [m["id"] for m in models]
                    joined = " ".join(ids).lower()
                    if any("gemini" in m for m in ids):
                        ptype = "gemini"
                    elif any("claude" in m for m in ids):
                        ptype = "anthropic"
                    elif any("gpt" in m or "o1" in m or "o3" in m for m in ids):
                        ptype = "openai"
                    elif any("llama" in m or "qwen" in m or "mistral" in m for m in ids):
                        ptype = "llamacpp"
                    else:
                        ptype = detect_provider_type(url)
                    # Strip /models from the URL path
                    resolved = url[: -len("/models")]
                    return resolved, ptype
        except requests.RequestException:
            continue
    return None, None


def query_models(base_url, api_key=None):
    """Fetch model list from an OpenAI-compatible /v1/models endpoint.

    Tries the base_url as-is, then probes common path variations.
    Returns sorted list of model IDs (empty on failure).
    """
    # Try the URL as-is first
    for url in [base_url.rstrip("/") + "/models",
                base_url.rstrip("/") + "models"]:
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            models = [m["id"] for m in data.get("data", []) if "id" in m]
            if models:
                return sorted(models)
        except requests.RequestException:
            continue

    # Probe known path patterns
    resolved, _ = probe_endpoint(base_url, api_key=api_key)
    if resolved and resolved.rstrip("/") != base_url.rstrip("/"):
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            r = requests.get(
                resolved.rstrip("/") + "/models",
                headers=headers, timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            models = [m["id"] for m in data.get("data", []) if "id" in m]
            if models:
                return sorted(models)
        except requests.RequestException:
            pass

    return []


def update_config(updates):
    config.update(updates)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Updated configuration: {CONFIG_PATH}")


def get_chat_api_key(config, chat_url):
    """Return the API key for the provider matching chat_url, or the default."""
    # First try matching by active provider name
    active_name = config.get("provider", "")
    if active_name:
        for p in config.get("providers", []):
            if p.get("name") == active_name:
                return p.get("api_key", "sk-no-key-required")
    # Fall back to URL match
    normalized = chat_url.rstrip("/")
    for p in config.get("providers", []):
        if p.get("base_url", "").rstrip("/") == normalized:
            return p.get("api_key", "sk-no-key-required")
    return "sk-no-key-required"


_SPOKEN_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
    "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
}


def spoken_to_number(phrase):
    """Return an int 1-10 if *phrase* contains a number word/digit, else 0.

    Handles full phrases like "oh one" or "number two" by extracting the
    first recognized number token from the text.
    """
    phrase = phrase.strip().lower()
    # Fast path: exact match
    n = _SPOKEN_NUMBERS.get(phrase)
    if n:
        return n
    # Slow path: split on non-alphanumeric and check each token
    for word in re.split(r"[^a-z0-9]+", phrase):
        if not word:
            continue
        # "oh" is "zero" — only match if it's the sole number word
        if word == "oh":
            continue  # not useful as a 1-10 selection
        n = _SPOKEN_NUMBERS.get(word)
        if n:
            return n
    return 0


def match_dialog_response(spoken, options):
    """Fuzzy-match spoken text against a list of options.

    Returns the matched option string, None if no match, or '__CANCEL__'
    if the user said a cancel/stop keyword.
    """
    spoken = spoken.strip().lower()
    if not spoken:
        return None
    if re.search(r"^(cancel|never mind|forget it|stop|quit|dismiss|abort)\b", spoken):
        return "__CANCEL__"
    if not options:
        return spoken
    for opt in options:
        if spoken == opt.lower():
            return opt
        if spoken.rstrip(",.!?") == opt.lower():
            return opt
    num = spoken_to_number(spoken)
    if num > 0:
        num_str = str(num)
        if num_str in options:
            return num_str
    if re.search(r"^(yes|yeah|yep|sure|okay?|do it|go ahead|confirm)\b", spoken):
        for opt in options:
            if opt.lower() in ("yes", "y", "yeah", "sure"):
                return opt
    if re.search(r"^(no|nope|cancel|never mind|forget it|stop|quit|dismiss)\b", spoken):
        for opt in options:
            if opt.lower() in ("no", "n", "nope"):
                return opt
    return None
