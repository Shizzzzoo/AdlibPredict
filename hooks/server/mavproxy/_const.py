import os
import sys

from rich import print
from pathlib import Path
from platformdirs import user_cache_dir

# LL_STREAM_FILE = Path(user_cache_dir(
#   appname="nidar",
#   ensure_exists=True,
# )) / "tll.csv"
LL_STREAM_FILE = Path(r"C:\Users\Dell\AppData\Local\nidar\tll.csv")
MAVGEN_CONN_STR = "udpin:localhost:14551"
