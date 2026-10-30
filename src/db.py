"""DuckDB connection factory: spatial + httpfs, an S3 secret for Overture, and scan caches.

The first run downloads the `spatial` and `httpfs` extensions from extensions.duckdb.org into
~/.duckdb/extensions; later runs load them from there and need no network for that step.
"""

from __future__ import annotations

import duckdb

from config import Config


def connect(cfg: Config) -> duckdb.DuckDBPyConnection:
    """Return an in-memory connection ready to read Overture GeoParquet from S3."""
    # In-memory: the per-point candidate temp tables don't need to persist.
    con = duckdb.connect()
    con.execute("INSTALL spatial")
    con.execute("LOAD spatial")
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")

    if cfg.aws_access_key_id and cfg.aws_secret_access_key:
        if cfg.aws_session_token:
            con.execute(
                "CREATE OR REPLACE SECRET overture "
                "(TYPE s3, REGION ?, KEY_ID ?, SECRET ?, SESSION_TOKEN ?)",
                [
                    cfg.s3_region,
                    cfg.aws_access_key_id,
                    cfg.aws_secret_access_key,
                    cfg.aws_session_token,
                ],
            )
        else:
            con.execute(
                "CREATE OR REPLACE SECRET overture (TYPE s3, REGION ?, KEY_ID ?, SECRET ?)",
                [cfg.s3_region, cfg.aws_access_key_id, cfg.aws_secret_access_key],
            )
    else:
        # No keys: unsigned (anonymous) requests against the public Overture bucket.
        con.execute("CREATE OR REPLACE SECRET overture (TYPE s3, REGION ?)", [cfg.s3_region])

    # Each point re-scans the same parquet files; cache their footers and HTTP metadata.
    # (DuckDB 2.0 renamed enable_object_cache to parquet_metadata_cache; the old name is a no-op.)
    # GLOBAL: a plain SET of parquet_metadata_cache doesn't reach the workers' cursors.
    con.execute("SET GLOBAL parquet_metadata_cache = true")
    con.execute("SET GLOBAL enable_http_metadata_cache = true")
    return con
