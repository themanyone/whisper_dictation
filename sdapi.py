#!/usr/bin/python
## record.py
##
## Hands-free voice audio recording to mp3, wav, other types
##
## Usage: sdapi.py [prompt] [output image]
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

import os, sys
import json
import requests
import io
import base64
from PIL import Image

# Requires stable-diffusion web UI, optionally configured for low memory usage
# re. https://techtactician.com/stable-diffusion-low-vram-memory-errors-fix/
# Start it with --api option, e.g.: webui.sh --api --medvram

url = "http://127.0.0.1:7860"

def draw(prompt, output="output.png"):
    payload = {
        "prompt": prompt,
        "steps": 30
    }
    response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)

    r = response.json()

    image = Image.open(io.BytesIO(base64.b64decode(r['images'][0])))
    image.save(output)
    image.show()

if __name__ == '__main__':
    #  Draw an image from a prompt supplied on the command line.
    if len(sys.argv) == 2:
        draw(sys.argv[1])
    if len(sys.argv) == 3: # Provide a name for the image.
        draw(sys.argv[1], sys.argv[2])
    else:
        print(f"Usage: {sys.argv[0]} \"a horse riding an elephant\" horse_phant.png")
