from conftest import isolated_database
import pytest
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
    app.closeAllWindows()
    app.processEvents()
    QThreadPool.globalInstance().waitForDone(1000)
    app.processEvents()


def test_watchlist_entry_snapshot_and_event_persist(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)

    from app.watchlists.storage import (
        add_watchlist_event,
        add_watchlist_snapshot,
        get_latest_snapshot,
        get_watchlist_entry,
        list_watchlist_events,
        upsert_watchlist_entry,
    )

    entry_id, created = upsert_watchlist_entry(
        "Player",
        "Saminus",
        "saminus",
        source="Player Lookup",
        metadata={"handle": "Saminus"},
    )

    assert created is True
    assert get_watchlist_entry(entry_id).name == "Saminus"

    add_watchlist_snapshot(entry_id, "Checked", {"org": "NOVA"}, "Smoke test")
    latest = get_latest_snapshot(entry_id)
    assert latest.status == "Checked"
    assert latest.value == {"org": "NOVA"}

    event_id = add_watchlist_event(entry_id, "changed", "Profile changed")
    events = list_watchlist_events(entry_id)
    assert events[0].id == event_id
    assert events[0].message == "Profile changed"


def test_watchlist_overview_summary_uses_local_cache_status(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)

    from app import local_cache
    from app.watchlists import service

    service.add_trading_commodity_watch("Gold", metadata={"commodity": "Gold"})
    service.add_item_watch("Test Armor", "Armor", source="Item Finder")
    service.add_blueprint_watch("Field Recon Helmet", metadata={"category": "Blueprints"})
    local_cache.update_cache_metadata(
        local_cache.UEX_PRICES_CACHE_KEY,
        "UEX public market prices",
        "1",
        row_count=3,
    )

    summary = service.watchlist_overview_summary()

    assert summary["active"] == 3
    assert summary["groups"]["Trading"] == 1
    assert summary["groups"]["Items"] == 1
    assert summary["groups"]["Blueprints"] == 1
    assert "UEX Trading" in summary["local_data"]["available"]


def test_watchlist_delete_records_activity_log(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)

    from app.event_center.storage import list_notification_events
    from app.watchlists import service
    from app.watchlists.storage import delete_watchlist_entry

    entry = service.add_trading_commodity_watch("Gold", metadata={"commodity": "Gold"})

    assert delete_watchlist_entry(entry.id) == 1
    events = list_notification_events(query="Removed watchlist entry", category="Watchlists")

    assert events
    assert events[0].entity_name == "Gold"
    assert events[0].event_type == "deleted"


def test_watchlists_tab_source_and_status_filters_smoke(monkeypatch, tmp_path, qapp):
    isolated_database(monkeypatch, tmp_path)

    from app.watchlists import service
    from conftest import reload_module

    service.add_trading_commodity_watch("Gold", metadata={"commodity": "Gold"})
    service.add_item_watch("Test Armor", "Armor", source="Item Finder")

    watchlists_module = reload_module("app.gui.watchlists_tab")
    tab = watchlists_module.WatchlistsTab()
    tab.ensure_initial_load()
    panel = tab.trading_panel

    source_index = panel.source_filter.findData("UEX")
    status_index = panel.status_filter.findData("tracked")
    panel.source_filter.setCurrentIndex(source_index)
    panel.status_filter.setCurrentIndex(status_index)
    qapp.processEvents()

    assert panel.table.rowCount() == 1
    assert panel.visible_entries[0].name == "Gold"
    assert "Showing 1 watch" in panel.summary_label.text()
    tab.close()
    tab.deleteLater()
    qapp.processEvents()
