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
User-editable command table for semantic voice control.

Each entry:
  intent:    A natural-language phrase describing the command.
             The semantic matcher compares spoken text against this.
  handler:   Name of a function defined in whisper_cpp_client.py.
             The matcher calls globals()[handler](arg) at dispatch.
  argument:  How to extract the query argument:
               None        — no argument expected
               "remainder" — everything after the matched intent words

Add, remove, or reorder entries freely. The intent phrase is the only
matching criterion — users can say variations naturally.

The semantic matcher will pick the best match by cosine similarity.
Set threshold in matcher.py (default 0.45). Lower = more fuzzily match.
"""

COMMANDS = [
    # ── Mouse actions ──────────────────────────────────────────────────────
    {"intent": "left click", "handler": "left_click", "argument": None},
    {"intent": "click the mouse", "handler": "left_click", "argument": None},
    {"intent": "right click", "handler": "right_click", "argument": None},
    {"intent": "middle click", "handler": "middle_click", "argument": None},
    # ── Launch apps (argument = which app to open) ─────────────────────────
    {"intent": "open application", "handler": "open_app", "argument": "remainder"},
    {"intent": "launch program", "handler": "open_app", "argument": "remainder"},
    {"intent": "start application", "handler": "open_app", "argument": "remainder"},
    # ── Terminal (dedicated handlers so "open a terminal window" doesn't
    #    drift semantically toward "close window") ────────────────────────────
    {"intent": "open terminal", "handler": "open_terminal", "argument": None},
    {"intent": "open a terminal", "handler": "open_terminal", "argument": None},
    {"intent": "open a terminal window", "handler": "open_terminal", "argument": None},
    {"intent": "launch terminal", "handler": "open_terminal", "argument": None},
    # ── Navigation & window control ────────────────────────────────────────
    {"intent": "close window", "handler": "close_window", "argument": None},
    {"intent": "close the window", "handler": "close_window", "argument": None},
    # ── Web search (argument = search query) ───────────────────────────────
    {"intent": "search the web", "handler": "search_web", "argument": "remainder"},
    {"intent": "search the internet", "handler": "search_web", "argument": "remainder"},
    {"intent": "go to website", "handler": "go_to_website", "argument": "remainder"},
    {"intent": "open website", "handler": "go_to_website", "argument": "remainder"},
    # ── Email (argument = recipient) ───────────────────────────────────────
    {"intent": "send email", "handler": "send_email", "argument": "remainder"},
    {"intent": "compose email", "handler": "send_email", "argument": "remainder"},
    # ── Image generation (argument = prompt) ───────────────────────────────
    {"intent": "draw a picture", "handler": "draw_picture", "argument": "remainder"},
    {"intent": "generate image", "handler": "draw_picture", "argument": "remainder"},
    {"intent": "create an image", "handler": "draw_picture", "argument": "remainder"},
    # ── Dictation control ──────────────────────────────────────────────────
    {"intent": "resume dictation", "handler": "resume_dictation", "argument": None},
    {"intent": "continue typing", "handler": "resume_dictation", "argument": None},
    {"intent": "pause dictation", "handler": "pause_dictation", "argument": None},
    {"intent": "pause listening", "handler": "pause_dictation", "argument": None},
    {"intent": "stop dictation", "handler": "stop_dictation", "argument": None},
    {"intent": "stop listening", "handler": "stop_dictation", "argument": None},
    # ── Recording ──────────────────────────────────────────────────────────
    {"intent": "record audio", "handler": "record_mp3", "argument": None},
    {"intent": "start recording", "handler": "record_mp3", "argument": None},
    # ── Webcam ─────────────────────────────────────────────────────────────
    {"intent": "show webcam", "handler": "show_webcam", "argument": None},
    {"intent": "turn on webcam", "handler": "show_webcam", "argument": None},
    {"intent": "hide webcam", "handler": "hide_webcam", "argument": None},
    {"intent": "turn off webcam", "handler": "hide_webcam", "argument": None},
    {"intent": "take a picture", "handler": "take_picture", "argument": None},
    {"intent": "snap a photo", "handler": "take_picture", "argument": None},
    {"intent": "show pictures", "handler": "show_pictures", "argument": None},
    {"intent": "view photo album", "handler": "show_pictures", "argument": None},
    # ── Keyboard shortcuts ─────────────────────────────────────────────────
    {"intent": "new paragraph", "handler": "hotkey_new_para", "argument": None},
    {"intent": "new line", "handler": "hotkey_enter", "argument": None},
    {"intent": "press enter", "handler": "hotkey_enter", "argument": None},
    {"intent": "press backspace", "handler": "hotkey_backspace", "argument": None},
    {"intent": "press space", "handler": "hotkey_space", "argument": None},
    {"intent": "select all", "handler": "hotkey_select_all", "argument": None},
    {"intent": "copy selection", "handler": "hotkey_copy", "argument": None},
    {"intent": "cut selection", "handler": "hotkey_cut", "argument": None},
    {"intent": "paste clipboard", "handler": "hotkey_paste", "argument": None},
    {"intent": "undo that", "handler": "hotkey_undo", "argument": None},
    {"intent": "go up", "handler": "hotkey_up", "argument": None},
    {"intent": "go down", "handler": "hotkey_down", "argument": None},
    {"intent": "go left", "handler": "hotkey_left", "argument": None},
    {"intent": "go right", "handler": "hotkey_right", "argument": None},
    {"intent": "go home", "handler": "hotkey_home", "argument": None},
    {"intent": "go to end", "handler": "hotkey_end", "argument": None},
    {"intent": "page up", "handler": "hotkey_page_up", "argument": None},
    {"intent": "page down", "handler": "hotkey_page_down", "argument": None},
    {"intent": "type directory listing", "handler": "hotkey_ls", "argument": None},
    # ── AI chat (argument = prompt) ────────────────────────────────────────
    # Keep this last — it's the broadest catch-all intent.
    {
        "intent": "chat with assistant",
        "handler": "generate_text",
        "argument": "remainder",
    },
]
