#!/usr/bin/env bash

uv run python -m uvicorn handler:app \
  --host 0.0.0.0 --port 8000
