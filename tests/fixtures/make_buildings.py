"""Build a small Overture-shaped buildings GeoParquet for unit tests.

Buildings are laid out in metres on a local azimuthal-equidistant grid centred on ORIGIN, then
transformed to WGS84, so tests can reason in exact metre offsets.

Run directly to write a copy for manual testing:
    python tests/fixtures/make_buildings.py out.parquet
"""

from __future__ import annotations

import sys

import duckdb

ORIGIN = (40.4168, -3.7038)  # (lat, lon), central Madrid

# id -> (name, class, subtype, height, num_floors, (x0, y0, x1, y1) in metres east/north of ORIGIN)
BUILDINGS = {
    # 20 x 20 m house on the origin.
    "house": ("Casa", "house", "residential", 6.0, 2, (-10, -10, 10, 10)),
    # 60 x 60 m block 200 m east, with a 10 x 10 m kiosk nested inside its centre.
    "block": ("Bloque", "commercial", "commercial", 30.0, 8, (170, -30, 230, 30)),
    "kiosk": (None, "kiosk", "commercial", 3.0, 1, (195, -5, 205, 5)),
    # A shed whose south edge is 99.9 m north of (0, 400): just inside the search radius and
    # just outside a margin-less degree window.
    "edge": (None, "shed", None, None, None, (-5, 499.9, 5, 509.9)),
}


def _proj() -> str:
    lat, lon = ORIGIN
    return f"+proj=aeqd +lat_0={lat} +lon_0={lon} +units=m"


def offset(dx: float, dy: float) -> tuple[float, float]:
    """(lat, lon) of the point dx metres east and dy metres north of ORIGIN."""
    con = duckdb.connect()
    con.execute("LOAD spatial")
    lon, lat = con.execute(
        "SELECT ST_X(g), ST_Y(g) FROM "
        "(SELECT ST_Transform(ST_Point(?, ?), ?, 'EPSG:4326', always_xy := true) AS g)",
        [dx, dy, _proj()],
    ).fetchone()
    return lat, lon


def write_buildings(path: str) -> None:
    con = duckdb.connect()
    con.execute("LOAD spatial")
    con.execute(
        "CREATE TEMP TABLE src (id VARCHAR, name VARCHAR, class VARCHAR, subtype VARCHAR, "
        "height DOUBLE, num_floors INTEGER, x0 DOUBLE, y0 DOUBLE, x1 DOUBLE, y1 DOUBLE)"
    )
    con.executemany(
        "INSERT INTO src VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [[bid, *attrs[:5], *attrs[5]] for bid, attrs in BUILDINGS.items()],
    )
    con.execute(
        """
        CREATE TEMP TABLE b AS
        SELECT * EXCLUDE (x0, y0, x1, y1),
               ST_Transform(ST_MakeEnvelope(x0, y0, x1, y1), ?, 'EPSG:4326',
                            always_xy := true) AS geometry
        FROM src
        """,
        [_proj()],
    )
    # Same column names and nesting as Overture's buildings theme (the subset we read).
    con.execute(
        f"""
        COPY (
          SELECT id,
                 {{'primary': name, 'common': NULL::MAP(VARCHAR, VARCHAR)}} AS names,
                 class, subtype, height, num_floors,
                 {{'xmin': ST_XMin(geometry)::FLOAT, 'xmax': ST_XMax(geometry)::FLOAT,
                   'ymin': ST_YMin(geometry)::FLOAT, 'ymax': ST_YMax(geometry)::FLOAT}} AS bbox,
                 geometry
          FROM b
        ) TO '{path}' (FORMAT parquet)
        """
    )


if __name__ == "__main__":
    write_buildings(sys.argv[1])
