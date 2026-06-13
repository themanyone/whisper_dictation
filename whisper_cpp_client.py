#!/usr/bin/python
# -*- coding: utf-8 -*-
##
## Copyright (C) 2023-2026 Henry Kroll III <nospam@thenerdshow.com>
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
import openai
import os
import json
import subprocess
import sys

# Session detection for X11/Wayland compatibility
if os.environ.get("XDG_SESSION_TYPE") == "wayland":
    from input_backend import InputSimulator

    pyautogui = InputSimulator()
else:
    import pyautogui

import time
import queue
import re

import webbrowser
import tempfile
import threading
import requests
import logging
import shutil
from on_screen import camera, show_pictures
from record import delayRecord
from commands_table import COMMANDS
from matcher import Matcher
from config import get_config, first_run, CONFIG_PATH, update_config

audio_queue = queue.Queue()
listening = True
chatting = False
record_process = None
running = True
cam = None
_first_utterance = True  # skip first noisy transcription at startup

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(lineno)d %(message)s",
    force=True,
    handlers=[
        # logging.FileHandler('/tmp/whisper_cpp_client.log'),
        logging.StreamHandler()
    ],
)

# ── Configuration ────────────────────────────────────────────────────
cfg = get_config()

audio_format = cfg["audio_format"]
conversation_length = cfg["conversation_length"]
whisper_cpp = cfg["whisper_url"]
local_chat_url = cfg["chat_url"]
chat_model = cfg.get("chat_model", "gpt-3.5-turbo")
debug = cfg.get("debug", False)

# ── Persistent custom commands ────────────────────────────────────────
CUSTOM_COMMANDS_FILE = os.path.expanduser(
    "~/.config/whisper_dictation/custom_commands.json"
)
custom_command_entries = []  # populated at startup by load_custom_commands()

# Derive api_key from the provider matching chat_url
chat_api_key = "sk-no-key-required"
for p in cfg.get("providers", []):
    if p.get("base_url", "").rstrip("/") == local_chat_url.rstrip("/"):
        chat_api_key = p.get("api_key", "sk-no-key-required")
        break

# ── Handler functions for the command table ──────────────────────────
# These are looked up by name in HANDLER_MAP when a command matches.

# OS-specific app launch commands
APPS_LINUX = {
    "file manager": "nemo --no-desktop&",
    "terminal": "xterm -bg gray20 -fg gray80 -fa 'Liberation Sans Mono' -fs 12 -rightbar&",
    "browser": "htmlview&",
    "web browser": "htmlview&",
    "webcam": "./on_screen.py",
}
APPS_WINDOWS = {
    "file manager": "start explorer",
    "terminal": "start cmd",
    "browser": "start iexplore",
    "web browser": "start iexplore",
    "webcam": "on_screen.py",
}


def open_app(q):
    """Launch an app by name, matched against OS-specific mappings."""
    app_map = APPS_WINDOWS if sys.platform.startswith("win") else APPS_LINUX
    ql = (q or "").strip().lower()
    for name, cmd in app_map.items():
        if name in ql or ql in name:
            subprocess.Popen(
                cmd, shell=True, start_new_session=True,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return
    if ql:
        subprocess.Popen(
            ql, shell=True, start_new_session=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )


def open_terminal(q=None):
    """Launch the terminal emulator directly."""
    app_map = APPS_WINDOWS if sys.platform.startswith("win") else APPS_LINUX
    cmd = app_map.get("terminal", "xterm&")
    subprocess.Popen(
        cmd, shell=True, start_new_session=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def left_click(q=None):
    pyautogui.click()


def right_click(q=None):
    pyautogui.rightClick()


def middle_click(q=None):
    pyautogui.middleClick()


def close_window(q=None):
    pyautogui.hotkey("alt", "F4")


def search_web(q):
    q = (q or "").strip()
    webbrowser.open("https://you.com/search?q=" + q.replace(" ", "%20"))


def go_to_website(q):
    q = (q or "").strip()
    # If it looks like a domain, prepend https://
    if not q.startswith("http"):
        q = "https://" + q
    webbrowser.open(q)


def send_email(q):
    q = (q or "").strip().replace(" at ", "@")
    os.popen(f'xdg-open "mailto://{q}"')


def draw_picture(q):
    os.popen(f'./sdapi.py "{q}"')


def show_webcam(q=None):
    global cam
    if not cam:
        cam = camera()
    cam.pipeline.set_state(cam.on)
    return cam


def hide_webcam(q=None):
    global cam
    if cam:
        cam = cam.stop_camera()


# ── Hotkey handlers ──────────────────────────────────────────────────
def hotkey_new_para(q=None):
    pyautogui.hotkey("shift", "enter")
    pyautogui.hotkey("shift", "enter")


def hotkey_new_line(q=None):
    pyautogui.hotkey("shift", "enter")


def hotkey_enter(q=None):
    pyautogui.hotkey("enter")


def hotkey_backspace(q=None):
    pyautogui.hotkey("backspace")


def hotkey_space(q=None):
    pyautogui.hotkey("space")


def hotkey_select_all(q=None):
    pyautogui.hotkey("ctrl", "a")


def hotkey_copy(q=None):
    pyautogui.hotkey("ctrl", "c")


def hotkey_cut(q=None):
    pyautogui.hotkey("ctrl", "x")


def hotkey_paste(q=None):
    pyautogui.hotkey("ctrl", "v")


def hotkey_undo(q=None):
    pyautogui.hotkey("ctrl", "z")


def hotkey_up(q=None):
    pyautogui.hotkey("up")


def hotkey_down(q=None):
    pyautogui.hotkey("down")


def hotkey_left(q=None):
    pyautogui.hotkey("left")


def hotkey_right(q=None):
    pyautogui.hotkey("right")


def hotkey_home(q=None):
    pyautogui.hotkey("home")


def hotkey_end(q=None):
    pyautogui.hotkey("end")


def hotkey_page_up(q=None):
    pyautogui.hotkey("pageup")


def hotkey_page_down(q=None):
    pyautogui.hotkey("pagedown")


def hotkey_ls(q=None):
    pyautogui.write("ls\n")


def ANSI_clear_line():
    """Check if the terminal supports ANSI escape codes."""
    # Get the TERM environment variable
    term = os.environ.get("TERM", "")

    # Common terms that indicate a compatible terminal
    compatible_terms = {
        "xterm",
        "xterm-256color",
        "rxvt",
        "rxvt-unicode",
        "rxvt-unicode-256color",
        "screen",
        "screen-256color",
        "tmux",
        "tmux-256color",
        "linux",
        "alacritty",
    }
    ANSI_delete_line = "\033[1K\r"

    # Check if the TERM environment variable indicates a compatible terminal
    return ANSI_delete_line if term in compatible_terms else "\b" * 99


bs = ANSI_clear_line()

# ── Piper TTS ────────────────────────────────────────────────────────
# Uses piper-tts Python API (piper-tts package, pip install piper-tts).
_piper_voice = None
_piper_player = None


def _find_piper_model():
    """Return path to a piper voice model, or None."""
    # 1. Explicit piper_model path in config
    path = cfg.get("piper_model", "")
    if path and os.path.isfile(path):
        return path
    # 2. Configured voice name → XDG_CACHE_HOME/piper/{voice}.onnx
    voice = cfg.get("piper_voice", "")
    if voice:
        pip_cache = os.path.join(
            os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")),
            "piper",
        )
        path = os.path.join(pip_cache, f"{voice}.onnx")
        if os.path.isfile(path):
            return path
    # 3. Common default locations
    candidates = [
        os.path.expanduser("~/piper-tts/voices/en_US-lessac-medium.onnx"),
        os.path.expanduser("~/piper-tts/voices/en_US-amy-medium.onnx"),
        os.path.expanduser("~/piper-tts/voices/en_US-ryan-medium.onnx"),
        "/usr/share/piper-tts/voices/en_US-lessac-medium.onnx",
        "/usr/local/share/piper-tts/voices/en_US-lessac-medium.onnx",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _find_player():
    """Return (path, name) for an audio playback binary, or (None, None)."""
    for name in ("paplay", "aplay", "pw-play"):
        path = shutil.which(name)
        if path:
            return (path, name)
    return (None, None)


def _load_piper_voice():
    """Lazy-load PiperVoice model, return True on success."""
    global _piper_voice
    if _piper_voice is not None:
        return True
    model = _find_piper_model()
    if not model:
        logging.warning("No piper voice model found. Set piper_model in config.")
        return False
    try:
        from piper import PiperVoice
        _piper_voice = PiperVoice.load(model)
        return True
    except Exception as e:
        logging.warning(f"Failed to load Piper voice: {e}")
        return False


def _speak_text(text):
    """Synthesize and play raw text (no markdown stripping)."""
    global _piper_player
    if not text.strip():
        return
    player_bin, player_name = _find_player()
    if not player_bin:
        return
    gen = _piper_voice.synthesize(text)
    try:
        first = next(gen)
    except StopIteration:
        return
    if player_name == "aplay":
        args = [player_bin, "-r", str(first.sample_rate), "-f", "S16_LE",
                "-c", str(first.sample_channels), "-t", "raw"]
    else:
        args = [player_bin, "--raw", "--rate", str(first.sample_rate),
                "--format", "s16le", "--channels", str(first.sample_channels)]
    try:
        player = subprocess.Popen(
            args, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        _piper_player = player
        player.stdin.write(first.audio_int16_bytes)
        for chunk in gen:
            player.stdin.write(chunk.audio_int16_bytes)
        player.stdin.close()
        player.wait()
    except BrokenPipeError:
        pass
    finally:
        if _piper_player == player:
            _piper_player = None


def _drain_audio(delay=1.0, remove_files=False):
    """Stop any echo recording, let TTS echo land, and drain the audio queue."""
    if record_process:
        record_process.stop_recording()
    time.sleep(delay)
    while True:
        try:
            f = audio_queue.get_nowait()
            if remove_files:
                try:
                    os.remove(f)
                except Exception:
                    pass
        except queue.Empty:
            break


def say(text, chunked=False):
    """Speak text via piper-tts.

    With chunked=True, speaks only the first paragraph and asks the user
    whether to continue with the rest via voice_dialog.
    """
    shutup()
    if not _load_piper_voice():
        return
    clean = re.sub(r"[*_#`~\[\]]", "", text)
    if chunked:
        paragraphs = [p.strip() for p in re.split(r'\n\n+', clean) if p.strip()]
        if len(paragraphs) > 1:
            _speak_text(paragraphs[0])
            remaining = '\n\n'.join(paragraphs[1:])
            word_count = len(remaining.split())
            response = voice_dialog(
                f"I can say about {word_count} more words on this topic. "
                "Do you want me to continue?",
                options=["yes", "no"],
            )
            if response == "yes":
                _speak_text(remaining)
            _drain_audio()
            return
    _speak_text(clean)
    _drain_audio()


def shutup():
    """Kill any currently playing piper utterance."""
    global _piper_player
    if _piper_player and _piper_player.poll() is None:
        _piper_player.terminate()
        try:
            _piper_player.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _piper_player.kill()
    _piper_player = None


def manage_whisper_service(action: str):
    """Start, stop, check, or install the whisper systemd user service.

    * ``start`` / ``stop`` — start or stop the service (no-op if absent).
    * ``check`` — return ``True`` if the ``whisper`` unit exists, else ``False``.
    * ``install`` — create the service file under
      ``~/.config/systemd/user/whisper.service`` and run ``daemon-reload``.
      No-op if the service is already installed.
    """
    if action not in ("start", "stop", "check", "install"):
        return

    # Is systemctl available at all?
    try:
        subprocess.run(
            ["systemctl", "--user", "--version"],
            capture_output=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return

    # ── check ────────────────────────────────────────────────────────
    if action == "check":
        try:
            r = subprocess.run(
                ["systemctl", "--user", "cat", "whisper"],
                capture_output=True, timeout=5,
            )
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    # ── install ──────────────────────────────────────────────────────
    if action == "install":
        # Already installed?
        try:
            r = subprocess.run(
                ["systemctl", "--user", "cat", "whisper"],
                capture_output=True, timeout=5,
            )
            if r.returncode == 0:
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return

        models_dir = os.environ.get("MODELS_DIR", "")
        model = "ggml-tiny.en.bin"
        model_path = os.path.join(models_dir, model) if models_dir else model

        if not models_dir or not os.path.isfile(model_path):
            print()
            print("  [whisper service] Could not install systemd unit.")
            print(f"  Set MODELS_DIR (currently {models_dir!r}) and make sure")
            print(f"  {model} is present before installing.")
            print()
            return

        unit_dir = os.path.expanduser("~/.config/systemd/user")
        os.makedirs(unit_dir, exist_ok=True)
        unit_path = os.path.join(unit_dir, "whisper.service")

        unit_content = f"""\
[Unit]
Description=Run Whisper server
Documentation=https://github.com/openai/whisper

[Service]
ExecStart=whisper-server -l en -m \\
 "{model_path}" \\
 --convert --port 7777

[Install]
WantedBy=default.target
"""
        with open(unit_path, "w") as f:
            f.write(unit_content)
        print(f"  Created {unit_path}")

        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True, timeout=10,
        )
        print(" This app will run 'systemctl --user start whisper' as needed.")
        print(" To optionally keep it running 24/7 type 'systemctl --user enable whisper'")
        return

    # ── start / stop ─────────────────────────────────────────────────
    # Only proceed if the unit actually exists.
    try:
        r = subprocess.run(
            ["systemctl", "--user", "cat", "whisper"],
            capture_output=True, timeout=5,
        )
        if r.returncode != 0:
            return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return

    # Don't stop a service the user explicitly wants always running.
    if action == "stop":
        try:
            r = subprocess.run(
                ["systemctl", "--user", "is-enabled", "whisper"],
                capture_output=True, timeout=5,
            )
            is_enabled = r.stdout.decode().strip() == "enabled"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            is_enabled = False
        if is_enabled:
            return

    subprocess.run(
        ["systemctl", "--user", action, "whisper"],
        capture_output=True, timeout=30,
    )


def on_screen():
    global cam
    if not cam:
        cam = camera()
    cam.pipeline.set_state(cam.on)
    return cam


def take_picture():
    global cam
    on = cam
    cam = on_screen()
    time.sleep(0.5)
    cam.take_picture()
    if not on:  # don't leave camera on, unless already on
        time.sleep(1.0)
        off_screen()


def off_screen():
    global cam
    if cam:
        cam = cam.stop_camera()


# ── Custom command lifecycle ─────────────────────────────────────────
def load_custom_commands():
    """Load custom commands from JSON, exec handlers, register in HANDLER_MAP.

    Returns the list of command entries that were loaded.
    """
    global custom_command_entries
    try:
        if not os.path.exists(CUSTOM_COMMANDS_FILE):
            return []
        with open(CUSTOM_COMMANDS_FILE) as f:
            entries = json.load(f)
        if not isinstance(entries, list):
            return []
        for entry in entries:
            exec(entry["handler_code"], globals())
            HANDLER_MAP[entry["command"]["handler"]] = globals()[
                entry["command"]["handler"]
            ]
        custom_command_entries = [e["command"] for e in entries]
        return custom_command_entries
    except Exception as e:
        logging.warning(f"Failed to load custom commands: {e}")
    return []


def propose_command(utterance):
    """Ask the local LLM to turn an unrecognized utterance into a shell command.

    Returns a dict with keys (intent, shell, desc) or None if the LLM
    thinks it's just dictation text.
    """
    try:
        # Use the same OpenAI-compatible endpoint as generate_text
        client = openai.OpenAI(
            base_url=local_chat_url, api_key="sk-no-key-required"
        )
        r = client.chat.completions.create(
            model=chat_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You classify spoken utterances. Reply with JSON only.\n\n"
                        "If the user wants a system action (run, open, record, "
                        "create, adjust, take, play, search, send, etc.), respond:\n"
                        '{"action": true, "intent": "short intent phrase", '
                        '"shell": "shell command to run", '
                        '"desc": "brief description of what it does"}\n\n'
                        'If it is just dictation text to type, respond:\n'
                        '{"action": false}\n\n'
                        "Examples:\n"
                        '"record a 30 second video"\n'
                        '  → {"action": true, "intent": "record video for 30 seconds", '
                        '"shell": "ffmpeg -f v4l2 -t 30 -i /dev/video0 '
                        '\\\\"$(date +%%s)\\\\".mp4", '
                        '"desc": "Record a 30-second video from webcam"}\n'
                        '"how are you today"\n'
                        '  → {"action": false}'
                    ),
                },
                {"role": "user", "content": utterance},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        text = r.choices[0].message.content.strip()
        # Extract JSON from response (the LLM may wrap it in markdown)
        if "{" in text:
            text = text[text.index("{") : text.rindex("}") + 1]
        result = json.loads(text)
        if result.get("action"):
            return result
    except Exception as e:
        logging.debug(f"Command proposal failed: {e}")
    return None


def save_custom_command(intent, handler_name, handler_code, argument):
    """Persist a custom command entry so it loads on next startup."""
    entry = {
        "command": {
            "intent": intent,
            "handler": handler_name,
            "argument": argument,
        },
        "handler_code": handler_code,
    }
    try:
        os.makedirs(os.path.dirname(CUSTOM_COMMANDS_FILE), exist_ok=True)
        entries = []
        if os.path.exists(CUSTOM_COMMANDS_FILE):
            with open(CUSTOM_COMMANDS_FILE) as f:
                entries = json.load(f)
        entries.append(entry)
        with open(CUSTOM_COMMANDS_FILE, "w") as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        logging.warning(f"Failed to save custom command: {e}")


def recognize_speech(f: str) -> str:
    result = [""]
    if f and os.path.isfile(f):
        try:
            with open(f, "rb") as file:
                files = {"file": (os.path.basename(f), file)}
                data = {"temperature": 0.2, "response_format": "json"}

                response = requests.post(whisper_cpp, files=files, data=data)
                response.raise_for_status()  # Raise an exception for HTTP errors

                result = response.json().get("text", "")
                return result

        except requests.exceptions.RequestException as e:
            logging.warning(f"{bs}Network or Server Problem: {e}")
            return ""
        except FileNotFoundError:
            logging.debug(f"{bs}File not found: {f}")
            return ""
        except Exception as e:
            logging.debug(f"{bs}An error occurred: {e}")
            return ""
    else:
        logging.debug(f"{bs}File does not exist or is not a file: {f}")
        return ""


print("Tab over to another window and start speaking.")
print("Text should appear in the window you are working in.")
print('Say "Stop listening." or press CTRL-C to stop.')
say("All systems ready.")

messages = [
    {
        "role": "system",
        "content": "In this conversation between `user:` and `assistant:`, play the role of assistant. Reply as a helpful assistant.",
    },
]


def generate_text(prompt: str):
    logging.debug(f"{bs}Querying {local_chat_url}")
    global conversation_length, chatting, messages
    global listening
    messages.append({"role": "user", "content": prompt})
    completion = ""

    try:
        local_client = openai.OpenAI(
            base_url=local_chat_url, api_key=chat_api_key
        )
        resp = local_client.chat.completions.create(
            model=chat_model, messages=messages
        )
        completion = resp.choices[0].message.content
    except Exception as e:
        logging.warning(f"Server Warning: {e}")
        return "Sorry. I'm having some trouble accessing that."

    if completion:
        # remove '<|...|>' tags from completion
        completion = re.sub(r"<\|.*\|>", "", completion)
        print(f"{bs}{completion}")
        # handle queries for more information
        if (
            "more information?" in completion
            or "It sounds like" in completion
            or "It seems like" in completion
            or "you tell me" in completion
            or "Could you please" in completion
            or "a large language model" in completion
            or completion == "< nooutput >"
        ):
            say("Sorry, I didn't catch that. Can you give me more information, please?")
            chatting = False  # allow dictation into the prompt box
            response = pyautogui.prompt(
                "More information, please.", "Please clarify.", prompt
            )
            # on user cancel, stop AI chat & resume dictation
            if not response:
                return None
            # otherwise, process the new query
            chatting = True
            return generate_text(response)
        pyautogui.write(completion)
        listening = False
        chatting = True
        say(completion, chunked=True)
        _drain_audio(0.3)
        chatting = False
        listening = True
        # add to conversation
        messages.append({"role": "assistant", "content": completion})
        if len(messages) > conversation_length:
            messages.remove(messages[1])
            messages.remove(messages[1])  # remove oldest user & assistant messages


def resume_dictation():
    global chatting, listening
    chatting = False
    listening = True


def pause_dictation(q=None):
    """Echo text but don't simulate keystrokes."""
    global listening
    listening = False


def stop_dictation(q=None):
    """Shut down the dictation system."""
    global running
    say("Shutting down.")
    running = False


def record_mp3():
    global listening
    listening = False
    say("Recording audio clip...")
    time.sleep(1)
    rec = delayRecord("audio.mp3")
    rec.start()
    say(f"Recording saved to {rec.file_name}")
    time.sleep(1)
    listening = True


# ── Provider / model voice selection ────────────────────────────────

_SPOKEN_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
    "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
}


def _spoken_to_number(phrase):
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


def _query_models(base_url):
    """Fetch model list from an OpenAI-compatible /v1/models endpoint."""
    try:
        r = requests.get(
            base_url.rstrip("/") + "/models",
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        # OpenAI returns {"data": [{"id": "..."}, ...]}
        # llama.cpp returns same format
        models = [m["id"] for m in data.get("data", []) if "id" in m]
        return sorted(models)
    except Exception as e:
        logging.warning(f"Failed to fetch models from {base_url}: {e}")
        return []


def _match_dialog_response(spoken, options):
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
    num = _spoken_to_number(spoken)
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


def voice_dialog(prompt, options=None, timeout=30):
    """Speak a prompt, listen for a spoken response, return the matched option.

    Temporarily takes over audio consumption from the transcription queue
    so the function blocks until a response, timeout, or cancel.

    Args:
        prompt: Text to speak via TTS (the question or menu listing)
        options: List of valid response strings to match against.
                 Supports number word -> digit conversion (e.g. "three" -> "3")
                 and yes/no fuzzy matching (e.g. "yeah" -> "yes", "nope" -> "no").
                 If None, accepts any spoken text.
        timeout: Max seconds to wait before returning None.

    Returns:
        The matched option string, or None if cancelled/timed out.
    """
    global listening
    was_listening = listening
    # Drain any lingering audio (TTS echo, previous utterance)
    listening = False
    _drain_audio(1.5, remove_files=True)
    listening = was_listening
    shutup()
    say(prompt)
    # Drain the echo of the prompt itself before listening for a response
    listening = False
    _drain_audio(1.5, remove_files=True)
    listening = was_listening
    start = time.time()
    while time.time() - start < timeout:
        try:
            f = audio_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        txt = recognize_speech(f)
        try:
            os.remove(f)
        except Exception:
            pass
        if not txt:
            continue
        txt = re.sub(r"(^|\n)\s", r"\1", txt)
        if re.search(r"[\(\[\*]", txt):
            txt = re.sub(r"[\*\[\(][^\]\)]*[\]\)\*]*\s*$", "", txt)
        lower_case = txt.lower().strip()
        print(bs + (txt.strip() or lower_case))
        if not lower_case:
            continue
        matched = _match_dialog_response(lower_case, options)
        if matched == "__CANCEL__":
            return None
        if matched:
            return matched
        say("I didn't understand. Please try again.")
        # Drain the echo of that message before re-listening
        listening = False
        _drain_audio(1.5, remove_files=True)
        listening = True
    return None


def switch_provider(q=None):
    """List configured providers and wait for a number choice."""
    global listening
    providers = cfg.get("providers", [])
    if not providers:
        say("No providers configured.")
        return
    print("\nAvailable providers:")
    for i, p in enumerate(providers, 1):
        print(f"  {i}. {p['name']}  ({p['base_url']})")
    options = [str(i) for i in range(1, len(providers) + 1)]
    response = voice_dialog("Say a number to select a provider.", options=options)
    if not response:
        return
    provider = providers[int(response) - 1]
    models = _query_models(provider["base_url"])
    if not models:
        say("No models found on that provider.")
        return
    print("\nAvailable models:")
    for i, m in enumerate(models, 1):
        print(f"  {i}. {m}")
    options = [str(i) for i in range(1, len(models) + 1)]
    response = voice_dialog("Say a number to select a model.", options=options)
    if not response:
        return
    model = models[int(response) - 1]
    global local_chat_url, chat_model, chat_api_key
    base_url = provider["base_url"]
    api_key = provider.get("api_key", "sk-no-key-required")
    local_chat_url = base_url
    chat_model = model
    chat_api_key = api_key
    update_config({"chat_url": base_url, "chat_model": model})
    say(f"Switched to {model} on {provider['name']}.")


def switch_model(q=None):
    """Fetch models from the current provider and wait for a number choice."""
    models = _query_models(local_chat_url)
    if not models:
        say("No models found on current provider.")
        return
    print("\nAvailable models:")
    for i, m in enumerate(models, 1):
        print(f"  {i}. {m}")
    options = [str(i) for i in range(1, len(models) + 1)]
    response = voice_dialog("Say a number to select a model.", options=options)
    if not response:
        return
    model = models[int(response) - 1]
    global chat_model
    chat_model = model
    update_config({"chat_model": model})
    say(f"Switched to {model}.")


# Auto-built from command tables — resolves handler names to functions
HANDLER_MAP = {h: globals()[h] for h in set(
    cmd["handler"] for cmd in COMMANDS
    if cmd["handler"] in globals()
)}

# Load persisted custom commands (if any) into HANDLER_MAP
load_custom_commands()

# Initialize semantic command matcher (built-in + custom entries)
matcher = Matcher(
    COMMANDS + custom_command_entries,
    embed_url=cfg.get("embed_url", "http://127.0.0.1:8080/v1/embeddings"),
    threshold=cfg.get("threshold", 0.45),
    embed_model=cfg.get("embed_model", ""),
)


def transcribe():
    global listening, chatting
    while True:
        try:
            # transcribe audio from queue
            if f := audio_queue.get():
                txt = recognize_speech(f)
                # delete temporary audio file
                try:
                    os.remove(f)
                except Exception:
                    pass
                if not txt:
                    continue
                # skip first transcription (pipeline noise at startup)
                global _first_utterance
                if _first_utterance:
                    _first_utterance = False
                    continue
                # filter space at beginning of lines
                txt = re.sub(r"(^|\n)\s", r"\1", txt)
                # print messages [BLANK_AUDIO], (swoosh), *barking*
                if re.search(r"[\(\[\*]", txt):
                    print(bs + txt.strip())
                    # filter it out
                    txt = re.sub(r"[\*\[\(][^\]\)]*[\]\)\*]*\s*$", "", txt)
                # get lower-case spoken command string
                lower_case = txt.lower().strip()
                if not lower_case:
                    continue
                shutup()  # stop bot from talking
                if match := re.search(r"[^\w\s]$", lower_case):
                    lower_case = lower_case[: match.start()]  # remove punctuation
                # strip txt unless we specifically say "new paragraph"
                txt = txt.strip(" \n") + " "
                print(bs + txt)  # print the text

                # — Semantic command matching —
                result = matcher.match(lower_case)
                if result:
                    handler_name, arg, score = result
                    if debug:
                        print(f"[DEBUG] matched '{handler_name}' (score={score:.3f})")
                    handler_fn = HANDLER_MAP.get(handler_name)
                    if handler_fn:
                        if handler_name != "stop_dictation":
                            say("okay")
                        handler_fn(arg)
                        if not running:
                            break
                        continue

                # — LLM command proposal (unrecognized → ask LLM) —
                # Only trigger when a wake word is used, so dictation
                # text doesn't hit the LLM on every utterance.
                has_wake = re.search(r"^(peter|samantha|computer)[,\s]",
                                     lower_case)
                if not chatting and has_wake:
                    # Strip wake word before sending to LLM
                    proposal = propose_command(
                        re.sub(r"^(peter|samantha|computer)[,\s]+",
                               "", lower_case, flags=re.I)
                    )
                    if proposal:
                        handler_name = "custom_" + re.sub(
                            r"\W+", "_", proposal["intent"]
                        ).lower().strip("_")
                        shell = proposal["shell"]
                        handler_code = (
                            f"def {handler_name}(q=None):\n"
                            f'    subprocess.Popen({shell!r},\n'
                            f"        shell=True, start_new_session=True,\n"
                            f"        stdin=subprocess.DEVNULL,\n"
                            f"        stdout=subprocess.DEVNULL,\n"
                            f"        stderr=subprocess.DEVNULL)\n"
                        )
                        print(f"\n[{proposal['desc']}]")
                        print(f"  Shell: {shell}")
                        print(f"  Intent: {proposal['intent']}")
                        response = voice_dialog("Run this command?", options=["yes", "no"])
                        if response == "yes":
                            exec(handler_code, globals())
                            HANDLER_MAP[handler_name] = globals()[handler_name]
                            save_custom_command(
                                proposal["intent"], handler_name,
                                handler_code, None,
                            )
                            matcher.add_command(proposal["intent"], handler_name)
                            say("okay")
                            HANDLER_MAP[handler_name]()
                        else:
                            say("Cancelled.")
                        continue

                # If a wake word was spoken but the LLM didn't propose
                # a command, treat it as an AI chat query.
                if has_wake:
                    if not chatting:
                        chatting = True
                    lower_case = re.sub(r"^(peter|samantha|computer)[,\s]+",
                                        "", lower_case, flags=re.I)
                    # fall through to AI chat handler below

                # — AI chat fallback —
                if chatting:
                    generate_text(lower_case)
                    # After LLM response, reset to dictation mode
                    chatting = False
                    listening = True
                    continue
                # — Dictation —
                if not listening:
                    continue
                if len(txt) > 1:
                    pyautogui.write(txt.replace("\n", " "))
            # continue looping
        except KeyboardInterrupt:
            say("Goodbye.")
            break


def record_to_queue():
    global record_process
    global running
    while running:
        if not listening:
            time.sleep(0.05)
            continue
        record_process = delayRecord(tempfile.mktemp() + audio_format)
        record_process.start()
        audio_queue.put(record_process.file_name)


def discard_input():
    """Discard any pending terminal input without waiting for Enter.
    Works on POSIX (uses tcflush when stdin is a tty; falls back to nonblocking read)
    and on Windows (uses msvcrt). Safe to call if stdin is not a tty."""
    try:
        if os.name == "nt":
            import msvcrt

            while msvcrt.kbhit():
                msvcrt.getwch()  # consume wide char; use getch() for bytes
        else:  # POSIX
            fd = sys.stdin.fileno()
            if sys.stdin.isatty():
                # use termios.tcflush when available
                try:
                    from termios import tcflush, TCIFLUSH

                    tcflush(fd, TCIFLUSH)
                    return
                except Exception:
                    pass
            # fallback: nonblocking read to drain whatever is available
            import fcntl
            import errno

            orig_fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            try:
                fcntl.fcntl(fd, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)
                try:
                    while True:
                        chunk = os.read(fd, 4096)
                        if not chunk:
                            break
                except OSError as e:
                    if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                        raise
            finally:
                fcntl.fcntl(fd, fcntl.F_SETFL, orig_fl)

    except Exception:
        print("Quitting.")
        # best-effort: if everything fails, try to consume one line (may block)
        try:
            sys.stdin.readline()
        except Exception:
            pass
    print("Goodbye.")


def quit():
    logging.debug("\nStopping...")
    global running
    global listening
    listening = False
    running = False
    if record_process:
        record_process.stop_recording()
    record_thread.join()
    # clean up
    try:
        while f := audio_queue.get_nowait():
            logging.debug(f"{bs}Removing temporary file: {f}")
            if f[:5] == "/tmp/":  # safety check
                os.remove(f)
    except Exception:
        pass
    logging.debug("\nFreeing system resources.\n")
    manage_whisper_service("stop")
    discard_input()
    time.sleep(1.0)
    shutup()
    print()


if __name__ == "__main__":
    # ── First-run: offer to install the whisper systemd service ──────
    if first_run and sys.stdin.isatty():
        if not manage_whisper_service("check"):
            print()
            print("  It looks like the whisper-server systemd service is not installed.")
            resp = input("  Install it now? [Y/n] ").strip().lower()
            if resp in ("", "y", "yes"):
                manage_whisper_service("install")

    record_thread = threading.Thread(target=record_to_queue)
    manage_whisper_service("start")
    record_thread.start()
    transcribe()
    quit()
