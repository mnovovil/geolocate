import duckdb
import pytest

from tests.fixtures.make_buildings import write_buildings


@pytest.fixture(scope="session")
def fixture_parquet(tmp_path_factory):
    path = tmp_path_factory.mktemp("overture") / "buildings.parquet"
    try:
        write_buildings(str(path))
    except duckdb.IOException as e:  # spatial extension not installed and no network
        pytest.skip(f"DuckDB extensions unavailable: {e}")
    return path
