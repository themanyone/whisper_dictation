#!/usr/bin/python
# -*- coding: utf-8 -*-
##
## Copyright (C) 2026 Henry Kroll III <nospam@thenerdshow.com>
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
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "default_config.json")

DEFAULT_CONFIG = {
    "whisper_url": "http://127.0.0.1:7777/inference",
    "embed_url": "http://127.0.0.1:8080/v1/embeddings",
    "conversation_length": 9,
    "audio_format": ".wav",
    "debug": False,
    "threshold": 0.45,
    "agent_threshold": 0.60,
    "piper_model": "",
    "piper_binary": "",
    "piper_voice": "en_US-libritts_r-medium",
    "embed_model": "",
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
            "model": "gpt-3.5-turbo",
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
            "base_url": "https://api.deepseek.com",
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
            "name": "Charm Hyper",
            "base_url": "https://hyper.charm.land/v1",
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
    # ── Embeddings server ────────────────────────────────────────────
    config["embed_url"] = _prompt(
        "  Embeddings server URL (semantic matching)", config["embed_url"]
    )

    # Same port as chat? Then we need a model name for router-mode.
    active_name = config.get("provider", "")
    chat_base = "http://127.0.0.1:8080/v1"
    if active_name:
        for p in config.get("providers", []):
            if p.get("name") == active_name and p.get("base_url"):
                chat_base = p["base_url"]
                break
    chat_port = urlparse(chat_base).port
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
    print()
    print("  ── Enable AI Agent Chat ──────────────────────────────")
    print(f"  Edit providers in {DEFAULT_CONFIG_PATH}")
    print("  or in your config file above. Each provider needs a")
    print("  base_url (including port) and api_key. Switch providers")
    print("  at runtime by saying 'switch provider'.")
    print("  ─────────────────────────────────────────────────────")
    print()

    return config


# Track whether get_config() triggered first-run setup this session.
first_run = False


def _load_defaults():
    """Return the defaults dict, sourced from default_config.json.

    Creates the file from DEFAULT_CONFIG if it doesn't exist, so users
    can edit default_config.json freely without touching Python code.
    """
    if not os.path.exists(DEFAULT_CONFIG_PATH):
        os.makedirs(os.path.dirname(DEFAULT_CONFIG_PATH) or ".", exist_ok=True)
        with open(DEFAULT_CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"  Created {DEFAULT_CONFIG_PATH}")
    try:
        with open(DEFAULT_CONFIG_PATH) as f:
            data = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        return merged
    except Exception as e:
        logging.warning(f"Failed to read {DEFAULT_CONFIG_PATH}: {e}")
        return dict(DEFAULT_CONFIG)


def _load_from_file():
    """Load config from file, or run first-run setup if missing.

    Uses default_config.json (editable, outside git) as the base,
    then overlays ~/.config/whisper_dictation/config.json on top.

    Merges providers list by name — new default providers appear even
    when an old config.json has a smaller providers list.
    """
    global first_run
    defaults = _load_defaults()
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        config = dict(defaults)
        config.update(data)
        # Merge providers by name: file providers override defaults,
        # but new default providers not in the file are preserved.
        if "providers" in data and isinstance(data["providers"], list):
            file_names = {p["name"] for p in data["providers"] if "name" in p}
            merged = list(data["providers"])
            for dp in defaults.get("providers", []):
                if dp["name"] not in file_names:
                    merged.append(dp)
            config["providers"] = merged
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
        "whisper_url": os.getenv("WHISPER_URL"),
        "embed_url": os.getenv("EMBED_URL"),
        "embed_model": os.getenv("EMBED_MODEL"),
        "piper_model": os.getenv("PIPER_MODEL"),
        "piper_binary": os.getenv("PIPER_BINARY"),
        "piper_voice": os.getenv("PIPER_VOICE"),
        "agent_threshold": os.getenv("AGENT_THRESHOLD"),
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

    # Derive chat_url and chat_model from the active provider
    active = get_active_provider(config)
    if active and active.get("base_url"):
        ptype = active.get("provider_type") or detect_provider_type(
            active["base_url"]
        )
        config["chat_url"] = resolve_provider_url(
            active["base_url"], ptype
        )
        if active.get("model"):
            config["chat_model"] = active["model"]

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
    (re.compile(r"charm\.land", re.I), "openai"),
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
            data = r.json()
            models = [m["id"] for m in data.get("data", []) if "id" in m]
            if models:
                return sorted(models)
        except requests.RequestException:
            pass

    # If the API doesn't return models, fall back to well-known IDs for
    # popular providers so the user isn't stuck with "No models found".
    host = urlparse(base_url).netloc.lower()
    known_models = {
        "api.deepseek.com": ["deepseek-chat", "deepseek-reasoner"],
        "api.openai.com": [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
        ],
        "api.anthropic.com": ["claude-sonnet-4-20250514"],
        "api.groq.com": [
            "llama-3.3-70b-versatile", "gemma2-9b-it",
            "llama-3.1-8b-instant",
        ],
        "api.together.xyz": [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        ],
        "api.fireworks.ai": [
            "accounts/fireworks/models/llama-v3p1-70b-instruct",
        ],
    }
    if host in known_models:
        return known_models[host]
    return []


def update_config(updates):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    else:
        cfg = _load_defaults()
    cfg.update(updates)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"  Updated configuration: {CONFIG_PATH}")


def update_provider_model(provider_name, model):
    """Store model name under the specified provider entry in config."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    else:
        cfg = _load_defaults()
    for p in cfg.get("providers", []):
        if p.get("name") == provider_name:
            p["model"] = model
            break
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"  Updated configuration: {CONFIG_PATH}")


def ensure_api_key(provider_name, providers):
    """If provider has no API key, check env var, then prompt and save.
    """
    _KEY_ENV = {
        "OpenAI": "OPENAI_API_KEY",
        "DeepSeek": "DEEPSEEK_API_KEY",
        "Google Gemini": "GENAI_TOKEN",
        "Anthropic Claude": "ANTHROPIC_API_KEY",
        "Groq": "GROQ_API_KEY",
        "Together AI": "TOGETHER_API_KEY",
        "DeepInfra": "DEEPINFRA_API_KEY",
        "OpenRouter": "OPENROUTER_API_KEY",
        "xAI Grok": "XAI_API_KEY",
        "Mistral AI": "MISTRAL_API_KEY",
        "Perplexity": "PERPLEXITY_API_KEY",
        "Charm Hyper": "HYPER_API_KEY",
        "Fireworks AI": "FIREWORKS_API_KEY",
        "AIHubMix": "AIHUBMIX_API_KEY",
    }
    # Fallback aliases
    _KEY_ALIAS = {
        "Google Gemini": ("GEMINI_API_KEY",),
    }
    for i, p in enumerate(providers):
        if p.get("name") != provider_name:
            continue
        key = p.get("api_key", "")
        if key and key != "sk-no-key-required":
            return key
        # Don't prompt for localhost providers
        base_url = p.get("base_url", "")
        if "localhost" in base_url or "127.0.0.1" in base_url or key == "sk-no-key-required":
            return key
        # Check known env vars
        env_key = os.environ.get(_KEY_ENV.get(provider_name, ""))
        if not env_key:
            for alias in _KEY_ALIAS.get(provider_name, ()):
                env_key = os.environ.get(alias)
                if env_key:
                    break
        if env_key:
            p["api_key"] = env_key
            update_config({"providers": providers})
            return env_key
        new_key = _prompt(f"  API key for {provider_name}", "")
        if new_key:
            p["api_key"] = new_key
            update_config({"providers": providers})
            return new_key
        return key
    return ""


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
