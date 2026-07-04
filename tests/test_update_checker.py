from app.update_checker import (
    check_for_updates,
    find_windows_asset,
    is_newer_version,
    select_latest_release,
    version_key,
)


def test_prerelease_version_comparison_handles_alpha_dot_versions():
    assert is_newer_version("v0.1.0-alpha.8.1", "0.1.0-alpha.8")
    assert is_newer_version("0.1.0-alpha.9", "0.1.0-alpha.8.1")
    assert is_newer_version("0.1.0-alpha.10", "0.1.0-alpha.9")
    assert is_newer_version("0.1.0-alpha.8.9.10", "0.1.0-alpha.8.9.9")
    assert is_newer_version("0.1.0-alpha.8.10.0", "0.1.0-alpha.8.9.10")
    assert is_newer_version("0.1.0-beta.1", "0.1.0-alpha.10")
    assert is_newer_version("0.2.0-beta", "0.1.0-alpha.8.9.10")
    assert is_newer_version("0.1.0", "0.1.0-alpha.99")
    assert not is_newer_version("0.1.0-alpha.8.9.10", "0.1.0-alpha.8.9.10")


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


def test_select_latest_release_sorts_semver_instead_of_api_order():
    releases = [
        {"draft": False, "tag_name": "v0.1.0-alpha.8.9.9", "published_at": "2026-07-04T05:32:37Z"},
        {"draft": False, "tag_name": "v0.1.0-alpha.8.9.10", "published_at": "2026-07-04T10:00:17Z"},
        {"draft": False, "tag_name": "v0.1.0-alpha.8.9.8", "published_at": "2026-07-03T21:33:44Z"},
    ]

    assert select_latest_release(releases)["tag_name"] == "v0.1.0-alpha.8.9.10"


def test_select_latest_release_includes_github_prereleases_and_ignores_drafts():
    releases = [
        {"draft": True, "tag_name": "v9.9.9"},
        {"draft": False, "prerelease": True, "tag_name": "v0.2.0-beta"},
        {"draft": False, "prerelease": True, "tag_name": "v0.1.0-alpha.8.9.10"},
    ]

    assert select_latest_release(releases)["tag_name"] == "v0.2.0-beta"


def test_check_for_updates_accepts_release_assets_without_digest(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [
                {
                    "draft": False,
                    "tag_name": "v0.1.0-alpha.8.8",
                    "name": "SC Intel Tool v0.1.0-alpha.8.8",
                    "html_url": "https://example.test/releases/v0.1.0-alpha.8.8",
                    "published_at": "2026-06-14T00:00:00Z",
                    "assets": [
                        {
                            "name": "SC-Intel-Tool.exe",
                            "browser_download_url": "https://example.test/SC-Intel-Tool.exe",
                            "size": 123,
                        }
                    ],
                }
            ]

    monkeypatch.setattr("app.update_checker.requests.get", lambda *args, **kwargs: Response())
    monkeypatch.setattr("app.update_checker.APP_VERSION", "0.1.0-alpha.8.7")

    result = check_for_updates(timeout=1)

    assert result.update_available is True
    assert result.asset_name == "SC-Intel-Tool.exe"
    assert result.asset_digest == ""


def test_check_for_updates_sorts_release_list_before_comparison(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [
                {
                    "draft": False,
                    "tag_name": "v0.1.0-alpha.8.9.9",
                    "name": "SC Intel Tool v0.1.0-alpha.8.9.9",
                    "html_url": "https://example.test/releases/v0.1.0-alpha.8.9.9",
                    "published_at": "2026-07-04T05:32:37Z",
                    "assets": [{"name": "SC-Intel-Tool.exe", "browser_download_url": "https://example.test/old.exe"}],
                },
                {
                    "draft": False,
                    "tag_name": "v0.1.0-alpha.8.9.10",
                    "name": "SC Intel Tool v0.1.0-alpha.8.9.10",
                    "html_url": "https://example.test/releases/v0.1.0-alpha.8.9.10",
                    "published_at": "2026-07-04T10:00:17Z",
                    "assets": [{"name": "SC-Intel-Tool.exe", "browser_download_url": "https://example.test/new.exe"}],
                },
            ]

    monkeypatch.setattr("app.update_checker.requests.get", lambda *args, **kwargs: Response())
    monkeypatch.setattr("app.update_checker.APP_VERSION", "0.1.0-alpha.8.9.9")

    result = check_for_updates(timeout=1)

    assert result.latest_version == "v0.1.0-alpha.8.9.10"
    assert result.update_available is True
    assert result.asset_url == "https://example.test/new.exe"
