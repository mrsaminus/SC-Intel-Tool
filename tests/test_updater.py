import re

from app.updater import expected_sha256, safe_asset_name, update_script


def test_safe_asset_name_uses_stable_executable_for_non_exe_assets():
    assert safe_asset_name("release.zip", "0.1.0-alpha.8.7") == "SC-Intel-Tool.exe"
    assert safe_asset_name("", "0.1.0-alpha.8.7") == "SC-Intel-Tool.exe"


def test_expected_sha256_only_accepts_github_sha256_digest_format():
    assert expected_sha256("sha256:ABCDEF") == "abcdef"
    assert expected_sha256("ABCDEF") == ""
    assert expected_sha256("") == ""


def test_update_script_uses_manual_restart_and_safe_path_interpolation():
    script = update_script()

    assert "Please start SC-Intel-Tool.exe manually." in script
    assert "Start-Process" not in script
    assert "${Path}:" in script
    assert not re.search(r"\$[A-Za-z_][A-Za-z0-9_]*:", script)
