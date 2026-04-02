import argparse
import asyncio
import json
import math
import os
import sqlite3
from pathlib import Path

import aiohttp


# Helper for tile math: Web Mercator
def latlon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0**zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int(
        (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)
        / 2.0
        * n
    )
    return (xtile, ytile)


def tile_to_latlon(x, y, zoom):
    n = 2.0**zoom
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)


class MBTilesWriter:
    def __init__(self, filename, metadata=None):
        self.filename = filename
        self.conn = sqlite3.connect(filename)
        self.cursor = self.conn.cursor()
        self._init_db()
        if metadata:
            self._write_metadata(metadata)

    def _init_db(self):
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS metadata (name text, value text)"
        )
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS tiles "
            "(zoom_level integer, tile_column integer, tile_row integer, "
            "tile_data blob)"
        )
        self.cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS tile_index "
            "ON tiles (zoom_level, tile_column, tile_row)"
        )

    def _write_metadata(self, metadata):
        for k, v in metadata.items():
            self.cursor.execute(
                "INSERT OR REPLACE INTO metadata (name, value) VALUES (?, ?)",
                (k, str(v)),
            )
        self.conn.commit()

    def add_tile(self, z, x, y, data):
        # MBTiles uses TMS format for Y coordinate: (2^z - 1) - y
        tms_y = (2**z - 1) - y
        self.cursor.execute(
            "INSERT OR REPLACE INTO tiles "
            "(zoom_level, tile_column, tile_row, tile_data) "
            "VALUES (?, ?, ?, ?)",
            (z, x, tms_y, data),
        )

    def close(self):
        self.conn.commit()
        self.conn.close()


async def download_tile(
    session, z, x, y, layer_url, token, base_path, mbtiles_writer=None, semaphore=None
):
    if semaphore:
        async with semaphore:
            return await _do_download(
                session, z, x, y, layer_url, token, base_path, mbtiles_writer
            )
    else:
        return await _do_download(
            session, z, x, y, layer_url, token, base_path, mbtiles_writer
        )


async def _do_download(session, z, x, y, layer_url, token, base_path, mbtiles_writer):
    # Norge i bilder new WMTS seems to be:
    # {base_url}?token={token}&service=WMTS&request=GetTile&version=1.0.0
    # &layer=nib&style=default&format=image/png&tilematrixset=webmercator
    # &tilematrix={z}&tilerow={y}&tilecol={x}

    params = {
        "service": "WMTS",
        "request": "GetTile",
        "version": "1.0.0",
        "layer": "nib",
        "style": "default",
        "format": "image/png",
        "tilematrixset": "webmercator",
        "tilematrix": str(z),
        "tilerow": str(y),
        "tilecol": str(x),
        "token": token,
    }

    url = layer_url

    try:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.read()

                # Save to disk
                tile_dir = base_path / str(z) / str(x)
                tile_dir.mkdir(parents=True, exist_ok=True)
                with open(tile_dir / f"{y}.png", "wb") as f:
                    f.write(data)

                # Add to MBTiles
                if mbtiles_writer:
                    mbtiles_writer.add_tile(z, x, y, data)
                return True
            else:
                return False
    except Exception as e:
        print(f"Error downloading tile {z}/{x}/{y}: {e}")
        return False


async def download_tiles(config):
    token = config["token"]
    extent = config["extent"]  # [min_lon, min_lat, max_lon, max_lat]
    layer_url = config["layerUrl"]
    min_zoom = config["zoom"]
    max_zoom = config.get("maxZoom", 18)

    min_lon, min_lat, max_lon, max_lat = extent

    output_dir = Path("data/nib_tiles")
    output_dir.mkdir(parents=True, exist_ok=True)

    mbtiles_path = output_dir / "norgeibilder.mbtiles"
    metadata = {
        "name": "Norge i Bilder Export",
        "type": "overlay",
        "version": "1",
        "description": f"Exported from norgeibilder.no at {config.get('timestamp')}",
        "format": "png",
        "bounds": f"{min_lon},{min_lat},{max_lon},{max_lat}",
    }
    writer = MBTilesWriter(str(mbtiles_path), metadata)

    semaphore = asyncio.Semaphore(10)  # Limit concurrency

    async with aiohttp.ClientSession() as session:
        tasks = []
        for z in range(min_zoom, max_zoom + 1):
            x1, y1 = latlon_to_tile(max_lat, min_lon, z)
            x2, y2 = latlon_to_tile(min_lat, max_lon, z)

            # Ensure order for range
            x_min, x_max = min(x1, x2), max(x1, x2)
            y_min, y_max = min(y1, y2), max(y1, y2)

            print(f"Zoom {z}: Tiles from ({x_min}, {y_min}) to ({x_max}, {y_max})")

            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    tasks.append(
                        download_tile(
                            session,
                            z,
                            x,
                            y,
                            layer_url,
                            token,
                            output_dir,
                            writer,
                            semaphore,
                        )
                    )

        print(f"Total tiles to download: {len(tasks)}")
        if not tasks:
            print("No tiles to download. Check extent and zoom.")
            return

        results = await asyncio.gather(*tasks)
        print(f"Successfully downloaded {sum(results)} tiles.")

    writer.close()
    print(f"MBTiles saved to {mbtiles_path}")


if __name__ == "__main__":
    desc = "Download Norge i Bilder tiles to MBTiles"
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to config.json from bookmarklet",
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: {args.config} not found.")
        print("Please run the bookmarklet on norgeibilder.no")
    else:
        with open(args.config, "r") as f:
            config_data = json.load(f)
        asyncio.run(download_tiles(config_data))
