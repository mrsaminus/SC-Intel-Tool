import re
from types import SimpleNamespace

from app.updater import download_update, expected_sha256, safe_asset_name, update_script


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


def test_download_update_allows_missing_github_digest(monkeypatch, tmp_path):
    class Response:
        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield b"SC"
            yield b"IT"

    monkeypatch.setenv("SC_INTEL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("app.updater.requests.get", lambda *args, **kwargs: Response())

    update_info = SimpleNamespace(
        asset_url="https://example.test/SC-Intel-Tool.exe",
        asset_name="SC-Intel-Tool.exe",
        latest_version="0.1.0-alpha.8.8",
        asset_size=4,
        asset_digest="",
    )

    downloaded = download_update(update_info, timeout=1)

    assert downloaded.path.name == "SC-Intel-Tool.exe"
    assert downloaded.path.read_bytes() == b"SCIT"
    assert downloaded.size == 4
    assert len(downloaded.sha256) == 64
