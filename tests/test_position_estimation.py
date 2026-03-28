import pytest
import datetime
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from python.estimate_vehicle_positions import estimate_position

def test_estimate_position_interpolation():
    # Mock stops data
    stops_data = {
        "stop_id": ["A", "B"],
        "geometry": [Point(10.0, 59.0), Point(10.1, 59.1)]
    }
    stops_gdf = gpd.GeoDataFrame(stops_data, crs="EPSG:4326")

    # Mock journey data
    now = datetime.datetime(2024, 1, 1, 12, 5, 0, tzinfo=datetime.timezone.utc)
    t1 = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    t2 = datetime.datetime(2024, 1, 1, 12, 10, 0, tzinfo=datetime.timezone.utc)

    journey = {
        "journey_ref": "trip1",
        "line_ref": "line1",
        "line_name": "Line 1",
        "stop_times": [
            {
                "stop_ref": "A",
                "departure_time": t1.isoformat(),
                "arrival_time": None
            },
            {
                "stop_ref": "B",
                "departure_time": None,
                "arrival_time": t2.isoformat()
            }
        ]
    }

    # At 12:05, it should be exactly halfway between (10.0, 59.0) and (10.1, 59.1)
    # 10.0 + (10.1 - 10.0) * 0.5 = 10.05
    # 59.0 + (59.1 - 59.0) * 0.5 = 59.05

    result = estimate_position(journey, stops_gdf, now)

    assert result is not None
    assert result["lat"] == pytest.approx(59.05)
    assert result["lon"] == pytest.approx(10.05)
    assert result["journey_ref"] == "trip1"

def test_estimate_position_out_of_bounds():
    stops_data = {
        "stop_id": ["A", "B"],
        "geometry": [Point(10.0, 59.0), Point(10.1, 59.1)]
    }
    stops_gdf = gpd.GeoDataFrame(stops_data, crs="EPSG:4326")

    t1 = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    t2 = datetime.datetime(2024, 1, 1, 12, 10, 0, tzinfo=datetime.timezone.utc)

    journey = {
        "journey_ref": "trip1",
        "line_ref": "line1",
        "line_name": "Line 1",
        "stop_times": [
            {"stop_ref": "A", "departure_time": t1.isoformat(), "arrival_time": None},
            {"stop_ref": "B", "departure_time": None, "arrival_time": t2.isoformat()}
        ]
    }

    # Before start
    now_before = datetime.datetime(2024, 1, 1, 11, 59, 0, tzinfo=datetime.timezone.utc)
    assert estimate_position(journey, stops_gdf, now_before) is None

    # After end
    now_after = datetime.datetime(2024, 1, 1, 12, 11, 0, tzinfo=datetime.timezone.utc)
    assert estimate_position(journey, stops_gdf, now_after) is None
