from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.blueprints_storage import (
    delete_owned_crafting_material,
    list_owned_crafting_materials,
    normalized_material_key,
    set_owned_crafting_material,
)
from app.event_center.service import record_event

from .shared import ROW_ROLE, create_card, create_table, format_number, table_item


class CraftingMaterialsTab(QWidget):
    def __init__(self, materials_changed_callback=None):
        super().__init__()
        self.material_rows = []
        self.materials_changed_callback = materials_changed_callback

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        card = create_card("OWNED CRAFTING MATERIALS")
        card_layout = card.layout()

        help_text = QLabel(
            "Track material quantities locally. Blueprint details use these values to show craftability and missing materials."
        )
        help_text.setObjectName("moduleSubtitle")
        help_text.setWordWrap(True)
        card_layout.addWidget(help_text)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.material_input = QLineEdit()
        self.material_input.setPlaceholderText("Material name...")
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Quantity...")
        self.quantity_input.setValidator(QDoubleValidator(0, 999999999, 4, self))
        self.save_button = QPushButton("Save Material")
        self.delete_button = QPushButton("Delete Selected")
        self.refresh_button = QPushButton("Refresh")
        controls.addWidget(self.material_input, 2)
        controls.addWidget(self.quantity_input)
        controls.addWidget(self.save_button)
        controls.addWidget(self.delete_button)
        controls.addWidget(self.refresh_button)
        card_layout.addLayout(controls)

        self.status_label = QLabel("")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        card_layout.addWidget(self.status_label)

        self.material_table = create_table([
            "Material",
            "Quantity",
            "Updated",
        ])
        card_layout.addWidget(self.material_table, 1)

        self.empty_label = QLabel("No owned crafting materials tracked yet.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setWordWrap(True)
        card_layout.addWidget(self.empty_label)

        layout.addWidget(card, 1)
        self.setLayout(layout)

        self.save_button.clicked.connect(self.save_material)
        self.delete_button.clicked.connect(self.delete_selected_material)
        self.refresh_button.clicked.connect(self.refresh_materials)
        self.material_table.itemSelectionChanged.connect(self.populate_selected_material)
        self.refresh_materials()

    def refresh_materials(self, *_):
        self.material_rows = list_owned_crafting_materials()
        self.material_table.setSortingEnabled(False)
        self.material_table.setRowCount(len(self.material_rows))
        for row, material in enumerate(self.material_rows):
            values = [
                material.get("material_name") or material.get("material_key") or "",
                format_number(material.get("quantity")),
                material.get("updated_at") or "",
            ]
            sort_values = [
                values[0],
                float(material.get("quantity") or 0),
                values[2],
            ]
            for column, value in enumerate(values):
                item = table_item(value, sort_values[column])
                item.setData(ROW_ROLE, row)
                self.material_table.setItem(row, column, item)
        self.material_table.setSortingEnabled(True)
        self.empty_label.setVisible(not self.material_rows)
        self.status_label.setText(f"{len(self.material_rows)} owned material{'s' if len(self.material_rows) != 1 else ''} tracked locally.")

    def save_material(self):
        material_name = self.material_input.text().strip()
        quantity_text = self.quantity_input.text().strip().replace(",", ".")
        if not material_name:
            QMessageBox.warning(self, "Material Required", "Enter a material name first.")
            return
        try:
            quantity = float(quantity_text or 0)
        except ValueError:
            QMessageBox.warning(self, "Invalid Quantity", "Enter a valid material quantity.")
            return

        previous = {
            row["material_key"]: row
            for row in list_owned_crafting_materials()
        }.get(normalized_material_key(material_name))
        material_key = set_owned_crafting_material(material_name, quantity)
        record_event(
            category="Item",
            source="BP Overview",
            entity_name=material_name,
            event_type="crafting_material_quantity_changed",
            message=f"Crafting material quantity set: {material_name} = {format_number(quantity)}",
            metadata={
                "material_key": material_key,
                "previous_quantity": previous.get("quantity") if previous else None,
                "quantity": quantity,
            },
            severity="Info",
        )
        self.refresh_materials()
        self.notify_materials_changed()

    def delete_selected_material(self):
        material = self.selected_material()
        if not material:
            QMessageBox.information(self, "No Material Selected", "Select a material row first.")
            return
        delete_owned_crafting_material(material["material_key"])
        record_event(
            category="Item",
            source="BP Overview",
            entity_name=material.get("material_name") or material["material_key"],
            event_type="crafting_material_removed",
            message=f"Removed crafting material tracking: {material.get('material_name') or material['material_key']}",
            metadata={"material_key": material["material_key"]},
            severity="Info",
        )
        self.material_input.clear()
        self.quantity_input.clear()
        self.refresh_materials()
        self.notify_materials_changed()

    def selected_material(self):
        row = self.material_table.currentRow()
        if row < 0:
            return None
        item = self.material_table.item(row, 0)
        if not item:
            return None
        source_row = item.data(ROW_ROLE)
        if source_row is None or source_row >= len(self.material_rows):
            return None
        return self.material_rows[source_row]

    def populate_selected_material(self):
        material = self.selected_material()
        if not material:
            return
        self.material_input.setText(material.get("material_name") or "")
        self.quantity_input.setText(format_number(material.get("quantity")))

    def notify_materials_changed(self):
        if self.materials_changed_callback:
            self.materials_changed_callback()
