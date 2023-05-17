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
import os, shlex, time, queue, sys, re
import webbrowser
import tempfile
import threading
import subprocess
import requests
import json

# address of Fallback Chat Server.
url = 'http://localhost:5000'
api_key = os.getenv("OPENAI_API_KEY")

if (api_key):
    import openai
    openai.api_key = api_key
else:
    print("Export OPENAI_API_KEY if you want answers from ChatGPT.")

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
    "^new paragraph.?$": [['enter'],['enter']],
    "^page up.?$":     [['pageup']],
    "^page down.?$":    [['pagedown']],
    "^undo that.?$":    [['ctrl', 'z']],
    "^copy that.?$":    [['ctrl', 'c']],
    "^paste it.?$":     [['ctrl', 'v']],
    }
actions = {
    "^left click.?$": "pyautogui.click()",
    "^(peter|computer).? (run|open|start|launch)(up)?( a| the)? ": "os.system(commands[sys.platform][q])",
    "^(peter|computer).? closed? window": "pyautogui.hotkey('alt', 'F4')",
    "^(peter|computer).? search( the)?( you| web| google| bing| online)?(.com)? for ": 
        "webbrowser.open('https://you.com/search?q=' + re.sub(' ','%20',q))",
    "^(peter|computer).? ": "pyautogui.hotkey('alt', 'F4')",
    "^(peter|computer).? ": "chatGPT(q)",
    "^(click)( the)?( mouse).? ": "pyautogui.click()",
    "^(resume|zoom|continue|start)( typing| dictation)$" : "exec('global chatting;chatting = False')",
    "^(send|compose|write)( an| a) email to ": "os.popen('xdg-open \"mailto://' + q.replace(' at ', '@') + '\"')"
    }

def process_actions(tl):
    for action, command in actions.items():
        # look for action in list
        if s:=re.search(action, tl):
            q = tl[s.end():] # get q for command
            eval(command); speak("okay")
            return True # success
    if chatting:
        chatGPT(tl); return True
    return False # no action
    
# fix race conditions
audio_queue = queue.Queue()
listening = True
chatting = False

# search text for hotkeys
def process_hotkeys(txt):
    global start
    for key,val in hotkeys.items():
        # if hotkey command
        if re.search(key, txt):
            start = 0 # reset paragraph timer
            # unpack list of key combos such as ctrl-v
            for x in val:
                # press each key combo in turn
                # The * unpacks x to separate args
                pyautogui.hotkey(*x)
            return True
    return False

# init whisper_jax
print("Loading... Please wait.")
from whisper_jax import FlaxWhisperPipline
# https://huggingface.co/models?sort=downloads&search=whisper
# openai/whisper-tiny       39M Parameters
# openai/whisper-tiny.en    39M Parameters
# openai/whisper-base       74M
# openai/whisper-small.en   244M
# openai/whisper-medium.en  769M
# openai/whisper-large      1550M
# openai/whisper-large-v2   1550M
pipeline = FlaxWhisperPipline("openai/whisper-small.en")

def gettext(f):
    try:
        outputs = pipeline(f, task="transcribe", language="English")
    except:
        return ''
    return outputs['text']

def preload():
    gettext("click.wav")
    
def pastetext(t):
    # paste text in window
    if t == " you": return # ignoring you
    pyperclip.copy(t) # weird that primary won't work the first time
    if pyautogui.platform.system() == "Linux":
        pyperclip.copy(t, primary=True) # now it works
        pyautogui.middleClick()
    else:
        pyautogui.hotkey('ctrl', 'v')

def speak(t):
    try:
        subprocess.check_output(["which", "mimic3"])
        os.system("mimic3 --length-scale 0.66 " + shlex.quote(t)+" 2>/dev/null&")
    except Exception as e:
        print("Problem with mimic3, required for voice output.")
        print(e)

print("Start speaking. Text should appear in the window you are working in.")
print("Say \"Stop listening.\" or press CTRL-C to stop.")
speak("Computer ready.")

def chatGPT(prompt):
    global chatting
    completion = ""
    # Call chatGPT
    if api_key:
        try:
            completion = openai.ChatCompletion.create(
              model="gpt-3.5-turbo",
              messages=[ {"role": "user", "content": prompt} ]
            )
            completion = completion.choices[0].message.content
        except Exception as e:
                print("ChatGPT had a problem. Here's the error message.")
                print(e)
    # Fallback to localhost
    if not completion:
        try:
            data = {'prompt': prompt}
            completion = requests.post(url, data=data).text
        except Exception as e:
            print("Problem with fallback chat server on localhost.")
            print(e)
    # Read back the response
    if completion:
        if completion == "< nooutput >": completion = "No comment."
        print(completion)
        pastetext(completion)
        speak(completion)
        chatting = True

def transcribe():
    global start
    while True:
        # transcribe audio from queue
        if f := audio_queue.get():
            t = gettext(f)
            print('\r' + t)
            # delete temporary audio file
            try: os.remove(f)
            except: pass
            if not t: break
            
            # get lower-case spoken command string
            lower_case = t.lower().strip()
            if match := re.search(r"[^\w\s]$", lower_case):
                lower_case = lower_case[:match.start()] # remove punctuation
            
            # see list of actions and hotkeys at top of file :)
            # Go to Website.
            if s:=re.search("^(peter|computer).? (go|open|browse|visit|navigate)( up| to| the| website)* [a-zA-Z0-9-]{1,63}(\.[a-zA-Z0-9-]{1,63})+$", lower_case):
                q = lower_case[s.end():] # get q for command
                webbrowser.open('https://' + q.strip())
                continue
            elif process_actions(lower_case): continue
            elif process_hotkeys(lower_case): continue

            # Stop listening.
            elif re.search("^.{0,6}listening.?$", lower_case): break
            else:
                now = time.time()
                # Remove leading space from new paragraph
                if now - start > 120: t = t.strip()
                # Paste it now
                start = now; pastetext(t)
        # continue looping every second
        else: time.sleep(0.5)
        
def recorder():
    # If it wasn't for Gst conflict with pyperclip,
    # we could import record.py instead of os.system()
    # from record import Record
    # rec = Record()
    
    global listening
    while listening:
        # record some (more) audio to queue
        temp_name = tempfile.mktemp()+ '.mp3'
        os.system("./record.py " + temp_name)
        audio_queue.put(temp_name)

record_thread = threading.Thread(target=recorder)
record_thread.start()

# preload whisper_jax for subsequent speedup
preload_thread = threading.Thread(target=preload)
preload_thread.start()
pyperclip.init_xsel_clipboard()
start = 0

transcribe()
print("Stopping... Make some noise to return to command prompt.")
listening = False
record_thread.join()
