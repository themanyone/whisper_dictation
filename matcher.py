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

Uses sentence-transformers/all-MiniLM-L6-v2 to embed intent phrases
and match spoken text by cosine similarity. Replaces regex-based
command routing with natural-language-tolerant matching.

Usage:
    from matcher import Matcher
    from commands_table import COMMANDS

    matcher = Matcher(COMMANDS)
    result = matcher.match("open terminal", threshold=0.45)
    if result:
        handler_name, arg, score = result
        globals()[handler_name](arg)
"""

import re
import logging

from sentence_transformers import SentenceTransformer, util

# Wake words to strip from spoken text before matching
WAKE_WORDS_RE = re.compile(r"^(peter|samantha|computer)[,\s]*", re.IGNORECASE)


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


class Matcher:
    """
    Semantic command matcher using sentence-transformers.

    Pre-computes intent embeddings at construction, then matches
    spoken text by cosine similarity at match() time.
    """

    def __init__(self, commands, model_name="all-MiniLM-L6-v2", threshold=0.45):
        """
        Initialize the matcher with a command list.

        Args:
            commands: List of dicts with "intent", "handler", and "argument" keys.
            model_name: Sentence transformer model name.
            threshold: Default cosine similarity threshold for match().
        """
        self.commands = commands
        self.default_threshold = threshold
        self.intent_texts = [c["intent"] for c in commands]
        logging.debug(f"Loading sentence transformer model '{model_name}'...")
        self.model = SentenceTransformer(model_name)
        self.embeddings = self.model.encode(self.intent_texts, convert_to_tensor=True)
        logging.debug(f"Pre-computed {len(self.intent_texts)} intent embeddings.")

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

        emb = self.model.encode(cleaned, convert_to_tensor=True)
        scores = util.cos_sim(emb, self.embeddings)[0]
        best_idx = scores.argmax().item()
        best_score = scores[best_idx].item()

        if best_score < threshold:
            return None

        entry = self.commands[best_idx]
        arg = None
        if entry.get("argument") == "remainder":
            arg = _extract_remainder(cleaned, entry["intent"])

        return entry["handler"], arg, best_score
