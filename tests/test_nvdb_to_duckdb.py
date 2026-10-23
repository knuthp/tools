from unittest.mock import MagicMock, patch

import duckdb
import pytest
import requests

from python.nvdb_to_duckdb import (
    extract_object_row,
    fetch_nvdb_page,
    ingest_nvdb_type,
)


def test_extract_object_row():
    sample_obj = {
        "id": 12345,
        "metadata": {
            "versjon": 2,
            "startdato": "2021-01-01",
            "sist_modifisert": "2023-05-10T10:00:00Z",
        },
        "geometri": {
            "wkt": "POINT Z (10.75 59.91 100.0)",
            "srid": 4326,
        },
        "egenskaper": [{"id": 1, "navn": "Test", "verdi": 50}],
        "lokasjon": {"kommuner": [3001]},
        "relasjoner": {},
        "vegsegmenter": [],
    }

    row = extract_object_row(sample_obj)
    assert row[0] == 12345  # id
    assert row[1] == 2  # version
    assert row[2] == "2021-01-01"  # startdato
    assert row[3] == "2023-05-10T10:00:00Z"  # sist_modifisert
    assert row[4] == "POINT Z (10.75 59.91 100.0)"  # wkt
    assert row[5] == "POINT Z (10.75 59.91 100.0)"
    assert row[6] == "POINT Z (10.75 59.91 100.0)"
    assert '"verdi": 50' in row[7]  # egenskaper
    assert "3001" in row[8]  # lokasjon


@patch("time.sleep", return_value=None)
@patch("requests.get")
def test_fetch_nvdb_page_retry(mock_get, mock_sleep):
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {"Retry-After": "1"}

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {"objekter": [{"id": 1}]}

    mock_get.side_effect = [mock_resp_429, mock_resp_200]

    res = fetch_nvdb_page("http://example.com", {}, {}, max_retries=3)
    assert res == {"objekter": [{"id": 1}]}
    assert mock_get.call_count == 2
    assert mock_sleep.call_count == 1


@patch("python.nvdb_to_duckdb.fetch_nvdb_page")
def test_ingest_nvdb_type_mocked(mock_fetch, tmp_path):
    mock_fetch.side_effect = [
        {
            "objekter": [
                {
                    "id": 1001,
                    "metadata": {"versjon": 1, "startdato": "2020-01-01"},
                    "geometri": {"wkt": "POINT Z (10.75 59.91 10.0)"},
                    "egenskaper": [],
                    "lokasjon": {},
                }
            ],
            "metadata": {"neste": {"start": "cursor_2"}},
        },
        {
            "objekter": [
                {
                    "id": 1002,
                    "metadata": {"versjon": 1, "startdato": "2020-01-01"},
                    "geometri": {"wkt": "POINT Z (10.76 59.92 20.0)"},
                    "egenskaper": [],
                    "lokasjon": {},
                }
            ],
            "metadata": {},
        },
    ]

    db_path = str(tmp_path / "nvdb_test.duckdb")
    total = ingest_nvdb_type(type_id=105, db_path=db_path)

    assert total == 2
    con = duckdb.connect(db_path)
    con.execute("LOAD spatial;")
    rows = con.execute(
        "SELECT id, ST_AsText(geometry) FROM vegobjekt_105 ORDER BY id"
    ).fetchall()
    con.close()

    assert len(rows) == 2
    assert rows[0][0] == 1001
    assert "10.75" in rows[0][1]
    assert rows[1][0] == 1002
    assert "10.76" in rows[1][1]


@pytest.mark.integration
def test_ingest_nvdb_type_real_api(tmp_path):
    db_path = str(tmp_path / "nvdb_real.duckdb")
    total = ingest_nvdb_type(type_id=105, db_path=db_path, limit=3)

    assert total > 0
    con = duckdb.connect(db_path)
    con.execute("LOAD spatial;")
    rows = con.execute(
        "SELECT id, ST_AsText(geometry) FROM vegobjekt_105"
    ).fetchall()
    con.close()

    assert len(rows) == total
    for row in rows:
        assert row[0] is not None
