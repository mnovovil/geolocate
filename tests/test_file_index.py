import json
import re
from pathlib import Path

import duckdb
import pytest

from config import ConfigError, buildings_glob, load_config
from file_index import IndexBuildError, build_index, dumps_index

INFRA = Path(__file__).resolve().parent.parent / "infra"
INDEX_FILE = INFRA / "overture_file_index.json"

# Bounds that come out wrong under string comparison: "-10.5" < "-100.0" < "-9.5" and "2.0" > "10".
ROW_GROUPS = [
    (-9.5, -5.0, 2.0, 3.0),
    (-100.0, -90.0, 10.0, 20.0),
    (-10.5, 2.0, -7.0, -5.0),
    (1.0, 10.0, 3.0, 9.0),
]


def _write(path, rows):
    """One row group per entry in rows; DuckDB merges row groups below a vector (2048 rows)."""
    values = ", ".join(
        f"({_sql(a)}::FLOAT, {_sql(b)}::FLOAT, {_sql(c)}::FLOAT, {_sql(d)}::FLOAT, {n})"
        for n, (a, b, c, d) in enumerate(rows)
    )
    duckdb.execute(
        f"""
        COPY (
          SELECT {{'xmin': a, 'xmax': b, 'ymin': c, 'ymax': d}} AS bbox, n, n > 0 AS flag
          FROM (VALUES {values}) t(a, b, c, d, n), range(2048) ORDER BY n
        ) TO '{path}' (FORMAT parquet, ROW_GROUP_SIZE 2048)
        """
    )


def _sql(v):
    return "NULL" if v is None else repr(v)


def _row_groups(path):
    return duckdb.execute(
        "SELECT count(DISTINCT row_group_id) FROM parquet_metadata(?)", [str(path)]
    ).fetchone()[0]


@pytest.fixture
def folder(tmp_path):
    d = tmp_path / "release"
    d.mkdir()
    return d


def test_bounds_are_numeric_across_row_groups(folder):
    path = folder / "a.parquet"
    _write(path, ROW_GROUPS)
    assert _row_groups(path) == len(ROW_GROUPS)

    index = build_index(duckdb.connect(), str(folder))

    assert index == {
        "source": str(folder),
        "files": [
            {"name": "a.parquet", "xmin": -100.0, "xmax": 10.0, "ymin": -7.0, "ymax": 20.0},
        ],
    }


def test_one_entry_per_file_sorted_and_source_normalized(folder):
    _write(folder / "b.parquet", ROW_GROUPS[:1])
    _write(folder / "a.parquet", ROW_GROUPS[1:2])
    index = build_index(duckdb.connect(), f" {folder}/ ")
    assert index["source"] == str(folder)
    assert [f["name"] for f in index["files"]] == ["a.parquet", "b.parquet"]


def test_row_group_without_stats_fails_the_build(folder):
    path = folder / "a.parquet"
    _write(path, [*ROW_GROUPS[:1], (None, -5.0, 2.0, 3.0)])
    assert _row_groups(path) == 2  # else min() would have nothing to silently narrow to
    with pytest.raises(IndexBuildError, match="missing bbox statistics"):
        build_index(duckdb.connect(), str(folder))


def test_inverted_stats_fail_the_build(folder):
    _write(folder / "a.parquet", [(5.0, 1.0, 2.0, 3.0)])
    with pytest.raises(IndexBuildError, match="inverted"):
        build_index(duckdb.connect(), str(folder))


def test_dumps_round_trips_with_one_file_per_line(folder):
    _write(folder / "a.parquet", ROW_GROUPS)
    _write(folder / "b.parquet", ROW_GROUPS)
    index = build_index(duckdb.connect(), str(folder))
    text = dumps_index(index)
    assert json.loads(text) == index
    assert sum('"name"' in line for line in text.splitlines()) == 2


def test_built_index_loads_through_config(folder, tmp_path):
    _write(folder / "a.parquet", ROW_GROUPS)
    index = build_index(duckdb.connect(), str(folder))
    p = tmp_path / ".geolocate.json"
    p.write_text(
        json.dumps(
            {
                "overture_buildings_path": f"{folder}/",
                "s3_region": "us-west-2",
                "aws_access_key_id": "",
                "aws_secret_access_key": "",
                "aws_session_token": "",
                "search_radius_m": 100,
                "overture_file_index": index,
            }
        )
    )
    cfg = load_config(p)
    assert cfg.overture_file_index[0].path == f"{folder}/a.parquet"
    assert cfg.overture_buildings_path == buildings_glob(str(folder))


def test_committed_index_is_for_the_default_release():
    default = re.search(
        r'variable "overture_buildings_path".*?default\s*=\s*"([^"]+)"',
        (INFRA / "variables.tf").read_text(),
        re.DOTALL,
    )[1]
    index = json.loads(INDEX_FILE.read_text())
    assert index["source"] == default.rstrip("/"), "rebuild: scripts/build_file_index.py"


def test_committed_index_is_valid(tmp_path):
    index = json.loads(INDEX_FILE.read_text())
    assert len(index["files"]) > 100
    p = tmp_path / ".geolocate.json"
    p.write_text(
        json.dumps(
            {
                "overture_buildings_path": index["source"],
                "s3_region": "us-west-2",
                "aws_access_key_id": "",
                "aws_secret_access_key": "",
                "aws_session_token": "",
                "search_radius_m": 100,
                "overture_file_index": index,
            }
        )
    )
    try:
        cfg = load_config(p)
    except ConfigError as e:
        pytest.fail(str(e))
    assert all(
        -180 <= f.xmin <= f.xmax <= 180 and -90 <= f.ymin <= f.ymax <= 90
        for f in cfg.overture_file_index
    )
