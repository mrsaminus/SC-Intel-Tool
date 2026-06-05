from app.ship_metadata import SHIP_METADATA, ship_metadata_for

from .searchable_combo import configure_searchable_combo, set_combo_items


SHIP_NAMES = sorted(SHIP_METADATA)
SUPPORTED_BOX_SIZES = (32, 24, 16, 8, 4, 2, 1)


def configure_ship_combo(combo, ship_names=None):
    configure_searchable_combo(combo, "Select ship...")
    set_combo_items(combo, combined_ship_names(ship_names))
    return combo


def combined_ship_names(ship_names=None):
    names = set(SHIP_NAMES)
    for ship_name in ship_names or ():
        name = getattr(ship_name, "name", ship_name)
        if name:
            names.add(str(name))
    return sorted(names, key=lambda value: value.lower())


def update_ship_combo(combo, ship_names):
    set_combo_items(combo, combined_ship_names(ship_names))


def cargo_scu_for_ship(ship_name):
    metadata = ship_metadata_for(ship_name)
    if not metadata:
        return None
    return metadata.cargo_scu


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
