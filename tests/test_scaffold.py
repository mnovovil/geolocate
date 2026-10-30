import importlib


def test_src_modules_importable():
    for name in ("geolocate", "config", "db", "file_index", "match"):
        importlib.import_module(name)
