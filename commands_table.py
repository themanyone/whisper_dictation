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
  handler:   Name of a function defined in ship_commander.py.
             HANDLER_MAP is auto-built via globals()[handler] at startup.
  argument:  How to extract the query argument:
               None        — no argument expected
               "remainder" — everything after the matched intent words
  requires_wake: If True, the command only triggers when preceded by a
                 wake word ("Computer", "Samantha", or "Peter").
                 Editing/dictation commands set this to False so they
                 work without a wake word.

Add, remove, or reorder entries freely. The intent phrase is the only
matching criterion — users can say variations naturally.

The semantic matcher will pick the best match by cosine similarity.
Set threshold in matcher.py (default 0.45). Lower = more fuzzily match.
"""

COMMANDS = [
    # ── Mouse actions (editing — no wake word) ─────────────────────────────
    {"intent": "left click", "handler": "left_click", "argument": None, "requires_wake": False},
    {"intent": "click the mouse", "handler": "left_click", "argument": None, "requires_wake": False},
    {"intent": "right click", "handler": "right_click", "argument": None, "requires_wake": False},
    {"intent": "middle click", "handler": "middle_click", "argument": None, "requires_wake": False},
    # ── Launch apps (argument = which app to open) ─────────────────────────
    {"intent": "open application", "handler": "open_app", "argument": "remainder", "requires_wake": True},
    {"intent": "launch program", "handler": "open_app", "argument": "remainder", "requires_wake": True},
    {"intent": "start application", "handler": "open_app", "argument": "remainder", "requires_wake": True},
    # ── Terminal (dedicated handlers so "open a terminal window" doesn't
    #    drift semantically toward "close window") ────────────────────────────
    {"intent": "open terminal", "handler": "open_terminal", "argument": None, "requires_wake": True},
    {"intent": "open a terminal", "handler": "open_terminal", "argument": None, "requires_wake": True},
    {"intent": "open a terminal window", "handler": "open_terminal", "argument": None, "requires_wake": True},
    {"intent": "launch terminal", "handler": "open_terminal", "argument": None, "requires_wake": True},
    # ── Navigation & window control ────────────────────────────────────────
    {"intent": "close window", "handler": "close_window", "argument": None, "requires_wake": True},
    {"intent": "close the window", "handler": "close_window", "argument": None, "requires_wake": True},
    # ── Web search (argument = search query) ───────────────────────────────
    {"intent": "search the web", "handler": "search_web", "argument": "remainder", "requires_wake": True},
    {"intent": "search the internet", "handler": "search_web", "argument": "remainder", "requires_wake": True},
    {"intent": "go to website", "handler": "go_to_website", "argument": "remainder", "requires_wake": True},
    {"intent": "open website", "handler": "go_to_website", "argument": "remainder", "requires_wake": True},
    # ── Email (argument = recipient) ───────────────────────────────────────
    {"intent": "send email", "handler": "send_email", "argument": "remainder", "requires_wake": True},
    {"intent": "compose email", "handler": "send_email", "argument": "remainder", "requires_wake": True},
    # ── Image generation (argument = prompt) ───────────────────────────────
    {"intent": "draw a picture", "handler": "draw_picture", "argument": "remainder", "requires_wake": True},
    {"intent": "generate image", "handler": "draw_picture", "argument": "remainder", "requires_wake": True},
    {"intent": "create an image", "handler": "draw_picture", "argument": "remainder", "requires_wake": True},
    # ── Dictation control (no wake word — these manage the dictation state) ─
    {"intent": "resume dictation", "handler": "resume_dictation", "argument": None, "requires_wake": False},
    {"intent": "resume listening", "handler": "resume_dictation", "argument": None, "requires_wake": False},
    {"intent": "wake up", "handler": "resume_dictation", "argument": None, "requires_wake": False},
    {"intent": "continue typing", "handler": "resume_dictation", "argument": None, "requires_wake": False},
    {"intent": "pause dictation", "handler": "pause_dictation", "argument": None, "requires_wake": False},
    {"intent": "pause listening", "handler": "pause_dictation", "argument": None, "requires_wake": False},
    {"intent": "go to sleep", "handler": "pause_dictation", "argument": None, "requires_wake": False},
    {"intent": "wait for further instructions", "handler": "pause_dictation", "argument": None, "requires_wake": False},
    {"intent": "stop dictation", "handler": "stop_dictation", "argument": None, "requires_wake": False},
    {"intent": "stop listening", "handler": "stop_dictation", "argument": None, "requires_wake": False},
    # ── Recording ──────────────────────────────────────────────────────────
    {"intent": "record audio", "handler": "record_mp3", "argument": None, "requires_wake": False},
    {"intent": "start recording", "handler": "record_mp3", "argument": None, "requires_wake": False},
    # ── Webcam ─────────────────────────────────────────────────────────────
    {"intent": "show webcam", "handler": "show_webcam", "argument": None, "requires_wake": True},
    {"intent": "turn on webcam", "handler": "show_webcam", "argument": None, "requires_wake": True},
    {"intent": "hide webcam", "handler": "hide_webcam", "argument": None, "requires_wake": True},
    {"intent": "turn off webcam", "handler": "hide_webcam", "argument": None, "requires_wake": True},
    {"intent": "take a picture", "handler": "take_picture", "argument": None, "requires_wake": True},
    {"intent": "snap a photo", "handler": "take_picture", "argument": None, "requires_wake": True},
    {"intent": "show pictures", "handler": "show_pictures", "argument": None, "requires_wake": True},
    {"intent": "view photo album", "handler": "show_pictures", "argument": None, "requires_wake": True},
    # ── Keyboard shortcuts (editing — no wake word) ─────────────────────────
    {"intent": "new paragraph", "handler": "hotkey_new_para", "argument": None, "requires_wake": False},
    {"intent": "new line", "handler": "hotkey_new_line", "argument": None, "requires_wake": False},
    {"intent": "press enter", "handler": "hotkey_enter", "argument": None, "requires_wake": False},
    {"intent": "submit post", "handler": "hotkey_enter", "argument": None, "requires_wake": False},
    {"intent": "submit", "handler": "hotkey_enter", "argument": None, "requires_wake": False},
    {"intent": "press backspace", "handler": "hotkey_backspace", "argument": None, "requires_wake": False},
    {"intent": "press space", "handler": "hotkey_space", "argument": None, "requires_wake": False},
    {"intent": "select all", "handler": "hotkey_select_all", "argument": None, "requires_wake": False},
    {"intent": "copy selection", "handler": "hotkey_copy", "argument": None, "requires_wake": False},
    {"intent": "cut selection", "handler": "hotkey_cut", "argument": None, "requires_wake": False},
    {"intent": "paste clipboard", "handler": "hotkey_paste", "argument": None, "requires_wake": False},
    {"intent": "undo that", "handler": "hotkey_undo", "argument": None, "requires_wake": False},
    {"intent": "go up", "handler": "hotkey_up", "argument": None, "requires_wake": False},
    {"intent": "go down", "handler": "hotkey_down", "argument": None, "requires_wake": False},
    {"intent": "go left", "handler": "hotkey_left", "argument": None, "requires_wake": False},
    {"intent": "go right", "handler": "hotkey_right", "argument": None, "requires_wake": False},
    {"intent": "go home", "handler": "hotkey_home", "argument": None, "requires_wake": False},
    {"intent": "go to end", "handler": "hotkey_end", "argument": None, "requires_wake": False},
    {"intent": "page up", "handler": "hotkey_page_up", "argument": None, "requires_wake": False},
    {"intent": "page down", "handler": "hotkey_page_down", "argument": None, "requires_wake": False},
    {"intent": "type directory listing", "handler": "hotkey_ls", "argument": None, "requires_wake": False},
    # ── AI chat (argument = prompt) ────────────────────────────────────────
    # Keep this last — it's the broadest catch-all intent.
    {
        "intent": "chat with assistant",
        "handler": "generate_text",
        "argument": "remainder",
        "requires_wake": True,
    },
    # ── Project initialization ─────────────────────────────────────────────
    {"intent": "initialize project", "handler": "initialize_project", "argument": None, "requires_wake": True},
    {"intent": "initialize documentation", "handler": "initialize_project", "argument": None, "requires_wake": True},
    {"intent": "scan project", "handler": "initialize_project", "argument": None, "requires_wake": True},
    {"intent": "update project file", "handler": "initialize_project", "argument": None, "requires_wake": True},
    {"intent": "set up project", "handler": "initialize_project", "argument": None, "requires_wake": True},
    # ── Provider / model selection ─────────────────────────────────────────
    {"intent": "switch provider", "handler": "switch_provider", "argument": None, "requires_wake": True},
    {"intent": "change provider", "handler": "switch_provider", "argument": None, "requires_wake": True},
    {"intent": "choose provider", "handler": "switch_provider", "argument": None, "requires_wake": True},
    {"intent": "change model", "handler": "switch_model", "argument": None, "requires_wake": True},
    {"intent": "switch model", "handler": "switch_model", "argument": None, "requires_wake": True},
    {"intent": "choose model", "handler": "switch_model", "argument": None, "requires_wake": True},
]
