# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb",
#   "pyarrow",
# ]
# ///
#   db:
# image: postgis/postgis:16-3.4
# restart: always
# environment:
#   - POSTGRES_USER=postgres
#   - POSTGRES_PASSWORD=postgres
#   - POSTGRES_DB=spartid_ais
# ports:
#   - '5432:5432'


# ATTACH 'postgresql://postgres:postgres@ptest:5432/spartid_ais' AS ais (TYPE POSTGRES);
# SELECT COUNT(*) FROM ais.historic_position;
# (1.02 billion)

# DESCRIBE ais.historic_position;
# ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
# │                                                historic_position                                                │
# │                                                                                                                 │
# │ id        integer                                                                                      not null │
# │ msg_type  smallint                                                                                     not null │
# │ repeat    smallint                                                                                     not null │
# │ mmsi      integer                                                                                      not null │
# │ status    enum('underwayusingengine', 'atanchor', 'notundercommand', 'restrictedmanoeuverability', 'c… not null │
# │ turn      double                                                                                       not null │
# │ speed     double                                                                                       not null │
# │ accuracy  boolean                                                                                      not null │
# │ lat       double                                                                                       not null │
# │ long      double                                                                                       not null │
# │ course    double                                                                                       not null │
# │ heading   integer                                                                                      not null │
# │ maneuver  enum('notavailable', 'nospecialmaneuver', 'specialmaneuver', 'undefined')                    not null │
# │ raim      boolean                                                                                      not null │
# │ radio     integer                                                                                      not null │
# │ timestamp timestamp                                                                                    not null │
# └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
#!/usr/bin/env python3
"""
Extract AIS historic position data from PostgreSQL into a Parquet file for a given ISO week.

Usage:
    python fetch_ais_history_to_parquet.py --year 2024 --week 23
    python fetch_ais_history_to_parquet.py --year 2024 --week 23 --output-dir /data/parquet
    python fetch_ais_history_to_parquet.py --year 2024 --week 23 --conn "postgresql://user:pass@host:5432/dbname"
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb

DEFAULT_CONN = "postgresql://postgres:postgres@ptest:5432/spartid_ais"
DEFAULT_OUTPUT_DIR = Path(".")


def iso_week_bounds(year: int, week: int) -> tuple[date, date]:
    """Return (monday, next_monday) for the given ISO year/week."""
    monday = date.fromisocalendar(year, week, 1)   # ISO weekday 1 = Monday
    next_monday = monday + timedelta(weeks=1)
    return monday, next_monday


def extract(year: int, week: int, conn_str: str, output_dir: Path) -> Path:
    monday, next_monday = iso_week_bounds(year, week)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"ais_pos_{year}_W{week:02d}.parquet"

    print(f"Extracting ISO week {year}-W{week:02d}  ({monday} – {next_monday - timedelta(days=1)})")
    print(f"Output: {out_path}")

    con = duckdb.connect()
    con.execute(f"ATTACH '{conn_str}' AS ais (TYPE POSTGRES)")

    con.execute(f"""
        COPY (
            SELECT *
            FROM ais.historic_position
            WHERE timestamp >= TIMESTAMPTZ '{monday}'
              AND timestamp  < TIMESTAMPTZ '{next_monday}'
            ORDER BY timestamp
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
        description="Extract AIS historic position data to a weekly Parquet file."
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
