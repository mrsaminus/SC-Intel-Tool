import os
from datetime import timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.blueprints_client import BlueprintRecord
from app.uex_client import UEXCommodityPrice
from conftest import isolated_database, reload_module


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def sample_price_rows():
    return [
        UEXCommodityPrice(
            commodity_name="Gold",
            price_buy=7500,
            price_sell=None,
            terminal_name="TDD",
            star_system_name="Stanton",
            location_name="Area18",
            date_modified=100,
        ),
        UEXCommodityPrice(
            commodity_name="Gold",
            price_buy=None,
            price_sell=8100,
            terminal_name="TDD",
            star_system_name="Stanton",
            location_name="Orison",
            date_modified=100,
        ),
    ]


def sample_blueprints():
    return [
        BlueprintRecord(
            key="bp-1",
            blueprint_name="Test Blueprint",
            crafted_item="Test Blueprint",
            category="Field Recon",
            ownable=True,
            craft_time_seconds=None,
            ingredients=(),
            missions=(),
            patch="4.2",
            source="SC Craft Tools",
            source_url="https://example.invalid/blueprints",
            raw={"blueprint_id": "bp-1"},
        )
    ]


def test_cache_manager_enumerates_supported_sources(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    manager = reload_module("app.cache_manager")

    sources = manager.enumerate_cache_sources()

    assert [source.name for source in sources] == ["Item Finder", "Wikelo", "UEX Trading", "BP Overview"]
    assert {source.status for source in sources} == {"Missing"}
    assert all(source.refresh_supported for source in sources)
    assert all(source.clear_supported for source in sources)


def test_cache_manager_reports_age_and_stale_status(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    manager = reload_module("app.cache_manager")
    now = cache.utc_now()
    cache.update_cache_metadata(
        cache.UEX_PRICES_CACHE_KEY,
        "UEX public market prices",
        "1",
        row_count=2,
        updated_at=now - timedelta(hours=7),
    )

    info = manager.cache_source_info(cache.UEX_PRICES_CACHE_KEY, now=now)

    assert info.status == "Stale"
    assert info.row_count == 2
    assert info.schema_version == "1"
    assert info.age == "7 hr ago"


def test_cache_manager_reports_offline_when_cached_source_errors(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    manager = reload_module("app.cache_manager")
    cache.update_cache_metadata(cache.UEX_PRICES_CACHE_KEY, "UEX public market prices", "1", row_count=2)
    cache.mark_cache_error(cache.UEX_PRICES_CACHE_KEY, "UEX public market prices", "1", "network down")

    info = manager.cache_source_info(cache.UEX_PRICES_CACHE_KEY)

    assert info.status == "Offline"
    assert info.error_message == "network down"
    assert info.row_count == 2


def test_cache_manager_refresh_updates_uex_metadata(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    uex_client = reload_module("app.uex_client")
    manager = reload_module("app.cache_manager")
    monkeypatch.setattr(uex_client, "fetch_all_commodity_prices", sample_price_rows)

    result = manager.refresh_cache_source(cache.UEX_PRICES_CACHE_KEY)
    info = manager.cache_source_info(cache.UEX_PRICES_CACHE_KEY)

    assert result.success
    assert "Cached 2 UEX price rows" in result.message
    assert info.status == "Fresh"
    assert info.row_count == 2


def test_cache_manager_refresh_updates_blueprint_metadata(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    blueprints_client = reload_module("app.blueprints_client")
    manager = reload_module("app.cache_manager")
    monkeypatch.setattr(blueprints_client, "fetch_blueprints", sample_blueprints)

    result = manager.refresh_cache_source(cache.BLUEPRINT_CACHE_KEY)
    info = manager.cache_source_info(cache.BLUEPRINT_CACHE_KEY)

    assert result.success
    assert "Cached 1 blueprint rows" in result.message
    assert info.status == "Fresh"
    assert info.row_count == 1


def test_cache_manager_refresh_all_runs_sources_sequentially(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    manager = reload_module("app.cache_manager")
    calls = []

    def record_refresh(cache_key):
        calls.append(cache_key)
        info = manager.cache_source_info(cache_key)
        return manager.CacheRefreshResult(cache_key, info.name, True, "ok", info)

    monkeypatch.setattr(manager, "refresh_cache_source", record_refresh)

    results = manager.refresh_all_cache_sources()

    assert calls == [source.key for source in manager.cache_source_definitions()]
    assert len(results) == len(manager.cache_source_definitions())


def test_cache_manager_clear_source_and_clear_all(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    manager = reload_module("app.cache_manager")
    cache.save_uex_prices_cache(sample_price_rows())
    cache.update_cache_metadata(cache.ITEM_FINDER_CACHE_KEY, "Cornerstone + SC Focus", "1", row_count=3)
    cache.update_cache_metadata(cache.WIKELO_CACHE_KEY, "Public Wikelo spreadsheet", "1", row_count=4)
    cache.save_blueprint_cache(sample_blueprints())

    manager.clear_cache_source(cache.UEX_PRICES_CACHE_KEY)
    rows, metadata = cache.load_uex_prices_cache()
    assert rows == []
    assert metadata is None

    manager.clear_all_cached_data()
    assert {source.status for source in manager.enumerate_cache_sources()} == {"Missing"}


def test_diagnostics_include_cache_sources(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    diagnostics = reload_module("app.diagnostics")
    cache.update_cache_metadata(cache.UEX_PRICES_CACHE_KEY, "UEX public market prices", "1", row_count=2)

    text = diagnostics.safe_diagnostics_text()

    assert "Cache sources:" in text
    assert "UEX Trading: Fresh; rows=2" in text
    assert "BP Overview: Missing; rows=0" in text
    assert "schema=1" in text


def test_settings_local_data_platform_section_displays_cache_sources(monkeypatch, tmp_path, qapp):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    settings_module = reload_module("app.gui.settings_tab")
    cache.update_cache_metadata(cache.UEX_PRICES_CACHE_KEY, "UEX public market prices", "1", row_count=2)

    settings = settings_module.SettingsTab()
    labels = [label.text() for label in settings.findChildren(settings_module.QLabel)]

    assert "LOCAL DATA PLATFORM" in labels
    assert "Item Finder" in labels
    assert "Wikelo" in labels
    assert "UEX Trading" in labels
    assert "BP Overview" in labels
    assert any("Rows Cached: 2" in label for label in labels)
    settings.close()
