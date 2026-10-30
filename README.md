# geolocate

Match `(id, lat, lon)` points to the [Overture Maps](https://overturemaps.org) building they fall
in, or the nearest building within 100 m, anywhere in the world. Reads Overture's public
GeoParquet on S3 with DuckDB; no AWS account needed.

## Setup

```bash
uv venv .venv && uv pip install -p .venv -r requirements-dev.txt
terraform -chdir=infra init && terraform -chdir=infra apply   # writes .geolocate.json
```

`infra/` pins the Overture release and search radius; see `infra/terraform.tfvars.example` to
change them or add S3 credentials. The first run downloads DuckDB's `spatial` and `httpfs`
extensions, so it needs network access.

## Usage

```bash
.venv/bin/python src/geolocate.py points.csv                  # -> points_geolocated.csv
.venv/bin/python src/geolocate.py points.csv --output out.csv --config path/to/.geolocate.json
```

The input is any CSV with a header containing `id`, `lat`, `lon` (WGS84 degrees; header case and
column order don't matter, extra columns are ignored). Progress goes to stderr. The first point
is slow (~15–30 s: listing the S3 files and reading parquet metadata); later points take ~2 s.

Exit codes: `0` success, `1` missing/invalid config, `2` missing input file or missing columns.
Bad rows don't abort the run; they're written with `match_type = invalid`.

## Output

One row per input row, same order. Columns (a stable interface):

| Column | Description |
|---|---|
| `id`, `lat`, `lon` | Echoed from the input as given |
| `match_type` | `intersects` (point is inside the building), `nearest` (closest building within the radius), `none` (nothing within the radius) or `invalid` (missing id, or lat/lon missing, non-numeric or out of range) |
| `distance_m` | Metres from the point to the building, `0` for `intersects`, 2 decimals |
| `building_id` | Overture building `id` |
| `name` | `names.primary` |
| `class`, `subtype` | Overture building class and subtype |
| `height`, `num_floors` | As in Overture (often empty) |
| `geometry_wkt` | Building footprint as WKT |

Building columns are empty for `none` and `invalid`. When the point is inside several buildings
(e.g. nested parts), the smallest one wins.

Known limitation: points within the search radius of the ±180° meridian don't see buildings on
the other side.

## Development

```bash
.venv/bin/ruff check --fix . && .venv/bin/ruff format .
.venv/bin/pytest           # unit tests on a local fixture parquet
.venv/bin/pytest -m s3     # live tests against Overture on S3
```
