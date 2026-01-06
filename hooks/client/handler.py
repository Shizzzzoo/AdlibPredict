import time
import requests

from rich import print


URL = "http://localhost:8000/trigger"


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
