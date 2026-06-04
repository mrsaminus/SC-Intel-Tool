from .shared import *


class MiningQualityBandsMixin:
    def build_quality_bands_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("RESOURCE QUALITY BANDS")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.quality_search_input = QLineEdit()
        self.quality_search_input.setPlaceholderText("Filter resource...")
        self.quality_score_input = QLineEdit()
        self.quality_score_input.setPlaceholderText("Quality score...")
        row.addWidget(self.quality_search_input, 1)
        row.addWidget(self.quality_score_input)
        filter_layout.addLayout(row)

        hint = QLabel("Quality score columns show the mapped resource value for each score band.")
        hint.setObjectName("moduleSubtitle")
        filter_layout.addWidget(hint)
        layout.addWidget(filter_card)

        self.quality_bands_table = self.create_table([
            "Resource",
            "Matched Band",
            *self.mining_data.quality_band_labels,
        ])
        layout.addWidget(self.quality_bands_table, 1)
        self.quality_empty_label = self.create_empty_state("No quality bands match the current filters.")
        layout.addWidget(self.quality_empty_label)
        widget.setLayout(layout)
        return widget


    def populate_quality_bands(self):
        query = self.quality_search_input.text().strip().lower()
        score = self.parse_int(self.quality_score_input.text())
        rows = []

        for row in self.mining_data.quality_bands:
            if query and query not in row.resource.lower():
                continue

            matched_band = self.quality_match_text(row, score)
            rows.append([
                row.resource,
                matched_band,
                *[
                    self.format_quality_value(value)
                    for value in row.values
                ],
            ])

        rows.sort(key=lambda values: values[0].lower())
        self.set_table_rows(self.quality_bands_table, rows)
        self.quality_empty_label.setVisible(not rows)


    def quality_match_text(self, row, score):
        if score is None:
            return ""

        for label, value in zip(self.mining_data.quality_band_labels, row.values):
            bounds = label.rstrip("Q").split("-", 1)
            if len(bounds) != 2:
                continue
            low = self.parse_int(bounds[0])
            high = self.parse_int(bounds[1])
            if low is None or high is None:
                continue
            if low <= score <= high:
                return f"{label}: {self.format_quality_value(value)}"

        return "Out of range"


    def format_quality_value(self, value):
        if value is None:
            return "-"

        return str(value)

