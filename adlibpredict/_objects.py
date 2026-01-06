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
    self.rtsp_url = rtsp_url
    self._frame = None
    self._running = True
    self._lock = threading.RLock()
    self._cap = None
    self._connect()
    if not self._cap or not self._cap.isOpened():
      print("Error: Could not open RTSP stream.")
      exit()
    self._thread = threading.Thread(target=self._update, daemon=True)
    self._thread.start()
    print("Frame collector started.")

  def _connect(self):
    print("Trying to connect using FFmpeg backend...")
    try:
      cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
      cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
      if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
          print("Connection Successful.")
          self._cap = cap
          with self._lock:
            self._frame = frame
          return
        cap.release()
    except Exception as e:
      print(f"Connection failed: {e}")

  def _update(self):
    while self._running:
      try:
        if self._cap and self._cap.isOpened():
          ret, frame = self._cap.read()
          if ret and frame is not None:
            with self._lock:
              self._frame = frame
          else:
            time.sleep(0.01)
        else:
          time.sleep(0.1)
      except Exception as e:
        print(f"Error in frame update thread: {e}")
        time.sleep(0.1)

  def read(self):
    with self._lock:
      if self._frame is not None:
        try:
          return self._frame.copy()
        except Exception as e:
          print(f"Error copying frame: {e}")
          return None
      return None

  def stop(self):
    self._running = False
    if self._thread.is_alive():
      self._thread.join(timeout=2.0)
    if self._cap:
      self._cap.release()
    print("Frame collector stopped.")


class Detector:
  def __init__(
    self,
    model_path,
  ):
    self._model_path = model_path
    self._model = None

  def load(self):
    print(f"Loading model from {self._model_path}...")
    self._model = YOLO(self._model_path)
    print("Model loaded successfully.")

  def predict(
    self,
    frame,
    conf=0.25,
    iou=0.45,
    verbose=False,
  ):
    if self._model is None:
      raise RuntimeError("Model not loaded. Call load() first.")

    if frame is None:
      raise ValueError("Frame is None, cannot predict")

    try:
      results = self._model(
        frame,
        conf=conf,
        iou=iou,
        verbose=verbose,
      )
      return results[0]
    except Exception as e:
      print(f"Prediction error: {e}")
      raise
