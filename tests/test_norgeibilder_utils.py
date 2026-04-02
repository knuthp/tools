import os
import sqlite3
import unittest

from python.norgeibilder_to_mbtiles import (
    MBTilesWriter,
    latlon_to_tile,
    tile_to_latlon,
)


class TestTileUtils(unittest.TestCase):
    def test_latlon_to_tile(self):
        # Known coordinates for London (standard test case)
        # Lat: 51.5074, Lon: -0.1278, Zoom 10
        # Expected X: 511, Y: 340 (calculated manually)
        z = 10
        x, y = latlon_to_tile(51.5074, -0.1278, z)
        self.assertEqual(x, 511)
        self.assertEqual(y, 340)

    def test_tile_to_latlon(self):
        z = 10
        x, y = 511, 340
        lat, lon = tile_to_latlon(x, y, z)
        # Should return the top-left corner of the tile
        # For X=511, Z=10: Lon = 511/1024 * 360 - 180 = -0.3515625
        # For Y=340, Z=10: Lat = 51.6180165487737
        self.assertAlmostEqual(lon, -0.3515625, places=5)
        self.assertAlmostEqual(lat, 51.6180165, places=5)

    def test_mbtiles_writer(self):
        test_db = "test.mbtiles"
        if os.path.exists(test_db):
            os.remove(test_db)

        metadata = {"name": "test_map", "type": "overlay"}
        writer = MBTilesWriter(test_db, metadata)

        # Add a dummy tile
        z, x, y = 10, 511, 340
        dummy_data = b"fake-png-data"
        writer.add_tile(z, x, y, dummy_data)
        writer.close()

        # Verify with sqlite
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Check metadata
        cursor.execute("SELECT value FROM metadata WHERE name='name'")
        self.assertEqual(cursor.fetchone()[0], "test_map")

        # Check tile data and TMS Y conversion
        # MBTiles Y = (2^z - 1) - y = (2^10 - 1) - 340 = 1023 - 340 = 683
        sql = (
            "SELECT tile_data FROM tiles "
            "WHERE zoom_level=10 AND tile_column=511 AND tile_row=683"
        )
        cursor.execute(sql)
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], dummy_data)

        conn.close()
        os.remove(test_db)


if __name__ == "__main__":
    unittest.main()
