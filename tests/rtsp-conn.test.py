from dotenv import load_dotenv
load_dotenv()

import os
import sys
import time

sys.path.extend([
  os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
])

from rich import print
from adlibpredict import FrameCollector

print("Starting RTSP connection test...")
rec = FrameCollector(
    rtsp_url="rtsp://localhost:8554/live",
)
print("Waiting for frames...")
time.sleep(2)
print("Testing frame capture...")
for i in range(10):
  frame = rec.read()
  if frame is not None:
    print(f"Frame {i+1}: Shape={frame.shape}, DType={frame.dtype}")
  else:
    print(f"Frame {i+1}: None")
  time.sleep(0.5)
print("Stopping frame collector...")
rec.stop()
