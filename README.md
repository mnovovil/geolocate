# geolocate

Match `(id, lat, lon)` points to the [Overture Maps](https://overturemaps.org) building they fall
in, or the nearest building within 100 m, anywhere in the world. Reads Overture's public
GeoParquet on S3 with DuckDB; no AWS account needed.

## Prerequisites

- Python ≥ 3.10, or Docker (see [Docker](#docker))
- Terraform ≥ 1.3 (or OpenTofu) — only to generate the local config file
- Network access to S3 (`us-west-2`) and, on the first run, to `extensions.duckdb.org`

## Setup

```bash
uv venv .venv && uv pip install -p .venv -r requirements.txt
# or: python -m venv .venv && .venv/bin/pip install -r requirements.txt
terraform -chdir=infra init && terraform -chdir=infra apply   # writes .geolocate.json (mode 0600)
```

The first run downloads DuckDB's `spatial` and `httpfs` extensions into `~/.duckdb/extensions`.

### Changing the Overture release

Overture publishes a new release roughly monthly and removes old ones from S3, so a pinned release
eventually stops working (reads fail with `No files found that match the pattern`). To bump it,
copy `infra/terraform.tfvars.example` to `infra/terraform.tfvars` (git-ignored), set
`overture_buildings_path` to a current release from the
[Overture release calendar](https://docs.overturemaps.org/release-calendar/), rebuild the file
index for it, and run `terraform -chdir=infra apply` again:

```bash
.venv/bin/python scripts/build_file_index.py s3://overturemaps-us-west-2/release/<release>/theme=buildings/type=building/
terraform -chdir=infra apply
```

The index (`infra/overture_file_index.json`) records each parquet file's bounding box, so a point
reads only the files that can hold it. Building it takes about a minute and can use over 4 GB of
memory, but only needs doing once per release; commit the result. If it doesn't match the
configured release, `apply` reports `file_index_active = false` and the CLI warns and scans the
whole folder instead: the results are the same, but much slower and using several GB of memory.

The same file sets `search_radius_m` and optional S3
credentials; the state file then contains those credentials, so keep it out of git (it is
ignored by default).

## Usage

```bash
.venv/bin/python src/geolocate.py my-points.csv                  # -> my-points_geolocated.csv
.venv/bin/python src/geolocate.py my-points.csv --output out.csv --config path/to/.geolocate.json
```

### Input

Any CSV with a header containing `id`, `lat`, `lon` (WGS84 degrees). Header case and column order
don't matter; extra columns are ignored.

```csv
id,lat,lon
empire,40.7484,-73.9857
bigben,51.5007,-0.1246
```

Progress goes to stderr. Exit codes: `0` success, `1` missing/invalid config, `2` missing input
file or missing columns. Bad rows don't abort the run; they're written with `match_type = invalid`.

### Output

One row per input row, same order, written as each point finishes. Columns (a stable interface):

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

Building columns are empty for `none` and `invalid`.

## Docker

Run the CLI without a local Python setup. The image contains the code and DuckDB's `spatial` and
`httpfs` extensions, so at run time it only needs network access to S3.

Build it from the repo root:

```bash
docker build -f docker/Dockerfile -t geolocate .
```

The config is **not** in the image (it may contain AWS keys). Generate `.geolocate.json` on the
host as in [Setup](#setup), or write it by hand with the keys `overture_buildings_path`,
`s3_region`, `aws_access_key_id`, `aws_secret_access_key`, `aws_session_token` (`null` for
anonymous access) and `search_radius_m` (a hand-written config has no file index, so it runs the
slower whole-folder scan). Then mount it at `/config/.geolocate.json` and mount
the folder holding your CSV at `/data`:

```bash
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PWD/.geolocate.json:/config/.geolocate.json:ro" \
  -v "$PWD:/data" \
  geolocate my-points.csv                   # -> ./my-points_geolocated.csv
```

- Paths are relative to `/data`. For a CSV elsewhere, mount its folder instead:
  `-v /path/to/folder:/data`.
- Everything after `geolocate` goes to the CLI, e.g. `--output out.csv` or `--help`.
- `--user "$(id -u):$(id -g)"` runs as you, so the container can write into your folder and the
  output CSV is owned by you (without it the container runs as UID 1000).
- To keep the config somewhere else, mount it anywhere and pass `--config /that/path`.

## How it works

For each point:

1. **Candidates** — one query reads the Overture parquet files for buildings whose `bbox` overlaps
   a degree window around the point (the 100 m radius plus a 10 % margin), into a DuckDB temp
   table. The file index picks which files to read, so there is no S3 listing and no scan of the
   other files; filtering on `bbox` then lets DuckDB skip most row groups via parquet statistics.
   This is the only parquet read per point.
2. **Intersects** — `ST_Intersects` against the temp table finds the building containing the point.
   If several do (e.g. nested building parts), the smallest wins.
3. **Nearest** — otherwise, the closest building in the temp table within 100 m, measured in metres
   in an azimuthal-equidistant projection centred on the point.

## Known limitations

- **Per-point S3 latency**: points take ~1–2 s each (the first ~3 s), so large inputs take a
  while — about 30 minutes per 1 500 points. Without a file index the first points take ~15–30 s
  and later ones ~2–10 s, with a peak of about 3.6 GB of memory.
- **Antimeridian**: points within the search radius of ±180° longitude don't see buildings on the
  other side.
- **IPv6**: on hosts with broken IPv6, DuckDB's extension download can time out (it doesn't fall
  back to IPv4). Download the `.duckdb_extension.gz` files with `curl -4` from
  `http://extensions.duckdb.org/v<duckdb-version>/<platform>/` and run
  `INSTALL '/path/to/<name>.duckdb_extension'` once.

## Development

```bash
uv pip install -p .venv -r requirements-dev.txt
.venv/bin/ruff check --fix . && .venv/bin/ruff format .
.venv/bin/pytest              # unit tests on a local fixture parquet (no network)
.venv/bin/pytest -m s3 -s     # live tests against Overture on S3, with per-point timings
```
