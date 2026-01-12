import time
import requests

from rich import print


IP = "192.168.0.101"
PORT = "8000"
URL = f"http://{IP if not IP else "localhost"}:{PORT}/trigger"


def send_trigger(
  ts, # time.time()
):
  payload = {
    "timestamp": ts,
  }
  r = requests.post(
    URL,
    json=payload,
  )
  print(r.json())
  return r.status_code
