from pathlib import Path

from conftest import reload_module


def test_database_path_override_is_created(monkeypatch, tmp_path):
    db_path = tmp_path / "custom" / "data.db"
    monkeypatch.setenv("SC_INTEL_DB_PATH", str(db_path))

    paths = reload_module("app.paths")

    assert paths.get_database_path() == db_path
    assert db_path.parent.exists()


def test_data_dir_override_is_default_database_parent(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SC_INTEL_DATA_DIR", str(data_dir))
    monkeypatch.delenv("SC_INTEL_DB_PATH", raising=False)

    paths = reload_module("app.paths")

    assert paths.get_database_path() == data_dir / "sc_intel.db"
    assert data_dir.exists()


def test_old_database_migration_copies_without_deleting(monkeypatch, tmp_path):
    old_root = tmp_path / "old_app"
    old_root.mkdir()
    old_db = old_root / "sc_intel.db"
    old_db.write_bytes(b"old-db")
    new_db = tmp_path / "appdata" / "sc_intel.db"

    paths = reload_module("app.paths")
    monkeypatch.setattr(paths, "app_root", lambda: old_root)

    paths.migrate_old_database_if_needed(new_db)

    assert new_db.read_bytes() == b"old-db"
    assert old_db.exists()


def test_old_database_migration_does_not_overwrite_existing_appdata(monkeypatch, tmp_path):
    old_root = tmp_path / "old_app"
    old_root.mkdir()
    (old_root / "sc_intel.db").write_bytes(b"old-db")
    new_db = tmp_path / "appdata" / "sc_intel.db"
    new_db.parent.mkdir()
    new_db.write_bytes(b"existing-db")

    paths = reload_module("app.paths")
    monkeypatch.setattr(paths, "app_root", lambda: old_root)

    paths.migrate_old_database_if_needed(new_db)

    assert new_db.read_bytes() == b"existing-db"
