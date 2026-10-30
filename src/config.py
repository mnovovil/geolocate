"""Load .geolocate.json written by the Terraform stack in infra/.

The JSON keys are a contract with infra/main.tf — change both sides together.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

ENV_VAR = "GEOLOCATE_CONFIG"
DEFAULT_PATH = Path(__file__).resolve().parent.parent / ".geolocate.json"
KEYS = (
    "overture_buildings_path",
    "s3_region",
    "aws_access_key_id",
    "aws_secret_access_key",
    "aws_session_token",
    "search_radius_m",
)
# Optional, so configs written before the index existed (or by hand) still load: without it every
# point scans the whole folder. Built by scripts/build_file_index.py, passed on by infra/main.tf.
FILE_INDEX_KEY = "overture_file_index"
_APPLY_HINT = "run `terraform -chdir=infra apply` to generate it"


class ConfigError(Exception):
    """The config file is missing or malformed."""


class IndexedFile(NamedTuple):
    """One parquet file and the bounds of all the building bboxes in it."""

    path: str
    xmin: float
    xmax: float
    ymin: float
    ymax: float


@dataclass(frozen=True)
class Config:
    overture_buildings_path: str  # parquet glob, e.g. .../type=building/*.parquet
    s3_region: str
    aws_access_key_id: str | None
    aws_secret_access_key: str | None
    aws_session_token: str | None
    search_radius_m: float
    overture_file_index: tuple[IndexedFile, ...] | None = None

    def __repr__(self) -> str:
        # Keep credentials out of logs and tracebacks.
        return (
            f"Config(overture_buildings_path={self.overture_buildings_path!r}, "
            f"s3_region={self.s3_region!r}, has_credentials={self.aws_access_key_id is not None}, "
            f"search_radius_m={self.search_radius_m!r}, "
            f"indexed_files={len(self.overture_file_index or ())})"
        )


def config_path(path: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the config location: explicit path, then $GEOLOCATE_CONFIG, then the repo root."""
    if path is not None:
        return Path(path)
    if env := os.environ.get(ENV_VAR):
        return Path(env)
    return DEFAULT_PATH


def load_config(path: str | os.PathLike[str] | None = None) -> Config:
    p = config_path(path)
    try:
        raw = json.loads(p.read_text())
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {p} — {_APPLY_HINT}") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"Config file {p} is not valid JSON ({e}) — {_APPLY_HINT}") from None
    if not isinstance(raw, dict):
        raise ConfigError(f"Config file {p} must contain a JSON object — {_APPLY_HINT}")

    missing = [k for k in KEYS if k not in raw]
    if missing:
        raise ConfigError(f"Config file {p} is missing keys {missing} — {_APPLY_HINT}")

    buildings = raw["overture_buildings_path"]
    if not isinstance(buildings, str) or not buildings.strip():
        raise ConfigError(f"overture_buildings_path in {p} must be a non-empty string")

    radius = raw["search_radius_m"]
    if isinstance(radius, bool) or not isinstance(radius, (int, float)) or radius <= 0:
        raise ConfigError(f"search_radius_m in {p} must be a positive number, got {radius!r}")

    return Config(
        overture_buildings_path=buildings_glob(buildings),
        s3_region=raw["s3_region"],
        aws_access_key_id=_optional(raw["aws_access_key_id"]),
        aws_secret_access_key=_optional(raw["aws_secret_access_key"]),
        aws_session_token=_optional(raw["aws_session_token"]),
        search_radius_m=float(radius),
        overture_file_index=_file_index(raw.get(FILE_INDEX_KEY), buildings, p),
    )


def buildings_glob(path: str) -> str:
    """Turn an Overture folder path into a parquet glob; leave globs and .parquet paths alone."""
    path = path.strip()
    if "*" in path or path.endswith(".parquet"):
        return path
    return path.rstrip("/") + "/*.parquet"


def _file_index(raw, buildings: str, p: Path) -> tuple[IndexedFile, ...] | None:
    if raw is None:
        return None
    bad = f"{FILE_INDEX_KEY} in {p}"
    if not isinstance(raw, dict) or not isinstance(raw.get("source"), str):
        raise ConfigError(f"{bad} must be an object with a source and files — {_APPLY_HINT}")
    source = raw["source"].strip().rstrip("/")
    # An index from another release would silently read that release's files.
    if source != buildings.strip().rstrip("/"):
        raise ConfigError(f"{bad} is for {source}, not {buildings} — {_APPLY_HINT}")
    files = raw.get("files")
    if not isinstance(files, list) or not files:
        raise ConfigError(f"{bad} must list at least one file — {_APPLY_HINT}")
    return tuple(_indexed_file(f, source, bad) for f in files)


def _indexed_file(raw, source: str, bad: str) -> IndexedFile:
    try:
        name = raw["name"]
        xmin, xmax, ymin, ymax = (raw[k] for k in ("xmin", "xmax", "ymin", "ymax"))
    except (KeyError, TypeError):
        raise ConfigError(f"{bad} has a malformed file entry: {raw!r}") from None
    bounds = (xmin, xmax, ymin, ymax)
    if (
        not isinstance(name, str)
        or not name
        or not all(_is_finite_number(b) for b in bounds)
        or xmin > xmax
        or ymin > ymax
    ):
        raise ConfigError(f"{bad} has a malformed file entry: {raw!r}")
    return IndexedFile(f"{source}/{name}", *map(float, bounds))


def _is_finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _optional(value: str | None) -> str | None:
    return value or None
