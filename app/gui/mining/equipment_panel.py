from .shared import *


class MiningEquipmentMixin:
    def build_equipment_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("EQUIPMENT FILTERS")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.equipment_search_input = QLineEdit()
        self.equipment_search_input.setPlaceholderText("Search equipment...")
        self.equipment_type_filter = self.create_combo(["All equipment", "Laser", "Module", "Gadget", "Salvage"])
        self.equipment_size_filter = self.create_combo(["Any size", "FPS", "S0", "S1", "S2", "S3", "N/A"])
        row.addWidget(self.equipment_search_input, 1)
        row.addWidget(self.equipment_type_filter)
        row.addWidget(self.equipment_size_filter)
        filter_layout.addLayout(row)
        layout.addWidget(filter_card)

        self.equipment_table = self.create_table([
            "Item",
            "Type",
            "Size",
            "Price",
            "Shops",
            "Best Shop",
            "Best Location",
            "Effect",
            "Notes",
        ])
        configure_readable_table_columns(self.equipment_table, min_width=100, max_width=340, stretch_last=True)
        layout.addWidget(self.equipment_table, 1)
        self.equipment_empty_label = self.create_empty_state("No equipment matches the current filters.")
        layout.addWidget(self.equipment_empty_label)
        widget.setLayout(layout)
        return widget


    def populate_equipment_results(self):
        query = self.equipment_search_input.text().strip().lower()
        type_filter = self.equipment_type_filter.currentText()
        size_filter = self.equipment_size_filter.currentText()
        rows = []

        for item in self.mining_data.equipment:
            if type_filter != "All equipment" and item.equipment_type != type_filter:
                continue
            if size_filter != "Any size" and item.size != size_filter:
                continue
            searchable = " ".join((
                item.name,
                item.equipment_type,
                item.size,
                str(item.shop_count),
                item.best_shop,
                item.best_location,
                item.effect,
                item.notes,
            )).lower()
            if query and query not in searchable:
                continue

            rows.append([
                item.name,
                item.equipment_type,
                item.size,
                self.format_price(item.price),
                f"{item.shop_count} locations" if item.shop_count else "No known shops",
                item.best_shop,
                item.best_location,
                item.effect,
                item.notes,
            ])

        rows.sort(key=lambda row: (row[1], row[2], row[0].lower()))
        self.set_table_rows(self.equipment_table, rows)
        self.equipment_empty_label.setVisible(not rows)

