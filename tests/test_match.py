import math
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

import match
from config import Config, IndexedFile
from db import connect
from file_index import build_index
from match import FIELDS, bbox_deltas, fetch_candidates, files_for, match_point, pick_best
from tests.fixtures.make_buildings import offset


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


def test_concurrent_cursors_keep_their_own_candidates(con, cfg):
    points = {"house": offset(2, 3), "block": offset(180, 20), "kiosk": offset(200, 0), None: None}
    points[None] = offset(-160, 0)
    barrier = threading.Barrier(len(points))

    def worker(expected):
        with con.cursor() as cur:
            barrier.wait(10)
            for _ in range(30):
                m = match_point(cur, cfg, *points[expected])
                assert (m and m["building_id"]) == expected

    with ThreadPoolExecutor(len(points)) as pool:
        for future in [pool.submit(worker, k) for k in points]:
            future.result()


def test_files_for_selects_only_overlapping_files():
    index = (
        IndexedFile("west", -10.0, -5.0, 0.0, 10.0),
        IndexedFile("east", 5.0, 10.0, 0.0, 10.0),
        IndexedFile("wide", -10.0, 10.0, 0.0, 10.0),
    )
    assert files_for(index, 5.0, -7.0, 100) == ["west", "wide"]
    assert files_for(index, 5.0, 0.0, 100) == ["wide"]
    assert files_for(index, 50.0, 0.0, 100) == []


def test_files_for_includes_file_just_within_the_radius():
    dlat, dlon = bbox_deltas(5.0, 100)
    index = (IndexedFile("near", -3.0, -1.0, 0.0, 10.0),)
    assert files_for(index, 5.0, -1.0 + dlon * 0.99, 100) == ["near"]
    assert files_for(index, 5.0, -1.0 + dlon * 1.01, 100) == []
    index = (IndexedFile("north", -3.0, -1.0, 6.0, 7.0),)
    assert files_for(index, 6.0 - dlat * 0.99, -2.0, 100) == ["north"]


@pytest.fixture
def split_parquet(fixture_parquet, tmp_path):
    """The fixture buildings split in two files, plus an index of them."""
    c = connect(_config(fixture_parquet))
    folder = tmp_path / "split"
    folder.mkdir()
    for name, cond in (("west", "bbox.xmin < ?"), ("east", "bbox.xmin >= ?")):
        c.execute(
            f"COPY (SELECT * FROM read_parquet(?) WHERE {cond}) TO '{folder / name}.parquet' "
            "(FORMAT parquet)",
            [str(fixture_parquet), offset(100, 0)[1]],
        )
    index = build_index(c, str(folder))
    assert len(index["files"]) == 2
    return folder, tuple(
        IndexedFile(f"{folder}/{f['name']}", f["xmin"], f["xmax"], f["ymin"], f["ymax"])
        for f in index["files"]
    )


@pytest.mark.parametrize(
    "dxdy", [(2, 3), (0, -40), (-160, 0), (200, 0), (180, 20), (0, 400), (5000, 5000)]
)
def test_index_gives_same_result_as_glob(split_parquet, dxdy):
    folder, index = split_parquet
    glob_cfg = _config(f"{folder}/*.parquet")
    c = connect(glob_cfg)
    lat, lon = offset(*dxdy)
    indexed = match_point(c, replace(glob_cfg, overture_file_index=index), lat, lon)
    assert indexed == match_point(c, glob_cfg, lat, lon)


def test_unselected_file_is_never_read(split_parquet):
    folder, index = split_parquet
    (folder / "east.parquet").unlink()  # the house is in west; a read of east would now fail
    cfg = replace(_config(f"{folder}/*.parquet"), overture_file_index=index)
    assert match_point(connect(cfg), cfg, *offset(2, 3))["building_id"] == "house"


def test_no_overlapping_file_runs_no_query():
    index = (IndexedFile("/does/not/exist.parquet", 100.0, 101.0, 0.0, 1.0),)
    cfg = replace(_config("unused"), overture_file_index=index)

    class NoQueries:
        def execute(self, *_):
            raise AssertionError("no query expected")

    assert match_point(NoQueries(), cfg, 40.0, -3.0) is None


@pytest.mark.s3
def test_index_matches_glob_on_live_overture():
    from config import load_config

    cfg = load_config()
    assert cfg.overture_file_index, "run `terraform -chdir=infra apply` to get the file index"
    points = [(40.4153, -3.6844), (-33.8568, 151.2153), (0.0, -30.0), (40.4169, -3.7035)]
    indexed = connect(cfg)
    with_index = [match_point(indexed, cfg, *p) for p in points]
    indexed.close()
    glob_cfg = replace(cfg, overture_file_index=None)
    glob_con = connect(glob_cfg)
    assert with_index == [match_point(glob_con, glob_cfg, *p) for p in points]


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
