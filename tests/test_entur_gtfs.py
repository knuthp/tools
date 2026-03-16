import zipfile
from io import BytesIO

import geopandas as gpd
import pandas as pd

from python.entur_gtfs_to_geoparquet import process_gtfs


def create_mock_gtfs():
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as z:
        # stops.txt
        stops_csv = (
            "stop_id,stop_name,stop_lat,stop_lon\n"
            "1,Stop 1,59.91,10.75\n"
            "2,Stop 2,59.92,10.76\n"
        )
        z.writestr("stops.txt", stops_csv)

        # shapes.txt
        shapes_csv = (
            "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n"
            "shape1,59.91,10.75,1\n"
            "shape1,59.92,10.76,2\n"
        )
        z.writestr("shapes.txt", shapes_csv)

        # routes.txt
        routes_csv = (
            "route_id,route_short_name\n"
            "R1,10\n"
        )
        z.writestr("routes.txt", routes_csv)

    zip_buffer.seek(0)
    return zip_buffer

def test_process_gtfs(tmp_path):
    output_dir = tmp_path / "data"
    zip_buffer = create_mock_gtfs()

    process_gtfs(zip_buffer, output_dir)

    # Check stops.parquet
    stops_path = output_dir / "stops.parquet"
    assert stops_path.exists()
    gdf_stops = gpd.read_parquet(stops_path)
    assert len(gdf_stops) == 2
    assert "geometry" in gdf_stops.columns
    assert gdf_stops.iloc[0].geometry.x == 10.75

    # Check shapes.parquet
    shapes_path = output_dir / "shapes.parquet"
    assert shapes_path.exists()
    gdf_shapes = gpd.read_parquet(shapes_path)
    assert len(gdf_shapes) == 1
    assert "geometry" in gdf_shapes.columns
    assert gdf_shapes.iloc[0].geometry.geom_type == "LineString"

    # Check routes.parquet
    routes_path = output_dir / "routes.parquet"
    assert routes_path.exists()
    df_routes = pd.read_parquet(routes_path)
    assert len(df_routes) == 1
    assert "route_id" in df_routes.columns
