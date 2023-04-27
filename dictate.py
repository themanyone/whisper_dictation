#!/opt/conda/bin/python3.10
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
import os
import tempfile

# init whisper_jax
from whisper_jax import FlaxWhisperPipline
import jax.numpy as jnp

pipeline = FlaxWhisperPipline("openai/whisper-small.en",dtype=jnp.float16, batch_size=16)

# cache the function for subsequent speedup
pipeline("click.wav",  task="transcribe", return_timestamps=False)

while (1):
    # record some audio
    temp_name = tempfile.gettempdir() + '/' \
    + next(tempfile._get_candidate_names()) + ".mp3"
    os.system("./record.py " + temp_name)

    # transcribe it
    outputs = pipeline(temp_name,  task="transcribe", \
    return_timestamps=False)
    if outputs['text'] != ' you':
        print(outputs['text'])
    
    # cleanup
    os.remove(temp_name)
