import os
import sys

sys.path.extend([
  os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
  os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),
])

from hooks.server.handler import (
  TriggerRequest,
)


__all__ = [
  "TriggerRequest",
]
