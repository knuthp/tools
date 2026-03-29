# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb",
#   "pandas",
#   "pyarrow",
#   "requests",
# ]
# ///

import datetime
import sys
from pathlib import Path

import duckdb
import pandas as pd
import requests


def fetch_siri_et(dataset_id="RUT"):
    """Fetch SIRI ET data from Entur."""
    url = f"https://api.entur.io/realtime/v1/rest/et?datasetId={dataset_id}"
    headers = {
        "ET-Client-Name": "jules-vehicle-estimation-duckdb",
        "Accept": "application/json",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def parse_siri_et_to_df(siri_json):
    """Parse SIRI ET JSON into a Pandas DataFrame of calls."""
    rows = []
    deliveries = (
        siri_json.get("Siri", {})
        .get("ServiceDelivery", {})
        .get("EstimatedTimetableDelivery", [])
    )

    for delivery in deliveries:
        for frame in delivery.get("EstimatedJourneyVersionFrame", []):
            for evj in frame.get("EstimatedVehicleJourney", []):
                journey_ref = evj.get("FramedVehicleJourneyRef", {}).get(
                    "DatedVehicleJourneyRef"
                )
                line_ref = evj.get("LineRef", {}).get("value")

                line_name = "Unknown"
                if "PublishedLineName" in evj:
                    line_name = evj["PublishedLineName"][0].get("value", "Unknown")
                elif "LineRef" in evj:
                    line_name = evj["LineRef"].get("value", "Unknown")

                calls = evj.get("EstimatedCalls", {}).get("EstimatedCall", [])
                for i, call in enumerate(calls):
                    stop_ref = call.get("StopPointRef", {}).get("value")
                    dep_time = call.get("ExpectedDepartureTime") or call.get(
                        "AimedDepartureTime"
                    )
                    arr_time = call.get("ExpectedArrivalTime") or call.get(
                        "AimedArrivalTime"
                    )

                    rows.append(
                        {
                            "journey_ref": journey_ref,
                            "line_ref": line_ref,
                            "line_name": line_name,
                            "stop_ref": stop_ref,
                            "arrival_time": arr_time,
                            "departure_time": dep_time,
                            "call_index": i,
                        }
                    )
    return pd.DataFrame(rows)


def main():
    stops_file = Path("data/stops.parquet")
    if not stops_file.exists():
        print("data/stops.parquet not found. Attempting to fetch from Hugging Face...")
        try:
            url = (
                "https://huggingface.co/datasets/knuthp/GTFS_Entur/"
                "resolve/main/stops.parquet"
            )
            resp = requests.get(url)
            resp.raise_for_status()
            stops_file.parent.mkdir(parents=True, exist_ok=True)
            stops_file.write_bytes(resp.content)
            print(f"Downloaded to {stops_file}")
        except Exception as e:
            print(f"Failed to fetch stops.parquet: {e}")
            sys.exit(1)

    print("Fetching live SIRI ET data...")
    try:
        siri_data = fetch_siri_et()
        calls_df = parse_siri_et_to_df(siri_data)
    except Exception as e:
        print(f"Error fetching/parsing SIRI data: {e}")
        sys.exit(1)

    if calls_df.empty:
        print("No calls found in SIRI ET data.")
        return

    db_path = Path("data/vehicle_positions.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to DuckDB ({db_path})...")
    con = duckdb.connect(str(db_path))
    con.execute("INSTALL spatial; LOAD spatial;")

    # Load stops
    con.execute(
        f"CREATE OR REPLACE VIEW stops AS SELECT * FROM read_parquet('{stops_file}')"
    )

    # Load calls
    con.register("calls_tmp", calls_df)
    con.execute("CREATE OR REPLACE TABLE calls AS SELECT * FROM calls_tmp")

    now = datetime.datetime.now(datetime.timezone.utc)
    now_str = now.isoformat()

    print(f"Estimating positions for {now_str}...")

    try:
        cols = con.execute("DESCRIBE stops").fetchall()
        col_names = [c[0] for c in cols]
        has_lat_lon = "stop_lat" in col_names and "stop_lon" in col_names

        if has_lat_lon:
            lon1, lat1 = "s1.stop_lon", "s1.stop_lat"
            lon2, lat2 = "s2.stop_lon", "s2.stop_lat"
        else:
            # Assume we need to extract from geometry
            lon1 = "ST_X(ST_GeomFromWKB(s1.geometry))"
            lat1 = "ST_Y(ST_GeomFromWKB(s1.geometry))"
            lon2 = "ST_X(ST_GeomFromWKB(s2.geometry))"
            lat2 = "ST_Y(ST_GeomFromWKB(s2.geometry))"
    except Exception as e:
        print(f"Error inspecting stops table: {e}")
        con.close()
        sys.exit(1)

    query = f"""
    CREATE OR REPLACE TABLE estimated_positions AS
    WITH journey_legs AS (
        SELECT
            c1.journey_ref,
            c1.line_ref,
            c1.line_name,
            c1.departure_time::TIMESTAMPTZ as t1,
            c2.arrival_time::TIMESTAMPTZ as t2,
            {lon1} as lon1,
            {lat1} as lat1,
            {lon2} as lon2,
            {lat2} as lat2
        FROM calls c1
        JOIN calls c2 ON c1.journey_ref = c2.journey_ref
          AND c1.call_index + 1 = c2.call_index
        JOIN stops s1 ON c1.stop_ref = s1.stop_id
        JOIN stops s2 ON c2.stop_ref = s2.stop_id
        WHERE c1.departure_time IS NOT NULL
          AND c2.arrival_time IS NOT NULL
          AND c1.departure_time::TIMESTAMPTZ <= '{now_str}'::TIMESTAMPTZ
          AND c2.arrival_time::TIMESTAMPTZ >= '{now_str}'::TIMESTAMPTZ
    )
    SELECT
        journey_ref,
        line_ref,
        line_name,
        lat1 + (lat2 - lat1) * (epoch('{now_str}'::TIMESTAMPTZ) - epoch(t1))
            / NULLIF(epoch(t2) - epoch(t1), 0) as lat,
        lon1 + (lon2 - lon1) * (epoch('{now_str}'::TIMESTAMPTZ) - epoch(t1))
            / NULLIF(epoch(t2) - epoch(t1), 0) as lon,
        '{now_str}'::TIMESTAMPTZ as estimated_at
    FROM journey_legs
    """

    con.execute(query)

    result_df = con.execute("SELECT * FROM estimated_positions").df()
    print(f"Found {len(result_df)} estimated vehicle positions.")

    if not result_df.empty:
        print("\nFirst 10 estimates:")
        cols_to_print = ["line_name", "lat", "lon", "journey_ref"]
        print(result_df[cols_to_print].head(10).to_string(index=False))
    else:
        print("No estimates found for the current time.")

    con.close()


if __name__ == "__main__":
    main()
