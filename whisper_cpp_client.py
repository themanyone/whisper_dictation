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
from openai import OpenAI

import webbrowser
import tempfile
import threading
import requests
import logging
from mimic3_client import say, shutup
from on_screen import camera, show_pictures
from record import delayRecord
from commands_table import COMMANDS
from matcher import Matcher
from config import get_config

audio_queue = queue.Queue()
listening = True
chatting = False
record_process = None
running = True
cam = None

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(lineno)d %(message)s",
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
debug = cfg.get("debug", False)

gpt_key = cfg.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
gem_key = cfg.get("gemini_api_key") or os.getenv("GENAI_TOKEN")

client = None
if gpt_key:
    kwargs = {"api_key": gpt_key}
    if cfg.get("openai_base_url"):
        kwargs["base_url"] = cfg["openai_base_url"]
    client = OpenAI(**kwargs)
else:
    logging.debug("Export OPENAI_API_KEY if you prefer answers from ChatGPT.\n")
if gem_key:
    import google.generativeai as genai

    genai.configure(api_key=gem_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    logging.debug("Export GENAI_TOKEN if you prefer answers from Gemini.\n")

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
    pyautogui.hotkey("enter")
    pyautogui.hotkey("enter")


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
    logging.debug(f"{bs}Asking ChatGPT")
    global conversation_length, chatting, messages
    global listening, gpt_key, gem_key, client
    messages.append({"role": "user", "content": prompt})
    completion = ""
    # Try chatGPT
    if gpt_key:
        try:
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo", messages=messages
            )
            completion = completion.choices[0].message.content
        except Exception as e:
            logging.warning("ChatGPT had a problem.")
            logging.warning(e)

    # Fallback to Google Gemini
    elif gem_key and not completion:
        logging.debug("Asking Gemini")
        try:
            chat = model.start_chat(
                history=[
                    {
                        "role": "user" if x["role"] == "user" else "model",
                        "parts": x["content"],
                    }
                    for x in messages
                ]
            )
            response = chat.send_message(prompt)
            completion = response.text
        except Exception as e:
            logging.warning("Gemini had a problem.")
            logging.warning(e)

    # Fallback to localhost
    if not completion:
        logging.debug(f"Querying {local_chat_url}")
        # ref. llama.cpp/examples/server/README.md
        try:
            client = openai.OpenAI(
                base_url=local_chat_url, api_key="sk-no-key-required"
            )
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo", messages=messages
            )
        except Exception as e:
            logging.warning(f"Local Server Warning: {e}")
            return "Sorry. I'm having some trouble accessing that."
        completion = completion.choices[0].message.content

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
        say(completion)
        # add to conversation
        messages.append({"role": "assistant", "content": completion})
        if len(messages) > conversation_length:
            messages.remove(messages[1])
            messages.remove(messages[1])  # remove oldest user & assistant messages


def resume_dictation():
    global chatting, listening
    chatting = False
    listening = True


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


# Map handler names from commands_table.py → actual functions
HANDLER_MAP = {
    "left_click": left_click,
    "right_click": right_click,
    "middle_click": middle_click,
    "open_app": open_app,
    "open_terminal": open_terminal,
    "close_window": close_window,
    "search_web": search_web,
    "go_to_website": go_to_website,
    "send_email": send_email,
    "draw_picture": draw_picture,
    "resume_dictation": resume_dictation,
    "record_mp3": record_mp3,
    "show_webcam": show_webcam,
    "hide_webcam": hide_webcam,
    "take_picture": take_picture,
    "show_pictures": show_pictures,
    "hotkey_new_para": hotkey_new_para,
    "hotkey_enter": hotkey_enter,
    "hotkey_backspace": hotkey_backspace,
    "hotkey_space": hotkey_space,
    "hotkey_select_all": hotkey_select_all,
    "hotkey_copy": hotkey_copy,
    "hotkey_cut": hotkey_cut,
    "hotkey_paste": hotkey_paste,
    "hotkey_undo": hotkey_undo,
    "hotkey_up": hotkey_up,
    "hotkey_down": hotkey_down,
    "hotkey_left": hotkey_left,
    "hotkey_right": hotkey_right,
    "hotkey_home": hotkey_home,
    "hotkey_end": hotkey_end,
    "hotkey_page_up": hotkey_page_up,
    "hotkey_page_down": hotkey_page_down,
    "hotkey_ls": hotkey_ls,
    "generate_text": generate_text,
}

# Initialize semantic command matcher
matcher = Matcher(
    COMMANDS,
    embed_url=cfg.get("embed_url", "http://127.0.0.1:8088/v1/embeddings"),
    threshold=cfg.get("threshold", 0.45),
)


def transcribe():
    global listening
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
                # filter space at beginning of lines
                txt = re.sub(r"(^|\n)\s", r"\1", txt)
                # print messages [BLANK_AUDIO], (swoosh), *barking*
                if re.search(r"[\(\[\*]", txt):
                    print(bs + txt.strip())
                    # filter it out
                    txt = re.sub(r"[\*\[\(][^\]\)]*[\]\)\*]*\s*$", "", txt)
                if txt == " " or txt == "you " or txt == "Thanks for watching! ":
                    continue  # ignoring you
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

                # Stop dictation (special case — breaks the loop).
                if re.search(r"^stop.? (d.ctation|listening).?$", lower_case):
                    say("Shutting down.")
                    break
                # — Semantic command matching —
                result = matcher.match(lower_case)
                if result:
                    handler_name, arg, score = result
                    if debug:
                        print(f"[DEBUG] matched '{handler_name}' (score={score:.3f})")
                    handler_fn = HANDLER_MAP.get(handler_name)
                    if handler_fn:
                        say("okay")
                        handler_fn(arg)
                        continue
                # — AI chat fallback —
                if chatting:
                    generate_text(lower_case)
                    continue
                # — Dictation —
                if not listening:
                    continue
                if len(txt) > 1:
                    pyautogui.write(txt)
            # continue looping
        except KeyboardInterrupt:
            say("Goodbye.")
            break


def record_to_queue():
    global record_process
    global running
    while running:
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
    #    os.system("systemctl --user stop whisper")
    discard_input()
    time.sleep(1.0)
    shutup()


if __name__ == "__main__":
    record_thread = threading.Thread(target=record_to_queue)
    #    os.system("systemctl --user start whisper")
    record_thread.start()
    transcribe()
    quit()
