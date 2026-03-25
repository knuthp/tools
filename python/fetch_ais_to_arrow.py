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

PARQUET_URL = "hf://datasets/knuthp/ais_examples/pos/*.parquet"

def export_day(date: str, output: str):
    print(f"Connecting to DuckDB...")
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

    # print(f"Writing {arrow_table.num_rows} vessels to {output}...")
    feather.write_feather(arrow_table, output, compression="uncompressed")
    print(f"Done. {output} is {__import__('os').path.getsize(output) / 1024:.1f} KB")

if __name__ == "__main__":
    date   = sys.argv[1] if len(sys.argv) > 1 else "2024-03-16"
    output = sys.argv[2] if len(sys.argv) > 2 else f"data/ais/ais_{date}.feather"
    export_day(date, output)