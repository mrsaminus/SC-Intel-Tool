from pathlib import Path

from app.diagnostics import format_diagnostics, packaged_runtime_alias, redact_path, runtime_asset_status


def test_diagnostics_redacts_user_paths(monkeypatch, tmp_path):
    user_root = tmp_path / "Users" / "Alpha Tester"
    local_appdata = user_root / "AppData" / "Local"
    monkeypatch.setenv("USERPROFILE", str(user_root))
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    diagnostics = {
        "app_version": "0.1.0-test",
        "runtime": "source",
        "python": "3.12.0",
        "platform": "Windows-test",
        "executable": str(user_root / "Project" / ".venv" / "Scripts" / "python.exe"),
        "data_dir": str(local_appdata / "SC-Intel-Tool"),
        "database_path": str(local_appdata / "SC-Intel-Tool" / "sc_intel.db"),
        "log_file": str(local_appdata / "SC-Intel-Tool" / "logs" / "sc_intel_tool.log"),
        "public_mining_root": str(user_root / "Project" / "app" / "assets" / "mining_public"),
        "runtime_assets": {"app_icon": True, "optional_asset": False},
    }

    text = format_diagnostics(diagnostics)

    assert "Alpha Tester" not in text
    assert "%LOCALAPPDATA%\\SC-Intel-Tool" in text
    assert "%USERPROFILE%\\Project" in text
    assert "App version         : 0.1.0-test" in text
    assert "Runtime assets:" in text
    assert "tokens" in text.lower()
    assert "lookup history" in text.lower()


def test_redact_path_leaves_unmatched_paths_readable():
    value = r"Z:\public\file.txt"

    assert redact_path(value) == value


def test_runtime_asset_status_reports_missing_assets_without_crashing(monkeypatch, tmp_path):
    import app.paths as paths

    monkeypatch.setattr(paths, "bundled_path", lambda *parts: Path(tmp_path, *parts))

    status = runtime_asset_status()

    assert status
    assert all(available is False for available in status.values())


def test_packaged_runtime_paths_use_readable_alias():
    value = r"C:\Users\tester\AppData\Local\Temp\_MEI635162\app\assets\mining_public"

    assert packaged_runtime_alias(value) == r"<packaged_runtime>\app\assets\mining_public"
    assert redact_path(value) == r"<packaged_runtime>\app\assets\mining_public"
