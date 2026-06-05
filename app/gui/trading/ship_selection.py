from app.trading_ship_cargo import (
    canonical_trading_ship_name,
    trading_ship_cargo_scu,
    trading_ship_names,
)

from .searchable_combo import configure_searchable_combo, set_combo_items


SHIP_NAMES = trading_ship_names()
SUPPORTED_BOX_SIZES = (32, 24, 16, 8, 4, 2, 1)


def configure_ship_combo(combo, ship_names=None):
    configure_searchable_combo(combo, "Select ship...")
    set_combo_items(combo, known_cargo_ship_names(ship_names))
    return combo


def known_cargo_ship_names(ship_names=None):
    return trading_ship_names(ship_names)


def update_ship_combo(combo, ship_names):
    set_combo_items(combo, known_cargo_ship_names(ship_names))


def cargo_scu_for_ship(ship_name):
    return trading_ship_cargo_scu(ship_name)


def selected_ship_name(combo):
    return canonical_trading_ship_name(combo.currentText().strip())


def fill_cargo_from_ship(ship_combo, cargo_input, status_label=None):
    ship_name = ship_combo.currentText().strip()
    cargo_scu = cargo_scu_for_ship(ship_name)
    if cargo_scu is None:
        if status_label:
            status_label.setText("Ship cargo capacity is unknown. Enter Cargo SCU manually.")
        return

    cargo_input.setText(str(cargo_scu))
    if status_label:
        status_label.setText(f"Cargo capacity loaded from local ship metadata: {cargo_scu:,} SCU.")


def supported_box_size_for_cargo(cargo_scu):
    try:
        cargo = float(cargo_scu)
    except (TypeError, ValueError):
        cargo = 1

    for size in SUPPORTED_BOX_SIZES:
        if cargo >= size:
            return size

    return 1
