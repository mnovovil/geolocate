"""CLI entry point: python src/geolocate.py <coords.csv> [--output out.csv] [--config path].

Reads `id, lat, lon` rows, matches each point to an Overture building, and streams one output
row per input row (same order) so finished rows survive a crash.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import duckdb

from config import ConfigError, load_config
from db import connect
from match import FIELDS, match_point, validate_point

INPUT_COLUMNS = ("id", "lat", "lon")
OUTPUT_COLUMNS = (*INPUT_COLUMNS, *FIELDS)  # public interface — keep stable

EXIT_OK = 0
EXIT_CONFIG = 1
EXIT_INPUT = 2


class InputError(Exception):
    """The input CSV is missing or doesn't have the required columns."""


def default_output(csv_path: Path) -> Path:
    return csv_path.with_name(f"{csv_path.stem}_geolocated.csv")


def read_points(csv_path: Path) -> list[tuple[str, str, str]]:
    """Return (id, lat, lon) as raw strings; values are validated per row later."""
    if not csv_path.is_file():
        raise InputError(f"Input file not found: {csv_path}")
    con = duckdb.connect()
    try:
        rel = con.execute(
            "SELECT * FROM read_csv(?, header = true, all_varchar = true)", [str(csv_path)]
        )
    except duckdb.Error as e:
        raise InputError(f"Could not read {csv_path} as CSV: {e}") from None
    columns = [d[0].strip().lower() for d in rel.description]
    missing = [c for c in INPUT_COLUMNS if c not in columns]
    if missing:
        raise InputError(f"{csv_path} is missing required columns {missing} (found {columns})")
    idx = [columns.index(c) for c in INPUT_COLUMNS]
    return [tuple(row[i] for i in idx) for row in rel.fetchall()]


def parse_point(
    raw_id: str | None, raw_lat: str | None, raw_lon: str | None
) -> tuple[float, float]:
    """Parse and validate one row; raises ValueError when the row is invalid."""
    if not raw_id or not raw_id.strip():
        raise ValueError("missing id")
    if raw_lat is None or raw_lon is None:
        raise ValueError("missing lat/lon")
    lat, lon = float(raw_lat), float(raw_lon)
    validate_point(lat, lon)
    return lat, lon


def _cell(value) -> object:
    if value is None:
        return ""
    if isinstance(value, float):
        return "" if math.isnan(value) else round(value, 2)
    return value


def run(points, cfg, out_file) -> dict[str, int]:
    writer = csv.writer(out_file)
    writer.writerow(OUTPUT_COLUMNS)
    con = connect(cfg)
    counts = dict.fromkeys(("intersects", "nearest", "none", "invalid"), 0)
    total, start = len(points), time.perf_counter()
    tty = sys.stderr.isatty()
    for n, (raw_id, raw_lat, raw_lon) in enumerate(points, 1):
        try:
            lat, lon = parse_point(raw_id, raw_lat, raw_lon)
        except ValueError:
            result = {"match_type": "invalid"}
        else:
            result = match_point(con, cfg, lat, lon) or {"match_type": "none"}
        counts[result["match_type"]] += 1
        writer.writerow([raw_id, raw_lat, raw_lon, *(_cell(result.get(f)) for f in FIELDS)])
        out_file.flush()
        elapsed = time.perf_counter() - start
        print(f"\r{n}/{total} {elapsed:.1f}s", end="" if tty else "\n", file=sys.stderr)
    if tty and total:
        print(file=sys.stderr)
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Match id,lat,lon points to the Overture building they fall in "
        "(or the nearest within the search radius)."
    )
    parser.add_argument("csv_path", type=Path, help="input CSV with columns id, lat, lon")
    parser.add_argument(
        "--output", type=Path, help="output CSV (default: <input>_geolocated.csv next to input)"
    )
    parser.add_argument("--config", type=Path, help="config JSON (overrides $GEOLOCATE_CONFIG)")
    args = parser.parse_args(argv)

    output = args.output or default_output(args.csv_path)
    if output.resolve() == args.csv_path.resolve():
        print("error: --output must differ from the input file", file=sys.stderr)
        return EXIT_INPUT
    try:
        points = read_points(args.csv_path)
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_INPUT
    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_CONFIG

    if cfg.overture_file_index is None:
        print(
            "warning: no file index for this release, so every point scans the whole folder "
            "(slow, and can use several GB of memory). See 'Changing the Overture release' "
            "in the README.",
            file=sys.stderr,
        )

    with output.open("w", newline="") as f:
        counts = run(points, cfg, f)
    summary = ", ".join(f"{k}={v}" for k, v in counts.items())
    print(f"Wrote {len(points)} rows to {output} ({summary})", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
