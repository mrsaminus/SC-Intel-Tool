from .shared import *


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
        self.scan_value_input.setPlaceholderText("Exact value, ~value for +/-10%, or min-max...")
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

        hint = QLabel("Examples: 8600 | ~5000 | 8000-9000 | comma-separated values")
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
        tokens = self.parse_scan_tokens(self.scan_value_input.text())
        category_filter = self.scan_category_filter.currentText()
        rows = []

        for signature in self.mining_data.scan_signatures:
            if category_filter != "All categories" and signature.category != category_filter:
                continue

            matches = self.match_scan_values(signature.values, tokens)
            if tokens and not matches:
                continue

            rows.append([
                signature.resource,
                signature.category,
                f"{signature.max_multiplier}x",
                self.format_signature_values(matches) if matches else "",
                self.format_signature_values(signature.values),
            ])

        rows.sort(key=lambda row: (self.scan_category_rank(row[1]), row[0].lower()))
        self.set_table_rows(self.scan_signature_table, rows)
        self.scan_empty_label.setVisible(not rows)


    def parse_scan_tokens(self, text):
        tokens = []
        for raw_token in text.split(","):
            token = raw_token.strip().replace(" ", "")
            if not token:
                continue

            if token.startswith("~"):
                center = self.parse_int(token[1:])
                if center is None:
                    continue
                tokens.append((int(center * 0.9), int(center * 1.1)))
                continue

            if "-" in token:
                left, right = token.split("-", 1)
                low = self.parse_int(left)
                high = self.parse_int(right)
                if low is None or high is None:
                    continue
                tokens.append((min(low, high), max(low, high)))
                continue

            value = self.parse_int(token)
            if value is not None:
                tokens.append((value, value))

        return tokens


    def match_scan_values(self, values, tokens):
        if not tokens:
            return []

        matches = []
        for value in values:
            for low, high in tokens:
                if low <= value <= high:
                    matches.append(value)
                    break

        return matches


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

