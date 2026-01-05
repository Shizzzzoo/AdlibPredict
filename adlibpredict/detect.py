import cv2
import threading

from rich import print

class FrameCollector:
  def __init__(
    self,
    rtsp_url,
  ):
    self._gst_pipeline = (
      f"rtspsrc location={rtsp_url} latency=0 buffer-mode=0 ! "
      "rtph264depay ! h264parse ! avdec_h264 ! "
      "videoconvert ! appsink drop=true sync=false"
    )
    self._cap = cv2.VideoCapture(self.gst_pipeline, cv2.CAP_GSTREAMER)
    self._frame = None
    self._running = True
    self._lock = threading.RLock()
    if not self.cap.isOpened():
      print("Error: Could not open RTSP stream.")
      exit()
