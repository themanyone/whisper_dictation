#!.venv/bin/python
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
import pyperclip
import os
import time
import queue
import sys
import re
import openai
import webbrowser
import tempfile
import threading
import subprocess, signal
import requests
import logging
from mimic3_client import say

logging.basicConfig(
	level=logging.INFO,
	format="[%(levelname)s] %(lineno)d %(message)s",
	handlers=[
#		logging.FileHandler('/tmp/rec.log'),
		logging.StreamHandler()
	]
)
# address of whisper.cpp server
cpp_url = "http://127.0.0.1:7777/inference"
# address of Fallback Chat Server.
fallback_chat_url = "http://localhost:8888/v1"
debug = False

api_key = os.getenv("OPENAI_API_KEY")
if (api_key):
    openai.api_key = api_key
else:
    logging.debug("Export OPENAI_API_KEY if you want answers from ChatGPT.\n")

# commands and hotkeys for various platforms
commands = {
"windows": {
    "file manager":  "start explorer",
    "terminal":     "start cmd",
    "browser":      "start iexplore",
    "web browser":  "start iexplore",
    },

"linux": {
    "file manager":  "nemo --no-desktop&",
    "terminal":     "xterm -bg gray20 -fg gray80 -fa 'Liberation Sans Mono' -fs 12 -rightbar&",
    "browser":      "htmlview&",
    "web browser":   "htmlview&",
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
    r"^(click)( the)?( mouse).? ": "pyautogui.click()",
    r"^middle click.?$": "pyautogui.middleClick()",
    r"^right click.?$": "pyautogui.rightClick()",
    r"^(peter|samantha|computer).? (run|open|start|launch)(up)?( a| the)? ": "os.system(commands[sys.platform][q])",
    r"^(peter|samantha|computer).? closed? window": "pyautogui.hotkey('alt', 'F4')",
    r"^(peter|samantha|computer).? search( the)?( you| web| google| bing| online)?(.com)? for ": 
       "webbrowser.open('https://you.com/search?q=' + re.sub(' ','%20',q))",
    r"^(peter|samantha|computer).? (send|compose|write)( an| a) email to ": "os.popen('xdg-open \"mailto://' + q.replace(' at ', '@') + '\"')",
    r"^(peter|samantha|computer).? (i need )?(let's )?(see |have |show )?(us |me )?(an? )?(image|picture|draw|create|imagine|paint)(ing| of)? ": "os.popen(f'./sdapi.py \"{q}\"')",
    r"^(peter|samantha|computer).? (resume|zoom|continue|start|type) (typing|d.ctation|this)" : "exec('global chatting;global listening;chatting = False;listening = True')",
    r"^(peter|samantha|computer).? ": "chatGPT(q)"
    }

def process_actions(tl:str) -> bool:
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
        chatGPT(tl); return True
    return False # no action

# fix race conditions
audio_queue = queue.Queue()
listening = True
chatting = False

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

def pastetext(t:str):
    # filter (noise), (hiccups), *barking* and [system messages]
    t = re.sub(r'(\s*[\*\[\(][^\]\)]*[\]\)\*])*', '', t)
    if not t or t == " you" or t == " Thanks for watching!":
        return # ignoring you
    pyperclip.copy(t) # weird that primary won't work the first time
    if pyautogui.platform.system() == "Linux":
        pyperclip.copy(t, primary=True) # now it works
        pyautogui.middleClick()
    else:
        pyautogui.hotkey('ctrl', 'v')

print("Start speaking. Text should appear in the window you are working in.")
print("Say \"Stop listening.\" or press CTRL-C to stop.")
say("Computer ready.")

messages = [{ "role": "system", "content": "In this conversation between `user:` and `assistant:`, play the role of assistant. Reply as a helpful assistant." },]

def chatGPT(prompt: str):
    logging.debug("ChatGPT called") 
    global chatting, messages
    messages.append({"role": "user", "content": prompt})
    completion = ""
    # Call chatGPT
    if api_key:
        try:
            completion = openai.ChatCompletion.create(
              model="gpt-3.5-turbo",
              messages=messages
            )
            completion = completion.choices[0].message.content
        except Exception as e:
                logging.debug("ChatGPT had a problem. Here's the error message.")
                logging.debug(e)
                
    # Fallback to localhost
    if not completion:
        # ref. llama.cpp/examples/server/README.md
        client = openai.OpenAI(
            base_url=fallback_chat_url,
            api_key = "sk-no-key-required")
        
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        completion = completion.choices[0].message.content
 
    if completion:
        if completion == "< nooutput >": completion = "No comment."
        print(completion)
        pastetext(completion)
        say(completion)
        chatting = True
        # add to conversation
        messages.append({"role": "assistant", "content": completion})
        if len(messages) > 9:
            messages.remove(messages[1])
            messages.remove(messages[1])

def transcribe():
    global listening
    while True:
        try:
            # transcribe audio from queue
            if f := audio_queue.get():
                t = gettext(f).strip()
                # delete temporary audio file
                try: os.remove(f)
                except Exception: pass
                if not t: break
                print(t)

                # get lower-case spoken command string
                lower_case = t.lower()
                if match := re.search(r"[^\w\s]$", lower_case):
                    lower_case = lower_case[:match.start()] # remove punctuation

                # see list of actions and hotkeys at top of file :)
                # Go to Website.
                if s:=re.search(r"^(peter|computer).? (go|open|browse|visit|navigate)( up| to| the| website)* [a-zA-Z0-9-]{1,63}(\.[a-zA-Z0-9-]{1,63})+$", lower_case):
                    q = lower_case[s.end():] # get q for command
                    webbrowser.open('https://' + q.strip())
                    continue
                # Stop dictation.
                elif re.search(r"^.?stop.(d.ctation|listening).?$", lower_case):
                    say("Shutting down.")
                    break
                elif re.search(r"^.?(pause.d.ctation|positi.?i?cation).?$", lower_case):
                    listening = False
                    say("okay")
                elif process_actions(lower_case): continue
                if not listening: continue
                elif process_hotkeys(lower_case): continue
                else:
                    now = time.time()
                    start = now; pastetext(t + ' ')
            # continue looping every 1/5 second
            else: time.sleep(0.2)
        except KeyboardInterrupt:
            say("Goodbye.")
            break

def record_to_queue():
    from record import delayRecord
    global record_process
    global running
    while running:
        record_process = delayRecord(tempfile.mktemp()+ '.wav')
        record_process.start()
        audio_queue.put(record_process.file_name)

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

if __name__ == '__main__':
    record_process = None
    running = True
    record_thread = threading.Thread(target=record_to_queue)
    record_thread.start()
    transcribe()
    quit()
