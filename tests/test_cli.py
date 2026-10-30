import csv
import json
from pathlib import Path

import pytest

from geolocate import EXIT_CONFIG, EXIT_INPUT, EXIT_OK, OUTPUT_COLUMNS, default_output, main

COORDS = Path(__file__).parent / "fixtures" / "coords.csv"


@pytest.fixture
def config_file(fixture_parquet, tmp_path):
    p = tmp_path / ".geolocate.json"
    p.write_text(
        json.dumps(
            {
                "overture_buildings_path": str(fixture_parquet),
                "s3_region": "us-west-2",
                "aws_access_key_id": "",
                "aws_secret_access_key": "",
                "aws_session_token": "",
                "search_radius_m": 100,
            }
        )
    )
    return p


def _read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def test_end_to_end(config_file, tmp_path, capsys):
    out = tmp_path / "out.csv"
    assert main([str(COORDS), "--output", str(out), "--config", str(config_file)]) == EXIT_OK

    with open(out, newline="") as f:
        assert next(csv.reader(f)) == list(OUTPUT_COLUMNS)
    rows = _read(out)
    assert [(r["id"], r["match_type"], r["building_id"]) for r in rows] == [
        ("p1", "intersects", "house"),
        ("p2", "nearest", "house"),
        ("p3", "none", ""),
        ("p4", "intersects", "kiosk"),
        ("p5", "invalid", ""),
        ("p6", "invalid", ""),
        ("p7", "invalid", ""),
        ("", "invalid", ""),
        ("p9", "intersects", "block"),
    ]
    p1, p2 = rows[0], rows[1]
    assert (p1["lat"], p1["lon"]) == ("40.4168270", "-3.7037764")  # echoed as given
    assert float(p1["distance_m"]) == 0
    assert (p1["name"], p1["class"], p1["height"], p1["num_floors"]) == (
        "Casa",
        "house",
        "6.0",
        "2",
    )
    assert p1["geometry_wkt"].startswith("POLYGON")
    assert float(p2["distance_m"]) == pytest.approx(30, abs=1)
    assert rows[4]["lat"] == "95"

    err = capsys.readouterr().err
    assert "9/9" in err
    assert "intersects=3, nearest=1, none=1, invalid=4" in err


def test_default_output_path():
    assert default_output(Path("/data/pts.csv")) == Path("/data/pts_geolocated.csv")


def test_default_output_written_next_to_input(config_file, tmp_path):
    src = tmp_path / "pts.csv"
    src.write_text("id,lat,lon\na,40.4168270,-3.7037764\n")
    assert main([str(src), "--config", str(config_file)]) == EXIT_OK
    assert _read(tmp_path / "pts_geolocated.csv")[0]["building_id"] == "house"


def test_header_case_and_column_order_insensitive(config_file, tmp_path):
    src = tmp_path / "pts.csv"
    src.write_text("LON, Lat ,ID\n-3.7037764,40.4168270,a\n")
    out = tmp_path / "out.csv"
    assert main([str(src), "--output", str(out), "--config", str(config_file)]) == EXIT_OK
    assert _read(out)[0]["match_type"] == "intersects"


def test_missing_column_fails(config_file, tmp_path, capsys):
    src = tmp_path / "pts.csv"
    src.write_text("id,latitude,lon\na,1,2\n")
    out = tmp_path / "out.csv"
    assert main([str(src), "--output", str(out), "--config", str(config_file)]) == EXIT_INPUT
    assert "missing required columns ['lat']" in capsys.readouterr().err
    assert not out.exists()


def test_missing_input_file_fails(config_file, tmp_path, capsys):
    assert main([str(tmp_path / "nope.csv"), "--config", str(config_file)]) == EXIT_INPUT
    assert "not found" in capsys.readouterr().err


def test_output_same_as_input_fails(config_file, capsys):
    assert main([str(COORDS), "--output", str(COORDS), "--config", str(config_file)]) == EXIT_INPUT


def test_missing_config_fails(tmp_path, capsys):
    out = tmp_path / "out.csv"
    code = main([str(COORDS), "--output", str(out), "--config", str(tmp_path / "nope.json")])
    assert code == EXIT_CONFIG
    assert "terraform -chdir=infra apply" in capsys.readouterr().err
    assert not out.exists()


def test_header_only_input_writes_header(config_file, tmp_path):
    src = tmp_path / "pts.csv"
    src.write_text("id,lat,lon\n")
    out = tmp_path / "out.csv"
    assert main([str(src), "--output", str(out), "--config", str(config_file)]) == EXIT_OK
    assert out.read_text().strip() == ",".join(OUTPUT_COLUMNS)
