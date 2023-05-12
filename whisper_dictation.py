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
api_key = os.getenv("OPENAI_API_KEY")
if (api_key):
    import openai
    openai.api_key = api_key

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

# fix race conditions
audio_queue = queue.Queue()
listening = True

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
    outputs = pipeline(f,  task="transcribe", language="English")
    return outputs['text']
    
def pastetext(t):
    # copy text to clipboard
    pyperclip.copy(t)
    # paste text in window
    pyautogui.hotkey('ctrl', 'v')

def preload():
    gettext("click.wav")

def speak(t):
    try:
        subprocess.check_output(["which", "mimic3"])
        os.system("mimic3 --length-scale 0.66 " + shlex.quote(t))
    except:
        pass

print("Start speaking. Text should appear in the window you are working in.")
print("Say \"Stop listening.\" or press CTRL-C to stop.")

def chatGPT(prompt):
    if api_key:
        try:
            completion = openai.ChatCompletion.create(
              model="gpt-3.5-turbo",
              messages=[ {"role": "user", "content": prompt} ]
            )
            completion = completion.choices[0].message.content
            print(completion)
            pastetext(completion)
            speak(completion)
        except Exception as e:
                print(e)
    else:
        print("Export OPENAI_API_KEY if you want answers from ChatGPT.")
        

def transcribe():
    global start
    while True:
        # transcribe audio from queue
        if f := audio_queue.get():
            t = gettext(f); print('\r' + t)
            # delete temporary audio file
            os.remove(f)
            
            # Computer commands
            # see list of commands at top of file :)
            tl = t.lower().strip()
            if match := re.search(r"[^\w\s]$", tl):
                tl = tl[:match.start()] # remove punctuation
            # Open terminal.
            if s:=re.search("^(peter|computer).? (run|open|start|launch)( a| the)? ", tl):
                q = tl[s.end():] # get program name
                os.system(commands[sys.platform][q])
            # Close window.
            elif s:=re.search("^(peter|computer).? closed? window", tl):
                pyautogui.hotkey('alt', 'F4')
            # Search the web.
            elif s:=re.search("^(peter|computer).? search( the)?( you| web| google| bing| online)?(.com)? for ", tl):
                q = tl[s.end():] # get search query
                webbrowser.open('https://you.com/search?q=' + re.sub(' ','%20',q))
            # Go to Website.
            elif s:=re.search("^(peter|computer).? (go|open|browse|visit|navigate)( up| to| the| website)* ", tl):
                q = tl[s.end():] # get search query
                if re.search("^[a-zA-Z0-9-]{1,63}(\.[a-zA-Z0-9-]{1,63})+$", q):
                    webbrowser.open('https://' + q.strip())
             # Unknown Computer command, ask Chat-GPT
            elif s:=re.search("^(peter|computer).? ", tl):
                chatGPT(tl[s.end():])

            # Process hotkeys.
            elif process_hotkeys(tl):
                continue
            # Stop listening.
            elif re.search("^.{0,6}listening.?$", tl): break
            else:
                now = time.time()
                if now - start > 60:
                    # Remove leading space from new paragraphs
                    t = t.strip()
                    start = now
                # Type text into active terminal.
                # Paste into other types of windows
                window_name = subprocess.check_output(
                ["xdotool", "getwindowfocus", "getwindowname"]).decode().strip()
                if re.search("\w/\w",window_name):
                    # window is a terminal
                    pyautogui.typewrite(t)
                else:
                    pastetext(t)
                
        else: time.sleep(1)
        
def recorder():
    # If it wasn't for Gst conflict with pyperclip,
    # we could import record.py instead of os.system()
    # from record import Record
    # rec = Record()
    
    global listening
    while listening:
        # record some (more) audio to queue
        temp_name = tempfile.gettempdir() + '/' \
        + next(tempfile._get_candidate_names()) + ".mp3"
        
        # If it wasn't for Gst conflict with pyperclip
        # we could call recmain in record.py directly
        # rec.to_file(temp_name)
        
        # but instead, we have to call os.system()
        os.system("./record.py " + temp_name)

        # oh well, moving on, let's make sure we got something
        if not os.path.getsize(temp_name):
            if os.path.exists(temp_name):
                os.remove(temp_name)
            break
        else: audio_queue.put(temp_name)

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
