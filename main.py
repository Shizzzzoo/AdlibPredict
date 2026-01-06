from dotenv import load_dotenv
load_dotenv()

import os
import sys
import time

from rich import print
from adlibpredict import (
  FrameCollector,
  Detector
)


def workflow():
  # col = FrameCollector(os.environ.get("RTSP_URL"))
  col = FrameCollector("rtsp://localhost:8554/live")
  interval = float(os.environ.get("CHECK_INTERVAL"))
  det = Detector(os.environ.get("MODEL_PATH"))
  det.load()
  while True:
    cur = time.time()
    frame = col.read()
    if frame is not None:
      res = det.predict(frame)
      print(res)
      time.sleep(interval-(time.time()-cur))


def main():
  workflow()


if __name__ == "__main__":
    main()
