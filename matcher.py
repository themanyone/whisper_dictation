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
Semantic matching engine for voice commands.

Uses llama.cpp's embeddings endpoint (OpenAI-compatible API) with
all-MiniLM-L6-v2-GGUF to embed intent phrases and match spoken text
by cosine similarity. Replaces sentence-transformers to avoid CUDA/torch
dependencies.

Requires a llama.cpp server running with --embeddings flag, serving
an embedding model like all-MiniLM-L6-v2-GGUF.

Usage:
    from matcher import Matcher
    from commands_table import COMMANDS

    matcher = Matcher(COMMANDS)
    result = matcher.match("open terminal", threshold=0.45)
    if result:
        handler_name, arg, score = result
        globals()[handler_name](arg)
"""

import json
import math
import os
import re
import logging
import hashlib
from typing import Optional, Tuple

import requests

# Wake words to strip from spoken text before matching
WAKE_WORDS_RE = re.compile(r"^(peter|samantha|computer)[,\s]*", re.IGNORECASE)

# Cache file location
CONFIG_DIR = os.path.expanduser("~/.config/whisper_dictation")
CACHE_PATH = os.path.join(CONFIG_DIR, "embeddings_cache.json")


def _strip_wake_words(text: str) -> str:
    """Remove wake words from the beginning of spoken text."""
    return WAKE_WORDS_RE.sub("", text).strip()


def _extract_remainder(spoken: str, intent: str) -> str:
    """
    Return the part of `spoken` not covered by `intent` words.

    Finds each intent word in order in the spoken text and returns
    everything after the last matched word's position.

    Example:
        spoken = "draw a picture of a cat"
        intent = "draw a picture"
        result = "of a cat"
    """
    words = spoken.split()
    intent_words = intent.lower().split()
    last_idx = -1
    for iw in intent_words:
        for j in range(last_idx + 1, len(words)):
            if words[j].lower() == iw:
                last_idx = j
                break
    if last_idx >= 0 and last_idx < len(words) - 1:
        return " ".join(words[last_idx + 1 :])
    return spoken  # fallback: whole utterance is the argument


def _cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two vectors using plain Python."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _embed_texts(texts: list, embed_url: str) -> list:
    """
    Embed a list of texts via the llama.cpp embeddings endpoint.

    Uses the OpenAI-compatible /v1/embeddings API.
    Returns a list of embedding vectors (each a list of floats),
    or an empty list on failure.
    """
    if not texts:
        return []

    try:
        response = requests.post(
            embed_url,
            json={"input": texts, "model": "gpt-3.5-turbo"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        # Sort by index to maintain order
        embeddings = [None] * len(texts)
        for item in data["data"]:
            embeddings[item["index"]] = item["embedding"]
        return embeddings
    except Exception as e:
        logging.info(
            f"To enable voice commands, launch a sentence transformer:\n"
            f"  llama-server --embeddings -m /path/to/all-MiniLM-L6-v2-GGUF.bin "
            f"-c 8192 --port 8088\n"
            f"(Connection to {embed_url} failed: {e})"
        )
        return []


def _cache_key(texts: list, embed_url: str) -> str:
    """Generate a cache key from the intent texts and URL."""
    raw = embed_url + "|" + "|".join(texts)
    return hashlib.sha256(raw.encode()).hexdigest()


def _load_cache() -> dict:
    """Load cached embeddings from disk, or return empty dict."""
    try:
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH) as f:
                return json.load(f)
    except Exception as e:
        logging.debug(f"Failed to load embedding cache: {e}")
    return {}


def _save_cache(cache: dict):
    """Save cached embeddings to disk."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CACHE_PATH, "w") as f:
            json.dump(cache, f)
    except Exception as e:
        logging.debug(f"Failed to save embedding cache: {e}")


class Matcher:
    """
    Semantic command matcher using llama.cpp embeddings.

    Pre-computes intent embeddings at construction via HTTP, then matches
    spoken text by cosine similarity at match() time. Caches embeddings
    to disk to avoid redundant API calls.
    """

    def __init__(self, commands, embed_url="http://127.0.0.1:8888/v1/embeddings", threshold=0.45):
        """
        Initialize the matcher with a command list.

        Args:
            commands: List of dicts with "intent", "handler", and "argument" keys.
            embed_url: llama.cpp embeddings endpoint URL.
            threshold: Default cosine similarity threshold for match().
        """
        self.commands = commands
        self.default_threshold = threshold
        self.embed_url = embed_url
        self.intent_texts = [c["intent"] for c in commands]

        # Try to load from cache
        cache = _load_cache()
        key = _cache_key(self.intent_texts, embed_url)
        cached = cache.get(key)

        if cached and len(cached) == len(self.intent_texts):
            self.embeddings = cached
            logging.debug(f"Loaded {len(self.embeddings)} intent embeddings from cache.")
        else:
            logging.debug(f"Embedding {len(self.intent_texts)} intent phrases via {embed_url}...")
            self.embeddings = _embed_texts(self.intent_texts, embed_url)
            if self.embeddings and all(e is not None for e in self.embeddings):
                cache[key] = self.embeddings
                _save_cache(cache)
                logging.debug(f"Pre-computed and cached {len(self.embeddings)} intent embeddings.")
            else:
                logging.info("Sentence transformer not available; voice commands disabled.")
                self.embeddings = [None] * len(self.intent_texts)

    def match(self, text: str, threshold=None):
        """
        Match spoken text against the command table.

        Args:
            text: The spoken text (lower-cased, punctuation stripped).
            threshold: Minimum cosine similarity. Falls back to the
                       value passed at construction (default 0.45).

        Returns:
            (handler_name, arg, score) tuple if a match above threshold,
            or None if nothing matched.
        """
        if threshold is None:
            threshold = self.default_threshold
        cleaned = _strip_wake_words(text)
        if not cleaned:
            return None

        # Embed the spoken text
        emb_list = _embed_texts([cleaned], self.embed_url)
        if not emb_list or emb_list[0] is None:
            return None
        emb = emb_list[0]

        # Find best match by cosine similarity
        best_idx = -1
        best_score = 0.0
        for i, cmd_emb in enumerate(self.embeddings):
            if cmd_emb is None:
                continue
            score = _cosine_similarity(emb, cmd_emb)
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx < 0 or best_score < threshold:
            return None

        entry = self.commands[best_idx]
        arg = None
        if entry.get("argument") == "remainder":
            arg = _extract_remainder(cleaned, entry["intent"])

        return entry["handler"], arg, best_score

    def add_command(self, intent, handler, argument=None):
        """Add a single command entry and embed its intent at runtime.

        This lets voice commands be added on-the-fly without re-embedding
        the entire command table.

        Args:
            intent:     Natural-language intent phrase for the new command.
            handler:    Handler function name (must already be in HANDLER_MAP).
            argument:   ``None`` or ``"remainder"``.

        Returns:
            The new entry dict, or ``None`` if embedding failed.
        """
        entry = {"intent": intent, "handler": handler, "argument": argument}
        self.commands.append(entry)
        self.intent_texts.append(intent)

        emb = _embed_texts([intent], self.embed_url)
        if emb and emb[0]:
            self.embeddings.append(emb[0])
            return entry
        self.embeddings.append(None)
        return None
