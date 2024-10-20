#!/usr/bin/python
# -*- coding: utf-8 -*-
##
## Copyright 2023 Henry Kroll <nospam@thenerdshow.com>
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
import pyautogui
import os, sys
import time
import queue
import re
from openai import OpenAI

import webbrowser
import tempfile
import threading
import requests
import logging
import tracer
from mimic3_client import say, shutup
from on_screen import camera, show_pictures
from record import delayRecord
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
#		logging.FileHandler('/tmp/whisper_cpp_client.log'),
		logging.StreamHandler()
	]
)
# address of whisper.cpp server
cpp_url = "http://127.0.0.1:7777/inference"
# address of Fallback Chat Server.
fallback_chat_url = "http://localhost:8888/v1"
debug = False

gpt_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=gpt_key)
if not (gpt_key):
    logging.debug("Export OPENAI_API_KEY if you want answers from ChatGPT.\n")
gem_key = os.getenv("GENAI_TOKEN")
if (gem_key):
    import google.generativeai as genai
    genai.configure(api_key=gem_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    logging.debug("Export GENAI_TOKEN if you want answers from Gemini.\n")

# commands and hotkeys for various platforms
commands = {
"windows": {
    "file manager":  "start explorer",
    "terminal":     "start cmd",
    "browser":      "start iexplore",
    "web browser":  "start iexplore",
    "webcam":       "on_screen.py",
    },

"linux": {
    "file manager":  "nemo --no-desktop&",
    "terminal":     "xterm -bg gray20 -fg gray80 -fa 'Liberation Sans Mono' -fs 12 -rightbar&",
    "browser":      "htmlview&",
    "web browser":   "htmlview&",
    "webcam":       "./on_screen.py",
    },
}
hotkeys = {
    r"^new paragraph.?$": [['enter'],['enter']],
    r"^new line.?$":     [['enter']],
    r"^page up.?$":     	[['pageup']],
    r"^page down.?$":    [['pagedown']],
    r"^undo that.?$":    [['ctrl', 'z']],
    r"^copy that.?$":    [['ctrl', 'c']],
    r"^paste it.?$":     [['ctrl', 'v']],
    }
actions = {
    r"^left click.?$": "pyautogui.click()",
    r"^(click)( the)?( mouse).?": "pyautogui.click()",
    r"^middle click.?$": "pyautogui.middleClick()",
    r"^right click.?$": "pyautogui.rightClick()",
    r"^directory listing.?$": "pyautogui.write('ls\n')",
    r"^(peter|samantha|computer).?,? (run|open|start|launch)(up)?( a| the)? ": "os.system(commands[sys.platform][q])",
    r"^(peter|samantha|computer).?,? closed? window": "pyautogui.hotkey('alt', 'F4')",
    r"^(peter|samantha|computer).?,? search( the)?( you| web| google| bing| online)?(.com)? for ": 
       "webbrowser.open('https://you.com/search?q=' + re.sub(' ','%20',q))",
    r"^(peter|samantha|computer).?,? (send|compose|write)( an| a) email to ": "os.popen('xdg-open \"mailto://' + q.replace(' at ', '@') + '\"')",
    r"^(peter|samantha|computer).?,? (i need )?(let's )?(see |have |show )?(us |me )?(an? )?(image|picture|draw|create|imagine|paint)(ing| of)? ": "os.popen(f'./sdapi.py \"{q}\"')",
    r"^(peter|samantha|computer)?.?,? ?(resume|zoom|continue|start|type|thank|got|whoa|that's) (typing|d.ctation|this|you|there|enough|it)" : "resume_dictation()",
    r"^(peter|samantha|computer)?.?,? ?(record)( a| an)?( audio| sound| voice| file| clip)+" : "record_mp3()",
    r"^(peter|samantha|computer)?.?,? ?(on|show|start|open) (the )?(webcam|camera|screen)" : "on_screen()",
    r"^(peter|samantha|computer)?.?,? ?(off|stop|close) (the )?(webcam|camera|screen)" : "off_screen()",
    r"^(peter|samantha|computer)?.?,? ?(take|snap) (a|the|another) (photo|picture)" : "take_picture()",
    r"^(peter|samantha|computer)?.?,? ?(show|view) (the )?(photo|photos|pictures)( album| collection)?" : "show_pictures()",
    r"^(peter|samantha|computer).?,? ": "generate_text(q)"
    }

def process_actions(tl:str) -> bool:
    global chatting
    global listening
    for input, action in actions.items():
        # look for action in list
        if s:=re.search(input, tl):
            q = tl[s.end():] # get q for action
            say("okay")
            eval(action)
            if debug:
                print(q)
            return True # success
    if chatting:
        generate_text(tl); return True
    return False # no action

def on_screen():
    global cam
    if not cam: cam = camera()
    cam.pipeline.set_state(cam.on)
    return cam

def take_picture():
    global cam
    on = cam
    cam = on_screen()
    time.sleep(0.5)
    cam.take_picture()
    if not on: # don't leave camera on, unless already on
        time.sleep(1.0)
        off_screen()

def off_screen():
    global cam
    if cam: cam = cam.stop_camera()

# search text for hotkeys
def process_hotkeys(txt: str) -> bool:
    for key,val in hotkeys.items():
        # if hotkey command
        if re.search(key, txt):
            # unpack list of key combos such as ctrl-v
            for x in val:
                # press each key combo in turn
                # The * unpacks x to separate args
                pyautogui.hotkey(*x)
            return True
    return False

def gettext(f:str) -> str:
    result = ['']
    if f and os.path.isfile(f):
        files = {'file': (f, open(f, 'rb'))}
        data = {'temperature': '0.2', 'response_format': 'json'}

        try:
            response = requests.post(cpp_url, files=files, data=data)
            response.raise_for_status()  # Check for errors

            # Parse the JSON response
            result = [response.json()]
            return result[0]['text']

        except requests.exceptions.RequestException as e:
            logging.debug(f"Error: {e}")
            return ""
        return ""

print("Start speaking. Text should appear in the window you are working in.")
print("Say \"Stop listening.\" or press CTRL-C to stop.")
say("All systems ready.")

messages = [{ "role": "system", "content": "In this conversation between `user:` and `assistant:`, play the role of assistant. Reply as a helpful assistant." },]

def generate_text(prompt: str):
    conversation_length = 9 # try increasing if AI model has a large ctx window
    logging.debug("Asking ChatGPT") 
    global chatting, messages, gpt_key, gem_key
    messages.append({"role": "user", "content": prompt})
    completion = ""
    # Try chatGPT
    if gpt_key:
        try:
            completion = client.chat.completions.create(model="gpt-3.5-turbo",
            messages=messages)
            completion = completion.choices[0].message.content
        except Exception as e:
                logging.debug("ChatGPT had a problem. Here's the error message.")
                logging.debug(e)

    # Fallback to Google Gemini
    elif gem_key and not completion:
        logging.debug("Asking Gemini")
        chat = model.start_chat(
            history=[
            {"role": "user" if x["role"] == "user" else "model",
                "parts": x["content"]}for x in messages]
        )
        response = chat.send_message(prompt)
        completion = response.text

    # Fallback to localhost
    if not completion:
        logging.debug(f"Querying {fallback_chat_url}")
        # ref. llama.cpp/examples/server/README.md
        try:
            client = openai.OpenAI(
            base_url=fallback_chat_url,
            api_key = "sk-no-key-required")
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
        except Exception as e:
            logging.debug(f"Error: {e}")
            return "Sorry. I'm having some trouble accessing that."
        completion = completion.choices[0].message.content

    if completion:
        print(completion)
        # handle queries for more information
        if "more information?" in completion or \
            "It sounds like" in completion or \
            "It seems like" in completion or \
            "you tell me" in completion or \
            "Could you please" in completion or \
            "a large language model" in completion or \
            completion == "< nooutput >":
            say("Sorry, I didn't catch that. Can you give me more information, please?")
            chatting = False # allow dictation into the prompt box
            response = pyautogui.prompt("More information, please.",
            "Please clarify.", prompt)
            # on user cancel, stop AI chat & resume dictation
            if not response: return None
            # otherwise, process the new query
            chatting = True
            return generate_text(response)
        pyautogui.write(completion)
        say(completion)
        chatting = True
        # add to conversation
        messages.append({"role": "assistant", "content": completion})
        if len(messages) > conversation_length:
            messages.remove(messages[1])
            messages.remove(messages[1])

def resume_dictation():
    global chatting, listening
    chatting = False
    listening = True

def transcribe():
    global listening
    while True:
        try:
            # transcribe audio from queue
            if f := audio_queue.get():
                txt = gettext(f)
                # delete temporary audio file
                try: os.remove(f)
                except Exception: pass
                if not txt: continue
                print(txt.strip('\n')) # print the text, in case we filter something important
                # filter (noise), (hiccups), *barking* and [system messages]
                txt = re.sub(r'(^\s)|(\s*[\*\[\(][^\]\)]*[\]\)\*])*\s*$', '', txt)
                if txt == ' ' or txt == "you " or txt == "Thanks for watching! ":
                    continue # ignoring you
                # get lower-case spoken command string
                lower_case = txt.lower().strip()
                if not lower_case: continue
                shutup() # stop bot from talking
                if match := re.search(r"[^\w\s]$", lower_case):
                    lower_case = lower_case[:match.start()] # remove punctuation
                    txt += ' ' # add space
                # see list of actions and hotkeys at top of file :)
                # Go to Website.
                if s:=re.search(r"^(peter|computer).? (go|open|browse|visit|navigate)( up| to| the| website)* [a-zA-Z0-9-]{1,63}(\.[a-zA-Z0-9-]{1,63})+$", lower_case):
                    q = lower_case[s.end():] # get q for command
                    webbrowser.open('https://' + q.strip())
                    continue
                # Stop dictation.
                elif re.search(r"^stop.? (d.ctation|listening).?$", lower_case):
                    say("Shutting down.")
                    break
                elif re.search(r"^paused? (d.ctation|positi.?i?cation).?$", lower_case):
                    listening = False
                    say("okay")
                elif process_actions(lower_case): continue
                if not listening: continue
                elif process_hotkeys(lower_case): continue
                else:
                    pyautogui.write(txt)
            # continue looping every 1/5 second
            else: time.sleep(0.2)
        except KeyboardInterrupt:
            say("Goodbye.")
            break

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

def record_to_queue():
    global record_process
    global running
    while running:
        record_process = delayRecord(tempfile.mktemp()+ '.wav')
        record_process.start()
        audio_queue.put(record_process.file_name)

def discard_input():
    print("\nShutdown complete. Press ENTER to return to terminal.")
    pyautogui.write("\n")
    while input(""):
        time.sleep(0.1)

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
            logging.debug(f"Removing temporary file: {f}")
            if f[:5] == "/tmp/": # safety check
                os.remove(f)
    except Exception: pass
    logging.debug("\nFreeing system resources.\n")
    discard_input()
    shutup()

if __name__ == '__main__':
    record_thread = threading.Thread(target=record_to_queue)
    record_thread.start()
    transcribe()
    quit()
