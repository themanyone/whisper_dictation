#!/usr/bin/python
# -*- coding: utf-8 -*-
## record.py
##
## Hands-free voice audio recording to mp3, wav, possibly other types
##
## Help: ./record.py -h
##
## Copyright 2024 Henry Kroll <nospam@thenerdshow.com>
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
import os
import sys
import time
import math
import logging
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GObject, GLib

# Initialize GStreamer
Gst.init(None)

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(lineno)d %(message)s",
	handlers=[
#		logging.FileHandler('/tmp/rec.log'),
		logging.StreamHandler()
	]
)
class delayRecord:
    def __init__(self, file_name = ""):
        # set default options
        self.recording   = False
        self.quiet_timer = self.sound_timer = time.time() # start timers
        from_options = self.process_options()
        if not file_name: file_name = from_options
        ext = os.path.splitext(file_name)[1].lower()
        
        # Avoid overwriting files
        i = 1
        while os.path.exists(file_name):
            file_name = f'{os.path.splitext(file_name)[0].split('(')[0]}({i}){ext}'
            i += 1
        if (i > 1):
            logging.critical(f"File exists. Recording to '{file_name}'")
        else:
            logging.debug(f"Recording to '{file_name}'")
        self.file_name = file_name
        
        # Create GStreamer elements
        self.pipeline = Gst.Pipeline.new("audio_pipeline")
        # recording source (alsasrc, pulsesrc, autoaudiosrc, etc.)
        self.source = Gst.ElementFactory.make("autoaudiosrc", "source")
        encodings = {
            ".aiff": "aiffenc",
            ".mp3": "lamemp3enc",
            ".flac": "flacenc",
            ".gsm": "gsmsenc",
            ".ogg": "vorbisenc ! oggmux",
            ".ogx": "vorbisenc ! oggmux",
            ".opus": "opusenc ! oggmux",
            ".spx": "speexenc ! oggmux",
            ".wav": "wavenc",
            ".m4a": "avenc_aac ! mp4mux",
            ".wma": "wmav2enc ! asfmuxtype=Audio",
        }
        enc = encodings.get(ext) or 'wavenc'
        # vorbisenc doesn't support 16-bit rates
        rate = "" if ext[2] in "g" else self.rate
        logging.debug(f"format {rate}")
        logging.debug(f"using {enc} encoder")
        src = "autoaudiosrc" # alsasrc | pulsesrc
        delay = "ladspa-delay-so-delay-5s"
        # valve-type elements require async=off downstream
        self.pipeline = Gst.parse_launch(
        f"{src} ! tee name=t ! {delay} name=d ! valve name=v ! {self.gstreamer} audioconvert ! queue ! audioresample ! {rate} {enc} ! filesink name=fs location={file_name} async=false t. ! queue ! level ! fakesink"
        )
        self.filesink = self.pipeline.get_by_name('fs')
        self.delay = self.pipeline.get_by_name('d')
        self.delay.set_property("delay", self.preroll)
        self.delay.set_property("dry-wet-balance", 1.0)
        self.valve = self.pipeline.get_by_name('v')
        self.valve.set_property("drop", True)

    # handle sound-level messages 10 per second
    def monitor_levels(self, bus, message):
        rms = message.get_structure().get_value('rms')[0]
        # peak = message.get_structure().get_value('peak')[0]
        if math.isnan(rms): return True
        self.draw_meter(rms)
        reset = time.time()
        seconds_of_quiet = reset - self.quiet_timer
        seconds_of_sound = reset - self.sound_timer
        # Check sound level
        if rms > self.threshold:
            # Stop recording if recording time exceeded
            if seconds_of_sound / 60 > self.minutes:
                logging.critical('Recording time exceeded. Quitting.')
                self.pipeline.send_event(Gst.Event.new_eos())

            # Start recording when there are sustained sound levels
            elif self.ignore < seconds_of_sound and not self.recording:
                logging.debug("Recording started")
                self.valve.set_property("drop", False)
                self.recording = True
            self.quiet_timer = reset # reset quiet timer
        else:
            if self.recording and self.stop_after < seconds_of_quiet:
                self.pipeline.send_event(Gst.Event.new_eos())
            elif not self.recording:
                self.sound_timer = reset # wait for sounds

    # If loaded as a module, the parent process can call this
    def stop_recording(self):
        logging.debug(f"\n\nRecording stopped.\n")
        self.pipeline.set_state(Gst.State.NULL)
        self.loop.quit()

    def on_bus_message(self, bus, message):
        if message.type == Gst.MessageType.EOS:
            self.stop_recording()
        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logging.debug(f"Error: {err}, {debug}")
            elf.stop_recording()

    def start(self):
        # Set up bus to monitor messages from the pipeline
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        # Connect to the 'level' signal
        self.bus.connect("message", self.on_bus_message)
        self.bus.connect('message::element', self.monitor_levels)
        
        # Start playing the pipeline
        self.pipeline.set_state(Gst.State.PLAYING)
        logging.debug("Listening for voice...")

        # Main loop
        try:
            self.loop = GLib.MainLoop()
            self.loop.run()
        except Exception as e:
            logging.debug(f"Stopping...{e}")

        # Clean up
        logging.debug("Cleanup")
        self.pipeline.set_state(Gst.State.NULL)

    # Draw a VU meter in the terminal
    def draw_meter(self, level:float):
        terminal_size = os.get_terminal_size()
        try:
            level = 1 - (level / -53.0)
            num_chars = max(int(level * 50), 0)
            if terminal_size.columns < 61:
                meter_chars = 'Terminal too small'
            else:
                meter_chars = '=' * num_chars + '-' * (50 - num_chars)
            meterString = f"[{meter_chars}] {(1 - level) * -53.0:.1f} dB"
            print("\r", end='')
            leftToDelete = terminal_size.columns - 2
            for x in range(leftToDelete):
                print(' ' * (leftToDelete - x), x, end='\x1b[1K\r')
            print(f"\r{meterString}", end='')
        except Exception:
            logging.exception("Failed writing volume meter to terminal!")

    def print_help(self, options):
        print("""Usage:  record.py

        No arguments. Simply record voice to audio.wav until I stop speaking.
        
        record.py [file_name.ogg]
        
        record.py [-options] [file_name.[aiff|flac|gsm|m4a|mp3|ogg|ogx|spx|wav|wma]]
        """)
        for k in options:
            print(f"\t-{k}: {options[k]}")
        print()
        sys.exit(2)

    def process_options(self):
        file_name  = "audio.wav"
        self.quality    = False
        self.gstreamer  = ""
        self.minutes    = 10
        self.ignore     = 0.3
        self.preroll    = 0.6
        self.stop_after = 1.2
        self.threshold  = -20
        self.rate       = "audio/x-raw,rate=16000,channels=1,format=S16LE ! "
        lsa = len(sys.argv)
        if lsa == 1: return file_name
        options = {
            "h": "print_help(options) # Print this help message",
            "q": "quality    = True # use device bitrate",
            "g": f"gstreamer  = next_str or ''           # gstreamer-1.0 filters, etc.",
            "m": f"minutes    = next_float or {self.minutes}         # force stop after (minutes)",
            "i": f"ignore     = next_float or {self.ignore}        # ignore clicks < (seconds)",
            "p": f"preroll    = next_float or {self.preroll}        # preroll delay (seconds)",
            "s": f"stop_after = next_float or {self.stop_after}        # stop after (seconds of silence)",
            "t": f"threshold  = next_float or {self.threshold}        # wait for sound above this level (dB)",
        }
        for i in range(1, lsa):
            try:
                next_str = sys.argv[i+1] if i < lsa -1 else None
                next_float = float(sys.argv[i+1]) if i < lsa -1 else 0.0
            except ValueError:
                pass
            arg = sys.argv[i]
            if arg[0]=='-':
                for j in arg[1:]:
                    oj = options.get(j)
                    if oj: exec("self."+oj)
                    else:
                        logging.critical(f" Option '-{j}' not recognized.")
                        self.print_help(options)
            else:
                ext = os.path.splitext(arg)[1]
                if (len(ext) == 4 or len(ext) == 5) and ext[1] > '9':
                    file_name = arg
        if self.quality: self.rate = ""
        # connect plugin to pipeline
        if self.gstreamer and self.gstreamer[-1] != '!':
            self.gstreamer += ' !'
            logging.debug(f"Custom gstreamer options '{self.gstreamer}'")
        return file_name
        
if __name__ == "__main__":
    rec     = delayRecord()
    rec.start()
