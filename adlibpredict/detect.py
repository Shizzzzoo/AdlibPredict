import cv2
import time
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
    self._cap = cv2.VideoCapture(self._gst_pipeline, cv2.CAP_GSTREAMER)
    self._frame = None
    self._running = True
    self._lock = threading.RLock()
    if not self._cap.isOpened():
      print("Error: Could not open RTSP stream.")
      exit()
    self._thread = threading.Thread(
      target=self._update,
    )

  def _update(
    self,
  ):
    while self._running:
      ret, frame = self._cap.read()
      if ret:
        with self._lock:
          self._frame = frame
      else:
        time.sleep(0.1)

  def read(
    self,
  ):
    with self._lock:
      return (
        self._frame if self._frame is not None else None
      )

  def stop(
    self,
  ):
    self._running = False
    self._thread.join()
    self._cap.release()


class Detector:
  def __init__(
    self,
  ):
    pass

  def load(
    self,
  ):
    pass

  def predict(
    self,
  ):
    pass
