#!/bin/bash

last_fetch=0

while true; do
  now=$(date +%s)

  # Every 60 seconds
  if (( now - last_fetch >= 60 )); then
    uv run python/fetch_et_to_duckdb.py --dataset-id=RUT
    uv run python/fetch_et_to_duckdb.py --dataset-id=BRA
    last_fetch=$now
  fi

  # Every 3 seconds
  uv run python/interpolate_vehicle_positions.py

  sleep 3
done