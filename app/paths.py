import os
import sys
from pathlib import Path

from .version import APP_NAME


def is_packaged_app():
    return bool(getattr(sys, "frozen", False))


def app_root():
    if is_packaged_app():
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[1]


def get_user_data_dir():
    override = os.environ.get("SC_INTEL_DATA_DIR")
    if override:
        data_dir = Path(override).expanduser()
    elif not is_packaged_app():
        data_dir = app_root()
    elif os.name == "nt":
        appdata = os.environ.get("APPDATA")
        data_dir = Path(appdata) / APP_NAME if appdata else Path.home() / f".{APP_NAME.replace(' ', '-').lower()}"
    else:
        data_dir = Path.home() / f".{APP_NAME.replace(' ', '-').lower()}"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_database_path():
    override = os.environ.get("SC_INTEL_DB_PATH")
    if override:
        return Path(override).expanduser()

    if is_packaged_app():
        return get_user_data_dir() / "sc_intel.db"

    return app_root() / "sc_intel.db"
