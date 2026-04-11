#!/usr/bin/env bash

MODE=""
if [[ "${1}" == "test" ]]; then
  MODE+="test"
fi

uv run ./main.py "${MODE}"
