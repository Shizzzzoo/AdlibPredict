from dotenv import load_dotenv
load_dotenv()

import os
import sys
import time
import argparse

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
  if test:
    rtsp_url = "rtsp://localhost:8554/live"
  else:
    rtsp_url = os.environ.get("RTSP_URL")
    if not rtsp_url:
      print("environment variable `RTSP_URL` does not exist.")
  interval_str = os.environ.get(
    "CHECK_INTERVAL",
    "1.0",
  )
  model_path = os.environ.get("MODEL_PATH")
  if not model_path:
    print("environment variable `MODEL_PATH` does not exist.")
    sys.exit(1)
  if not Path(model_path).exists():
    print(f"model path: `{model_path}` does not exists.")
    sys.exit(1)
  try:
    interval = float(interval_str)
    if interval <= 0:
      raise ValueError("interval must be positive.")
  except ValueError:
    print(f"interval string must be a number, but got `{interval_str}`.")
    sys.exit()
  print(type(rtsp_url))
  print(f"rtsp url: `{rtsp_url}`")
  print(f"model path: `{model_path}`")
  print(f"interval: `{interval}`")
  col = FrameCollector(
    rtsp_url=rtsp_url,
  )
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
        print(f"detection result: {res}")
        if res != -1.0:
          send_trigger(res)
          print("trigger sent.")
        elapsed = time.perf_counter() - loop_start
        time.sleep(max(0, interval - elapsed))
    except KeyboardInterrupt:
      print("interrupted by user.")
      break
    except Exception as exc:
      print(f"exception: {exc}")
      time.sleep(1)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--test",
    action="store_true",
  )
  args = parser.parse_args()
  workflow(
    test=args.test,
  )


if __name__ == "__main__":
    main()
