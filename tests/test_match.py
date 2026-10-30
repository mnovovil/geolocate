import math
import re
import shutil
import time
from pathlib import Path

import duckdb
import pytest

import match
from config import Config
from db import connect
from match import FIELDS, bbox_deltas, fetch_candidates, match_point, pick_best
from tests.fixtures.make_buildings import offset, write_buildings


@pytest.fixture(scope="module")
def fixture_parquet(tmp_path_factory):
    path = tmp_path_factory.mktemp("overture") / "buildings.parquet"
    try:
        write_buildings(str(path))
    except duckdb.IOException as e:  # spatial extension not installed and no network
        pytest.skip(f"DuckDB extensions unavailable: {e}")
    return path


def _config(path) -> Config:
    return Config(
        overture_buildings_path=str(path),
        s3_region="us-west-2",
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        search_radius_m=100.0,
    )


@pytest.fixture(scope="module")
def cfg(fixture_parquet):
    return _config(fixture_parquet)


@pytest.fixture(scope="module")
def con(cfg):
    return connect(cfg)


def test_point_inside_polygon_intersects(con, cfg):
    m = match_point(con, cfg, *offset(2, 3))
    assert m["match_type"] == "intersects"
    assert m["building_id"] == "house"
    assert m["distance_m"] == 0
    assert (m["name"], m["class"], m["subtype"]) == ("Casa", "house", "residential")
    assert (m["height"], m["num_floors"]) == (6.0, 2)
    assert m["geometry_wkt"].startswith("POLYGON")
    assert tuple(m) == FIELDS


def test_point_30m_outside_is_nearest(con, cfg):
    m = match_point(con, cfg, *offset(0, -40))  # house's south edge is at y = -10
    assert m["match_type"] == "nearest"
    assert m["building_id"] == "house"
    assert m["distance_m"] == pytest.approx(30, abs=1)


def test_point_150m_from_everything_is_none(con, cfg):
    assert match_point(con, cfg, *offset(-160, 0)) is None


def test_nested_buildings_smallest_area_wins(con, cfg):
    m = match_point(con, cfg, *offset(200, 0))
    assert m["match_type"] == "intersects"
    assert m["building_id"] == "kiosk"


def test_outer_building_when_outside_nested_one(con, cfg):
    assert match_point(con, cfg, *offset(180, 20))["building_id"] == "block"


def test_bbox_margin_keeps_building_at_edge_of_radius(con, cfg):
    m = match_point(con, cfg, *offset(0, 400))
    assert m["building_id"] == "edge"
    assert m["distance_m"] == pytest.approx(99.9, abs=0.5)
    assert m["name"] is None and m["height"] is None


@pytest.mark.parametrize(
    ("lat", "lon"), [(0.0, 179.9999), (0.0, -180.0), (89.999, 10.0), (-90.0, 0.0)]
)
def test_extreme_coordinates_do_not_crash(con, cfg, lat, lon):
    assert match_point(con, cfg, lat, lon) is None


@pytest.mark.parametrize(("lat", "lon"), [(91, 0), (0, 181), (math.nan, 0), (0, math.inf)])
def test_invalid_coordinates_raise(con, cfg, lat, lon):
    with pytest.raises(ValueError):
        match_point(con, cfg, lat, lon)


def test_bbox_deltas_equator():
    dlat, dlon = bbox_deltas(0, 100)
    assert dlat == pytest.approx(100 * 1.1 / 111_320)
    assert dlon == pytest.approx(dlat)


def test_bbox_deltas_widen_with_latitude():
    dlat, dlon = bbox_deltas(60, 100)
    assert dlon == pytest.approx(2 * dlat)
    assert bbox_deltas(-60, 100) == (dlat, dlon)


def test_bbox_deltas_clamped_at_pole():
    _, dlon = bbox_deltas(90, 100)
    assert math.isfinite(dlon) and dlon <= 180


def test_fallback_reads_only_temp_table(fixture_parquet, tmp_path):
    copy = tmp_path / "buildings.parquet"
    shutil.copy(fixture_parquet, copy)
    c = connect(_config(copy))
    lat, lon = offset(0, -40)
    fetch_candidates(c, str(copy), lat, lon, 100)
    copy.unlink()  # any further parquet read would now fail
    assert pick_best(c, lat, lon, 100)["building_id"] == "house"


def test_parquet_read_in_one_query_only():
    source = Path(match.__file__).read_text()
    assert len(re.findall(r"read_parquet\(", source)) == 1


@pytest.mark.s3
def test_match_on_live_overture():
    from config import load_config

    cfg = load_config()
    c = connect(cfg)
    lat, lon = 40.4153, -3.6844  # Museo del Prado, Madrid
    t = time.perf_counter()
    m = match_point(c, cfg, lat, lon)
    elapsed = time.perf_counter() - t
    print(f"\nlive match: {elapsed:.1f}s -> {m and {k: m[k] for k in FIELDS[:4]}}")
    assert m is not None and m["match_type"] in ("intersects", "nearest")
