from .shared import *


class MiningHelpersMixin:
    def unique_options(self, values):
        options = []
        seen = set()
        for value in values:
            key = self.refinery_option_key(value)
            if not value or key in seen:
                continue
            seen.add(key)
            options.append(value)
        return options


    def create_debounce_timer(self, callback, interval=180):
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(interval)
        timer.timeout.connect(callback)
        return timer


    def schedule_ore_results_refresh(self):
        self.ore_filter_timer.start()


    def schedule_location_results_refresh(self):
        self.location_filter_timer.start()


    def schedule_scan_identifier_refresh(self):
        self.scan_filter_timer.start()


    def schedule_quality_bands_refresh(self):
        self.quality_filter_timer.start()


    def schedule_equipment_results_refresh(self):
        self.equipment_filter_timer.start()


    def schedule_rock_breaker_refresh(self):
        self.rock_filter_timer.start()


    def set_table_rows(self, table, rows, resize_columns=True):
        sorting_enabled = table.isSortingEnabled()
        table.setUpdatesEnabled(False)
        table.setSortingEnabled(False)
        try:
            table.setRowCount(len(rows))

            for row_index, row_values in enumerate(rows):
                for col_index, value in enumerate(row_values):
                    item = QTableWidgetItem(str(value))
                    table.setItem(row_index, col_index, item)

            if resize_columns:
                min_width = int(table.property("readable_min_width") or 90)
                max_width = int(table.property("readable_max_width") or 280)
                stretch_last = bool(table.property("readable_stretch_last"))
                configure_readable_table_columns(table, min_width, max_width, stretch_last)
        finally:
            table.setSortingEnabled(sorting_enabled)
            table.setUpdatesEnabled(True)


    def parse_int(self, value):
        cleaned = "".join(char for char in str(value) if char.isdigit())
        if not cleaned:
            return None

        try:
            return int(cleaned)
        except ValueError:
            return None


    def parse_float(self, value):
        text = str(value or "").strip().replace(" ", "")
        if not text:
            return 0.0

        if "," in text and "." not in text:
            parts = text.split(",")
            if len(parts[-1]) == 3 and all(part.isdigit() for part in parts):
                text = "".join(parts)
            else:
                text = text.replace(",", ".")
        else:
            text = text.replace(",", "")

        cleaned = "".join(char for char in text if char.isdigit() or char in ".-")
        if cleaned in ("", "-", ".", "-."):
            return 0.0

        try:
            return float(cleaned)
        except ValueError:
            return 0.0


    def format_price(self, value):
        if value in (None, "", 0):
            return "N/A"

        try:
            return f"{float(value):,.0f} aUEC"
        except (TypeError, ValueError):
            return str(value)


    def format_number(self, value):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)

        if abs(numeric - round(numeric)) < 0.001:
            return f"{numeric:,.0f}"

        return f"{numeric:,.2f}"


    def format_auec_amount(self, value):
        return f"{self.format_number(value)} aUEC"


    def create_filter_card(self, title):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)
        card.setLayout(layout)
        return card


    def create_combo(self, items):
        combo = QComboBox()
        combo.addItems(items)
        return combo


    def create_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSortingEnabled(True)
        configure_readable_table_columns(table)
        return table


    def create_empty_state(self, text):
        label = QLabel(text)
        label.setObjectName("emptyState")
        label.setAlignment(Qt.AlignCenter)
        return label

