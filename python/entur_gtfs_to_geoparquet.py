# /// script
# dependencies = [
#   "pandas",
#   "geopandas",
#   "pyarrow",
#   "requests",
#   "shapely",
#   "huggingface_hub",
# ]
# ///

import os
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from huggingface_hub import HfApi
from shapely.geometry import LineString

GTFS_URL = "https://storage.googleapis.com/marduk-production/outbound/gtfs/rb_norway-aggregated-gtfs.zip"
OUTPUT_DIR = Path("data")
HF_REPO_ID = "knuthp/GTFS_Entur"

def download_gtfs(url, temp_file):
    print(f"Downloading GTFS from {url}...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            temp_file.write(chunk)
    temp_file.flush()
    temp_file.seek(0)
    print("Download complete.")

def process_gtfs(zip_path, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for filename in z.namelist():
            if not filename.endswith(".txt"):
                continue

            table_name = filename.replace(".txt", "")
            print(f"Processing {filename}...")

            with z.open(filename) as f:
                df = pd.read_csv(f, low_memory=False)

            if df.empty:
                print(f"Skipping empty table: {table_name}")
                continue

            output_path = output_dir / f"{table_name}.parquet"

            if filename == "stops.txt":
                print(f"Converting {filename} to GeoParquet (Points)...")
                gdf = gpd.GeoDataFrame(
                    df,
                    geometry=gpd.points_from_xy(df.stop_lon, df.stop_lat),
                    crs="EPSG:4326"
                )
                gdf.to_parquet(output_path)

            elif filename == "shapes.txt":
                print(f"Converting {filename} to GeoParquet (LineStrings)...")
                # Sort to ensure correct order of points in LineString
                df = df.sort_values(["shape_id", "shape_pt_sequence"])

                # Group by shape_id and create LineStrings
                lines = df.groupby("shape_id").apply(
                    lambda x: LineString(zip(x.shape_pt_lon, x.shape_pt_lat)),
                    include_groups=False
                )

                # Create GeoDataFrame from the Series of geometries
                gdf = gpd.GeoDataFrame(
                    lines.reset_index(), geometry=0, crs="EPSG:4326"
                )
                gdf.columns = ["shape_id", "geometry"]
                gdf = gdf.set_geometry("geometry")

                # Try to join back other attributes if they are constant per shape_id.
                # In standard GTFS, shapes.txt usually only has shape_id, lon, lat,
                # sequence, dist_traveled. Only shape_id is constant.

                gdf.to_parquet(output_path)

            else:
                print(f"Converting {filename} to Parquet...")
                df.to_parquet(output_path)

            print(f"Saved to {output_path}")

def upload_to_huggingface(directory, repo_id):
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN not found in environment. Skipping upload.")
        return

    print(f"Uploading files from {directory} to Hugging Face repo {repo_id}...")
    api = HfApi()

    # Upload the entire directory to the dataset repository
    api.upload_folder(
        folder_path=str(directory),
        repo_id=repo_id,
        repo_type="dataset",
        token=token
    )
    print("Upload complete.")

def main():
    with tempfile.NamedTemporaryFile() as tmp:
        download_gtfs(GTFS_URL, tmp)
        process_gtfs(tmp.name, OUTPUT_DIR)

    upload_to_huggingface(OUTPUT_DIR, HF_REPO_ID)
    print("Done!")

if __name__ == "__main__":
    main()
