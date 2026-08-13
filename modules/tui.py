#!/usr/bin/python
# -*- coding: utf-8 -*-
## tui.py
##
## Agent TUI — prompt_toolkit full-screen UI
## Layout: Ship It! banner, log left, skills right, input bottom, VU inline.
## Dictation inserts into the buffer; Enter submits through the pipeline.
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
from __future__ import annotations

import logging
import math
from datetime import datetime
from threading import Lock

try:
    from prompt_toolkit import Application
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout.containers import (
        HSplit,
        VSplit,
        Window,
        WindowAlign,
    )
    from prompt_toolkit.layout.controls import FormattedTextControl, BufferControl
    from prompt_toolkit.layout.layout import Layout as PtLayout
    from prompt_toolkit.layout import ScrollablePane
    from prompt_toolkit.styles import Style

    HAS_PT = True
except ImportError:
    HAS_PT = False


class _LogHandler(logging.Handler):
    def __init__(self, tui: "TUI") -> None:
        super().__init__()
        self.tui = tui

    def emit(self, record: logging.LogRecord) -> None:
        self.tui.log(self.format(record), "dim")


_BANNER = """\
███████  ██   ██ ██ ██████     ██ ████████
██       ██   ██ ██ ██          ██    ██
███████  ███████ ██ ██          ██    ██
     ██  ██   ██ ██ ██          ██    ██
███████  ██   ██ ██ ██████     ██    ██"""


class TUI:
    """Full-screen prompt_toolkit TUI. Dictation inserts into input buffer."""

    def __init__(self):
        self._log: list[tuple[str, str]] = []
        self._mode = "dictating"
        self._model = ""
        self._match = ""
        self._vu_level = 0.0
        self._vu_db = 0.0
        self._skills: list[dict] = []
        self._lock = Lock()
        self._startup_buf: list[str] = []
        self._app: Application | None = None
        self._running = False
        self._input_handler = None
        self._input_buf: Buffer | None = None

    def capture_logging(self, level=logging.INFO,
                        fmt="%(asctime)s [%(levelname)s] %(lineno)d %(message)s"
                        ) -> None:
        handler = _LogHandler(self)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(fmt=fmt))
        logging.getLogger().addHandler(handler)

    # ── State setters ────────────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self.refresh()

    def set_model(self, model: str) -> None:
        self._model = model
        self.refresh()

    def set_skills(self, skills: list[dict]) -> None:
        self._skills = skills
        self.refresh()

    def set_vu(self, rms: float, db: float) -> None:
        self._vu_level = max(0.0, min(1.0, rms))
        self._vu_db = db
        self.refresh()

    def on_submit(self, handler) -> None:
        self._input_handler = handler

    # ── Log helpers ─────────────────────────────────────────────

    def log(self, text: str, style: str = "") -> None:
        if not HAS_PT:
            print(text)
            return
        ts = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self._log.append((f"[{ts}] {text}", style))
        self.refresh()

    def dictation(self, text: str) -> None:
        self.log(text.strip(), "white")

    def command(self, handler: str, score: float) -> None:
        self.log(f"[CMD] {handler}  (score={score:.3f})", "yellow")

    def llm(self, text: str) -> None:
        clipped = text[:120] + ("\u2026" if len(text) > 120 else "")
        self.log(clipped, "cyan")

    def error(self, text: str) -> None:
        self.log(f"\u26a0 {text}", "red")

    def system(self, text: str) -> None:
        self.log(text, "dim")

    def prompt(self, text: str) -> None:
        self.log(f"\U0001f3a4 {text}", "bold green")

    # ── Insert into buffer ──────────────────────────────────────

    def insert_text(self, text: str) -> None:
        if self._input_buf:
            try:
                self._input_buf.insert_text(text)
            except Exception:
                pass

    # ── Lifecycle ────────────────────────────────────────────────

    def start(self, refresh: int = 8) -> None:
        if not HAS_PT:
            return
        buf = self._startup_buf
        self._startup_buf = []
        for msg in buf:
            ts = datetime.now().strftime("%H:%M:%S")
            with self._lock:
                self._log.append((f"[{ts}] {msg}", "bold"))
        self._build_app()
        self._running = True
        try:
            self._app.run()
        except Exception:
            pass

    def stop(self) -> None:
        self._running = False
        if self._app:
            try:
                self._app.exit()
            except Exception:
                pass
            self._app = None

    def refresh(self) -> None:
        if self._app:
            try:
                self._app.invalidate()
            except Exception:
                pass

    # ── Input callback ───────────────────────────────────────────

    def _on_submit(self, buf: Buffer) -> bool:
        text = buf.text.strip()
        buf.text = ""
        self.refresh()
        if text and self._input_handler:
            self._input_handler(text)
        return True

    # ── UI build ─────────────────────────────────────────────────

    def _build_app(self) -> None:
        kb = KeyBindings()

        @kb.add("c-c")
        def _exit(event) -> None:
            event.app.exit()

        style = Style([
            ("banner", "fg:blue bold"),
            ("mode-dot", "fg:green bold"),
            ("mode-dot-paused", "fg:yellow bold"),
            ("mode-label", "bold"),
            ("model", "fg:cyan"),
            ("sep", "fg:gray"),
            ("vu-label", "fg:green bold"),
            ("vu-bar", "fg:green"),
            ("log-time", "fg:gray"),
            ("log-white", ""),
            ("log-yellow", "fg:yellow"),
            ("log-cyan", "fg:cyan"),
            ("log-red", "fg:red"),
            ("log-dim", "fg:gray"),
            ("log-green", "fg:green bold"),
            ("log-bold", "bold"),
            ("skills-name", "fg:cyan bold"),
            ("skills-desc", "fg:gray"),
            ("input", "fg:white bg:#111133"),
            ("prompt-char", "fg:green bold"),
        ])

        # ── Status bar ───────────────────────────────────────────
        def _status():
            dot = "\u25cf "
            cls = "class:mode-dot"
            if not self._mode.startswith("dictat"):
                dot = "\u25cb "
                cls = "class:mode-dot-paused"
            parts = [
                (cls + " class:mode-label", dot + self._mode.capitalize()),
            ]
            if self._model:
                parts.append(("class:model", " " + self._model))
            if self._vu_level > 0.0:
                w = 16
                filled = max(0, min(w, int(self._vu_level * w)))
                bar = "\u2588" * filled + "\u2591" * (w - filled)
                parts.append(("class:sep", "  \u2502  "))
                parts.append(("class:vu-label", "VU "))
                parts.append(("class:vu-bar", f"{bar} {self._vu_db:.1f}dB"))
            return parts

        info_bar = Window(FormattedTextControl(_status), dont_extend_height=True,
                          height=1, style="bg:#112222")

        # ── Log ──────────────────────────────────────────────────
        def _log_frags():
            with self._lock:
                lines = self._log[-200:]
            if not lines:
                return [("", " Waiting for speech\u2026")]
            out = []
            for i, (msg, style_name) in enumerate(lines):
                if i > 0:
                    out.append(("", "\n"))
                cls = "log-" + (style_name.replace(" ", "_") or "white")
                out.append((f"class:{cls}", msg))
            return out

        log_win = Window(FormattedTextControl(_log_frags), wrap_lines=False,
                         style="bg:#111122")
        scrollable_log = ScrollablePane(log_win, show_scrollbar=False)

        # ── Skills ───────────────────────────────────────────────
        def _skill_frags():
            if not self._skills:
                return [("", "No skills loaded.")]
            out = []
            for i, s in enumerate(self._skills):
                if i > 0:
                    out.append(("", "\n\n"))
                name = s.get("name", "?")
                desc = s.get("description", "").replace("\n", " ").strip()[:80]
                out.append(("class:skills-name", name))
                if desc:
                    out.append(("", "\n  "))
                    out.append(("class:skills-desc", desc))
            return out

        skill_win = Window(FormattedTextControl(_skill_frags), wrap_lines=True,
                           style="bg:#112211", width=28)
        scrollable_skills = ScrollablePane(skill_win, show_scrollbar=False)

        # ── Input ────────────────────────────────────────────────
        input_buf = Buffer(name="input", multiline=True)

        # Override default accept to keep Enter as accept (single press)
        @kb.add("enter")
        def _submit(event) -> None:
            buf = event.app.layout.get_buffer_by_name("input")
            if buf and buf.text.strip():
                self._on_submit(buf)

        @kb.add("escape", "enter")
        def _newline(event) -> None:
            buf = event.app.layout.get_buffer_by_name("input")
            if buf:
                buf.insert_text("\n")
        self._input_buf = input_buf
        input_win = Window(BufferControl(buffer=input_buf, focusable=True),
                           dont_extend_height=True, height=3, style="class:input")

        prompt_win = Window(
            FormattedTextControl([("class:prompt-char", "> ")]),
            dont_extend_height=True, width=2)

        sep = Window(FormattedTextControl("\u2500" * 200),
                     dont_extend_height=True, height=1, style="fg:gray")

        banner = Window(FormattedTextControl([("class:banner", _BANNER)]),
                        dont_extend_height=True, height=5, align=WindowAlign.CENTER)

        root = HSplit([
            banner,
            info_bar,
            VSplit([
                scrollable_log,
                Window(width=1, style="bg:#333"),
                scrollable_skills,
            ]),
            sep,
            VSplit([prompt_win, input_win]),
        ])

        layout = PtLayout(container=root, focused_element=input_win)
        self._app = Application(layout=layout, key_bindings=kb, style=style,
                                full_screen=True, mouse_support=False)

    # ── External helpers ─────────────────────────────────────────

    def message(self, text: str, style: str = "") -> None:
        if self._app:
            print(text)
        else:
            self._startup_buf.append(text)

    def table(self, title: str, items: list) -> None:
        if not HAS_PT:
            print(f"\n  {title}")
            for i, item in enumerate(items, 1):
                print(f"    {i}. {item}")
            return
        print(f"\n  {title}")
        for i, item in enumerate(items, 1):
            print(f"    {i}. {item}")
