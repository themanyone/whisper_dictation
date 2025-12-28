#!/usr/bin/python
from gi.repository import Gst, GLib
import logging
import gi
gi.require_version("Gst", "1.0")

# Initialize GStreamer
Gst.init(None)

logging.basicConfig(
	level=logging.DEBUG,
	format="%(asctime)s [%(levelname)s] %(lineno)d %(message)s",
	handlers=[
#		logging.FileHandler('/tmp/rec.log'),
		logging.StreamHandler()
	]
)

class delayRecord:
    def __init__(self):
        self.create_pipes("out.wav")

    def create_pipes(self, fname):
        # Create GStreamer elements
        self.pipeline = Gst.Pipeline.new("audio_pipeline")
        # recording source (alsasrc, pulsesrc, autoaudiosrc, etc.)
        self.source = Gst.ElementFactory.make("autoaudiosrc", "source")
        self.tee = Gst.ElementFactory.make("tee", "tee")
        self.encoder = Gst.ElementFactory.make("wavenc", "encoder")
        self.audioconvert = Gst.ElementFactory.make("audioconvert", "audioconvert")
        self.audioresample = Gst.ElementFactory.make("audioresample", "audioresample")
        self.queue = Gst.ElementFactory.make("queue", "queue")
        self.filesink = Gst.ElementFactory.make("filesink", "filesink")
        self.level = Gst.ElementFactory.make("level", "level")
        self.fakesink = Gst.ElementFactory.make("fakesink", "fakesink")

        # Set properties
        self.filesink.set_property("location", fname)

        # Add elements to the pipeline
        self.pipeline.add(self.source)
        self.pipeline.add(self.audioconvert)
        self.pipeline.add(self.audioresample)
        self.pipeline.add(self.tee)
        self.pipeline.add(self.queue)
        self.pipeline.add(self.encoder)
        self.pipeline.add(self.filesink)
        self.pipeline.add(self.level)
        self.pipeline.add(self.fakesink)

        # Link rec pipeline
        self.source.link(self.tee)
        self.tee.link(self.audioconvert)
        self.audioconvert.link(self.queue)
        self.queue.link(self.audioresample)
        self.audioresample.link(self.encoder)
        self.encoder.link(self.filesink)

        # Link monitor pipeline
        self.tee.link(self.level)
        self.level.link(self.fakesink)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message::element', self.on_sound_level)

    def on_sound_level(self, bus, message):
        rms = message.get_structure().get_value('rms')[0]
        print(f"RMS {rms}")

    def run(self):
        # Start playing the pipeline
        self.pipeline.set_state(Gst.State.PLAYING)
        logging.debug("recording...")

        # Main loop
        GLib.MainLoop().run()
        logging.debug("cleanup")

        # Clean up
        self.pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    rec     = delayRecord()
    try:
        rec.run()
    except KeyboardInterrupt:
        print("Stopping...")
