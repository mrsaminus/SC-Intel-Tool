import importlib
import sys


def reload_module(name):
    if name in sys.modules:
        return importlib.reload(sys.modules[name])
    return importlib.import_module(name)


def isolated_database(monkeypatch, tmp_path):
    data_dir = tmp_path / "SC-Intel-Tool"
    db_path = data_dir / "sc_intel.db"
    monkeypatch.setenv("SC_INTEL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SC_INTEL_DB_PATH", str(db_path))

    reload_module("app.paths")
    database = reload_module("app.database")
    database.init_db()
    return database, db_path
