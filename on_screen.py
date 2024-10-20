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
import os
import time
from PIL import Image
from record import unique_file_name
gi.require_version('Gst', '1.0')
from gi.repository import Gst

# don't need an instance of camera to show pictures
def show_pictures(dir="webcam"):
    images = os.listdir(dir)
    for i in images:
        img = Image.open(dir + os.sep + i)
        img.thumbnail((128, 128))
        img.show()

class camera:
    def __init__(self, callback=None):
        Gst.init(None)
        if not os.path.exists("webcam"): os.mkdir("webcam")
        self.file_name = file_name = unique_file_name("webcam/image.jpg")
        self.pipeline = Gst.parse_launch(
        'autovideosrc ! tee name=t ! videoconvert ! autovideosink t. ! valve name=v ! '+
        f'videoconvert ! jpegenc ! filesink async=false location={file_name} name=f')
        self.valve = self.pipeline.get_by_name('v')
        self.filesink = self.pipeline.get_by_name('f')
        self.valve.set_property("drop", True)
        self.on = Gst.State.PLAYING
        self.off = Gst.State.NULL
        self.pipeline.set_state(self.on)

    def countdown(self, secs:int):
        self.countdown = secs  # seconds
        while self.countdown > 0:
            print(self.countdown)
            time.sleep(1)
            self.countdown -= 1

    def take_picture(self):
        self.valve.set_property("drop", False)
        shutter = Gst.parse_launch("filesrc location=camera-shutter.oga ! "+
        "oggdemux ! vorbisdec ! audioconvert ! autoaudiosink")
        shutter.set_state(self.on)
        time.sleep(0.5) # Adjust this value if needed
        self.valve.send_event(Gst.Event.new_eos())
        self.wait_for_file_save()
        self.valve.set_property("drop", True)

    def stop_camera(self):
        self.pipeline.set_state(self.off)
        self.pipeline = None
        return None

    def wait_for_file_save(self):
        bus = self.pipeline.get_bus()
        msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS | Gst.MessageType.ERROR)
        if msg:
            if msg.type == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                print(f"Error: {err}, {debug}")
            else:
                print("Picture saved!")

if __name__ == '__main__':
    app = start_camera()
    app.countdown(5)
    app.take_picture()
    app.stop_camera()
