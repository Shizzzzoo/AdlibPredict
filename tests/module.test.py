from dotenv import load_dotenv

load_dotenv()

import os
import sys

sys.path.extend([
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
])


from adlibpredict import FrameCollector

rec = FrameCollector(
  rtsp_url="rtsp://192.168.0.5:8554/live",
)
