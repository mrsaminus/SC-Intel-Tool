from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app.trading_data import format_trade_age, is_suspicious_margin
from app.trading_en_route import (
    build_uex_en_route_opportunities,
    commodity_display_values,
    fetch_all_commodity_prices,
    location_display_values,
)
from app.trading_storage import (
    TradingRouteRecord,
    add_recent_trading_route,
    save_trading_route,
)

from ..sortable_table_item import ROW_ROLE, SORT_ROLE, SortableTableWidgetItem
from ..table_utils import configure_readable_table_columns
from ..workers import BackgroundTaskMixin
from .route_quality import calculate_route_quality, copy_to_clipboard
from .route_summary import format_route_summary, is_complete_route_record, notes_from_flags
from .searchable_combo import configure_searchable_combo, selected_combo_text, set_combo_items
from .ship_selection import configure_ship_combo, fill_cargo_from_ship


class EnRouteTab(BackgroundTaskMixin, QWidget):
    def __init__(self, reference_service=None):
        super().__init__()

        self.reference_service = reference_service
        self.uex_refresh_running = False
        self.route_calculation_running = False
        self.route_request_id = 0
        self.price_rows = []
        self.routes = []
        self.last_result = None

        self.build_ui()
        self.connect_signals()
        self.populate_routes_table()
        self.update_details()

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_header())
        layout.addWidget(self.create_controls())
        layout.addWidget(self.create_results_table(), 1)

        self.empty_label = QLabel("Refresh UEX Data to load public prices, then choose origin and destination.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        self.detail_label = QLabel("Select an En Route opportunity to see details.")
        self.detail_label.setObjectName("valueText")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

        self.copy_summary_button = QPushButton("Copy Route Summary")
        self.copy_summary_button.setEnabled(False)
        self.save_route_button = QPushButton("Save Route")
        self.save_route_button.setEnabled(False)
        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        button_row.addWidget(self.copy_summary_button)
        button_row.addWidget(self.save_route_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.setLayout(layout)

    def create_header(self):
        header = QFrame()
        header.setObjectName("playerCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title = QLabel("En Route")
        title.setObjectName("moduleHeading")
        subtitle = QLabel(
            "Point-to-point trade opportunities using public UEX prices. "
            "Results depend on the latest refreshed market data."
        )
        subtitle.setObjectName("moduleSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        header.setLayout(layout)
        return header

    def create_controls(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        title = QLabel("EN ROUTE LITE")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        first_row = QHBoxLayout()
        first_row.setSpacing(8)
        self.origin_combo = QComboBox()
        configure_searchable_combo(self.origin_combo, "Origin / buy location...")
        self.destination_combo = QComboBox()
        configure_searchable_combo(self.destination_combo, "Destination / sell location...")
        self.commodity_combo = QComboBox()
        configure_searchable_combo(self.commodity_combo, "Commodity optional...")
        first_row.addWidget(self.origin_combo, 1)
        first_row.addWidget(self.destination_combo, 1)
        first_row.addWidget(self.commodity_combo, 1)
        layout.addLayout(first_row)

        second_row = QHBoxLayout()
        second_row.setSpacing(8)
        self.ship_combo = QComboBox()
        configure_ship_combo(self.ship_combo)
        self.ship_combo.setMaximumWidth(200)
        self.cargo_input = QLineEdit("1")
        self.cargo_input.setPlaceholderText("Cargo SCU")
        self.cargo_input.setMaximumWidth(110)
        self.cargo_input.setToolTip("Cargo capacity in SCU. UEX commodity prices are per SCU.")
        self.investment_input = QLineEdit()
        self.investment_input.setPlaceholderText("Max aUEC optional")
        self.investment_input.setMaximumWidth(150)
        self.investment_input.setToolTip("Optional max investment. Empty or 0 uses full cargo capacity.")
        self.refresh_button = QPushButton("Refresh UEX Data")
        self.find_routes_button = QPushButton("Find En Route")
        second_row.addWidget(self.ship_combo)
        second_row.addWidget(self.cargo_input)
        second_row.addWidget(self.investment_input)
        second_row.addWidget(self.refresh_button)
        second_row.addWidget(self.find_routes_button)
        second_row.addStretch(1)
        layout.addLayout(second_row)

        filters = QHBoxLayout()
        filters.setContentsMargins(0, 2, 0, 0)
        filters.setSpacing(10)
        self.min_total_profit_input = QLineEdit()
        self.min_total_profit_input.setPlaceholderText("Min Total Profit...")
        self.min_total_profit_input.setMaximumWidth(150)
        self.min_profit_input = QLineEdit()
        self.min_profit_input.setPlaceholderText("Min Profit / SCU...")
        self.min_profit_input.setMaximumWidth(145)
        self.show_unprofitable_checkbox = QCheckBox("Show unprofitable")
        self.hide_suspicious_checkbox = QCheckBox("Hide suspicious margins")
        filters.addWidget(self.min_total_profit_input)
        filters.addWidget(self.min_profit_input)
        filters.addWidget(self.show_unprofitable_checkbox)
        filters.addWidget(self.hide_suspicious_checkbox)
        filters.addStretch(1)
        layout.addLayout(filters)

        self.status_label = QLabel(
            "Uses UEX prices from the latest refresh. Results depend on public market data availability."
        )
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        card.setLayout(layout)
        return card

    def create_results_table(self):
        self.routes_table = QTableWidget(0, 12)
        self.routes_table.setHorizontalHeaderLabels([
            "Commodity",
            "Buy Location",
            "Buy / SCU",
            "Sell Location",
            "Sell / SCU",
            "Profit / SCU",
            "Cargo SCU",
            "Investment",
            "Est. Profit",
            "Margin %",
            "Quality",
            "Notes",
        ])
        self.routes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.routes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.routes_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.routes_table.setAlternatingRowColors(True)
        self.routes_table.setSortingEnabled(True)
        configure_readable_table_columns(self.routes_table, min_width=110, max_width=380, stretch_last=True)
        return self.routes_table

    def connect_signals(self):
        self.refresh_button.clicked.connect(self.refresh_uex_data)
        self.find_routes_button.clicked.connect(self.find_routes)
        self.ship_combo.currentTextChanged.connect(self.on_ship_changed)
        self.routes_table.itemSelectionChanged.connect(self.update_details)
        self.copy_summary_button.clicked.connect(self.copy_route_summary)
        self.save_route_button.clicked.connect(self.save_selected_route)

    def on_ship_changed(self):
        fill_cargo_from_ship(self.ship_combo, self.cargo_input, self.status_label)

    def refresh_uex_data(self):
        if self.uex_refresh_running:
            return

        self.uex_refresh_running = True
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Loading...")
        self.status_label.setText("Loading public UEX price data...")

        self.start_background_task(
            fetch_all_commodity_prices,
            self.on_uex_prices_loaded,
            self.on_uex_prices_error,
            self.finish_uex_refresh,
        )

    def on_uex_prices_loaded(self, prices):
        self.price_rows = list(prices or [])
        self.routes = []
        self.last_result = None
        set_combo_items(self.origin_combo, location_display_values(self.price_rows))
        set_combo_items(self.destination_combo, location_display_values(self.price_rows))
        set_combo_items(self.commodity_combo, commodity_display_values(self.price_rows))
        self.status_label.setText(
            f"Loaded {len(self.price_rows)} UEX price rows. Choose origin/destination and click Find En Route."
        )
        self.empty_label.setText("UEX data loaded. Choose origin/destination and click Find En Route.")
        self.populate_routes_table()

    def on_uex_prices_error(self, exc):
        self.price_rows = []
        self.routes = []
        self.last_result = None
        self.status_label.setText(f"Failed to load UEX price data: {exc}")
        self.empty_label.setText("UEX price data failed to load. Try refreshing again later.")
        self.populate_routes_table()

    def finish_uex_refresh(self):
        self.uex_refresh_running = False
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh UEX Data")

    def find_routes(self):
        if self.route_calculation_running:
            self.status_label.setText("En Route calculation already running.")
            return
        if not self.price_rows:
            self.status_label.setText("Refresh UEX Data before finding En Route opportunities.")
            self.empty_label.setText("Refresh UEX Data to load public market prices.")
            self.routes = []
            self.populate_routes_table()
            return

        self.route_request_id += 1
        request_id = self.route_request_id
        price_rows = tuple(self.price_rows)
        filters = {
            "origin": selected_combo_text(self.origin_combo, allow_free_text=True),
            "destination": selected_combo_text(self.destination_combo, allow_free_text=True),
            "cargo_scu": self.parse_number(self.cargo_input.text(), default=1),
            "max_investment": self.parse_positive_number(self.investment_input.text()),
            "commodity_filter": selected_combo_text(self.commodity_combo, allow_free_text=True),
            "min_total_profit": self.parse_number(self.min_total_profit_input.text()),
            "min_profit_per_scu": self.parse_number(self.min_profit_input.text()),
            "include_unprofitable": self.show_unprofitable_checkbox.isChecked(),
            "hide_suspicious": self.hide_suspicious_checkbox.isChecked(),
        }

        self.route_calculation_running = True
        self.find_routes_button.setEnabled(False)
        self.find_routes_button.setText("Finding...")
        self.refresh_button.setEnabled(False)
        self.status_label.setText("Finding En Route opportunities from refreshed UEX prices...")
        self.empty_label.setText("Finding En Route opportunities...")
        self.empty_label.setVisible(True)

        self.start_background_task(
            lambda: build_uex_en_route_opportunities(price_rows, **filters),
            lambda result, current_request=request_id: self.on_routes_calculated(current_request, result),
            lambda exc, current_request=request_id: self.on_route_calculation_error(current_request, exc),
            lambda current_request=request_id: self.finish_route_calculation(current_request),
        )

    def on_routes_calculated(self, request_id, result):
        if request_id != self.route_request_id:
            return
        self.last_result = result
        self.routes = result.routes
        self.status_label.setText(
            f"{result.message} Matched {result.buy_row_count} buy rows and {result.sell_row_count} sell rows."
        )
        self.empty_label.setText(result.message)
        self.populate_routes_table()

    def on_route_calculation_error(self, request_id, exc):
        if request_id != self.route_request_id:
            return
        self.last_result = None
        self.routes = []
        self.status_label.setText(f"En Route calculation failed: {exc}")
        self.empty_label.setText("En Route calculation failed. Adjust filters or refresh UEX data.")
        self.populate_routes_table()

    def finish_route_calculation(self, request_id):
        if request_id != self.route_request_id:
            return
        self.route_calculation_running = False
        self.find_routes_button.setEnabled(True)
        self.find_routes_button.setText("Find En Route")
        self.refresh_button.setEnabled(not self.uex_refresh_running)

    def populate_routes_table(self):
        sorting_enabled = self.routes_table.isSortingEnabled()
        self.routes_table.setSortingEnabled(False)
        self.routes_table.setRowCount(len(self.routes))

        for row_index, route in enumerate(self.routes):
            quality = self.route_quality(route)
            notes = self.route_notes(route, quality)
            values = [
                route.commodity,
                route.buy_location,
                self.format_auec(route.buy_price),
                route.sell_location,
                self.format_auec(route.sell_price),
                self.format_auec(route.profit_per_scu),
                self.format_scu(route.cargo_scu),
                self.format_auec(route.buy_cost),
                self.format_auec(route.total_profit),
                self.format_percent(route.margin_percent),
                quality.label,
                notes,
            ]
            sort_values = [
                route.commodity,
                route.buy_location,
                route.buy_price,
                route.sell_location,
                route.sell_price,
                route.profit_per_scu,
                route.cargo_scu,
                route.buy_cost,
                route.total_profit,
                route.margin_percent,
                quality.sort_value,
                notes,
            ]
            for col_index, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setData(SORT_ROLE, sort_values[col_index])
                item.setData(ROW_ROLE, row_index)
                if col_index in (2, 4, 5, 6, 7, 8, 9):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if notes and col_index in (10, 11):
                    item.setToolTip(notes)
                self.routes_table.setItem(row_index, col_index, item)

        self.routes_table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(self.routes_table, min_width=110, max_width=380, stretch_last=True)
        self.empty_label.setVisible(not self.routes)
        self.update_details()

    def update_details(self):
        route = self.selected_route()
        if not route:
            self.detail_label.setText("Refresh UEX Data, choose origin/destination, then click Find En Route.")
            self.copy_summary_button.setEnabled(False)
            self.save_route_button.setEnabled(False)
            return

        self.detail_label.setText(format_route_summary(self.route_record_for_route(route)))
        self.copy_summary_button.setEnabled(True)
        self.save_route_button.setEnabled(True)

    def route_record_for_route(self, route):
        quality = self.route_quality(route)
        return TradingRouteRecord(
            source=route.source,
            commodity=route.commodity,
            buy_location=route.buy_location,
            sell_location=route.sell_location,
            buy_price=route.buy_price,
            sell_price=route.sell_price,
            profit_per_scu=route.profit_per_scu,
            cargo_scu=route.cargo_scu,
            buy_cost=route.buy_cost,
            total_profit=route.total_profit,
            quality=quality.label,
            notes=notes_from_flags(quality.flags, (*route.notes, f"Updated: {format_trade_age(route.date_modified)}")),
        )

    def copy_route_summary(self):
        route = self.selected_route()
        if not route:
            return

        record = self.route_record_for_route(route)
        copy_to_clipboard(format_route_summary(record))
        if is_complete_route_record(record):
            add_recent_trading_route(record)
            self.status_label.setText("Route summary copied and added to recent routes.")
        else:
            self.status_label.setText("Route summary copied to clipboard.")

    def save_selected_route(self):
        route = self.selected_route()
        if not route:
            return

        record = self.route_record_for_route(route)
        if not is_complete_route_record(record):
            self.status_label.setText("This route is missing required buy/sell data and cannot be saved.")
            return

        save_trading_route(record)
        add_recent_trading_route(record)
        self.status_label.setText("Route saved locally.")

    def route_quality(self, route):
        investment_limited = "Budget limited" in route.notes
        return calculate_route_quality(
            total_profit=route.total_profit,
            profit_per_scu=route.profit_per_scu,
            full_cargo=not investment_limited,
            affordable=not investment_limited,
            suspicious=is_suspicious_margin(route),
        )

    def route_notes(self, route, quality):
        notes = []
        for note in (*quality.flags, *route.notes):
            if note and note not in notes:
                notes.append(note)
        return ", ".join(notes) if notes else "UEX"

    def selected_route(self):
        row = self.routes_table.currentRow()
        if row < 0:
            return self.routes[0] if self.routes else None

        item = self.routes_table.item(row, 0)
        if not item:
            return None

        index = item.data(ROW_ROLE)
        if index is None or index >= len(self.routes):
            return None

        return self.routes[index]

    def parse_number(self, value, default=None):
        value = (value or "").replace(",", "").replace(" ", "").strip()
        if not value:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def parse_positive_number(self, value):
        parsed = self.parse_number(value)
        if parsed is None or parsed <= 0:
            return None
        return parsed

    def format_auec(self, value):
        if value is None:
            return "N/A"
        return f"{self.format_number(value)} aUEC"

    def format_scu(self, value):
        if value is None:
            return "N/A"
        return f"{self.format_number(value)} SCU"

    def format_percent(self, value):
        if value is None:
            return "N/A"
        return f"{self.format_number(value)}%"

    def format_number(self, value):
        if value is None:
            return "N/A"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "N/A"
        if number.is_integer():
            return f"{int(number):,}"
        return f"{number:,.2f}".rstrip("0").rstrip(".")
