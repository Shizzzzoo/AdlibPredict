import cv2
import time
import threading

from rich import print
from ultralytics import YOLO


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
      print("[red]Error: Could not open RTSP stream.[/red]")
      exit()
    self._thread = threading.Thread(
      target=self._update,
      daemon=True,
    )
    self._thread.start()
    print("Frame collector started.")

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
        self._frame.copy() if self._frame is not None else None
      )

  def stop(
    self,
  ):
    self._running = False
    self._thread.join()
    self._cap.release()
    print("Frame collector stopped.")


class Detector:
  def __init__(
    self,
    model_path,
  ):
    self._model_path =  model_path
    self._model = None

  def load(
    self,
  ):
    print(f"Loading model from {self._model_path}...")
    self._model = YOLO(self._model_path)
    print("Model loaded successfully.")

  def predict(
    self,
    frame,
    conf=0.25,
    iou=0.45,
  ):
    if self._model is None:
      raise RuntimeError("Model not loaded. Call load() first.")
    res = self._model(
      frame,
      conf=conf,
      iou=iou,
    )
    return res
