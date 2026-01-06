from dotenv import load_dotenv
load_dotenv()

import os
import sys
import cv2
import time

sys.path.extend([
  os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
])

from rich import print
from adlibpredict import (
  FrameCollector,
  Detector,
)

root = os.path.dirname(__file__)
model_path = os.environ.get("MODEL_PATH")
input_dir = os.path.join(
  root, "./images/inputs/"
)
images = sorted([
  os.path.join(input_dir, f)
  for f in os.listdir(input_dir)
  if os.path.isfile(os.path.join(input_dir, f))
])
if not images:
  print("No images found.")
  exit()

detector = Detector(model_path)
detector.load()

for idx, img_path in enumerate(images):
  frame = cv2.imread(img_path)
  if frame is None:
    print(f"Failed to read {img_path}")
    continue
  frame_ts = time.time()
  detected_ts = detector.is_detected(
    frame=frame,
    frame_ts=frame_ts,
    min_conf=0.3,
  )
  print(detected_ts)
