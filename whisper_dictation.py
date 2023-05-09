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
import os, shlex, time, queue, sys
import tempfile
import threading

# fix race conditions
audio_queue = queue.Queue()
listening = True

# init whisper_jax
from whisper_jax import FlaxWhisperPipline
import jax.numpy as jnp

# https://huggingface.co/models?sort=downloads&search=whisper
# openai/whisper-tiny       39M Parameters
# openai/whisper-base       74M
# openai/whisper-small.en   244M
# openai/whisper-medium.en  769M
# openai/whisper-large      1550M
# openai/whisper-large-v2   1550M
pipeline = FlaxWhisperPipline("openai/whisper-base", dtype = jnp.float16, batch_size=16)

# cache the function for subsequent speedup
print("Loading. Please wait...")
pipeline("click.wav",  task="transcribe", language="English")

print("Start speaking. Text should appear in the window you are working in.")
print("Say \"Stop listening.\" or press CTRL-C to stop.")

def transcribe():
    while True:
        # transcribe audio serially, from queue
        if f := audio_queue.get():
            # try:
            outputs = pipeline(f,  task="transcribe", language="English")
            t = outputs['text']
            if t.endswith("listening.") and len(t) < 16:
                print("Stopping... Make some noise to return to command prompt.")
                global listening
                global record_thread
                os.remove(f)
                listening = False
                record_thread.join()
                break
            if t != ' you':
                print('\r' + t)
                txt = shlex.quote(t)
                os.system("xdotool type --clearmodifiers " + txt)
            # except Exception as e: print(e)
            # cleanup
            os.remove(f)
        else: time.sleep(1)
        
def record():
    global listening
    while listening:
        # record some (more) audio to queue
        temp_name = tempfile.gettempdir() + '/' \
        + next(tempfile._get_candidate_names()) + ".mp3"
        os.system("./record.py " + temp_name)
        if not os.path.getsize(temp_name):
            if os.path.exists(temp_name):
                os.remove(temp_name)
            exit()
        else: audio_queue.put(temp_name)

record_thread = threading.Thread(target=record)
record_thread.start()

transcribe()