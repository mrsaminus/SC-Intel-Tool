import os

import pytest
from PySide6.QtWidgets import QApplication

from conftest import isolated_database, reload_module

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def build_tab(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    module = reload_module("app.gui.hauling_tab")
    return module.HaulingTab()


def sample_contract_text(quantity=32):
    return f"""
    Pick up: Checkmate
    Deliver to: Teasa Spaceport
    Commodity: Construction Materials
    Quantity: {quantity} SCU
    Reward: 12000 aUEC
    """


def test_hauling_tab_manual_parse_updates_manifest(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.ship_combo.setCurrentText("Railen")
    tab.contract_text.setPlainText(sample_contract_text())

    tab.parse_contracts()
    qapp.processEvents()

    assert len(tab.contracts) == 1
    assert tab.manifest.selected_ship == "Railen"
    assert tab.manifest.ship_capacity_scu == 640
    assert tab.manifest.total_scu == 32
    assert tab.manifest.remaining_scu == 608
    assert tab.contracts_table.rowCount() == 1
    assert tab.contracts_table.item(0, 0).text() == "Checkmate"
    assert tab.contracts_table.item(0, 1).text() == "Teasa Spaceport"
    assert "Parsed 1 contract candidate" in tab.status_label.text()
    tab.close()


def test_hauling_tab_ship_selection_recalculates_remaining_scu(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.contract_text.setPlainText(sample_contract_text(quantity=500))
    tab.parse_contracts()

    tab.ship_combo.setCurrentText("C2 Hercules")
    tab.on_ship_changed()
    qapp.processEvents()

    assert tab.manifest.ship_capacity_scu == 696
    assert tab.manifest.remaining_scu == 196

    tab.ship_combo.setCurrentText("Caterpillar")
    tab.on_ship_changed()
    qapp.processEvents()

    assert tab.manifest.ship_capacity_scu == 576
    assert tab.manifest.remaining_scu == 76
    tab.close()


def test_hauling_tab_over_capacity_warning(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.ship_combo.setCurrentText("Caterpillar")
    tab.contract_text.setPlainText(sample_contract_text(quantity=700))

    tab.parse_contracts()
    qapp.processEvents()

    assert tab.manifest.remaining_scu == -124
    assert "exceeds ship capacity" in tab.capacity_warning_label.text()
    assert "exceeds ship capacity" in tab.warnings_text.toPlainText()
    tab.close()


def test_hauling_tab_no_contracts_warning(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.contract_text.setPlainText("noise only")

    tab.parse_contracts()
    qapp.processEvents()

    assert tab.contracts == ()
    assert "No hauling contracts parsed" in tab.status_label.text()
    assert "No contracts parsed." in tab.warnings_text.toPlainText()
    tab.close()


def test_hauling_tab_grouped_views(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.ship_combo.setCurrentText("Railen")
    tab.contract_text.setPlainText(
        """
        Pick up: Checkmate
        Deliver to: Teasa Spaceport
        Commodity: Construction Materials
        Quantity: 32 SCU

        Pick up: Checkmate
        Deliver to: Lorville
        Commodity: Medical Supplies
        Quantity: 12 SCU
        """
    )

    tab.parse_contracts()
    qapp.processEvents()

    assert tab.pickup_table.rowCount() == 1
    assert tab.pickup_table.item(0, 0).text() == "Checkmate"
    assert tab.pickup_table.item(0, 1).text() == "44"
    assert tab.destination_table.rowCount() == 2
    assert tab.route_table.rowCount() == 2
    manifest_text = tab.manifest_text()
    assert "Construction Materials" in manifest_text
    assert "Medical Supplies" in manifest_text
    tab.close()
