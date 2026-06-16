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
Tool loading, normalization, and dispatch for whisper_dictation.

Supports both Claude-format tools (name / description / input_schema)
and OpenAI-format tools (type: "function" / function: {name, parameters}).

Tools live in ~/.config/whisper_dictation/tools/*.json.
Built-in tools (image_gen) are registered in code via register_handler().

Each tool JSON may include a ``handler_code`` key containing Python source
that defines a callable (``handler(args: dict)``) to execute the tool.
"""

import json
import logging
import os
import glob

PROJECT_TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")
TOOLS_DIR = os.path.expanduser("~/.config/whisper_dictation/tools")

# Registry: tool_name -> callable that takes (args: dict) and returns str | None
_tool_handlers = {}


def register_handler(name, handler):
    """Register a handler function for a tool by name."""
    _tool_handlers[name] = handler


def get_handler(name):
    """Get handler for a tool name, or None."""
    return _tool_handlers.get(name)


def load_from_disk():
    """Load tool definitions from project tools/ then user tools/.

    Project tools are scanned first; user tools with the same name
    override them. Returns a list of normalized tool dicts.

    If a file includes ``handler_code`` the handler is compiled and
    registered automatically.
    """
    seen = set()
    tools = []

    def _scan(base):
        if not os.path.isdir(base):
            return
        for path in sorted(glob.glob(os.path.join(base, "*.json"))):
            try:
                with open(path) as f:
                    data = json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load tool {path}: {e}")
                continue
            tool = _normalize(data)
            if not tool:
                logging.warning(f"Unrecognised tool format in {path}")
                continue
            if tool["name"] in seen:
                continue  # user tool overrides project tool
            seen.add(tool["name"])
            # Compile inline handler code if present and no handler registered yet
            handler_code = data.get("handler_code") or (
                data.get("handler", {}).get("handler_code")
            )
            if handler_code and tool["name"] not in _tool_handlers:
                _compile_handler(tool["name"], handler_code)
            # Skip tools that already have a handler registered in code
            tools.append(tool)

    _scan(PROJECT_TOOLS_DIR)
    _scan(TOOLS_DIR)
    return tools


def _normalize(data):
    """Convert any supported input format to {name, description, input_schema}.

    Accepted formats (checked in order):
      1. Claude:  {name, description?, input_schema}
      2. OpenAI:  {type: "function", function: {name, description?, parameters}}
      3. Naked:   {name, description?, parameters}
    """
    # Claude
    if "name" in data and "input_schema" in data:
        return {
            "name": data["name"],
            "description": data.get("description", ""),
            "input_schema": data["input_schema"],
        }
    # OpenAI
    if data.get("type") == "function" and "function" in data:
        fn = data["function"]
        return {
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {}),
        }
    # Naked function
    if "name" in data and "parameters" in data:
        return {
            "name": data["name"],
            "description": data.get("description", ""),
            "input_schema": data["parameters"],
        }
    return None


def _compile_handler(name, code):
    """Exec *code*, register the resulting callable as *name*'s handler."""
    ns = {}
    try:
        exec(code, ns)
    except Exception as e:
        logging.warning(f"Failed to compile handler for tool '{name}': {e}")
        return

    # Try common entry-point names first
    for key in ("handler", name, f"{name}_handler"):
        if key in ns and callable(ns[key]):
            register_handler(name, ns[key])
            return
    # Fallback: register the first public callable we find
    for key, val in ns.items():
        if callable(val) and not key.startswith("_"):
            register_handler(name, val)
            return


def to_openai_format(tools):
    """Convert internal tool list to OpenAI ``tools`` parameter format.

    Returns ``None`` when the list is empty so callers can omit ``tools=``
    from the API request, which avoids unnecessary overhead on simple chats.
    """
    if not tools:
        return None
    result = []
    for t in tools:
        result.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        })
    return result


def execute(name, args_json):
    """Run a tool handler and return a (success, message) tuple.

    *args_json* may be a JSON string or an already-parsed dict.
    """
    handler = get_handler(name)
    if not handler:
        return (False, f"No handler registered for tool '{name}'")

    try:
        args = json.loads(args_json) if isinstance(args_json, str) else args_json
        result = handler(args)
        if result is None:
            return (True, "")
        return (True, str(result))
    except Exception as e:
        logging.warning(f"Tool '{name}' failed: {e}")
        return (False, f"Tool '{name}' error: {e}")


def add_to_matcher(tools, matcher):
    """Register each tool name as a matcher intent for voice-first invocation.

    Converts underscores to spaces so ``send_email`` becomes intent
    ``send email``.
    """
    if not matcher:
        return
    for t in tools:
        intent = t["name"].replace("_", " ")
        matcher.add_command(intent, t["name"])
