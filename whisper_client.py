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
import pyperclip
import os, time, queue, sys, re
import webbrowser
import tempfile
import threading
import subprocess, signal
import requests
import json
from mimic3_client import say
from gradio_client import Client
client = Client("http://localhost:7860/")

# address of Fallback Chat Server.
fallback_chat_url = 'http://localhost:5000'
api_key = os.getenv("OPENAI_API_KEY")

if (api_key):
    import openai
    openai.api_key = api_key
else:
    sys.stderr.write("Export OPENAI_API_KEY if you want answers from ChatGPT.")

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
    r"^(peter|computer).? (run|open|start|launch)(up)?( a| the)? ": "os.system(commands[sys.platform][q])",
    r"^(peter|computer).? closed? window": "pyautogui.hotkey('alt', 'F4')",
    r"^(peter|computer).? search( the)?( you| web| google| bing| online)?(.com)? for ": 
       "webbrowser.open('https://you.com/search?q=' + re.sub(' ','%20',q))",
    r"^(peter|computer).? (send|compose|write)( an| a) email to ": "os.popen('xdg-open \"mailto://' + q.replace(' at ', '@') + '\"')",
    r"^(peter|computer).? (i need )?(let's )?(see |have |show )?(us |me )?(an? )?(image|picture|draw|create|imagine|paint)(ing| of)? ": "os.popen(f'./sdapi.py \"{q}\"')",
    r"^(peter.? |computer.? )?(resume|zoom|continue|start|type) (typing|d.ctation|this)" : "exec('global chatting;global listening;chatting = False;listening = True')",
    r"^(peter|computer).? ": "chatGPT(q)"
    }

def process_actions(tl):
    for input, action in actions.items():
        # look for action in list
        if s:=re.search(input, tl):
            q = tl[s.end():] # get q for action
            say("okay")
            eval(action)
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

def gettext(f):
    result = ['']
    if f and os.path.isfile(f):
        result = client.predict(f, "transcribe", False, api_name="/predict")
    return result[0]
    
def pastetext(t):
    # paste text in window
    if t == " you" or t == " Thanks for watching!" or "[" in t:
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

def chatGPT(prompt):
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
                sys.stderr.write("ChatGPT had a problem. Here's the error message.")
                sys.stderr.write(e)
    # Fallback to localhost
    if not completion:
        try:
            msg = {"messages": messages}
            response = requests.post(fallback_chat_url, json=msg)
            if response.status_code == 200:
                data = response.json()
                completion = data["content"]
        except Exception as e:
                sys.stderr.write("Chat had a problem. Here's the error message.")
                sys.stderr.write(e)
    # Read back the response completion
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
    global start
    global listening
    while True:
        try:
            # transcribe audio from queue
            if f := audio_queue.get():
                t = gettext(f).strip('\n')
                print(t)
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
                    #record_process.send_signal(signal.SIGINT)
                    #record_process.wait()
                    #say("Acknowledged.")
                    #input("Paused. Press Enter to continue...")
                    #audio_queue.get() # discard truncated sample
                    #listening = True
                elif process_actions(lower_case): continue
                if not listening: continue
                elif process_hotkeys(lower_case): continue
                else:
                    now = time.time()
                    # Remove leading space from new paragraph
                    if now - start > 120: t = t.strip()
                    # Paste it now
                    start = now; pastetext(t)
            # continue looping every second
            else: time.sleep(0.5)
        except KeyboardInterrupt:
            say("Goodbye.")
            break

def recorder():
    # If it wasn't for Gst conflict with pyperclip,
    # we could import record.py instead of os.system()
    # from record import Record
    # rec = Record()
    global record_process
    global running
    while running:
        # record some (more) audio to queue
        temp_name = tempfile.mktemp()+ '.mp3'
        record_process = subprocess.Popen(["python", "./record.py", temp_name])
        record_process.wait()
        audio_queue.put(temp_name)

def quit():
    sys.stderr.write("Stopping...")
    global running
    global listening
    listening = False
    running = False
    try:
        record_process.send_signal(signal.SIGINT)
        record_process.wait()
    except:
        pass
    time.sleep(1)
    record_thread.join()
    # clean up
    try:
        while f := audio_queue.get_nowait():
            sys.stderr.write("Removing temporary file: ", f)
            if f[:5] == "/tmp/": # safety check
                os.remove(f)
    except: pass
    sys.stderr.write("Freeing system resources.\n")

if __name__ == '__main__':
    record_process = None
    running = True
    record_thread = threading.Thread(target=recorder)
    record_thread.start()
    start = 0
    transcribe()
    quit()
