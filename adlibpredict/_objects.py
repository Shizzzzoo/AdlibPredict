import copy
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
    self._frame_ts = None
    self._running = True
    self._lock = threading.RLock()
    self._cap = None
    self._connect()
    if not self._cap or not self._cap.isOpened():
      print("Error: Could not open RTSP stream.")
      exit()
    self._thread = threading.Thread(
      target=self._update,
      daemon=True,
    )
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
          ts = time.time()
          print("Connection Successful.")
          self._cap = cap
          with self._lock:
            self._frame = frame
            self._frame_ts = ts
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
            ts = time.time()
            with self._lock:
              self._frame = frame
              self._frame_ts = ts
          else:
            time.sleep(0.01)
        else:
          time.sleep(0.1)
      except Exception as e:
        print(f"Error in frame update thread: {e}")
        time.sleep(0.1)

  def read(self):   # (timestamp, frame)
    with self._lock:
      if self._frame is not None and self._frame_ts is not None:
        try:
          return (
            copy.deepcopy(self._frame_ts),
            self._frame.copy(),
          )
        except Exception as e:
          print(f"Error copying frame: {e}")
          return (None, None)
      return (None, None)

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
    frame_ts,
    conf=0.25,
    iou=0.45,
    verbose=False,
  ):
    if self._model is None:
      raise RuntimeError("Model not loaded. Call load() first.")
    if frame is None:
      raise ValueError("Frame is None, cannot predict")
    if frame_ts is None:
      raise ValueError("Frame Timestamp is None, cannot predict")
    results = self._model(
      frame,
      conf=conf,
      iou=iou,
      verbose=verbose,
    )
    return results[0]

  def is_detected(
    self,
    frame,
    frame_ts,
    conf=0.25,
    iou=0.45,
    verbose=False,
    class_id=0,
    min_conf=0.3,
  ):
    # -1.0      -> False
    # <float>ts -> True
    res = self.predict(
      frame,
      frame_ts,
      conf,
      iou,
      verbose,
    )
    boxes = res.boxes
    if boxes is None or len(boxes) == 0:
      return -1.0
    pred_cls = boxes.cls
    pred_conf = boxes.conf
    for c, s in zip(pred_cls, pred_conf):
      if int(c) != class_id:
        continue
      if s < min_conf:
        continue
      return frame_ts
    return -1.0
