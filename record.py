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

import sys

class Record:
    silence = 0
    dB = -20.0 # threshold audio level for speech
    src = "autoaudiosrc" # audio source (alsasrc, pulsesrc, autoaudiosrc, etc.)

    def __init__(self):
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst, GLib
        # Initialize GStreamer
        Gst.init(None)
        self.Gst = Gst
        self.GLib = GLib

    # Define a callback function to handle sound-level messages
    def on_sound_level(self, bus, message):
        dB = self.dB
        Gst = self.Gst
        if message.get_structure().get_name() == 'level':
            rms = message.get_structure().get_value('rms')[0]
            
            # if not recording
            if self.rec_pipe.get_state(0)[1] != Gst.State.PLAYING:
                if rms < dB: # wait for silence at start
                    self.silence = 1
                elif rms > dB and self.silence: # start recording
                        self.rec_pipe.set_state(Gst.State.PLAYING)
            else: # stop recording after some silence
                if rms < dB:
                    self.silence = self.silence + 1
                    if self.silence > 10:
                        self.rec_pipe.set_state(Gst.State.NULL)
                        self.lvl_pipe.set_state(Gst.State.NULL)
                        self.main_loop.quit(); print(); return
                # keep recording if there is more speech
                elif rms > dB:
                    self.silence = 1

                # show VU meter display
                self.draw_meter(rms)

    # Draw a VU meter in the terminal
    def draw_meter(self, level):
        level = 1 - (level / -53.0)
        num_chars = int(level * 50)
        meter_chars = '=' * num_chars + '-' * (50 - num_chars)
        print("\r[%s] %.1f dBFS" % (meter_chars, (1 - level) * -53.0), end='')

    # Create the lvl and rec pipes
    def create_pipes(self, fname):
        Gst = self.Gst
        src = self.src
        enc = "lamemp3enc" if fname[-3:] == "mp3" else "wavenc"
        rate = "audio/x-raw,rate=16000,channels=1,format=S16LE ! "
        if len(sys.argv) > 2:
            enc = sys.argv[2]
            rate = ""
        self.rec_pipe = Gst.parse_launch(
        src + ' ! audioconvert ! audioresample ! ' + rate
            + enc + ' ! filesink location=' + fname)
        self.rec_pipe.set_state(Gst.State.PAUSED)

        self.lvl_pipe = Gst.parse_launch(
        src + ' ! audioconvert ! level name=level ! fakesink')
        # Create a bus to get messages from the lvl_pipe
        bus = self.lvl_pipe.get_bus()
        bus.add_signal_watch()
        bus.connect('message::element', self.on_sound_level)
        self.lvl_pipe.set_state(Gst.State.PLAYING)

    def to_file(self, fname):
        Gst = self.Gst
        # Start the pipes
        self.create_pipes(fname)

        # Run the main loop
        self.main_loop = self.GLib.MainLoop()
        self.main_loop.run()

        # Stop the pipes when the main loop exits
        self.lvl_pipe.set_state(Gst.State.NULL)
        if self.rec_pipe:
            self.rec_pipe.set_state(Gst.State.NULL)

if __name__ == '__main__':
    Record = Record()
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else: fname = "audio.mp3"
    Record.to_file(fname)
