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

import os, sys, time
import subprocess, tempfile
import signal

# quit recording after (seconds)
max_recording_time = 1800

def convert_to_ffmpeg_time(t):
    hours = int(t // 3600)
    minutes = int((t % 3600) // 60)
    seconds = int(t % 60)
    milliseconds = round((t % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    
class Record:
    # frequently-configured variables
    lead_in = 0.25 # Lead-in time. Increase if it cuts off the beginning.
    dB = -20.0 # threshold audio level, for detecting start of speech
    eta = 10 # in tenths: 10 = stop recording after 1 sec. of silence.
    src = "autoaudiosrc" # audio source (alsasrc, pulsesrc, autoaudiosrc, etc.)
    
    def __init__(self):
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst, GLib
        # Initialize GStreamer
        Gst.init(None)
        self.Gst = Gst
        self.GLib = GLib
        self.temp_name = tempfile.mktemp()+ '.mp3'
        self.silence = 0
        self.ss = ""

    def signal_handler(self, signal, frame):
        self.quit("")
    
    def quit(self, ss):
        Gst = self.Gst
        # Send EOS event to the pipeline to stop them
        self.lvl_pipe.send_event(Gst.Event.new_eos())
        self.rec_pipe.send_event(Gst.Event.new_eos())
        # Wait until the recording pipeline has finished
        bus = self.rec_pipe.get_bus()
        bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS)
        # trim time off temp audio, save to fname
        if ss:
            command = f"ffmpeg -nostdin -v -8 -y -ss {self.ss} -i {self.temp_name} -c copy {fname}"
            subprocess.run(command+">/dev/null", shell=True)
        # clean up
        os.remove(self.temp_name)
        try:
            self.main_loop.quit();
        except:
            pass
        print()

    # Define a callback function to handle sound-level messages
    def on_sound_level(self, bus, message):
        dB = self.dB
        Gst = self.Gst
        
        if message.get_structure().get_name() == 'level':
            rms = message.get_structure().get_value('rms')[0]
            # seconds of silence to trim off beginning of audio
            ss = time.time() - self.lead_in
            
            # if not recording
            if self.ss == "":
                if ss > max_recording_time:
                    print(sys.argv[0]+": Max recording time reached.", file=sys.stderr)
                    self.quit(self.ss); return
                if rms < dB: # wait for startup clicks and pops to die down
                    self.silence = 1 # got it, we have silence!
                elif rms > dB and self.silence: # now wait for voice
                    self.ss = convert_to_ffmpeg_time(ss)
            else: # stop recording after eta of silence is reached
                if rms < dB:
                    self.silence = self.silence + 1
                    if self.silence > self.eta: # eta reached
                        self.quit(ss); return # wrap it up, we're done!
                # keep recording if there is more speech
                elif rms > dB: # speech detected
                    self.silence = 1 # reset silence counter

                # show VU meter display
                self.draw_meter(rms)

    # Draw a VU meter in the terminal
    def draw_meter(self, level):
        try:
            level = 1 - (level / -53.0)
            num_chars = int(level * 50)
            meter_chars = '=' * num_chars + '-' * (50 - num_chars)
            print("\r[%s] %.1f dB" % (meter_chars, (1 - level) * -53.0), end='')
        except:
            pass

    # Create the lvl and rec pipes
    def create_pipes(self, fname):
        Gst = self.Gst
        src = self.src
        enc = "lamemp3enc" if fname[-3:] == "mp3" else "wavenc"
        rate = "audio/x-raw,rate=16000,channels=1,format=S16LE ! "
        if len(sys.argv) > 2:
            enc = sys.argv[2]
            rate = ""
        # record to temp_name
        self.rec_pipe = Gst.parse_launch(
        src + ' ! audioconvert ! audioresample ! ' + rate
            + enc + ' ! filesink location=' + self.temp_name)
        self.rec_pipe.set_state(Gst.State.PLAYING)
        # give recording 0.25 sec. lead-in time
        self.lead_in = time.time() + self.lead_in
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
    signal.signal(signal.SIGINT, Record.signal_handler)
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else: fname = "audio.mp3"
    Record.to_file(fname)
    