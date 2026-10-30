"""End-to-end run of the CLI against the live Overture release (opt-in: pytest -m s3 -s).

Uses the real .geolocate.json (or $GEOLOCATE_CONFIG). Prints per-point runtimes as a baseline.
"""

import csv
import re

import pytest

from geolocate import EXIT_OK, OUTPUT_COLUMNS, main

# id -> (lat, lon, expected match_type, substring expected in name or None)
POINTS = {
    "sydney_opera_house": (-33.8568, 151.2153, "intersects", "Opera House"),
    "tokyo_station": (35.6812, 139.7671, "intersects", None),
    "cape_town_city_hall": (-33.9255, 18.4235, "intersects", "City Hall"),
    "empire_state": (40.7484, -73.9857, "intersects", "Empire State"),
    "big_ben": (51.5007, -0.1246, "intersects", "Elizabeth Tower"),
    "madrid_sol_street": (40.4169, -3.7035, "nearest", None),
    "atlantic_ocean": (0.0, -30.0, "none", None),
}


@pytest.mark.s3
def test_cli_against_live_overture(tmp_path, capsys):
    src = tmp_path / "points.csv"
    src.write_text(
        "id,lat,lon\n" + "".join(f"{k},{lat},{lon}\n" for k, (lat, lon, *_) in POINTS.items())
    )
    out = tmp_path / "out.csv"

    assert main([str(src), "--output", str(out)]) == EXIT_OK

    with open(out, newline="") as f:
        reader = csv.DictReader(f)
        assert tuple(reader.fieldnames) == OUTPUT_COLUMNS
        rows = {r["id"]: r for r in reader}
    assert list(rows) == list(POINTS)

    for pid, (_, _, expected, name) in POINTS.items():
        r = rows[pid]
        assert r["match_type"] == expected, pid
        if expected == "none":
            assert r["building_id"] == ""
            continue
        assert r["building_id"], pid
        assert r["geometry_wkt"].startswith(("POLYGON", "MULTIPOLYGON")), pid
        distance = float(r["distance_m"])
        if expected == "intersects":
            assert distance == 0, pid
        else:
            assert 0 < distance <= 100, pid
        if name:
            assert name in r["name"], pid

    # Progress lines are "n/total <cumulative>s"; diff them into per-point runtimes.
    cumulative = [float(s) for s in re.findall(r"\d+/\d+ ([\d.]+)s", capsys.readouterr().err)]
    per_point = [b - a for a, b in zip([0.0, *cumulative], cumulative, strict=False)]
    with capsys.disabled():
        print("\nper-point runtime (live S3):")
        for pid, secs in zip(POINTS, per_point, strict=True):
            print(f"  {secs:6.1f}s  {pid:22} {rows[pid]['match_type']}")
        print(
            f"  total {cumulative[-1]:.1f}s, first point {per_point[0]:.1f}s, "
            f"rest avg {sum(per_point[1:]) / (len(per_point) - 1):.1f}s"
        )
