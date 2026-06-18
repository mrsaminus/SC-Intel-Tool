import platform
import sys
import os
from pathlib import Path, PureWindowsPath

from .logging_config import get_log_file_path
from .mining_data import PUBLIC_MINING_ROOT
from .paths import get_active_data_dir, is_packaged_app
from .version import APP_VERSION


def runtime_asset_status():
    assets = {
        "app_icon": ("app", "assets", "SC-Intel-Tool.ico"),
        "app_logo": ("app", "assets", "SC-Intel-Tool-Logo.png"),
        "community_logo": ("app", "assets", "MadeByTheCommunity_White.png"),
        "mining_public_bundle": ("app", "assets", "mining_public"),
        "mining_locations": ("app", "assets", "mining_public", "assets", "Mineral Stats", "Mineral_Where.txt"),
        "mining_rock_data": ("app", "assets", "mining_public", "Calculator", "rock-breaking-calculator-data.json"),
        "mining_equipment_shops": (
            "app",
            "assets",
            "mining_public",
            "defaults",
            "equipment_shops_cache_default.json",
        ),
    }

    from .paths import bundled_path

    return {
        name: bundled_path(*parts).exists()
        for name, parts in assets.items()
    }


def collect_diagnostics(database_path=None):
    if database_path is None:
        from .database import DB_PATH

        database_path = DB_PATH

    return {
        "app_version": APP_VERSION,
        "runtime": "packaged" if is_packaged_app() else "source",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "executable": str(sys.executable),
        "data_dir": str(get_active_data_dir()),
        "database_path": str(database_path),
        "log_file": str(get_log_file_path()),
        "public_mining_root": str(PUBLIC_MINING_ROOT),
        "runtime_assets": runtime_asset_status(),
    }


def redact_path(value):
    text = str(value or "")
    if not text:
        return text

    pyinstaller_alias = packaged_runtime_alias(text)
    if pyinstaller_alias:
        return pyinstaller_alias

    aliases = []
    for env_name, replacement in (
        ("SC_INTEL_DATA_DIR", "%SC_INTEL_DATA_DIR%"),
        ("LOCALAPPDATA", "%LOCALAPPDATA%"),
        ("APPDATA", "%APPDATA%"),
        ("USERPROFILE", "%USERPROFILE%"),
    ):
        raw_value = os.environ.get(env_name)
        if raw_value:
            aliases.append((str(Path(raw_value).expanduser()), replacement))

    try:
        aliases.append((str(Path.home()), "~"))
    except RuntimeError:
        pass

    for prefix, replacement in sorted(aliases, key=lambda item: len(item[0]), reverse=True):
        if not prefix:
            continue
        normalized_prefix = prefix.rstrip("\\/")
        lower_text = text.lower()
        lower_prefix = normalized_prefix.lower()
        if lower_text == lower_prefix:
            return replacement
        if lower_text.startswith(lower_prefix + "\\") or lower_text.startswith(lower_prefix + "/"):
            return replacement + text[len(normalized_prefix):]

    return text


def packaged_runtime_alias(value):
    text = str(value or "")
    if not text:
        return ""

    try:
        parts = Path(text).parts
    except (OSError, ValueError):
        return ""

    for index, part in enumerate(parts):
        if part.lower().startswith("_mei"):
            suffix = parts[index + 1:]
            if suffix:
                return str(PureWindowsPath("<packaged_runtime>", *suffix))
            return "<packaged_runtime>"

    runtime_root = getattr(sys, "_MEIPASS", "")
    if runtime_root:
        runtime_root = str(Path(runtime_root))
        if text.lower().startswith(runtime_root.lower()):
            suffix = text[len(runtime_root):].lstrip("\\/")
            if suffix:
                return str(PureWindowsPath("<packaged_runtime>", *Path(suffix).parts))
            return "<packaged_runtime>"

    return ""


def diagnostic_line(label, value):
    return f"{label:<20}: {value}"


def format_diagnostics(diagnostics):
    lines = [
        "SC Intel Tool Diagnostics",
        diagnostic_line("App version", diagnostics.get("app_version", "Unknown")),
        diagnostic_line("Runtime", diagnostics.get("runtime", "Unknown")),
        diagnostic_line("Python", diagnostics.get("python", "Unknown")),
        diagnostic_line("Platform", diagnostics.get("platform", "Unknown")),
        diagnostic_line("Executable", redact_path(diagnostics.get("executable", "Unknown"))),
        diagnostic_line("Data directory", redact_path(diagnostics.get("data_dir", "Unknown"))),
        diagnostic_line("Database path", redact_path(diagnostics.get("database_path", "Unknown"))),
        diagnostic_line("Log file", redact_path(diagnostics.get("log_file", "Unknown"))),
        diagnostic_line("Public mining root", redact_path(diagnostics.get("public_mining_root", "Unknown"))),
        "Runtime assets:",
    ]

    for name, available in sorted((diagnostics.get("runtime_assets") or {}).items()):
        lines.append(f"  - {name}: {'available' if available else 'missing'}")

    lines.extend([
        "",
        "Privacy note: diagnostics include paths and runtime availability only.",
        "They do not include tokens, notes, lookup history, watchlists, OCR text, or database contents.",
    ])
    return "\n".join(lines)


def safe_diagnostics_text(database_path=None):
    return format_diagnostics(collect_diagnostics(database_path=database_path))
