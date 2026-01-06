import os
import sys
import time
import pandas as pd

sys.path.extend([
  os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")),
])

from hooks.server.mavproxy._const import LL_STREAM_FILE

def get_ll(ts):
  data = pd.read_csv(LL_STREAM_FILE)
  idx = (data["Timestamp"] - ts).abs().idxmin()
  return (
    data.at[idx, "Latitude"],
    data.at[idx, "Longitude"],
  )


def do_action(
  timestamp,
):
  lat, long = get_ll(timestamp)
