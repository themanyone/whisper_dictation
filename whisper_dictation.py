#!/opt/conda/bin/python3.10
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
import os, shlex
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
def transcribe(f):
    # transcribe it
    try:
        outputs = pipeline(f,  task="transcribe", \
        language="English")
        txt = shlex.quote(outputs['text'])
        if outputs['text'] != ' you':
            print('\r' + outputs['text'])
            os.system("xdotool type --clearmodifiers " + txt)
    except Exception as e: print(e)
    # cleanup
    os.remove(f)
    
while (1):
    # record some (more) audio
    temp_name = tempfile.gettempdir() + '/' \
    + next(tempfile._get_candidate_names()) + ".mp3"
    os.system("./record.py " + temp_name)
    
    if not os.path.getsize(temp_name):
        if os.path.exists(temp_name):
            os.remove(temp_name)
        exit()
        
    # transcribe and remove
    t1 = threading.Thread(target=transcribe, args=[temp_name])
    t1.start()
