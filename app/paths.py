import os
import shutil
import sys
import logging
from pathlib import Path


DATA_DIR_NAME = "SC-Intel-Tool"
DATABASE_FILE_NAME = "sc_intel.db"
_LOGGED_PATH_MESSAGES = set()


def is_packaged_app():
    return bool(getattr(sys, "frozen", False))


def app_root():
    if is_packaged_app():
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[1]


def bundled_root():
    if is_packaged_app() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    return app_root()


def bundled_path(*parts):
    return bundled_root().joinpath(*parts)


def log_path_message(message):
    if message in _LOGGED_PATH_MESSAGES:
        return

    _LOGGED_PATH_MESSAGES.add(message)
    print(f"[SC Intel Tool] {message}")
    logging.getLogger(__name__).info(message)


def default_user_data_dir():
    if os.name == "nt":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / DATA_DIR_NAME

        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / DATA_DIR_NAME

    return Path.home() / f".{DATA_DIR_NAME.lower()}"


def get_user_data_dir():
    override = os.environ.get("SC_INTEL_DATA_DIR")
    if override:
        data_dir = Path(override).expanduser()
    else:
        data_dir = default_user_data_dir()

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_active_data_dir():
    database_override = os.environ.get("SC_INTEL_DB_PATH")
    if database_override:
        data_dir = Path(database_override).expanduser().parent
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    return get_user_data_dir()


def old_local_database_path():
    return app_root() / DATABASE_FILE_NAME


def migrate_old_database_if_needed(database_path):
    old_database = old_local_database_path()
    if old_database == database_path or not old_database.exists():
        return

    if database_path.exists():
        log_path_message(
            f"Old local database found at {old_database}, but active database already exists at "
            f"{database_path}; leaving old database untouched."
        )
        return

    try:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old_database, database_path)
    except OSError as exc:
        log_path_message(f"Failed to migrate local database from {old_database} to {database_path}: {exc}")
        return

    log_path_message(f"Migrated local database to {database_path}; old database left untouched.")


def get_database_path():
    override = os.environ.get("SC_INTEL_DB_PATH")
    if override:
        database_path = Path(override).expanduser()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        log_path_message(f"Using database path from SC_INTEL_DB_PATH: {database_path}")
        return database_path

    database_path = get_user_data_dir() / DATABASE_FILE_NAME
    migrate_old_database_if_needed(database_path)
    log_path_message(f"Using local database at {database_path}")
    return database_path
