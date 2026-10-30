# geolocate

Match `(id, lat, lon)` points from a user-supplied CSV to the Overture Maps building they fall in
(or the nearest building within 100 m), anywhere in the world, and write a CSV with building details.

Run: `python src/geolocate.py <coords.csv> [--output out.csv]`

## Stack
- Python + DuckDB >= 2.0 (`import duckdb`, `spatial` + `httpfs` extensions — downloaded to
  `~/.duckdb/extensions` on first run, so the first run needs network)
- Data: Overture buildings GeoParquet on public S3
  (`s3://overturemaps-us-west-2/release/<release>/theme=buildings/type=building/`)
- Terraform (`infra/`) owns the Overture path and optional S3 credentials and writes them to a
  git-ignored `.geolocate.json` at the repo root.

## Architecture
```
src/geolocate.py  CLI: argparse, read + validate input CSV, loop points, write output CSV
  → src/config.py  load .geolocate.json (override path with GEOLOCATE_CONFIG / --config)
  → src/db.py      one DuckDB connection: load extensions, create S3 secret, enable caches
  → src/match.py   per point: TEMP TABLE of candidates within 100 m (the only parquet read)
                   → ST_Intersects pick → else nearest candidate from the temp table
```
All code lives in `src/`; there is no package install — `src/` is put on the path by pytest
(`pythonpath` in `pyproject.toml`) and by running the script directly.

## Contracts
- **`.geolocate.json`** (written by `infra/`, read by `src/config.py`): keys
  `overture_buildings_path`, `s3_region`, `aws_access_key_id`, `aws_secret_access_key`,
  `aws_session_token`, `search_radius_m`. Change both sides together.
- **Input CSV**: columns `id, lat, lon` (WGS84 degrees).
- **Output CSV** columns, in order: `id, lat, lon, match_type, distance_m, building_id, name,
  class, subtype, height, num_floors, geometry_wkt`. `match_type` ∈
  `intersects | nearest | none | invalid`. Treat as a public interface.

## Rules
- The parquet folder is scanned **once per point**, into the candidates temp table. The
  nearest-building fallback must query the temp table, never the parquet folder again.
- Unit tests never touch S3: use the local Overture-shaped fixture parquet. Live-S3 tests are
  marked `@pytest.mark.s3` and are excluded by default.
- Pass values into SQL as parameters (`?`), never via string formatting. The only exception is
  the per-point PROJ string for `ST_Transform`, built from validated floats.
- Always pass `always_xy := true` to `ST_Transform` (EPSG:4326 is lat/lon order in PROJ).
- Never commit `.geolocate.json`, `*.tfstate*` or `*.tfvars` — they may contain credentials.

## Commands
- Install: `uv venv .venv && uv pip install -p .venv -r requirements-dev.txt`
  (or `python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`)
- Lint: `.venv/bin/ruff check --fix .` · Format: `.venv/bin/ruff format .`
- Tests: `.venv/bin/pytest` (excludes S3) · Live S3: `.venv/bin/pytest -m s3`
- Infra: `terraform -chdir=infra init && terraform -chdir=infra apply`
