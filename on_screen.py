#!/usr/bin/python
import gi
import time
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib
class start_camera:
    def __init__(self, callback=None):
        Gst.init(None)
        self.pipeline = Gst.parse_launch(
        'v4l2src ! tee name=t ! videoconvert ! autovideosink t. ! valve name=v ! '+
        'videoconvert ! jpegenc ! filesink async=false location=/tmp/on_screen.jpg name=f')
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
