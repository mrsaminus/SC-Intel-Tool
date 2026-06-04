from .shared import *


class MiningLocationsMixin:
    def build_locations_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("LOCATION FILTERS")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.location_system_filter = self.create_combo(["All systems", "Stanton", "Pyro", "Nyx", "Unknown"])
        self.location_search_input = QLineEdit()
        self.location_search_input.setPlaceholderText("Filter body/mineral...")
        self.location_focus_filter = self.create_combo(["All mining types", "Surface", "Asteroid", "General"])
        row.addWidget(self.location_system_filter)
        row.addWidget(self.location_search_input, 1)
        row.addWidget(self.location_focus_filter)
        filter_layout.addLayout(row)
        layout.addWidget(filter_card)

        self.location_table = self.create_table([
            "System",
            "Body / Area",
            "Deposit",
            "Minerals",
            "Count",
            "Notes",
        ])
        configure_readable_table_columns(self.location_table, stretch_last=True)
        layout.addWidget(self.location_table, 1)
        self.location_empty_label = self.create_empty_state("No locations match the current filters.")
        layout.addWidget(self.location_empty_label)
        widget.setLayout(layout)
        return widget


    def populate_location_results(self):
        query = self.location_search_input.text().strip().lower()
        system_filter = self.location_system_filter.currentText()
        deposit_filter = self.location_focus_filter.currentText()
        grouped = {}

        for location in self.mining_data.locations:
            if system_filter != "All systems" and location.system != system_filter:
                continue
            if deposit_filter != "All mining types" and location.deposit_type != deposit_filter:
                continue
            if query and query not in self.location_search_text(location):
                continue

            key = (location.system, location.body, location.deposit_type)
            group = grouped.setdefault(key, {"minerals": set(), "notes": set()})
            group["minerals"].add(location.mineral)
            if location.notes:
                group["notes"].add(location.notes)

        rows = []
        for (system, body, deposit_type), group in grouped.items():
            minerals = sorted(group["minerals"])
            rows.append([
                system,
                body,
                deposit_type,
                ", ".join(minerals),
                str(len(minerals)),
                ", ".join(sorted(group["notes"])),
            ])

        rows.sort(key=lambda row: (row[0], row[1].lower(), row[2]))
        self.set_table_rows(self.location_table, rows)
        self.location_empty_label.setVisible(not rows)


    def location_search_text(self, location):
        return " ".join((
            location.mineral,
            location.system,
            location.body,
            location.deposit_type,
            location.notes,
        )).lower()

