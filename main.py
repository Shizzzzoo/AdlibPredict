from dotenv import load_dotenv
load_dotenv()

import os
import sys
import time

from rich import print
from pathlib import Path
from hooks.client import send_trigger
from adlibpredict import (
  FrameCollector,
  Detector
)


def workflow(
  test=False
):
  rtsp_url = os.environ.get("RTSP_URL", "rtsp://localhost:8554/live")
  interval_str = os.environ.get("CHECK_INTERVAL", "1.0")
  model_path = os.environ.get("MODEL_PATH")
  if not model_path:
    print("environment variable `MODEL_PATH` does not exists.")
    exit()
  if not Path(model_path).exists():
    print(f"model path: `{model_path}` does not exists.")
    exit()
  col = FrameCollector(rtsp_url)
  try:
    interval = float(interval_str)
  except ValueError:
    print(f"interval string must be a number, but got `{interval_str}`.")
    exit()
  det = Detector(model_path)
  det.load()
  while True:
    try:
      loop_start = time.perf_counter()
      frame_ts, frame = col.read()
      if frame is None:
        print("frame is not read or lost.")
      else:
        res = det.is_detected(
          frame,
          frame_ts,
        )
        print(res)
        if res != -1.0:
          send_trigger(res)
          print("sended.")
        elapsed = time.perf_counter() - loop_start
        time.sleep(max(0, interval - elapsed))
    except KeyboardInterrupt:
      print("interrupted by user.")
      break
    except Exception as exc:
      print(f"exception: {exc}")
      time.sleep(exc)


def main():
  workflow()


if __name__ == "__main__":
    main()
