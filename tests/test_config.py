import json

import pytest

from config import (
    DEFAULT_PATH,
    ENV_VAR,
    FILE_INDEX_KEY,
    KEYS,
    Config,
    ConfigError,
    IndexedFile,
    buildings_glob,
    load_config,
)

# Mirrors jsonencode({...}) in infra/main.tf with the variable defaults.
TERRAFORM_OUTPUT = {
    "overture_buildings_path": (
        "s3://overturemaps-us-west-2/release/2026-10-21.0/theme=buildings/type=building/"
    ),
    "s3_region": "us-west-2",
    "aws_access_key_id": "",
    "aws_secret_access_key": "",
    "aws_session_token": "",
    "search_radius_m": 100,
    "overture_file_index": None,
}
FOLDER = TERRAFORM_OUTPUT["overture_buildings_path"]
ENTRY = {"name": "a.parquet", "xmin": -4.5, "xmax": -3, "ymin": 40, "ymax": 41.5}


@pytest.fixture
def write_config(tmp_path):
    def _write(**overrides):
        p = tmp_path / ".geolocate.json"
        p.write_text(json.dumps({**TERRAFORM_OUTPUT, **overrides}))
        return p

    return _write


def test_fixture_matches_contract_keys():
    assert set(TERRAFORM_OUTPUT) == {*KEYS, FILE_INDEX_KEY}


def test_loads_terraform_output(write_config):
    cfg = load_config(write_config())
    assert cfg == Config(
        overture_buildings_path=(
            "s3://overturemaps-us-west-2/release/2026-10-21.0/theme=buildings/type=building/*.parquet"
        ),
        s3_region="us-west-2",
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        search_radius_m=100.0,
    )


def test_credentials_kept_when_set(write_config):
    cfg = load_config(write_config(aws_access_key_id="AKIA", aws_secret_access_key="s3cret"))
    assert cfg.aws_access_key_id == "AKIA"
    assert cfg.aws_secret_access_key == "s3cret"
    assert cfg.aws_session_token is None
    assert "s3cret" not in repr(cfg)


def test_config_is_frozen(write_config):
    cfg = load_config(write_config())
    with pytest.raises(AttributeError):
        cfg.s3_region = "eu-west-1"


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("s3://b/type=building/", "s3://b/type=building/*.parquet"),
        ("s3://b/type=building", "s3://b/type=building/*.parquet"),
        ("s3://b/type=building/*.parquet", "s3://b/type=building/*.parquet"),
        ("tests/fixtures/buildings.parquet", "tests/fixtures/buildings.parquet"),
    ],
)
def test_buildings_glob(path, expected):
    assert buildings_glob(path) == expected


def test_missing_file_mentions_terraform(tmp_path):
    with pytest.raises(ConfigError, match=r"terraform -chdir=infra apply"):
        load_config(tmp_path / "nope.json")


def test_env_var_override(write_config, monkeypatch):
    monkeypatch.setenv(ENV_VAR, str(write_config(s3_region="eu-west-1")))
    assert load_config().s3_region == "eu-west-1"


def test_explicit_path_beats_env_var(write_config, tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_VAR, str(tmp_path / "nope.json"))
    assert load_config(write_config()).s3_region == "us-west-2"


def test_default_path_is_repo_root():
    assert DEFAULT_PATH.name == ".geolocate.json"
    assert (DEFAULT_PATH.parent / "pyproject.toml").exists()


def test_missing_key(write_config):
    p = write_config()
    data = json.loads(p.read_text())
    del data["s3_region"]
    p.write_text(json.dumps(data))
    with pytest.raises(ConfigError, match="s3_region"):
        load_config(p)


def test_invalid_json(tmp_path):
    p = tmp_path / ".geolocate.json"
    p.write_text("{not json")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_config(p)


@pytest.mark.parametrize("radius", [0, -5, "100", True])
def test_invalid_radius(write_config, radius):
    with pytest.raises(ConfigError, match="search_radius_m"):
        load_config(write_config(search_radius_m=radius))


def test_file_index_key_is_optional(write_config):
    p = write_config()
    raw = json.loads(p.read_text())
    del raw[FILE_INDEX_KEY]
    p.write_text(json.dumps(raw))
    assert load_config(p).overture_file_index is None


def test_file_index_loaded_with_full_paths(write_config):
    cfg = load_config(write_config(overture_file_index={"source": FOLDER, "files": [ENTRY]}))
    assert cfg.overture_file_index == (
        IndexedFile(FOLDER.rstrip("/") + "/a.parquet", -4.5, -3.0, 40.0, 41.5),
    )


def test_file_index_stays_out_of_repr(write_config):
    cfg = load_config(write_config(overture_file_index={"source": FOLDER, "files": [ENTRY]}))
    assert "a.parquet" not in repr(cfg) and "indexed_files=1" in repr(cfg)


def test_file_index_source_ignores_trailing_slash(write_config):
    index = {"source": FOLDER.rstrip("/"), "files": [ENTRY]}
    assert load_config(write_config(overture_file_index=index)).overture_file_index


def test_file_index_from_another_release_is_rejected(write_config):
    index = {"source": "s3://b/release/old/", "files": [ENTRY]}
    with pytest.raises(ConfigError, match="s3://b/release/old"):
        load_config(write_config(overture_file_index=index))


@pytest.mark.parametrize(
    "bad",
    [
        "nope",
        {"files": [ENTRY]},
        {"source": FOLDER},
        {"source": FOLDER, "files": []},
        {"source": FOLDER, "files": ["nope"]},
        {"source": FOLDER, "files": [{**ENTRY, "name": ""}]},
        {"source": FOLDER, "files": [{k: v for k, v in ENTRY.items() if k != "ymax"}]},
        {"source": FOLDER, "files": [{**ENTRY, "xmin": "-4.5"}]},
        {"source": FOLDER, "files": [{**ENTRY, "xmin": True}]},
        {"source": FOLDER, "files": [{**ENTRY, "xmin": float("nan")}]},
        {"source": FOLDER, "files": [{**ENTRY, "xmin": 5}]},  # inverted
    ],
)
def test_malformed_file_index_is_rejected(write_config, bad):
    with pytest.raises(ConfigError, match=FILE_INDEX_KEY):
        load_config(write_config(overture_file_index=bad))
