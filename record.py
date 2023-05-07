#!/usr/bin/python
## record.py
##
## Hands-free voice audio recording to mp3, wav, other types
##
## Usage: record.py [name] [encoder]
## ./record.py filename.wav
## ./record.py filename.mp3
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

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import sys

# Initialize GStreamer
Gst.init(None)
silence = 0
dB = -20.0 # threshold audio level for speech
src = "autoaudiosrc" # audio source (alsasrc, pulsesrc, autoaudiosrc, etc.)

# Define a callback function to handle sound-level messages
def on_sound_level(bus, message):
    global dB
    if message.get_structure().get_name() == 'level':
        rms = message.get_structure().get_value('rms')[0]
        global rec_pipe, silence
        
        # if not recording
        if rec_pipe.get_state(0)[1] != Gst.State.PLAYING:
            if rms < dB: # wait for silence at start
                silence = 1
            elif rms > dB and silence: # start recording
                    rec_pipe.set_state(Gst.State.PLAYING)
        else: # stop recording after some silence
            if rms < dB:
                silence = silence + 1
                if silence > 10:
                    rec_pipe.set_state(Gst.State.NULL)
                    lvl_pipe.set_state(Gst.State.NULL)
                    print(); exit()
            # keep recording if there is more speech
            elif rms > dB:
                silence = 1

            # show VU meter display
            draw_meter(rms)

# Draw a VU meter in the terminal
def draw_meter(level):
    level = 1 - (level / -53.0)
    num_chars = int(level * 50)
    meter_chars = '=' * num_chars + '-' * (50 - num_chars)
    print("\r[%s] %.1f dBFS" % (meter_chars, (1 - level) * -53.0), end='')

# Create the lvl and rec pipes
def create_pipes():
    global lvl_pipe, rec_pipe, src
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else: fname = "audio.mp3"
    enc = "lamemp3enc" if fname[-3:] == "mp3" else "wavenc"
    rate = "audio/x-raw,rate=16000,channels=1,format=S16LE ! "
    if len(sys.argv) > 2:
        enc = sys.argv[2]
        rate = ""
    rec_pipe = Gst.parse_launch(
    src + ' ! audioconvert ! audioresample ! ' + rate
        + enc + ' ! filesink location=' + fname)
    rec_pipe.set_state(Gst.State.PAUSED)

    lvl_pipe = Gst.parse_launch(
    src + ' ! audioconvert ! level name=level ! fakesink')
    # Create a bus to get messages from the lvl_pipe
    bus = lvl_pipe.get_bus()
    bus.add_signal_watch()
    bus.connect('message::element', on_sound_level)
    lvl_pipe.set_state(Gst.State.PLAYING)

# Start the pipes
create_pipes()

# Run the main loop
main_loop = GLib.MainLoop()
try:
    main_loop.run()
except KeyboardInterrupt:
    pass

# Stop the pipes when the main loop exits
lvl_pipe.set_state(Gst.State.NULL)
if rec_pipe:
    rec_pipe.set_state(Gst.State.NULL)

