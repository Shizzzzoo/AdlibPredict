import os
import sys
import time

sys.path.extend([
  os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
])

from rich import print
from hooks.client import send_trigger

print(send_trigger(time.time()))
