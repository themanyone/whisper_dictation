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
# Initialize GStreamer
import time
import logging
import urllib.parse
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
pipeline = None
Gst.init(None)
talk_process = None
logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(lineno)d %(message)s",
	handlers=[
#		logging.FileHandler('/tmp/mimic_client.log'),
		logging.StreamHandler()
	]
)
def say(text, base_url="http://localhost:59125/api/tts"):
    global pipeline
    # Define the parameters for the TTS request
    params = {'text': text, "voice": "en_US/vctk_low"}
    query_string = "&".join(f"{k}={urllib.parse.quote_plus(v)}" for k, v in params.items())
    # Define the GStreamer pipeline
    pipeline_description = (
        f" souphttpsrc name=soup location={base_url}?{query_string} "
        "! wavparse "
        "! audioconvert "
        "! audioresample "
        "! autoaudiosink"
    )
    pipeline = Gst.parse_launch(pipeline_description)

    # Bus callback to handle EOS and ERROR
    def on_message(bus, message):
        global pipeline
        mtype = message.type
        if mtype == Gst.MessageType.EOS:
            logging.debug("End-Of-Stream reached.")
            pipeline.set_state(Gst.State.NULL)
        elif mtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logging.debug(f"Error received from element {message.src.get_name()}: {err.message}", file=sys.stderr)
            if debug:
                logging.debug(f"Debugging information: {debug}", file=sys.stderr)
        return True

    # Add a bus watch to the pipeline
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", on_message)

    # Start the pipeline
    pipeline.set_state(Gst.State.PLAYING)

def shutup():
    global pipeline
    for element in pipeline.children:
        if isinstance(element, Gst.Element):
            element.set_state(Gst.State.NULL)
    if pipeline is not None:
        pipeline.send_event(Gst.Event.new_eos())
        pipeline.set_state(Gst.State.NULL)

# Example usage
if __name__ == "__main__":
    say("Hello, this is a test of the text to speech system.")
    time.sleep(1)
    shutup()
