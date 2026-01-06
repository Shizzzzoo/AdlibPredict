import os
import sys
import time

sys.path.extend([
  os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")),
])


def do_action(
  timestamp,
):
  time.sleep(10)
