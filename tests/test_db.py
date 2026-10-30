import duckdb
import pytest

from config import Config
from db import connect

ANON = Config(
    overture_buildings_path=(
        "s3://overturemaps-us-west-2/release/2026-10-21.0/theme=buildings/type=building/*.parquet"
    ),
    s3_region="us-west-2",
    aws_access_key_id=None,
    aws_secret_access_key=None,
    aws_session_token=None,
    search_radius_m=100.0,
)
WITH_KEYS = Config(
    **{
        **ANON.__dict__,
        "aws_access_key_id": "AKIATEST",
        "aws_secret_access_key": "SUPERSECRET",
        "aws_session_token": "SESSIONTOKEN",
    }
)


def _connect_or_skip(cfg):
    try:
        return connect(cfg)
    except duckdb.IOException as e:  # extensions not installed and no network to fetch them
        pytest.skip(f"DuckDB extensions unavailable: {e}")


def _secret(con):
    return con.execute(
        "SELECT type, secret_string FROM duckdb_secrets() WHERE name = 'overture'"
    ).fetchone()


def test_spatial_loaded():
    con = _connect_or_skip(ANON)
    assert con.execute("SELECT ST_AsText(ST_Point(0, 0))").fetchone() == ("POINT (0 0)",)


def test_anonymous_secret_has_region_only():
    con = _connect_or_skip(ANON)
    kind, secret = _secret(con)
    assert kind == "s3"
    assert "region=us-west-2" in secret
    assert "key_id=" not in secret


def test_secret_with_keys_is_redacted():
    con = _connect_or_skip(WITH_KEYS)
    _, secret = _secret(con)
    assert "key_id=AKIATEST" in secret
    assert "SUPERSECRET" not in secret
    assert "SESSIONTOKEN" not in secret


def test_secret_without_session_token():
    con = _connect_or_skip(Config(**{**WITH_KEYS.__dict__, "aws_session_token": None}))
    _, secret = _secret(con)
    assert "key_id=AKIATEST" in secret
    assert "session_token" not in secret


def test_caches_enabled():
    con = _connect_or_skip(ANON)
    rows = dict(
        con.execute(
            "SELECT name, value FROM duckdb_settings() "
            "WHERE name IN ('parquet_metadata_cache', 'enable_http_metadata_cache')"
        ).fetchall()
    )
    assert rows == {"parquet_metadata_cache": "true", "enable_http_metadata_cache": "true"}


@pytest.mark.s3
def test_reads_overture_from_s3():
    con = connect(ANON)
    row = con.execute(
        "SELECT id FROM read_parquet(?) LIMIT 1", [ANON.overture_buildings_path]
    ).fetchone()
    assert row is not None


def test_cursors_share_secret_extensions_and_caches():
    with _connect_or_skip(ANON).cursor() as cur:
        assert cur.execute("SELECT count(*) FROM duckdb_secrets()").fetchone() == (1,)
        assert cur.execute("SELECT ST_AsText(ST_Point(1, 2))").fetchone() == ("POINT (1 2)",)
        for setting in ("parquet_metadata_cache", "enable_http_metadata_cache"):
            assert cur.execute("SELECT current_setting(?)", [setting]).fetchone() == (True,)
