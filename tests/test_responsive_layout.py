import importlib
import os
from pathlib import Path

import pytest
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication, QBoxLayout, QScrollArea, QWidget

from conftest import isolated_database

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
    app.closeAllWindows()
    app.processEvents()
    QThreadPool.globalInstance().waitForDone(1000)
    app.processEvents()


def process_layout(widget, qapp, width=900, height=600):
    widget.resize(width, height)
    widget.show()
    qapp.processEvents()
    widget.layout().activate()
    qapp.processEvents()


def test_responsive_stack_switches_before_children_are_cramped(qapp):
    responsive = importlib.import_module("app.gui.responsive")
    stack = responsive.ResponsiveStack(breakpoint_width=980)
    stack.addWidget(responsive.QFrame(), 1)
    stack.addWidget(responsive.QFrame(), 1)

    process_layout(stack, qapp, width=1300, height=300)
    assert stack.direction() == QBoxLayout.LeftToRight

    process_layout(stack, qapp, width=900, height=300)
    assert stack.direction() == QBoxLayout.TopToBottom
    stack.close()


def test_install_scroll_area_wraps_module_content(qapp):
    responsive = importlib.import_module("app.gui.responsive")
    parent = QWidget()
    content = QWidget()

    scroll_area = responsive.install_scroll_area(parent, content)
    process_layout(parent, qapp, width=900, height=600)

    assert isinstance(scroll_area, QScrollArea)
    assert scroll_area.widget() is content
    assert scroll_area.widgetResizable()
    parent.close()


def test_hauling_uses_scroll_and_contextual_cargo_actions(monkeypatch, tmp_path, qapp):
    isolated_database(monkeypatch, tmp_path)
    hauling_module = importlib.import_module("app.gui.hauling_tab")
    tab = hauling_module.HaulingTab()

    process_layout(tab, qapp, width=900, height=600)
    assert isinstance(tab.hauling_scroll_area, QScrollArea)
    assert tab.intake_stack.direction() == QBoxLayout.TopToBottom
    assert tab.toggle_loaded_button.text() == "Load Cargo"
    assert tab.toggle_delivered_button.text() == "Mark Delivered"
    assert not tab.toggle_loaded_button.isEnabled()
    assert not tab.toggle_delivered_button.isEnabled()

    tab.contract_text.setPlainText(
        """
        Pick up: Checkmate
        Deliver to: Teasa Spaceport
        Commodity: Construction Materials
        Quantity: 32 SCU
        """
    )
    tab.parse_contracts()
    qapp.processEvents()
    tab.contracts_table.setCurrentCell(0, 0)
    qapp.processEvents()

    assert tab.toggle_loaded_button.text() == "Load Cargo"
    assert tab.toggle_delivered_button.text() == "Mark Delivered"
    assert tab.toggle_loaded_button.isEnabled()
    assert tab.toggle_delivered_button.isEnabled()

    tab.toggle_selected_loaded()
    qapp.processEvents()
    assert tab.toggle_loaded_button.text() == "Unload Cargo"
    assert tab.toggle_delivered_button.text() == "Mark Delivered"

    tab.toggle_selected_delivered()
    qapp.processEvents()
    assert tab.toggle_loaded_button.text() == "Cargo Delivered"
    assert not tab.toggle_loaded_button.isEnabled()
    assert tab.toggle_delivered_button.text() == "Undo Delivered"
    assert tab.toggle_delivered_button.isEnabled()
    tab.close()


@pytest.mark.parametrize(
    ("relative_path", "scroll_attr"),
    [
        ("app/gui/notes_tab.py", "notes_scroll_area"),
        ("app/gui/watchlists_tab.py", "watchlists_scroll_area"),
        ("app/gui/event_center_tab.py", "event_center_scroll_area"),
        ("app/gui/hauling_tab.py", "hauling_scroll_area"),
        ("app/gui/item_finder/item_finder_tab.py", "item_finder_scroll_area"),
        ("app/gui/wikelo_tab.py", "wikelo_scroll_area"),
        ("app/gui/bp_overview/blueprint_browser_tab.py", "blueprint_browser_scroll_area"),
        ("app/gui/bp_overview/reward_scanner_tab.py", "reward_scanner_scroll_area"),
    ],
)
def test_major_module_sources_define_scroll_containment(relative_path, scroll_attr):
    source = Path(relative_path).read_text(encoding="utf-8")
    assert "install_scroll_area" in source
    assert scroll_attr in source


@pytest.mark.parametrize(
    ("relative_path", "scroll_attr"),
    [
        ("app/gui/trading/uex_trading_tab.py", "uex_scroll_area"),
        ("app/gui/trading/saved_routes_tab.py", "saved_routes_scroll_area"),
        ("app/gui/trading/create_routes_tab.py", "create_routes_scroll_area"),
        ("app/gui/trading/trade_routes_tab.py", "trade_routes_scroll_area"),
        ("app/gui/trading/best_buyer_tab.py", "best_buyer_scroll_area"),
        ("app/gui/trading/en_route_tab.py", "en_route_scroll_area"),
        ("app/gui/trading/commodities_tab.py", "commodities_scroll_area"),
        ("app/gui/trading/shops_tab.py", "shops_scroll_area"),
    ],
)
def test_trading_subtab_sources_define_scroll_containment(relative_path, scroll_attr):
    source = Path(relative_path).read_text(encoding="utf-8")
    assert "install_scroll_area" in source
    assert scroll_attr in source
