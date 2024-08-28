#!/usr/bin/python
# -*- coding: utf-8 -*-
## record.py
##
## Hands-free voice audio recording to mp3, wav, possibly other types
##
## Usage: record.py [name].[type] [optional encoder, e.g. wavpackenc]
## ./record.py filename.wav
## ./record.py filename.mp3
##
## Specify an encoder to record highest quality audio (no rate limit!)
## ./record.py filename.flac flacenc
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

import os, sys, time
import tempfile
from ffmpeg import FFmpeg
import logging
from difflib import get_close_matches

logging.basicConfig(
	level=logging.CRITICAL,
	format="%(asctime)s [%(levelname)s] %(message)s",
	handlers=[
#		logging.FileHandler('/tmp/rec.log'),
		logging.StreamHandler()
	]
)

# Buffer ~30 seconds until sound, possibly speech, is detected.
# A longer buffer won't help much, and just uses memory.
buffer_seconds = 30

def convert_to_ffmpeg_time(t):
    hours = int(t // 3600)
    minutes = int((t % 3600) // 60)
    seconds = int(t % 60)
    milliseconds = round((t % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

class Record:
    # frequently-configured variables
    lead_in_time = 0.25 # Lead-in time. Increase if it cuts off the beginning.
    lead_in = 0
    dB = -20.0 # threshold audio level, for detecting start of speech
    quiet_period = 10 # in tenths: 10 = stop recording after 1 sec. of silence.
    src = "autoaudiosrc" # audio source (alsasrc, pulsesrc, autoaudiosrc, etc.)
    count = 0

    def __init__(self):
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst, GLib
        # Initialize GStreamer
        Gst.init(None)
        self.Gst = Gst
        self.GLib = GLib
        self.audio_buffer = tempfile.mktemp()+ '.mp3'
        self.silence = 0
        self.ss = ""

    def stop_recording(self):
        Gst = self.Gst
        # Send EOS event to the pipeline to stop them
        self.lvl_pipe.send_event(Gst.Event.new_eos())
        self.rec_pipe.send_event(Gst.Event.new_eos())
        # Wait until the recording pipeline has finished
        bus = self.rec_pipe.get_bus()
        bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS)
        self.lvl_pipe.set_state(Gst.State.NULL)
        self.rec_pipe.set_state(Gst.State.NULL)

    # CTRL-C is pressed
    def signal_handler(self, signal, frame):
        self.stop_recording()
        self.main_loop.quit()

    # buffer_seconds has elapsed
    def try_restart(self, ss, to):
        Gst = self.Gst
        self.stop_recording()
        # trim time off temp audio, save to fname
        if ss:
            process = (
            FFmpeg()
                .input(self.audio_buffer, v=0, ss=ss, to=to)
                .output(self.fname)
            )
            logging.debug(f'\ntrimmed ss: {ss} to: {to}')
            try:
                process.execute()
            except Exception:
                logging.critical(f"\nFfmpeg quit. It's probably an encoder problem")
            self.main_loop.quit();
        else:
            os.truncate(self.audio_buffer, 0)
            self.count = 0
            self.silence = 0
            self.lead_in = time.time() + self.lead_in_time
            self.rec_pipe.set_state(Gst.State.PLAYING)
            self.lvl_pipe.set_state(Gst.State.PLAYING)
            return

    # handle sound-level messages 10 per second
    def on_sound_level(self, bus, message):
        dB = self.dB
        self.count += 1
        if message.get_structure().get_name() == 'level':
            rms = message.get_structure().get_value('rms')[0]
            # seconds of silence to trim off beginning of audio
            ss = time.time() - self.lead_in

            # if not recording
            if self.ss == "":
                if self.count % (10 * buffer_seconds) == 0:
                    # print(sys.argv[0]+":  Still listening...", file=sys.stderr)
                    self.try_restart("", ""); return
                if rms < dB: # wait for startup clicks and pops to die down
                    self.silence = 1 # got it, we have silence!
                elif rms > dB and self.silence: # now wait for voice
                    self.ss = convert_to_ffmpeg_time(ss)
            else: # stop recording after quiet_period is detected
                if rms < dB:
                    self.silence = self.silence + 1
                    if self.silence > self.quiet_period:
                        to = convert_to_ffmpeg_time(self.count / 10)
                        self.try_restart(self.ss, to); return # wrap it up, we're done!
                # keep recording if there is more speech
                elif rms > dB: # speech detected
                    self.silence = 1 # reset silence counter

                # show VU meter display
                self.draw_meter(rms)

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
    # Create the lvl and rec pipes
    def create_pipes(self, fname):
        Gst = self.Gst
        src = self.src
        encodings = {
            "mp3": "lamemp3enc",
            "ogg": "oggenc",
            "gsm": "gsmsenc",
            "wav": "wavenc",
        }
        enc = encodings.get(fname.split(".")[-1].lower())
        # default to "speech quality" audio that whisper.cpp expects
        rate = "audio/x-raw,rate=16000,channels=1,format=S16LE ! "
        if len(sys.argv) > 2:
            extra_encoders = [
"alawenc",
"amrnbenc",
"fdkaacenc",
"flacenc",
"gsmenc",
"ldacenc",
"mulawenc",
"opusenc",
"speexenc",
"voamrwbenc",
"vorbisenc",
"wavenc",
"wavpackenc"
]
            enc = sys.argv[2]
            if enc not in extra_encoders:
                matches = get_close_matches(enc, extra_encoders, n=1, cutoff=0.6)
                logging.critical(f'{enc} unknown. Did you mean {matches[0]}?')
            # specify an encoder to get high quality audio (no rate limit!)
            else:
                logging.info(f'Setting rate to default, best')
                rate = ""
        elif enc is None:
            logging.info(f'Use gst-inspect-1.0 to find an encoder')
            raise ValueError(f"File extension: {fname} requires an encoder.")

        # record to audio buffer
        self.rec_pipe = Gst.parse_launch(
        src + ' ! audioconvert ! audioresample ! ' + rate
            + enc + ' ! filesink location=' + self.audio_buffer)
        self.rec_pipe.set_state(Gst.State.PLAYING)
        # give recording 0.25 sec. lead-in time
        self.lead_in = time.time() + self.lead_in_time
        self.lvl_pipe = Gst.parse_launch(
        src + ' ! audioconvert ! level name=level ! fakesink')
        # Create a bus to get messages from the lvl_pipe
        bus = self.lvl_pipe.get_bus()
        bus.add_signal_watch()
        bus.connect('message::element', self.on_sound_level)
        self.lvl_pipe.set_state(Gst.State.PLAYING)

    def to_file(self, fname):
        Gst = self.Gst
        i = 1
        while os.path.exists(fname):
            fname = f'{os.path.splitext(fname)[0]}_{i}{os.path.splitext(fname)[1]}'
            i += 1
        if (i > 1):
            logging.critical(f'\nFile exists. Saving to {fname}')
        self.fname = fname
        # Start the pipes
        self.create_pipes(fname)

        # Run the main loop
        self.main_loop = self.GLib.MainLoop()
        self.main_loop.run()

        # Stop the pipes when the main loop exits
        try:
            os.remove(self.audio_buffer)
            self.lvl_pipe.set_state(Gst.State.NULL)
            self.rec_pipe.set_state(Gst.State.NULL)
        except:
            pass
        print()

if __name__ == '__main__':
    Record = Record()
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else: fname = "audio.mp3"
    Record.to_file(fname)
