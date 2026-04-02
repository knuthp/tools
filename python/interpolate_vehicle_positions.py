# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb",
#   "pandas",
#   "pyarrow",
# ]
# ///

import argparse
import datetime
import json
import sys
from pathlib import Path

import duckdb

DUCKDB_PATH = "data/entur_et/siri_et.duckdb"
STOPS_PATH = "data/stops.parquet"
OUT_PATH = "data/entur_et/positions_interpolated.geojson"


def main():
    parser = argparse.ArgumentParser(
        description="Interpolate vehicle positions from SIRI ET data in DuckDB."
    )
    parser.add_argument(
        "--time",
        help="ISO timestamp for interpolation (default: current UTC time)",
    )
    parser.add_argument(
        "--output",
        default=OUT_PATH,
        help=f"Output GeoJSON file path (default: {OUT_PATH})",
    )
    args = parser.parse_args()

    if args.time:
        try:
            now = datetime.datetime.fromisoformat(args.time.replace("Z", "+00:00"))
        except ValueError as e:
            print(f"Invalid time format: {e}")
            sys.exit(1)
    else:
        now = datetime.datetime.now(datetime.timezone.utc)

    now_str = now.isoformat()

    db_path = Path(DUCKDB_PATH)
    if not db_path.exists():
        msg = f"Database not found at {DUCKDB_PATH}. Run fetch_et_to_duckdb.py first."
        print(msg)
        sys.exit(1)

    stops_path = Path(STOPS_PATH)
    if not stops_path.exists():
        print(f"Stops file not found at {STOPS_PATH}.")
        sys.exit(1)

    con = duckdb.connect(str(db_path))
    con.execute("INSTALL spatial; LOAD spatial;")

    # Load stops from parquet
    con.execute(
        f"CREATE OR REPLACE VIEW stops AS SELECT * FROM read_parquet('{STOPS_PATH}')"
    )

    # Get column names of stops to handle different formats
    cols = [c[0] for c in con.execute("DESCRIBE stops").fetchall()]
    lat_proj = "stop_lat" if "stop_lat" in cols else "ST_Y(ST_GeomFromWKB(geometry))"
    lon_proj = "stop_lon" if "stop_lon" in cols else "ST_X(ST_GeomFromWKB(geometry))"

    # Query to find vehicles and their positions at the given time
    # 1. Enriched calls with stop coordinates and journey boundaries
    # 2. In-transit vehicles (between two stops)
    # 3. At-stop vehicles (between arrival and departure at a stop)
    # 4. Near-start vehicles (5 mins before first stop)
    # 5. Near-end vehicles (5 mins after last stop)

    query = f"""
    WITH enriched_calls AS (
        SELECT
            c.*,
            {lat_proj} as stop_lat,
            {lon_proj} as stop_lon,
            COALESCE(expected_arrival_time, aimed_arrival_time) as arrival_time,
            COALESCE(expected_departure_time, aimed_departure_time) as departure_time,
            FIRST_VALUE("order") OVER (
                PARTITION BY dataframe_ref, dated_vehicle_journey_ref ORDER BY "order"
            ) as first_order,
            LAST_VALUE("order") OVER (
                PARTITION BY dataframe_ref, dated_vehicle_journey_ref ORDER BY "order"
                ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
            ) as last_order
        FROM calls c
        JOIN stops s ON c.stop_point_ref = s.stop_id
    ),
    in_transit AS (
        SELECT
            c1.dataframe_ref,
            c1.dated_vehicle_journey_ref as journey_ref,
            c1.line_ref,
            c1.vehicle_ref,
            c1.stop_lat + (c2.stop_lat - c1.stop_lat) * (
                epoch('{now_str}'::TIMESTAMPTZ) - epoch(c1.departure_time)
            ) / NULLIF(
                epoch(c2.arrival_time) - epoch(c1.departure_time), 0
            ) as lat,
            c1.stop_lon + (c2.stop_lon - c1.stop_lon) * (
                epoch('{now_str}'::TIMESTAMPTZ) - epoch(c1.departure_time)
            ) / NULLIF(
                epoch(c2.arrival_time) - epoch(c1.departure_time), 0
            ) as lon,
            'IN_TRANSIT' as status,
            FALSE as is_stationary
        FROM enriched_calls c1
        JOIN enriched_calls c2 ON
            c1.dataframe_ref = c2.dataframe_ref AND
            c1.dated_vehicle_journey_ref = c2.dated_vehicle_journey_ref AND
            c1."order" < c2."order"
        -- Find the two consecutive stops where the vehicle is currently between
        WHERE '{now_str}'::TIMESTAMPTZ > c1.departure_time
          AND '{now_str}'::TIMESTAMPTZ < c2.arrival_time
          AND NOT EXISTS (
              SELECT 1 FROM enriched_calls c3
              WHERE c3.dataframe_ref = c1.dataframe_ref
                AND c3.dated_vehicle_journey_ref = c1.dated_vehicle_journey_ref
                AND c3."order" > c1."order" AND c3."order" < c2."order"
          )
    ),
    at_stop AS (
        SELECT
            dataframe_ref,
            dated_vehicle_journey_ref as journey_ref,
            line_ref,
            vehicle_ref,
            stop_lat as lat,
            stop_lon as lon,
            'AT_STOP' as status,
            TRUE as is_stationary
        FROM enriched_calls
        WHERE '{now_str}'::TIMESTAMPTZ >= arrival_time
          AND '{now_str}'::TIMESTAMPTZ <= departure_time
    ),
    at_start AS (
        SELECT
            dataframe_ref,
            dated_vehicle_journey_ref as journey_ref,
            line_ref,
            vehicle_ref,
            stop_lat as lat,
            stop_lon as lon,
            'AT_START' as status,
            TRUE as is_stationary
        FROM enriched_calls
        WHERE "order" = first_order
          AND '{now_str}'::TIMESTAMPTZ >= (
              COALESCE(arrival_time, departure_time) - INTERVAL 5 MINUTE
          )
          AND '{now_str}'::TIMESTAMPTZ < COALESCE(arrival_time, departure_time)
    ),
    at_end AS (
        SELECT
            dataframe_ref,
            dated_vehicle_journey_ref as journey_ref,
            line_ref,
            vehicle_ref,
            stop_lat as lat,
            stop_lon as lon,
            'AT_END' as status,
            TRUE as is_stationary
        FROM enriched_calls
        WHERE "order" = last_order
          AND '{now_str}'::TIMESTAMPTZ > COALESCE(departure_time, arrival_time)
          AND '{now_str}'::TIMESTAMPTZ <= (
              COALESCE(departure_time, arrival_time) + INTERVAL 5 MINUTE
          )
    ),
    combined AS (
        SELECT * FROM in_transit
        UNION ALL SELECT * FROM at_stop
        UNION ALL SELECT * FROM at_start
        UNION ALL SELECT * FROM at_end
    )
    SELECT * FROM combined
    """

    print(f"Interpolating positions for {now_str}...")
    # Replacing NaN with None to ensure valid JSON output
    df = con.execute(query).df().replace({float("nan"): None})
    con.close()

    if df.empty:
        print("No vehicles found for the specified time.")
        return

    features = []
    for _, row in df.iterrows():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["lon"], row["lat"]]
            },
            "properties": {
                "dataframe_ref": row["dataframe_ref"],
                "journey_ref": row["journey_ref"],
                "line_ref": row["line_ref"],
                "vehicle_ref": row["vehicle_ref"],
                "status": row["status"],
                "is_stationary": bool(row["is_stationary"]),
                "estimated_at": now_str
            }
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        # allow_nan=False to catch any remaining serialization issues
        json.dump(geojson, f, ensure_ascii=False, indent=2, allow_nan=False)

    print(f"Exported {len(features)} vehicle positions to {out_path}")


if __name__ == "__main__":
    main()
