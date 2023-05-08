#!/usr/bin/env python
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
import os, shlex, time
import tempfile
import threading

# init whisper_jax
from whisper_jax import FlaxWhisperPipline
import jax.numpy as jnp

pipeline = FlaxWhisperPipline("openai/whisper-small.en", \
   dtype = jnp.float16, batch_size=16)

# cache the function for subsequent speedup
pipeline("click.wav",  task="transcribe", language="English")

print("Start speaking. Text should appear in current window.")

# fix race conditions
audio_queue = queue.Queue()
typing_queue = queue.Queue()

def transcribe():
    while True:
        # transcribe audio from queue
        if f := audio_queue.get():
            try:
                outputs = pipeline(f,  task="transcribe", \
                language="English")
                txt = shlex.quote(outputs['text'])
                if outputs['text'] != ' you':
                    print('\r' + outputs['text'])
                    typing_queue.put(txt)
            except Exception as e: print(e)
            # cleanup
            os.remove(f)
        else: time.sleep(1)
        
def record():
    while True:
        # record some (more) audio to queue
        temp_name = tempfile.gettempdir() + '/' \
        + next(tempfile._get_candidate_names()) + ".mp3"
        os.system("./record.py " + temp_name)
        if not os.path.getsize(temp_name):
            if os.path.exists(temp_name):
                os.remove(temp_name)
            exit()
        else: audio_queue.put(temp_name)

transcribe_thread = threading.Thread(target=transcribe)
record_thread = threading.Thread(target=record)

# start background threads only once
transcribe_thread.start()
record_thread.start()

# type out messages as they apppear in queue
while True:
    time.sleep(1)
    if message := typing_queue.get():
        os.system("xdotool type --clearmodifiers " + txt)