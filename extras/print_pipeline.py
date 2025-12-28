import gi
from gi.repository import Gst
gi.require_version('Gst', '1.0')

def print_gst_pipeline(pipeline_string):
    """
    Prints the GStreamer pipeline as a parseable graph.

    Args:
      pipeline_string: A string representing the GStreamer pipeline.

    Returns:
      None. Prints the graph to console.
    """

    try:
        # Create a GStreamer pipeline
        pipeline = Gst.parse_launch(pipeline_string)

        # Get the elements in the pipeline
        elements = pipeline.get_by_name()

        # Print the graph
        print("Gst Pipeline Graph:")
        for element in elements:
            print(f"  {element.get_name()} ->")
            for pad in element.get_pads():
                print(f"    - Pad: {pad.get_name()}")
                if pad.get_direction() == Gst.PadDirection.SRC:
                    for sink in pad.get_linked_pads():
                        print(f"      -> {sink.get_parent().get_name()}.{sink.get_name()}")
                elif pad.get_direction() == Gst.PadDirection.SINK:
                    for source in pad.get_linked_pads():
                        print(f"      -> {source.get_parent().get_name()}.{source.get_name()}")

        # Free resources
        pipeline.unref()
    except Exception as e:
        print(f"Error: {e}")


# Example usage:
pipeline_string = "videotestsrc ! videoconvert ! appsink name=sink"
print_gst_pipeline(pipeline_string)