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

from pymavlink import mavutil
from hooks.server.mavproxy._const import (
    LL_STREAM_FILE,
    MAVGEN_CONN_STR,
  )


_SLAVE = None


def _get_ll(ts):
  data = pd.read_csv(LL_STREAM_FILE)
  idx = (data["Timestamp"] - ts).abs().idxmin()
  return (
    data.at[idx, "Latitude"],
    data.at[idx, "Longitude"],
  )


def _get_mavlink(
  conn_str,
):
  global _SLAVE
  if _SLAVE is None:
    _SLAVE = mavutil.mavlink_connection(MAVGEN_CONN_STR)
    _SLAVE.wait_heartbeat()
    print(
      "[mavlink] connection established successfull."
      f"(sysid={_SLAVE.target_system}, compid={_SLAVE.target_component})"
    )
  else:
    print(
      "[mavlink] using the existing connection."
      f"(sysid={_SLAVE.target_system}, compid={_SLAVE.target_component})"
    )
  return _SLAVE


def _goto(
  lat,
  long,
  alt=None,
  conn_str=MAVGEN_CONN_STR,
):
  mav = _get_mavlink(conn_str)


def do_action(
  timestamp,
):
  lat, long = _get_ll(timestamp)
  _goto(
    lat,
    long,
  )
