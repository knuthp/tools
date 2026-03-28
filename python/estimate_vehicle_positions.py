# /// script
# dependencies = [
#   "pandas",
#   "geopandas",
#   "pyarrow",
#   "requests",
#   "shapely",
# ]
# ///

import datetime
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests


def fetch_siri_et(dataset_id="RUT"):
    """Fetch SIRI ET data from Entur."""
    url = f"https://api.entur.io/realtime/v1/rest/et?datasetId={dataset_id}"
    headers = {
        "ET-Client-Name": "jules-vehicle-estimation",
        "Accept": "application/json",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def parse_siri_et(siri_json):
    """Parse SIRI ET JSON into a list of vehicle journeys with stop times."""
    journeys = []
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

                # Try to get line name from different possible fields
                line_name = "Unknown"
                if "PublishedLineName" in evj:
                    line_name = evj["PublishedLineName"][0].get("value", "Unknown")
                elif "LineRef" in evj:
                    line_name = evj["LineRef"].get("value", "Unknown")

                calls = evj.get("EstimatedCalls", {}).get("EstimatedCall", [])
                stop_times = []
                for call in calls:
                    stop_ref = call.get("StopPointRef", {}).get("value")
                    # Use ExpectedDepartureTime if available, else AimedDepartureTime
                    dep_time = call.get("ExpectedDepartureTime") or call.get(
                        "AimedDepartureTime"
                    )
                    arr_time = call.get("ExpectedArrivalTime") or call.get(
                        "AimedArrivalTime"
                    )

                    stop_times.append(
                        {
                            "stop_ref": stop_ref,
                            "arrival_time": arr_time,
                            "departure_time": dep_time,
                        }
                    )

                if stop_times:
                    journeys.append(
                        {
                            "journey_ref": journey_ref,
                            "line_ref": line_ref,
                            "line_name": line_name,
                            "stop_times": stop_times,
                        }
                    )
    return journeys


def estimate_position(journey, stops_gdf, now=None):
    """Estimate position by linearly interpolating between two stops."""
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)

    current_stop_times = journey["stop_times"]
    prev_stop = None
    next_stop = None

    for i in range(len(current_stop_times) - 1):
        s1 = current_stop_times[i]
        s2 = current_stop_times[i + 1]

        t1_str = s1["departure_time"]
        t2_str = s2["arrival_time"]

        t1 = pd.to_datetime(t1_str).to_pydatetime() if t1_str else None
        t2 = pd.to_datetime(t2_str).to_pydatetime() if t2_str else None

        if t1 and t2 and t1 <= now <= t2:
            prev_stop = s1
            next_stop = s2
            break

    if not (prev_stop and next_stop):
        return None

    # Interpolation progress
    t1 = pd.to_datetime(prev_stop["departure_time"]).to_pydatetime()
    t2 = pd.to_datetime(next_stop["arrival_time"]).to_pydatetime()

    duration = (t2 - t1).total_seconds()
    if duration <= 0:
        progress = 0
    else:
        progress = (now - t1).total_seconds() / duration

    # Get stop coordinates from stops_gdf
    p1_ref = prev_stop["stop_ref"]
    p2_ref = next_stop["stop_ref"]

    # Entur SIRI often uses NSR:Quay:XXXX which matches stop_id in their GTFS
    s1_row = stops_gdf[stops_gdf["stop_id"] == p1_ref]
    s2_row = stops_gdf[stops_gdf["stop_id"] == p2_ref]

    if s1_row.empty or s2_row.empty:
        return None

    s1_geom = s1_row.geometry.iloc[0]
    s2_geom = s2_row.geometry.iloc[0]

    # Linear interpolation between the two points
    lat = s1_geom.y + (s2_geom.y - s1_geom.y) * progress
    lon = s1_geom.x + (s2_geom.x - s1_geom.x) * progress

    return {
        "journey_ref": journey["journey_ref"],
        "line_ref": journey["line_ref"],
        "line_name": journey["line_name"],
        "lat": lat,
        "lon": lon,
    }


def main():
    stops_file = Path("data/stops.parquet")
    if not stops_file.exists():
        print("data/stops.parquet not found. Attempting to fetch from Hugging Face...")
        try:
            url = "https://huggingface.co/datasets/knuthp/GTFS_Entur/resolve/main/stops.parquet"
            resp = requests.get(url)
            resp.raise_for_status()
            stops_file.parent.mkdir(parents=True, exist_ok=True)
            stops_file.write_bytes(resp.content)
            print(f"Downloaded to {stops_file}")
        except Exception as e:
            print(f"Failed to fetch stops.parquet: {e}")
            sys.exit(1)

    try:
        print("Loading stops data...")
        stops_gdf = gpd.read_parquet(stops_file)
    except Exception as e:
        print(f"Error loading stops.parquet: {e}")
        sys.exit(1)

    print("Fetching live SIRI ET data...")
    try:
        siri_data = fetch_siri_et()
        journeys = parse_siri_et(siri_data)
    except Exception as e:
        print(f"Error fetching SIRI data: {e}")
        sys.exit(1)

    print(f"Estimating positions for {len(journeys)} journeys...")
    now = datetime.datetime.now(datetime.timezone.utc)

    estimates = []
    for journey in journeys:
        est = estimate_position(journey, stops_gdf, now)
        if est:
            estimates.append(est)

    print(f"Found {len(estimates)} estimated vehicle positions.")

    if estimates:
        df = pd.DataFrame(estimates)
        print("\nFirst 10 estimates:")
        cols = ["line_name", "lat", "lon", "journey_ref"]
        print(df[cols].head(10).to_string(index=False))
    else:
        msg = (
            "No estimates found. This could be because the current time doesn't match "
            "any scheduled legs, or stop IDs don't match."
        )
        print(msg)


if __name__ == "__main__":
    main()
