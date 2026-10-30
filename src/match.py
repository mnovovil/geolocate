"""Per-point building matching against Overture GeoParquet.

For each point the parquet folder is scanned exactly once, into the `candidates` temp table
(every building whose bbox lies within the search radius). The containing building, or else the
nearest one within the radius, is then picked from that temp table only.

Known limitation: the bbox window does not wrap the antimeridian, so a point within the radius
of ±180° longitude misses buildings on the other side.
"""

from __future__ import annotations

import math

import duckdb

from config import Config

METRES_PER_DEGREE = 111_320.0
# Widen the degree window: 111 320 m/° is the equatorial figure, and a meridian degree is only
# ~110 574 m, so an unpadded window can fall short of the radius by ~0.7 %.
BBOX_MARGIN = 1.1
MAX_LAT_FOR_COS = 89.9  # cos(lat) -> 0 at the poles

FIELDS = (
    "match_type",
    "distance_m",
    "building_id",
    "name",
    "class",
    "subtype",
    "height",
    "num_floors",
    "geometry_wkt",
)

# The only query that reads parquet. Filtering on the bbox struct lets DuckDB prune row groups
# via parquet statistics.
_FETCH_CANDIDATES = """
CREATE OR REPLACE TEMP TABLE candidates AS
SELECT id AS building_id, names.primary AS name, class, subtype,
       height, num_floors, geometry
FROM read_parquet(?, hive_partitioning = true)
WHERE bbox.xmin <= ? AND bbox.xmax >= ?
  AND bbox.ymin <= ? AND bbox.ymax >= ?
"""

# Distances in metres via an azimuthal-equidistant projection centred on the point. Among
# intersecting buildings the smallest (most specific) wins.
_PICK = """
WITH p AS (SELECT ST_Point(?, ?) AS pt),
scored AS (
  SELECT c.*,
         ST_Intersects(c.geometry, p.pt) AS hit,
         ST_Distance(
           ST_Transform(c.geometry, 'EPSG:4326', ?, always_xy := true),
           ST_Transform(p.pt, 'EPSG:4326', ?, always_xy := true)) AS distance_m
  FROM candidates c, p
)
SELECT CASE WHEN hit THEN 'intersects' ELSE 'nearest' END AS match_type,
       distance_m, building_id, name, class, subtype, height, num_floors,
       ST_AsText(geometry) AS geometry_wkt
FROM scored
WHERE hit OR distance_m <= ?
ORDER BY hit DESC, distance_m ASC, ST_Area(geometry) ASC
LIMIT 1
"""


def validate_point(lat: float, lon: float) -> None:
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise ValueError(f"lat/lon must be finite, got ({lat}, {lon})")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"lat/lon out of range, got ({lat}, {lon})")


def bbox_deltas(lat: float, radius_m: float) -> tuple[float, float]:
    """Half-widths (dlat, dlon) in degrees of a window covering radius_m around latitude lat."""
    r = radius_m * BBOX_MARGIN
    dlat = r / METRES_PER_DEGREE
    clamped = min(abs(lat), MAX_LAT_FOR_COS)
    dlon = min(r / (METRES_PER_DEGREE * math.cos(math.radians(clamped))), 180.0)
    return dlat, dlon


def fetch_candidates(
    con: duckdb.DuckDBPyConnection, path: str, lat: float, lon: float, radius_m: float
) -> None:
    """(Re)create the `candidates` temp table: buildings whose bbox is within radius_m."""
    dlat, dlon = bbox_deltas(lat, radius_m)
    con.execute(_FETCH_CANDIDATES, [path, lon + dlon, lon - dlon, lat + dlat, lat - dlat])


def pick_best(
    con: duckdb.DuckDBPyConnection, lat: float, lon: float, radius_m: float
) -> dict | None:
    """Pick the containing or nearest building from `candidates`; never touches parquet."""
    # Built from validated floats: the one allowed exception to parameter-only SQL values.
    proj = f"+proj=aeqd +lat_0={float(lat)} +lon_0={float(lon)} +units=m"
    row = con.execute(_PICK, [lon, lat, proj, proj, radius_m]).fetchone()
    return dict(zip(FIELDS, row, strict=True)) if row else None


def match_point(con: duckdb.DuckDBPyConnection, cfg: Config, lat: float, lon: float) -> dict | None:
    """Match one point. Returns a dict keyed by FIELDS, or None when nothing is within range."""
    validate_point(lat, lon)
    fetch_candidates(con, cfg.overture_buildings_path, lat, lon, cfg.search_radius_m)
    return pick_best(con, lat, lon, cfg.search_radius_m)
