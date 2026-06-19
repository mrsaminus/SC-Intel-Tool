from .shared import *
from .scan_id_helpers import (
    format_scan_match_summary,
    match_scan_values as match_scan_values_for_query,
    parse_scan_query,
    query_has_filters,
    scan_signature_matches,
)


class MiningScanIdMixin:
    def build_scan_identifier_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("SCAN SIGNATURE IDENTIFIER")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.scan_value_input = QLineEdit()
        self.scan_value_input.setPlaceholderText("Resource name, exact value, ~value, min-max, or comma-separated...")
        self.scan_category_filter = self.create_combo([
            "All categories",
            "Legendary",
            "Epic",
            "Rare",
            "Uncommon",
            "Common",
            "ROC Mineables",
            "FPS Mineables",
            "Salvage",
        ])
        row.addWidget(self.scan_value_input, 1)
        row.addWidget(self.scan_category_filter)
        filter_layout.addLayout(row)

        hint = QLabel("Examples: Gold | Bexalite | Gold, Taranite, Quantanium | 8600 | Gold, 5200")
        hint.setObjectName("moduleSubtitle")
        filter_layout.addWidget(hint)
        layout.addWidget(filter_card)

        self.scan_signature_table = self.create_table([
            "Resource",
            "Category",
            "Max",
            "Matches",
            "All Signatures",
        ])
        configure_readable_table_columns(self.scan_signature_table, stretch_last=True)
        layout.addWidget(self.scan_signature_table, 1)
        self.scan_empty_label = self.create_empty_state("No scan signatures match the current input.")
        layout.addWidget(self.scan_empty_label)
        widget.setLayout(layout)
        return widget


    def populate_scan_identifier(self):
        query = self.parse_scan_tokens(self.scan_value_input.text())
        category_filter = self.scan_category_filter.currentText()
        rows = []

        for signature in self.mining_data.scan_signatures:
            if category_filter != "All categories" and signature.category != category_filter:
                continue

            name_match, matches = scan_signature_matches(signature, query)
            if query_has_filters(query) and not name_match and not matches:
                continue

            rows.append([
                signature.resource,
                signature.category,
                f"{signature.max_multiplier}x",
                format_scan_match_summary(name_match, matches, self.format_signature_values),
                self.format_signature_values(signature.values),
            ])

        rows.sort(key=lambda row: (self.scan_category_rank(row[1]), row[0].lower()))
        self.set_table_rows(self.scan_signature_table, rows)
        self.scan_empty_label.setVisible(not rows)


    def parse_scan_tokens(self, text):
        return parse_scan_query(text, self.parse_int)


    def match_scan_values(self, values, tokens):
        if isinstance(tokens, dict):
            tokens = tokens.get("numeric_ranges", ())
        return match_scan_values_for_query(values, tokens)


    def scan_category_rank(self, category):
        order = {
            "Legendary": 0,
            "Epic": 1,
            "Rare": 2,
            "Uncommon": 3,
            "Common": 4,
            "ROC Mineables": 5,
            "FPS Mineables": 6,
            "Salvage": 7,
        }
        return order.get(category, 99)


    def format_signature_values(self, values):
        return " | ".join(f"{value:,}" for value in values)

