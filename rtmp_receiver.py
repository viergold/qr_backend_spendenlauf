import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

Gst.init(None)

pipeline = Gst.parse_launch(
    'rtmpsrc location="rtmp://0.0.0.0/live/stream" ! '
    'flvdemux ! decodebin ! videoconvert ! autovideosink sync=false'
)

pipeline.set_state(Gst.State.PLAYING)

bus = pipeline.get_bus()
while True:
    msg = bus.timed_pop_filtered(
        Gst.CLOCK_TIME_NONE,
        Gst.MessageType.ERROR | Gst.MessageType.EOS
    )
    print(msg)