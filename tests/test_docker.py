"""Static checks on docker/ — no Docker daemon needed.

The build context is the repo root, which holds .geolocate.json (may contain AWS keys) and
Terraform state; these tests guard that nothing but code and requirements gets into the image.
"""

import re
from pathlib import Path

from config import ENV_VAR

DOCKER = Path(__file__).resolve().parent.parent / "docker"
ALLOWED = {"requirements.txt", "src/"}


def _rules(path: Path) -> list[str]:
    lines = (line.strip() for line in path.read_text().splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def test_dockerignore_is_an_allow_list():
    rules = _rules(DOCKER / "Dockerfile.dockerignore")
    assert rules[0] == "*"
    assert {r[1:] for r in rules if r.startswith("!")} <= ALLOWED


def test_dockerfile_copies_only_code_and_requirements():
    dockerfile = (DOCKER / "Dockerfile").read_text()
    sources = {m.split()[0] for m in re.findall(r"^COPY\s+(.+)$", dockerfile, re.MULTILINE)}
    assert sources <= ALLOWED


def test_dockerfile_points_config_env_var_at_the_mount():
    assert f"{ENV_VAR}=/config/.geolocate.json" in (DOCKER / "Dockerfile").read_text()
