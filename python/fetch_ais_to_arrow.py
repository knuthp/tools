# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb",
#   "pyarrow",
#   "numpy",
# ]
# ///

import sys

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.feather as feather

PARQUET_URL = "hf://datasets/knuthp/ais_examples/pos/*.parquet"
MAX_SPEED_KNOTS = 80
METERS_PER_KNOT = 1852
MAX_SPEED_MPS = (MAX_SPEED_KNOTS * METERS_PER_KNOT) / 3600

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371000 # Radius of earth in meters.
    return c * r

def clean_trajectory(lons, lats, ts):
    if not lons:
        return [], [], []

    cleaned_lons = []
    cleaned_lats = []
    cleaned_ts = []

    last_lon, last_lat, last_t = None, None, None

    for lon, lat, t in zip(lons, lats, ts):
        # Basic sanity check
        if lon == 0 and lat == 0:
            continue
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            continue

        if last_t is None:
            # First valid point
            cleaned_lons.append(lon)
            cleaned_lats.append(lat)
            cleaned_ts.append(t)
            last_lon, last_lat, last_t = lon, lat, t
        else:
            dt = t - last_t
            if dt <= 0:
                continue # Duplicate or out-of-order timestamp

            dist = haversine(last_lon, last_lat, lon, lat)
            speed = dist / dt

            if speed <= MAX_SPEED_MPS:
                cleaned_lons.append(lon)
                cleaned_lats.append(lat)
                cleaned_ts.append(t)
                last_lon, last_lat, last_t = lon, lat, t

    return cleaned_lons, cleaned_lats, cleaned_ts

def export_day(date: str, output: str):
    print("Connecting to DuckDB...")
    conn = duckdb.connect()
    conn.execute("INSTALL httpfs; LOAD httpfs;")

    print(f"Querying {date}...")
    arrow_table = conn.execute(f"""
        SELECT
            mmsi,
            list(long ORDER BY timestamp) as lons,
            list(lat  ORDER BY timestamp) as lats,
            list(epoch(timestamp) - epoch('{date} 00:00:00'::TIMESTAMP)
                 ORDER BY timestamp) as ts
        FROM '{PARQUET_URL}'
        WHERE timestamp >= '{date} 00:00:00'
          AND timestamp <  '{date} 00:00:00'::TIMESTAMP + INTERVAL 1 DAY
        GROUP BY mmsi
    """).to_arrow_table()

    print(f"Cleaning trajectories for {arrow_table.num_rows} vessels...")
    new_data = {
        'mmsi': [],
        'lons': [],
        'lats': [],
        'ts': []
    }

    for row in arrow_table.to_pylist():
        clons, clats, cts = clean_trajectory(row['lons'], row['lats'], row['ts'])
        if clons: # Only keep if we still have points
            new_data['mmsi'].append(row['mmsi'])
            new_data['lons'].append(clons)
            new_data['lats'].append(clats)
            new_data['ts'].append(cts)

    cleaned_table = pa.Table.from_pydict(new_data)

    print(f"Writing {cleaned_table.num_rows} vessels to {output}...")
    feather.write_feather(cleaned_table, output, compression="uncompressed")
    print(f"Done. {output} is {__import__('os').path.getsize(output) / 1024:.1f} KB")

if __name__ == "__main__":
    date   = sys.argv[1] if len(sys.argv) > 1 else "2024-03-16"
    output = sys.argv[2] if len(sys.argv) > 2 else f"data/ais/ais_{date}.feather"
    export_day(date, output)