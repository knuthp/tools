# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb",
#   "pyarrow",
# ]
# ///

import sys

import duckdb
import pyarrow.feather as feather

PARQUET_URL = "hf://datasets/knuthp/entur_vm/*.parquet"

def export_day(date: str, output: str):
    print("Connecting to DuckDB...")
    conn = duckdb.connect()
    conn.execute("INSTALL httpfs; LOAD httpfs;")

    print(f"Querying {date}...")
    arrow_table = conn.execute(f"""
        SELECT
            DatedVehicleJourneyRef,
            list(Longitude ORDER BY RecordedAtTime) as lons,
            list(Latitude  ORDER BY RecordedAtTime) as lats,
            list(epoch(RecordedAtTime) - epoch('{date} 00:00:00'::TIMESTAMP)
                 ORDER BY RecordedAtTime) as ts
        FROM '{PARQUET_URL}'
        WHERE DataFrameRef = '{date}'
        GROUP BY DatedVehicleJourneyRef
    """).to_arrow_table()

    # print(f"Writing {arrow_table.num_rows} vessels to {output}...")
    feather.write_feather(arrow_table, output, compression="uncompressed")
    print(f"Done. {output} is {__import__('os').path.getsize(output) / 1024:.1f} KB")

if __name__ == "__main__":
    date   = sys.argv[1] if len(sys.argv) > 1 else "2025-06-06"
    output = sys.argv[2] if len(sys.argv) > 2 else f"data/entur/vm_{date}.feather"
    export_day(date, output)