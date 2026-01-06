import os
import sys
import time
import threading

sys.path.extend([
  os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),
])

from collections import deque
from fastapi import FastAPI
from pydantic import BaseModel
from hooks.server.mavproxy import do_action


app = FastAPI()
queue = deque()
queue_lock = threading.RLock()

INITIAL_EXTRA_DELAY = 3.0
IGNORE_THRESHOLD = 2.0


def _queue_worker(func):
  first = True
  while True:
    with queue_lock:
      if not queue:
        item = None
        first = True
      else:
        item = queue.popleft()
    if item is None:
      time.sleep(0.1)
      continue
    if first:
      time.sleep(INITIAL_EXTRA_DELAY)
      first = False
    print(f"An Item Popped. Queue: {queue}")
    try:
      func(item)
    except Exception as e:
      print(f"worker failed: {e}")


class TriggerRequest(BaseModel):
    timestamp: float


@app.post("/trigger")
def trigger(
  req: TriggerRequest,
):
  ts = req.timestamp
  with queue_lock:
    if not queue:
      queue.append(ts)
      print(f"An Item Appended. Queue: {queue}")
      return {
        "status": "added",
        "reason": "queue was empty",
      }
    last_ts = queue[-1]
    interval = ts - last_ts
    if interval < IGNORE_THRESHOLD:
      print(f"An Item Ignored. Queue: {queue}")
      return {
        "status": "ignored",
        "reason": f"interval too small ({interval:.2f}s)",
      }
    queue.append(ts)
    print(f"An Item Appended. Queue: {queue}")
    return {
      "status": "added",
      "reason": "interval ok",
    }


@app.on_event("startup")
def start_worker():
  print("worker thread started.")
  threading.Thread(
    target=_queue_worker,
    args=(do_action,),
    daemon=True,
  ).start()
