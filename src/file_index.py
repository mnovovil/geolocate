"""Build the per-file bbox index that lets a point read only the parquet files that can hold it.

The index is generated once per Overture release by scripts/build_file_index.py and stored in
infra/overture_file_index.json; Terraform copies it into .geolocate.json (see src/config.py).
"""

from __future__ import annotations

import json
import math

import duckdb

from config import buildings_glob

# parquet_metadata() returns stats as VARCHAR, and for every column type, so the bounds must be
# cast (a plain min() compares strings) with TRY_CAST (non-numeric columns' stats are in the scan).
# A row group without stats would silently narrow a file's bounds, so they're counted as missing.
_FILE_BOUNDS = """
WITH stats AS (
  SELECT file_name, path_in_schema AS col,
         TRY_CAST(CASE WHEN path_in_schema LIKE '%min' THEN stats_min ELSE stats_max END
                  AS DOUBLE) AS bound
  FROM parquet_metadata(?)
  WHERE path_in_schema IN ('bbox, xmin', 'bbox, xmax', 'bbox, ymin', 'bbox, ymax')
)
SELECT file_name,
       min(bound) FILTER (col = 'bbox, xmin') AS xmin,
       max(bound) FILTER (col = 'bbox, xmax') AS xmax,
       min(bound) FILTER (col = 'bbox, ymin') AS ymin,
       max(bound) FILTER (col = 'bbox, ymax') AS ymax,
       count(*) - count(bound) AS missing
FROM stats
GROUP BY file_name
ORDER BY file_name
"""


class IndexBuildError(Exception):
    """A parquet file's bbox statistics can't be trusted for pruning."""


def build_index(con: duckdb.DuckDBPyConnection, folder: str) -> dict:
    """Scan the footers under folder and return {"source": folder, "files": [per-file bounds]}."""
    source = folder.strip().rstrip("/")
    prefix = source + "/"
    files = []
    for name, xmin, xmax, ymin, ymax, missing in con.execute(
        _FILE_BOUNDS, [buildings_glob(source)]
    ).fetchall():
        bounds = (xmin, xmax, ymin, ymax)
        if missing or not all(b is not None and math.isfinite(b) for b in bounds):
            raise IndexBuildError(f"{name}: missing bbox statistics")
        if xmin > xmax or ymin > ymax:
            raise IndexBuildError(f"{name}: inverted bbox statistics {bounds}")
        files.append(
            {
                "name": name.removeprefix(prefix),
                "xmin": xmin,
                "xmax": xmax,
                "ymin": ymin,
                "ymax": ymax,
            }
        )
    if not files:
        raise IndexBuildError(f"no bbox statistics found under {source}")
    return {"source": source, "files": files}


def dumps_index(index: dict) -> str:
    """Serialize with one file per line, so a release bump reads as a plain diff."""
    files = ",\n".join(f"    {json.dumps(f)}" for f in index["files"])
    return f'{{\n  "source": {json.dumps(index["source"])},\n  "files": [\n{files}\n  ]\n}}\n'
