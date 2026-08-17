import copy
import os
from dataclasses import dataclass

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.gui.mining.mining_tab import MiningTab


@dataclass(frozen=True)
class PriceRow:
    star_system_name: str
    location_name: str
    terminal_name: str
    price_sell: float


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def refinery(qapp):
    tab = MiningTab()
    tab.create_refinery_session()
    yield tab
    tab.refinery_timer.stop()
    tab.close()


def price(location, sell, terminal="TDD", system="Stanton"):
    return PriceRow(
        star_system_name=system,
        location_name=location,
        terminal_name=terminal,
        price_sell=sell,
    )


def set_material(tab, material, qty_cscu, yield_cscu=None):
    session = tab.refinery_session()
    session["materials"][material] = {
        "code": tab.refinery_material_code(material),
        "qty_cscu": qty_cscu,
        "yield_cscu": tab.calculate_refinery_yield(material, qty_cscu) if yield_cscu is None else yield_cscu,
    }
    return session["materials"][material]


def table_values(table, row):
    return [
        table.item(row, column).text()
        for column in range(table.columnCount())
        if table.item(row, column)
    ]


def material_row(tab, material):
    for row in range(tab.refinery_table.rowCount()):
        item = tab.refinery_table.item(row, 0)
        if item and item.data(0x0100) == material:
            return row
    raise AssertionError(f"Material row not found: {material}")


def edit_refinery_cell(tab, row, column, value):
    item = tab.refinery_table.item(row, column)
    assert item is not None
    tab.refinery_table.blockSignals(True)
    item.setText(str(value))
    tab.refinery_table.blockSignals(False)
    tab.on_refinery_item_changed(item)


def test_construction_salvage_ferron_matches_observed_in_game_quote(refinery):
    refinery.refinery_method_filter.setCurrentText("Ferron Exchange")

    observed_yield = refinery.calculate_refinery_yield("Construction Salvage", 171200)

    assert observed_yield == 25680
    assert observed_yield != 44512
    assert observed_yield / 171200 == pytest.approx(0.15)


@pytest.mark.parametrize(
    ("method", "coefficient"),
    [
        ("Cormack Method", 0.14),
        ("XCR Reaction", 0.14),
        ("Kazen Winnowing", 0.14),
        ("Thermonatic Deposition", 0.17),
        ("Gaskin Process", 0.17),
        ("Electrostarolysis", 0.17),
        ("Dinyx Solventation", 0.20),
        ("Dynix Solventation", 0.20),
        ("Pyrometric Chromalysis", 0.20),
        ("Ferron Exchange", 0.20),
    ],
)
def test_construction_pieces_refinery_coefficients(refinery, method, coefficient):
    if refinery.refinery_method_filter.findText(method) < 0:
        refinery.refinery_method_filter.addItem(method)
    refinery.refinery_method_filter.setCurrentText(method)

    assert refinery.calculate_refinery_yield("Construction Pieces", 10000) == round(10000 * coefficient)


def test_construction_pieces_fix_does_not_change_ore_yield(refinery):
    refinery.refinery_method_filter.setCurrentText("Cormack Method")

    assert refinery.calculate_refinery_yield("Gold", 10000) == round(10000 * 0.315)


def test_refinery_session_save_to_history_preserves_totals(refinery):
    session = refinery.refinery_session()
    session["name"] = "Alpha Run"
    session["station"] = "Any refinery"
    session["method"] = "Dinyx Solventation"
    session["fee"] = 750
    set_material(refinery, "Gold", qty_cscu=2000, yield_cscu=1000)
    set_material(refinery, "Laranite", qty_cscu=3000, yield_cscu=1500)
    refinery.uex_prices = {
        "gold": price("Area18", 1000),
        "laranite": price("Area18", 2000),
    }

    assert refinery.refinery_session_totals(session) == (5000, 2500, 40000.0, 39250.0)

    refinery.save_refinery_session_to_history()

    assert len(refinery.refinery_completed_sessions) == 1
    saved = refinery.refinery_completed_sessions[0]
    assert saved["name"] == "Alpha Run"
    assert saved["total_qty"] == 5000
    assert saved["total_yield"] == 2500
    assert saved["gross_value"] == 40000.0
    assert saved["net_value"] == 39250.0
    assert refinery.refinery_history_table.rowCount() == 1
    assert table_values(refinery.refinery_history_table, 0)[0] == "Alpha Run"


def test_refinery_session_serialization_recalculate_keeps_totals(refinery):
    session = refinery.refinery_session()
    session["method"] = refinery.refinery_method_filter.currentText()
    set_material(refinery, "Gold", qty_cscu=10000)
    set_material(refinery, "Laranite", qty_cscu=25000)
    refinery.uex_prices = {
        "gold": price("Area18", 500),
        "laranite": price("Area18", 750),
    }
    before = refinery.refinery_session_totals(session)

    restored = copy.deepcopy(session)
    refinery.refinery_sessions = {"restored": restored}
    refinery.current_refinery_session = "restored"
    refinery.recalculate_refinery_yields()

    assert refinery.refinery_session_totals(refinery.refinery_session()) == before


def test_refinery_sell_locations_single_material(refinery):
    session = refinery.refinery_session()
    set_material(refinery, "Gold", qty_cscu=1000, yield_cscu=1000)
    refinery.uex_price_lists = {
        "gold": [
            price("Area18", 1000),
            price("Orison", 900),
        ],
    }

    refinery.populate_refinery_sell_locations(session)

    assert refinery.refinery_sell_locations_table.rowCount() == 2
    labels = [table_values(refinery.refinery_sell_locations_table, row)[0] for row in range(2)]
    assert "Area18 / TDD" in labels
    assert "Orison / TDD" in labels


def test_refinery_sell_locations_require_common_locations(refinery):
    session = refinery.refinery_session()
    set_material(refinery, "Gold", qty_cscu=1000, yield_cscu=1000)
    set_material(refinery, "Laranite", qty_cscu=1000, yield_cscu=1000)
    refinery.uex_price_lists = {
        "gold": [price("Area18", 1000)],
        "laranite": [price("Orison", 2000)],
    }

    refinery.populate_refinery_sell_locations(session)

    assert refinery.refinery_sell_locations_table.rowCount() == 0
    assert refinery.refinery_sell_locations_empty_label.text() == (
        "No shared UEX sell locations can buy every selected material."
    )

    refinery.uex_price_lists["laranite"].append(price("Area18", 1500))
    refinery.populate_refinery_sell_locations(session)

    assert refinery.refinery_sell_locations_table.rowCount() == 1
    row = table_values(refinery.refinery_sell_locations_table, 0)
    assert row[0] == "Area18 / TDD"
    assert "Gold" in row[2]
    assert "Laranite" in row[2]


def test_refinery_sell_locations_sort_multiple_common_locations_by_combined_value(refinery):
    session = refinery.refinery_session()
    set_material(refinery, "Gold", qty_cscu=1000, yield_cscu=1000)
    set_material(refinery, "Laranite", qty_cscu=2000, yield_cscu=2000)
    refinery.uex_price_lists = {
        "gold": [
            price("Area18", 1000),
            price("Orison", 900),
        ],
        "laranite": [
            price("Area18", 2000),
            price("Orison", 3000),
        ],
    }

    refinery.populate_refinery_sell_locations(session)

    assert refinery.refinery_sell_locations_table.rowCount() == 2
    first = table_values(refinery.refinery_sell_locations_table, 0)
    second = table_values(refinery.refinery_sell_locations_table, 1)
    assert first[0] == "Orison / TDD"
    assert first[1] == "69,000 aUEC"
    assert second[0] == "Area18 / TDD"
    assert second[1] == "50,000 aUEC"


def test_refinery_sell_prices_dedupe_to_best_location_price(refinery):
    prices = [
        price("Area18", 800),
        price("Area18", 1100),
        price("Orison", 900),
    ]

    deduped = refinery.deduped_refinery_sell_prices(prices)

    assert len(deduped) == 2
    assert deduped[0].location_name == "Area18"
    assert deduped[0].price_sell == 1100


def test_refinery_qty_and_yield_editing_handles_cscu_scu_zero_and_large_values(refinery):
    refinery.add_refinery_material("Gold")
    row = material_row(refinery, "Gold")
    session = refinery.refinery_session()

    edit_refinery_cell(refinery, row, 1, "1000")
    assert session["materials"]["Gold"]["qty_cscu"] == 1000
    assert session["materials"]["Gold"]["yield_cscu"] >= 0

    edit_refinery_cell(refinery, row, 2, "12.5")
    assert session["materials"]["Gold"]["qty_cscu"] == 1250

    edit_refinery_cell(refinery, row, 1, "0")
    assert session["materials"]["Gold"]["qty_cscu"] == 0
    assert session["materials"]["Gold"]["yield_cscu"] == 0

    edit_refinery_cell(refinery, row, 1, "1000000")
    assert session["materials"]["Gold"]["qty_cscu"] == 1000000
    assert session["materials"]["Gold"]["yield_cscu"] >= 0

    edit_refinery_cell(refinery, row, 4, "3.25")
    assert session["materials"]["Gold"]["yield_cscu"] == 325
    assert session["materials"]["Gold"]["yield_manual"] is True


def test_refinery_value_totals_handle_missing_partial_prices_and_fees(refinery):
    session = refinery.refinery_session()
    set_material(refinery, "Gold", qty_cscu=1000, yield_cscu=1000)
    set_material(refinery, "Laranite", qty_cscu=2000, yield_cscu=2000)
    set_material(refinery, "Janalite", qty_cscu=300, yield_cscu=0)
    refinery.uex_prices = {
        "gold": price("Area18", 1000),
        "janalite": price("Area18", 10000),
    }

    session["fee"] = 0
    assert refinery.refinery_session_totals(session) == (3300, 3000, 40000.0, 40000.0)

    session["fee"] = 5000
    assert refinery.refinery_session_totals(session) == (3300, 3000, 40000.0, 35000.0)

    session["fee"] = 50000
    assert refinery.refinery_session_totals(session) == (3300, 3000, 40000.0, -10000.0)
