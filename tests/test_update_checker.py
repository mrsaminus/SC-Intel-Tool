from app.update_checker import find_windows_asset, is_newer_version, version_key


def test_prerelease_version_comparison_handles_alpha_dot_versions():
    assert is_newer_version("v0.1.0-alpha.8.1", "0.1.0-alpha.8")
    assert is_newer_version("0.1.0-alpha.9", "0.1.0-alpha.8.1")
    assert is_newer_version("0.1.0-alpha.10", "0.1.0-alpha.9")
    assert is_newer_version("0.1.0-beta.1", "0.1.0-alpha.10")
    assert is_newer_version("0.1.0", "0.1.0-alpha.99")


def test_version_key_strips_optional_v_prefix():
    assert version_key("v0.1.0-alpha.8.2") == version_key("0.1.0-alpha.8.2")


def test_find_windows_asset_prefers_stable_executable_name():
    release = {
        "assets": [
            {"name": "SC-Intel-Tool-0.1.0-alpha.8-windows.exe"},
            {"name": "SC-Intel-Tool.exe"},
        ]
    }

    assert find_windows_asset(release)["name"] == "SC-Intel-Tool.exe"


def test_find_windows_asset_keeps_legacy_windows_fallback():
    release = {
        "assets": [
            {"name": "notes.txt"},
            {"name": "SC-Intel-Tool-0.1.0-alpha.7-windows.exe"},
        ]
    }

    assert find_windows_asset(release)["name"].endswith("-windows.exe")
