"""Load .geolocate.json written by the Terraform stack in infra/.

The JSON keys are a contract with infra/main.tf — change both sides together.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

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
_APPLY_HINT = "run `terraform -chdir=infra apply` to generate it"


class ConfigError(Exception):
    """The config file is missing or malformed."""


@dataclass(frozen=True)
class Config:
    overture_buildings_path: str  # parquet glob, e.g. .../type=building/*.parquet
    s3_region: str
    aws_access_key_id: str | None
    aws_secret_access_key: str | None
    aws_session_token: str | None
    search_radius_m: float

    def __repr__(self) -> str:
        # Keep credentials out of logs and tracebacks.
        return (
            f"Config(overture_buildings_path={self.overture_buildings_path!r}, "
            f"s3_region={self.s3_region!r}, has_credentials={self.aws_access_key_id is not None}, "
            f"search_radius_m={self.search_radius_m!r})"
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
    )


def buildings_glob(path: str) -> str:
    """Turn an Overture folder path into a parquet glob; leave globs and .parquet paths alone."""
    path = path.strip()
    if "*" in path or path.endswith(".parquet"):
        return path
    return path.rstrip("/") + "/*.parquet"


def _optional(value: str | None) -> str | None:
    return value or None
