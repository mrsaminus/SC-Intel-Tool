import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from conftest import isolated_database, reload_module


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def tab_labels(tab_widget):
    return [tab_widget.tabText(index) for index in range(tab_widget.count())]


def fake_update_info():
    update_checker = reload_module("app.update_checker")
    return update_checker.UpdateInfo(
        current_version="0.1.0-alpha.test",
        latest_version="v0.1.0-alpha.test",
        release_name="SC Intel Tool test",
        release_url="https://example.invalid/release",
        published_at="",
        update_available=False,
        asset_name="SC-Intel-Tool.exe",
        asset_url="https://example.invalid/SC-Intel-Tool.exe",
    )


def fake_reference_data(reference_module):
    return reference_module.TradingReferenceData(
        commodities=(),
        commodity_types=(),
        locations=(),
        shops=(),
        ships=tuple(reference_module.trading_ship_names()),
        price_rows=(),
    )


def build_window(monkeypatch, tmp_path, deferred_calls=None, local_deferred_calls=None):
    isolated_database(monkeypatch, tmp_path)

    reference_module = reload_module("app.gui.trading.reference_data")
    reference_module._REFERENCE_SERVICE = None
    monkeypatch.setattr(
        reference_module,
        "load_trading_reference_data",
        lambda: fake_reference_data(reference_module),
    )
    if deferred_calls is not None:
        monkeypatch.setattr(
            reference_module.TradingReferenceService,
            "ensure_loaded",
            lambda self: deferred_calls.append("trading_reference"),
        )

    wikelo_module = reload_module("app.gui.wikelo_tab")
    monkeypatch.setattr(wikelo_module, "fetch_wikelo_items", lambda: [])
    if deferred_calls is not None:
        def record_wikelo_refresh(self, silent=False):
            self.initial_refresh_started = True
            deferred_calls.append(("wikelo", silent))

        monkeypatch.setattr(wikelo_module.WikeloItemsTab, "refresh_wikelo_items", record_wikelo_refresh)

    if local_deferred_calls is not None:
        history_module = reload_module("app.gui.search_history_tab")

        def record_history_refresh(self, selected_handle=None):
            self._initial_load_started = True
            self._initial_load_done = True
            local_deferred_calls.append("search_history")

        monkeypatch.setattr(history_module.SearchHistoryTab, "refresh_history", record_history_refresh)

        watchlists_module = reload_module("app.gui.watchlists_tab")

        def record_watchlists_reload(self):
            self._initial_load_started = True
            self._initial_load_done = True
            local_deferred_calls.append("watchlists")

        monkeypatch.setattr(watchlists_module.WatchlistsTab, "reload_all", record_watchlists_reload)

        event_center_module = reload_module("app.gui.event_center_tab")

        def record_activity_log_refresh(self):
            self._initial_load_started = True
            self._initial_load_done = True
            local_deferred_calls.append("activity_log")

        monkeypatch.setattr(event_center_module.EventCenterTab, "refresh_events", record_activity_log_refresh)

        mining_module = reload_module("app.gui.mining.mining_tab")
        mining_wrapper_module = reload_module("app.gui.mining_tab")

        def record_mining_population(self):
            self._initial_load_started = True
            self._initial_load_done = True
            local_deferred_calls.append("mining")

        monkeypatch.setattr(mining_module.MiningTab, "populate_mining_tables", record_mining_population)
        monkeypatch.setattr(mining_wrapper_module.MiningTab, "populate_mining_tables", record_mining_population)

    main_window_module = reload_module("app.gui.main_window")
    monkeypatch.setattr(main_window_module, "fetch_update_info", fake_update_info)
    return main_window_module.MainWindow()


def test_main_navigation_is_grouped_and_reachable(monkeypatch, tmp_path, qapp):
    window = build_window(monkeypatch, tmp_path)
    window.show()
    qapp.processEvents()

    assert tab_labels(window.tabs) == ["Home", "Intel", "Industrial", "Reference", "System"]
    assert tab_labels(window.intel_tabs) == ["Player Lookup", "Search History", "Watchlists"]
    assert tab_labels(window.industrial_tabs) == ["Mining / Salvage", "Trading", "BP Overview", "Hauling"]
    assert tab_labels(window.reference_tabs) == ["Item Finder", "Wikelo Items"]
    assert tab_labels(window.system_tabs) == ["Activity Log", "Notes", "Settings"]

    main_height = window.tabs.tabBar().tabRect(0).height()
    group_height = window.intel_tabs.tabBar().tabRect(0).height()
    module_height = window.trading_tab.tabs.tabBar().tabRect(0).height()
    assert window.tabs.tabBar().objectName() == "mainNavigationTabBar"
    assert window.intel_tabs.tabBar().objectName() == "groupNavigationTabBar"
    assert main_height >= 50
    assert group_height >= 36
    assert module_height < group_height < main_height

    routes = {
        "Player Lookup": ("Intel", window.intel_tabs, "Player Lookup"),
        "Search History": ("Intel", window.intel_tabs, "Search History"),
        "Watchlists": ("Intel", window.intel_tabs, "Watchlists"),
        "Mining / Salvage": ("Industrial", window.industrial_tabs, "Mining / Salvage"),
        "Trading": ("Industrial", window.industrial_tabs, "Trading"),
        "BP Overview": ("Industrial", window.industrial_tabs, "BP Overview"),
        "Hauling": ("Industrial", window.industrial_tabs, "Hauling"),
        "Item Finder": ("Reference", window.reference_tabs, "Item Finder"),
        "Wikelo Items": ("Reference", window.reference_tabs, "Wikelo Items"),
        "Activity Log": ("System", window.system_tabs, "Activity Log"),
        "Event Center": ("System", window.system_tabs, "Activity Log"),
        "Notes": ("System", window.system_tabs, "Notes"),
        "Settings": ("System", window.system_tabs, "Settings"),
    }
    for target, (top_label, child_tabs, child_label) in routes.items():
        window.open_tab(target)
        qapp.processEvents()
        assert window.tabs.tabText(window.tabs.currentIndex()) == top_label
        assert child_tabs.tabText(child_tabs.currentIndex()) == child_label

    assert tab_labels(window.trading_tab.tabs) == [
        "UEX Trading",
        "Saved Routes",
        "Create Routes",
        "Trade Routes",
        "Best Buyer",
        "En Route",
        "Commodities",
        "Shops",
    ]
    assert any(label.text() == "Activity Log" for label in window.event_center_tab.findChildren(QLabel))
    window.close()


def test_deferred_online_loads_run_on_first_module_show(monkeypatch, tmp_path, qapp):
    calls = []
    window = build_window(monkeypatch, tmp_path, deferred_calls=calls)
    window.show()
    qapp.processEvents()

    assert calls == []

    window.open_tab("Trading")
    qapp.processEvents()
    assert calls == ["trading_reference"]

    window.open_tab("Home")
    window.open_tab("Trading")
    qapp.processEvents()
    assert calls == ["trading_reference"]

    window.open_tab("Wikelo Items")
    qapp.processEvents()
    assert calls == ["trading_reference", ("wikelo", True)]

    window.open_tab("Home")
    window.open_tab("Wikelo Items")
    qapp.processEvents()
    assert calls == ["trading_reference", ("wikelo", True)]

    window.close()


def test_deferred_local_loads_run_once_on_first_module_show(monkeypatch, tmp_path, qapp):
    calls = []
    window = build_window(monkeypatch, tmp_path, local_deferred_calls=calls)
    window.show()
    qapp.processEvents()

    assert calls == []

    window.home_tab.open_target_tab("Search History")
    qapp.processEvents()
    assert calls == ["search_history"]

    window.open_tab("Home")
    window.home_tab.open_target_tab("Search History")
    qapp.processEvents()
    assert calls == ["search_history"]

    window.open_tab("Watchlists")
    qapp.processEvents()
    assert calls == ["search_history", "watchlists"]

    window.open_tab("Home")
    window.open_tab("Watchlists")
    qapp.processEvents()
    assert calls == ["search_history", "watchlists"]

    window.home_tab.open_target_tab("Mining / Salvage")
    qapp.processEvents()
    assert calls == ["search_history", "watchlists", "mining"]

    window.open_tab("Home")
    window.home_tab.open_target_tab("Mining / Salvage")
    qapp.processEvents()
    assert calls == ["search_history", "watchlists", "mining"]

    window.open_tab("Activity Log")
    qapp.processEvents()
    assert calls == ["search_history", "watchlists", "mining", "activity_log"]

    window.open_tab("Home")
    window.open_tab("Activity Log")
    qapp.processEvents()
    assert calls == ["search_history", "watchlists", "mining", "activity_log"]

    window.close()
