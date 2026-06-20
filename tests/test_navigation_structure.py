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


def build_window(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)

    reference_module = reload_module("app.gui.trading.reference_data")
    reference_module._REFERENCE_SERVICE = None
    monkeypatch.setattr(
        reference_module,
        "load_trading_reference_data",
        lambda: fake_reference_data(reference_module),
    )

    wikelo_module = reload_module("app.gui.wikelo_tab")
    monkeypatch.setattr(wikelo_module, "fetch_wikelo_items", lambda: [])

    main_window_module = reload_module("app.gui.main_window")
    monkeypatch.setattr(main_window_module, "fetch_update_info", fake_update_info)
    return main_window_module.MainWindow()


def test_main_navigation_is_grouped_and_reachable(monkeypatch, tmp_path, qapp):
    window = build_window(monkeypatch, tmp_path)
    window.show()
    qapp.processEvents()

    assert tab_labels(window.tabs) == ["Home", "Intel", "Industrial", "Reference", "System"]
    assert tab_labels(window.intel_tabs) == ["Player Lookup", "Search History", "Watchlists"]
    assert tab_labels(window.industrial_tabs) == ["Mining / Salvage", "Trading", "BP Overview"]
    assert tab_labels(window.reference_tabs) == ["Item Finder", "Wikelo Items"]
    assert tab_labels(window.system_tabs) == ["Activity Log", "Notes", "Settings"]

    routes = {
        "Player Lookup": ("Intel", window.intel_tabs, "Player Lookup"),
        "Search History": ("Intel", window.intel_tabs, "Search History"),
        "Watchlists": ("Intel", window.intel_tabs, "Watchlists"),
        "Mining / Salvage": ("Industrial", window.industrial_tabs, "Mining / Salvage"),
        "Trading": ("Industrial", window.industrial_tabs, "Trading"),
        "BP Overview": ("Industrial", window.industrial_tabs, "BP Overview"),
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
