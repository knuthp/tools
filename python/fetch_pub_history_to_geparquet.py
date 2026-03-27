# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb",
#   "pyarrow",
# ]
# ///
# db:
#     image: postgis/postgis:16-3.4
#     restart: always
#     environment:
#       - POSTGRES_USER=postgres
#       - POSTGRES_PASSWORD=postgres
#       - POSTGRES_DB=spartid_pubtransport
#     ports:
#       - '9202:5432'


# ATTACH 'postgresql://postgres:postgres@ptest:9202/spartid_pubtransport' AS pubtrans (TYPE POSTGRES);

# SELECT COUNT(*) FROM pubtrans.VEHICLE_MONITORING;
# (1.45 billion)

# DESCRIBE pubtrans.VEHICLE_MONITORING;
# ┌──────────────────────────────────┐
# │        VEHICLE_MONITORING        │
# │                                  │
# │ index                  bigint    │
# │ DataFrameRef           varchar   │
# │ DatedVehicleJourneyRef varchar   │
# │ RecordedAtTime         timestamp │
# │ LineRef                varchar   │
# │ VehicleMode            varchar   │
# │ Delay                  bigint    │
# │ Latitude               double    │
# │ Longitude              double    │
# └──────────────────────────────────┘

#!/usr/bin/env python3
"""
Extract VEHICLE_MONITORING data from PostgreSQL into a Parquet file for a given ISO week.

Usage:
    python extract_vehicle_monitoring.py --year 2024 --week 23
    python extract_vehicle_monitoring.py --year 2024 --week 23 --output-dir /data/parquet
    python extract_vehicle_monitoring.py --year 2024 --week 23 --conn "postgresql://user:pass@host:5432/dbname"
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb

DEFAULT_CONN = "postgresql://postgres:postgres@ptest:9202/spartid_pubtransport"
DEFAULT_OUTPUT_DIR = Path(".")


def iso_week_bounds(year: int, week: int) -> tuple[date, date]:
    """Return (monday, next_monday) for the given ISO year/week."""
    monday = date.fromisocalendar(year, week, 1)   # ISO weekday 1 = Monday
    next_monday = monday + timedelta(weeks=1)
    return monday, next_monday


def extract(year: int, week: int, conn_str: str, output_dir: Path) -> Path:
    monday, next_monday = iso_week_bounds(year, week)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"vehicle_monitoring_{year}_W{week:02d}.parquet"

    print(f"Extracting ISO week {year}-W{week:02d}  ({monday} – {next_monday - timedelta(days=1)})")
    print(f"Output: {out_path}")

    con = duckdb.connect()
    con.execute(f"ATTACH '{conn_str}' AS pubtrans (TYPE POSTGRES)")

    con.execute(f"""
        COPY (
            SELECT *
            FROM pubtrans.VEHICLE_MONITORING
            WHERE RecordedAtTime >= TIMESTAMPTZ '{monday}'
              AND RecordedAtTime  < TIMESTAMPTZ '{next_monday}'
            ORDER BY RecordedAtTime
        )
        TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    # Report row count from the written file
    result = con.execute(f"SELECT COUNT(*) FROM '{out_path}'").fetchone()
    print(f"Rows written: {result[0]:,}")
    con.close()

    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Extract VEHICLE_MONITORING data to a weekly Parquet file."
    )
    parser.add_argument("--year",  type=int, required=True, help="ISO year  (e.g. 2024)")
    parser.add_argument("--week",  type=int, required=True, help="ISO week number 1-53")
    parser.add_argument(
        "--conn",
        default=DEFAULT_CONN,
        help=f"PostgreSQL connection string (default: {DEFAULT_CONN})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for output Parquet files (default: current directory)",
    )
    args = parser.parse_args()

    # Validate week number
    try:
        iso_week_bounds(args.year, args.week)
    except ValueError:
        print(f"Error: week {args.week} does not exist in year {args.year}", file=sys.stderr)
        sys.exit(1)

    out = extract(args.year, args.week, args.conn, args.output_dir)
    # Print just the path last so it's easy to capture in scripts
    print(out)


if __name__ == "__main__":
    main()