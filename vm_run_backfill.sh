#!/usr/bin/env bash
set -euo pipefail

# ---- CONFIG: starting point ----
START_YEAR=2024
START_WEEK=27

# ---- Determine last full ISO week ----
# ISO year (%G) and ISO week (%V)
CURRENT_ISO_YEAR=$(date +%G)
CURRENT_ISO_WEEK=$(date +%V)

# Last full week = current ISO week - 1
END_WEEK=$((10#$CURRENT_ISO_WEEK - 1))
END_YEAR=$CURRENT_ISO_YEAR

# Handle case where we're currently in week 1
if [ "$END_WEEK" -le 0 ]; then
  END_YEAR=$((CURRENT_ISO_YEAR - 1))
  END_WEEK=$(date -d "${END_YEAR}-12-28" +%V)  # last ISO week of previous year
fi

echo "Running from ${START_YEAR}-W$(printf "%02d" "$START_WEEK") \
to ${END_YEAR}-W$(printf "%02d" "$END_WEEK")"
echo

year=$START_YEAR
week=$START_WEEK

while true; do
  WEEK_PADDED=$(printf "%02d" "$week")

  echo "=== Processing ${year}-W${WEEK_PADDED} ==="

  uv run python/fetch_pub_history_to_geparquet.py --year "$year" --week "$week"

  hf buckets cp "./vehicle_monitoring_${year}_W${WEEK_PADDED}.parquet" \
    hf://buckets/knuthp/demo1

  rm "./vehicle_monitoring_${year}_W${WEEK_PADDED}.parquet"

  echo

  # Stop when we hit the end year/week
  if [ "$year" -eq "$END_YEAR" ] && [ "$week" -eq "$END_WEEK" ]; then
    break
  fi

  # Increment week, handling year rollover
  week=$((week + 1))
  max_week=$(date -d "${year}-12-28" +%V)

  if [ "$week" -gt "$max_week" ]; then
    week=1
    year=$((year + 1))
  fi
done

echo "✅ Done"
