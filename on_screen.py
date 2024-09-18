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
from record import unique_file_name
gi.require_version('Gst', '1.0')
from gi.repository import Gst
class start_camera:
    def __init__(self, callback=None):
        Gst.init(None)
        if not os.exists("webcam"): os.mkdir("webcam")
        file_name = unique_file_name("webcam/image.jpg")
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
        self.wait_for_file_save()
        self.valve.set_property("drop", True)

    def stop_camera(self):
        self.pipeline.set_state(self.off)
        self.pipeline = None
        return None

    def wait_for_file_save(self):
        while True:
            # Check the state of the filesink
            state_change_return, state, pending_state = self.filesink.get_state(0)
            if state_change_return == Gst.StateChangeReturn.SUCCESS:
                break
                print("Picture saved!")
            time.sleep(0.1) # Short delay

if __name__ == '__main__':
    app = start_camera()
    app.countdown(5)
    app.take_picture()
    app.stop_camera()
