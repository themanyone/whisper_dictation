#!/usr/bin/python
# -*- coding: utf-8 -*-
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
import sys
import urllib.parse
# Initialize GStreamer
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
pipeline = None
Gst.init(None)

def say(text, base_url="http://localhost:59125/api/tts"):
    global pipeline
    # Define the parameters for the TTS request
    params = {'text': text, "voice": "en_US/vctk_low"}
    query_string = "&".join(f"{k}={urllib.parse.quote_plus(v)}" for k, v in params.items())
    # Define the GStreamer pipeline
    pipeline_description = (
        f" souphttpsrc location={base_url}?{query_string} "
        "! wavparse "
        "! audioconvert "
        "! audioresample "
        "! autoaudiosink"
    )
    pipeline = Gst.parse_launch(pipeline_description)

    # Create a GLib Main Loop to handle asynchronous playback
    loop = GLib.MainLoop()

    # Bus callback to handle EOS and ERROR
    def on_message(bus, message):
        mtype = message.type
        if mtype == Gst.MessageType.EOS:
            # print("End-Of-Stream reached.")
            loop.quit()
        elif mtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error received from element {message.src.get_name()}: {err.message}", file=sys.stderr)
            if debug:
                print(f"Debugging information: {debug}", file=sys.stderr)
            loop.quit()

    # Add a bus watch to the pipeline
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", on_message)

    # Start the pipeline
    pipeline.set_state(Gst.State.PLAYING)

    try:
        # Run the main loop; this will block until EOS or ERROR occurs
        loop.run()
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        # Clean up
        pipeline.set_state(Gst.State.NULL)

def shutup():
    global pipeline
    if pipeline is not None:
        pipeline.send_event(Gst.Event.new_eos()) 

# Example usage
if __name__ == "__main__":
    say("Hello, this is a test of the text to speech system.")
