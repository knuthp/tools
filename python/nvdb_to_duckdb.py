# /// script
# dependencies = [
#     "duckdb",
#     "requests",
# ]
# ///

"""
NVDB to DuckDB Ingestion Script
--------------------------------
Fetches road data from Statens vegvesen NVDB API Les (v3) and ingests it into a local DuckDB database.

Usage:
    uv run python/nvdb_to_duckdb.py --type-id 105
    uv run python/nvdb_to_duckdb.py --type-id 105 --limit 10 --db-path data/nvdb.duckdb
"""

import argparse
import json
import logging
import random
import time
from typing import Any, Dict, Optional

import duckdb
import requests


def fetch_nvdb_page(
    url: str,
    headers: Dict[str, str],
    params: Dict[str, Any],
    max_retries: int = 5,
    base_backoff: float = 1.0,
) -> Dict[str, Any]:
    """Fetch a single page from NVDB API with exponential backoff and jitter for resilience."""
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == max_retries:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait_time = float(retry_after)
                else:
                    wait_time = base_backoff * (2**attempt) + random.uniform(0, 0.5)
                logging.warning(
                    f"HTTP {response.status_code} received. Retrying in {wait_time:.2f}s "
                    f"(attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            return response.json()
        except (requests.RequestException, Exception) as e:
            if attempt == max_retries:
                raise
            wait_time = base_backoff * (2**attempt) + random.uniform(0, 0.5)
            logging.warning(
                f"Request failed with error: {e}. Retrying in {wait_time:.2f}s "
                f"(attempt {attempt + 1}/{max_retries})..."
            )
            time.sleep(wait_time)
    raise RuntimeError("Failed to fetch page after maximum retries.")


def extract_object_row(obj: Dict[str, Any]) -> tuple:
    """Extract table attributes from an NVDB object dictionary."""
    obj_id = obj.get("id")
    metadata = obj.get("metadata", {})
    version = metadata.get("versjon")
    startdato = metadata.get("startdato")
    sist_modifisert = metadata.get("sist_modifisert")

    geom_obj = obj.get("geometri") or obj.get("lokasjon", {}).get("geometri") or {}
    wkt = geom_obj.get("wkt") if isinstance(geom_obj, dict) else None

    egenskaper_json = json.dumps(obj.get("egenskaper", []), ensure_ascii=False)
    lokasjon_json = json.dumps(obj.get("lokasjon", {}), ensure_ascii=False)
    metadata_json = json.dumps(metadata, ensure_ascii=False)
    relasjoner_json = json.dumps(obj.get("relasjoner", {}), ensure_ascii=False)
    vegsegmenter_json = json.dumps(obj.get("vegsegmenter", []), ensure_ascii=False)

    return (
        obj_id,
        version,
        startdato,
        sist_modifisert,
        wkt,
        wkt,
        wkt,
        egenskaper_json,
        lokasjon_json,
        metadata_json,
        relasjoner_json,
        vegsegmenter_json,
    )


def ingest_nvdb_type(
    type_id: int,
    db_path: str = "nvdb.duckdb",
    table_name: Optional[str] = None,
    srid: int = 4326,
    batch_size: int = 1000,
    limit: Optional[int] = None,
    overwrite: bool = True,
    max_retries: int = 5,
    con: Optional[duckdb.DuckDBPyConnection] = None,
) -> int:
    """Fetch objects of a given NVDB type ID and ingest them into DuckDB."""
    if table_name is None:
        table_name = f"vegobjekt_{type_id}"

    close_con = False
    if con is None:
        con = duckdb.connect(db_path)
        close_con = True

    try:
        con.execute("INSTALL spatial; LOAD spatial;")

        if overwrite:
            con.execute(f"DROP TABLE IF EXISTS {table_name}")

        con.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id BIGINT PRIMARY KEY,
            version INT,
            startdato VARCHAR,
            sist_modifisert VARCHAR,
            geometry GEOMETRY,
            egenskaper JSON,
            lokasjon JSON,
            metadata JSON,
            relasjoner JSON,
            vegsegmenter JSON
        )
        """
        )

        url = f"https://nvdbapiles.atlas.vegvesen.no/vegobjekter/{type_id}"
        headers = {
            "Accept": "application/vnd.vegvesen.nvdb-v3+json",
            "X-Client": "nvdb-duckdb-uv-script",
            "X-Client-Name": "nvdb-duckdb-uv-script",
            "User-Agent": "nvdb-duckdb-uv-script/1.0",
        }

        page_size = min(batch_size, limit) if limit else batch_size
        params: Dict[str, Any] = {
            "srid": str(srid),
            "antall": page_size,
            "inkluder": "alle",
        }

        total_ingested = 0
        while True:
            data = fetch_nvdb_page(
                url, headers=headers, params=params, max_retries=max_retries
            )
            objects = data.get("objekter", [])
            if not objects:
                break

            if limit and total_ingested + len(objects) > limit:
                objects = objects[: limit - total_ingested]

            rows = [extract_object_row(obj) for obj in objects]
            if rows:
                con.executemany(
                    f"""
                INSERT OR REPLACE INTO {table_name} VALUES (
                    ?, ?, ?, ?,
                    CASE WHEN ? IS NOT NULL AND ? != '' THEN ST_GeomFromText(?) ELSE NULL END,
                    ?, ?, ?, ?, ?
                )
                """,
                    rows,
                )

            total_ingested += len(rows)
            logging.info(
                f"Ingested {len(rows)} objects into '{table_name}' (Total: {total_ingested})"
            )

            if limit and total_ingested >= limit:
                break

            neste = data.get("metadata", {}).get("neste")
            if neste and "start" in neste:
                params["start"] = neste["start"]
                if limit:
                    params["antall"] = min(batch_size, limit - total_ingested)
            else:
                break

        return total_ingested
    finally:
        if close_con and con:
            con.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ingest NVDB road data from NVDB API Les v3 into a local DuckDB database."
    )
    parser.add_argument(
        "--type-id",
        type=int,
        required=True,
        help="NVDB vegobjekt type ID (e.g. 105 for Fartsgrense).",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="nvdb.duckdb",
        help="Path to output DuckDB database file (default: nvdb.duckdb).",
    )
    parser.add_argument(
        "--table-name",
        type=str,
        default=None,
        help="DuckDB table name (default: vegobjekt_<type_id>).",
    )
    parser.add_argument(
        "--srid",
        type=int,
        default=4326,
        help="Coordinate Reference System SRID (default: 4326 for WGS84).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Page size / antall objects per API request (default: 1000).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum total number of objects to fetch (optional).",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--overwrite",
        action="store_true",
        default=True,
        help="Overwrite (drop and recreate) the table if it exists (default behavior).",
    )
    group.add_argument(
        "--append",
        action="store_false",
        dest="overwrite",
        help="Append to / update existing table instead of dropping it.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    args = parse_args()
    count = ingest_nvdb_type(
        type_id=args.type_id,
        db_path=args.db_path,
        table_name=args.table_name,
        srid=args.srid,
        batch_size=args.batch_size,
        limit=args.limit,
        overwrite=args.overwrite,
    )
    logging.info(
        f"Done! Successfully ingested {count} objects of type {args.type_id} into {args.db_path}."
    )
