import os
from datetime import timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.cstone_client import CStoneItem
from app.scfocus_client import SCFocusShipItem, SCFocusShipLocation
from app.wikelo_client import WikeloItem, WikeloRequirement
from conftest import isolated_database, reload_module


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def sample_cstone_item():
    return CStoneItem(
        item_id="cstone-1",
        name="Test Armor",
        category="Armor - Helmets",
        size="S1",
        sold=True,
        detail_url="https://example.invalid/item",
        category_url="https://example.invalid/category",
        effect="Test protection",
        item_type="Helmet",
        availability="Pending",
    )


def sample_ship_item():
    return SCFocusShipItem(
        item_id="ships for sale:test ship",
        name="Test Ship",
        category="Ships for Sale",
        size="Ship",
        sold=True,
        detail_url="https://example.invalid/ships",
        category_url="https://example.invalid/ships",
        effect="Lowest 1,000 aUEC | 1 location",
        source="SC Focus",
        item_type="Ship",
        availability="1 location",
        locations=(
            SCFocusShipLocation(
                location="Area18",
                price="1,000 aUEC",
                verified="2026-06-22",
                url="https://example.invalid/area18",
            ),
        ),
    )


def sample_wikelo_item():
    return WikeloItem(
        item_id="ships-test-mission-test-reward",
        item_name="Test Reward",
        category="Ship",
        item_type="Reward",
        reward_method="Trade-in",
        mission_name="Test Mission",
        requirements=(
            WikeloRequirement(name="Wikelo Favor", quantity="15x", source="Mission"),
            WikeloRequirement(name="Comp-Board", quantity="4x", source="Salvage"),
        ),
        reward_item="Test Reward",
        location="Stanton",
        source_sheet="Ships 4.7",
        source_url="https://example.invalid/wikelo",
        notes="Test notes",
        updated="4.7",
        retired=False,
    )


def test_cache_metadata_tracks_fresh_and_stale_state(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")

    cache.update_cache_metadata(
        "unit.test",
        "Unit Test",
        "1",
        row_count=2,
        updated_at=cache.utc_now() - timedelta(hours=1),
    )

    metadata = cache.get_cache_metadata("unit.test")
    assert metadata is not None
    assert metadata.row_count == 2
    assert cache.cache_exists("unit.test")
    assert cache.cache_is_fresh("unit.test")
    assert cache.cache_status("unit.test") == "fresh"

    cache.update_cache_metadata(
        "unit.test",
        "Unit Test",
        "1",
        row_count=2,
        updated_at=cache.utc_now() - timedelta(hours=7),
    )

    assert not cache.cache_is_fresh("unit.test")
    assert cache.cache_status("unit.test") == "stale"


def test_cache_metadata_error_and_invalidation(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")

    assert cache.cache_status("missing.test") == "missing"

    cache.update_cache_metadata("unit.test", "Unit Test", "1", row_count=3)
    cache.mark_cache_error("unit.test", "Unit Test", "1", "network unavailable")

    metadata = cache.get_cache_metadata("unit.test")
    assert metadata.status == "error"
    assert metadata.error_message == "network unavailable"
    assert cache.cache_status("unit.test") == "error"

    cache.invalidate_cache("unit.test")
    assert cache.cache_status("unit.test") == "stale"


def test_item_finder_cache_round_trip(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")

    cache.save_item_finder_cache(
        [sample_cstone_item(), sample_ship_item()],
        ["Area18", "Orison"],
        warnings=["partial source warning"],
    )
    items, locations, metadata = cache.load_item_finder_cache()

    assert metadata.row_count == 2
    assert metadata.status == "ready"
    assert metadata.error_message == "partial source warning"
    assert locations == ["Area18", "Orison"]
    assert [item.name for item in items] == ["Test Armor", "Test Ship"]
    assert items[0].source == "Cornerstone"
    assert items[1].source == "SC Focus"
    assert items[1].locations[0].location == "Area18"


def test_item_finder_uses_cache_before_live_refresh(monkeypatch, tmp_path, qapp):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    cache.save_item_finder_cache([sample_cstone_item()], ["Area18"])

    item_finder_module = reload_module("app.gui.item_finder.item_finder_tab")
    tab = item_finder_module.ItemFinderTab()
    tab.auto_availability_limit = 0
    refresh_calls = []
    monkeypatch.setattr(tab, "refresh_finder_items", lambda *args, **kwargs: refresh_calls.append(args))

    tab.item_search_input.setText("test")
    tab.ensure_finder_data_then_search()
    qapp.processEvents()

    assert refresh_calls == []
    assert len(tab.finder_items) == 1
    assert tab.finder_items[0].name == "Test Armor"
    assert tab.cstone_location_names == ["Area18"]
    tab.close()


def test_wikelo_cache_round_trip(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")

    cache.save_wikelo_cache([sample_wikelo_item()])
    items, metadata = cache.load_wikelo_cache()

    assert metadata.row_count == 1
    assert metadata.status == "ready"
    assert len(items) == 1
    assert items[0].item_name == "Test Reward"
    assert [requirement.name for requirement in items[0].requirements] == ["Wikelo Favor", "Comp-Board"]


def test_wikelo_uses_cache_before_live_refresh(monkeypatch, tmp_path, qapp):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    cache.save_wikelo_cache([sample_wikelo_item()])

    wikelo_module = reload_module("app.gui.wikelo_tab")
    refresh_calls = []

    def record_refresh(self, silent=False):
        refresh_calls.append(silent)

    monkeypatch.setattr(wikelo_module.WikeloItemsTab, "refresh_wikelo_items", record_refresh)
    tab = wikelo_module.WikeloItemsTab()

    tab.ensure_initial_load()
    qapp.processEvents()

    assert refresh_calls == []
    assert len(tab.wikelo_items) == 1
    assert tab.wikelo_items[0].item_name == "Test Reward"
    assert "cached" in tab.wikelo_status_label.text().lower()
    tab.close()
