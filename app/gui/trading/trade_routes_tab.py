from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from app.trading_data import (
    build_trading_opportunities,
    calculate_trade_estimate,
    fetch_trading_opportunities,
    format_trade_age,
    is_suspicious_margin,
)
from app.trading_trade_routes import filter_trade_routes
from app.trading_storage import (
    TradingRouteRecord,
    add_recent_trading_route,
    save_trading_route,
)

from ..safe_combobox import SafeComboBox as QComboBox
from ..sortable_table_item import ROW_ROLE, SORT_ROLE, SortableTableWidgetItem
from ..responsive import install_scroll_area, stabilize_table
from ..table_utils import configure_readable_table_columns
from ..workers import BackgroundTaskMixin
from .reference_data import get_trading_reference_service
from .route_quality import calculate_route_quality, copy_to_clipboard
from .route_summary import format_route_summary, is_complete_route_record, notes_from_flags
from .searchable_combo import configure_searchable_combo, selected_combo_text, set_combo_items
from .ship_selection import configure_ship_combo, fill_cargo_from_ship, selected_ship_name, update_ship_combo


class TradeRoutesTab(BackgroundTaskMixin, QWidget):
    def __init__(self, reference_service=None):
        super().__init__()

        self.reference_service = reference_service or get_trading_reference_service()
        self.routes_refresh_running = False
        self.shops = []
        self.locations = []
        self.commodities = []
        self.routes = []
        self.route_estimates = {}
        self.price_row_count = 0

        self.build_ui()
        self.connect_signals()
        self.connect_reference_service()
        self.populate_routes_table()
        self.update_details()

    def connect_reference_service(self):
        self.reference_service.loaded.connect(self.on_reference_loaded)
        self.reference_service.error.connect(self.on_reference_error)
        self.reference_service.state_changed.connect(self.on_reference_state_changed)
        if self.reference_service.data is not None:
            self.on_reference_loaded(self.reference_service.data)
        elif self.reference_service.is_loading:
            self.on_reference_state_changed("loading")

    def build_ui(self):
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_header())
        layout.addWidget(self.create_controls())
        layout.addWidget(self.create_results_table(), 1)

        self.empty_label = QLabel("Load lists, choose route filters, then find trade routes.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        self.detail_label = QLabel("Select a trade route to see details.")
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

        self.trade_routes_scroll_area = install_scroll_area(self, content_widget)

    def create_header(self):
        header = QFrame()
        header.setObjectName("playerCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title = QLabel("Trade Routes")
        title.setObjectName("moduleHeading")
        subtitle = QLabel(
            "UEX-backed trade route explorer for commodity, origin, destination and budget filters."
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

        title = QLabel("ROUTE SEARCH")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        first_row = QHBoxLayout()
        first_row.setSpacing(8)
        self.origin_combo = QComboBox()
        configure_searchable_combo(self.origin_combo, "Start shop optional...")
        self.location_filter_combo = QComboBox()
        configure_searchable_combo(self.location_filter_combo, "Destination/location filter optional...")
        self.commodity_combo = QComboBox()
        configure_searchable_combo(self.commodity_combo, "Commodity optional...")
        first_row.addWidget(self.origin_combo, 1)
        first_row.addWidget(self.location_filter_combo, 1)
        first_row.addWidget(self.commodity_combo, 1)
        layout.addLayout(first_row)

        second_row = QHBoxLayout()
        second_row.setSpacing(8)
        self.ship_combo = QComboBox()
        configure_ship_combo(self.ship_combo)
        self.ship_combo.setMaximumWidth(180)
        self.cargo_input = QLineEdit("1")
        self.cargo_input.setPlaceholderText("Cargo SCU")
        self.cargo_input.setMaximumWidth(100)
        self.investment_input = QLineEdit("100000")
        self.investment_input.setPlaceholderText("Max investment aUEC")
        self.investment_input.setMaximumWidth(160)
        self.load_lists_button = QPushButton("Refresh Reference Data")
        self.search_button = QPushButton("Find Routes")
        second_row.addWidget(self.ship_combo)
        second_row.addWidget(self.cargo_input)
        second_row.addWidget(self.investment_input)
        second_row.addWidget(self.load_lists_button)
        second_row.addWidget(self.search_button)
        second_row.addStretch(1)
        layout.addLayout(second_row)

        self.status_label = QLabel("Loading UEX reference data...")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        card.setLayout(layout)
        return card

    def create_results_table(self):
        self.routes_table = QTableWidget(0, 11)
        self.routes_table.setHorizontalHeaderLabels([
            "Commodity",
            "Buy Location",
            "Buy Price",
            "Sell Location",
            "Sell Price",
            "Profit / SCU",
            "Cargo SCU",
            "Total Profit",
            "Buy Cost",
            "Quality",
            "Source / Updated",
        ])
        self.routes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.routes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.routes_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.routes_table.setAlternatingRowColors(True)
        self.routes_table.setSortingEnabled(True)
        stabilize_table(self.routes_table, minimum_height=300)
        configure_readable_table_columns(self.routes_table, min_width=110, max_width=380, stretch_last=True)
        return self.routes_table

    def connect_signals(self):
        self.load_lists_button.clicked.connect(self.load_reference_data)
        self.search_button.clicked.connect(self.find_routes)
        self.ship_combo.currentTextChanged.connect(self.on_ship_changed)
        self.routes_table.itemSelectionChanged.connect(self.update_details)
        self.copy_summary_button.clicked.connect(self.copy_route_summary)
        self.save_route_button.clicked.connect(self.save_selected_route)

    def on_ship_changed(self):
        fill_cargo_from_ship(self.ship_combo, self.cargo_input, self.status_label)

    def load_reference_data(self):
        self.reference_service.refresh(force=True)

    def on_reference_loaded(self, data):
        self.shops = list(data.shops)
        self.locations = list(data.locations)
        self.commodities = list(data.commodities)
        set_combo_items(self.origin_combo, (shop.name for shop in self.shops))
        set_combo_items(self.location_filter_combo, (location.name for location in self.locations))
        set_combo_items(self.commodity_combo, (commodity.name for commodity in self.commodities))
        update_ship_combo(self.ship_combo, data.ships)
        source_note = ""
        if getattr(data, "source_error", ""):
            source_note = f" UEX reference refresh failed: {data.source_error}"
        elif getattr(data, "cache_status", "") in {"stale", "error"}:
            source_note = " UEX cache stale; refresh available."
        elif getattr(data, "cache_status", "") == "fresh":
            source_note = " Local UEX cache loaded."
        self.status_label.setText(
            f"Loaded {len(self.shops)} shops, {len(self.locations)} locations and "
            f"{len(self.commodities)} commodities from UEX reference rows.{source_note}"
        )

    def on_reference_state_changed(self, state):
        if state == "loading":
            self.load_lists_button.setEnabled(False)
            self.load_lists_button.setText("Loading...")
            self.status_label.setText("Loading UEX reference data...")
        else:
            self.load_lists_button.setEnabled(True)
            self.load_lists_button.setText("Refresh Reference Data")

    def on_reference_error(self, exc):
        self.status_label.setText(f"Reference data failed to load: {exc}")

    def find_routes(self):
        if self.routes_refresh_running:
            return

        ship = selected_ship_name(self.ship_combo)
        if not ship:
            self.status_label.setText("Choose a ship from the searchable dropdown before finding routes.")
            return

        self.routes_refresh_running = True
        self.search_button.setEnabled(False)
        self.search_button.setText("Searching...")
        self.status_label.setText("Loading UEX trade routes...")

        self.start_background_task(
            self.load_trade_routes,
            self.on_routes_loaded,
            self.on_error,
            self.finish_routes_refresh,
        )

    def load_trade_routes(self):
        data = self.reference_service.data
        if data is not None and data.price_rows:
            routes = build_trading_opportunities(data.price_rows, include_unprofitable=False)
            return routes, len(data.price_rows)

        return fetch_trading_opportunities(include_unprofitable=False)

    def on_routes_loaded(self, result):
        routes, price_row_count = result
        self.price_row_count = price_row_count
        self.routes = self.filtered_routes(routes)
        self.routes.sort(
            key=lambda route: (
                -self.estimate_for_route(route).estimated_total_profit,
                -route.profit_per_scu,
                route.commodity.lower(),
            )
        )
        self.status_label.setText(
            f"Loaded {len(self.routes)} UEX trade routes from {price_row_count} price rows."
        )
        if not self.routes:
            self.empty_label.setText("No UEX routes matched the selected filters.")
        self.populate_routes_table()

    def filtered_routes(self, routes):
        origin = selected_combo_text(self.origin_combo, allow_free_text=True).lower()
        destination = selected_combo_text(self.location_filter_combo, allow_free_text=True).lower()
        commodity = selected_combo_text(self.commodity_combo, allow_free_text=True).lower()
        return filter_trade_routes(routes, origin=origin, destination=destination, commodity=commodity)

    def finish_routes_refresh(self):
        self.routes_refresh_running = False
        self.search_button.setEnabled(True)
        self.search_button.setText("Find Routes")

    def on_error(self, exc):
        self.status_label.setText(f"UEX route lookup failed: {exc}")
        self.empty_label.setText("UEX route data failed to load. Try refreshing again later.")
        self.routes = []
        self.route_estimates = {}
        self.populate_routes_table()

    def populate_routes_table(self):
        sorting_enabled = self.routes_table.isSortingEnabled()
        self.routes_table.setSortingEnabled(False)
        self.routes_table.setRowCount(len(self.routes))
        self.route_estimates = {}

        for row_index, route in enumerate(self.routes):
            estimate = self.estimate_for_route(route)
            quality = self.route_quality(route)
            values = [
                route.commodity,
                route.buy_location,
                self.format_auec(route.buy_price),
                route.sell_location,
                self.format_auec(route.sell_price),
                self.format_auec(route.profit_per_scu),
                self.format_scu(estimate.effective_cargo_scu),
                self.format_auec(estimate.estimated_total_profit),
                self.format_auec(estimate.estimated_buy_cost),
                quality.label,
                f"{route.source} | {format_trade_age(route.date_modified)}",
            ]
            sort_values = [
                route.commodity,
                route.buy_location,
                route.buy_price,
                route.sell_location,
                route.sell_price,
                route.profit_per_scu,
                estimate.effective_cargo_scu,
                estimate.estimated_total_profit,
                estimate.estimated_buy_cost,
                quality.sort_value,
                route.date_modified or 0,
            ]
            for col_index, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setData(SORT_ROLE, sort_values[col_index])
                item.setData(ROW_ROLE, row_index)
                if quality.flags and col_index == 9:
                    item.setToolTip(" | ".join(quality.flags))
                if col_index in (2, 4, 5, 6, 7, 8):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.routes_table.setItem(row_index, col_index, item)

        self.routes_table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(self.routes_table, min_width=110, max_width=380, stretch_last=True)
        self.empty_label.setVisible(not self.routes)
        if not self.routes and not self.empty_label.text():
            self.empty_label.setText("No route results yet. Choose filters and click Find Routes.")
        self.update_details()

    def update_details(self):
        route = self.selected_route()
        if not route:
            self.detail_label.setText(
                "Choose filters and click Find Routes to load UEX trade opportunities."
            )
            self.copy_summary_button.setEnabled(False)
            self.save_route_button.setEnabled(False)
            return

        record = self.route_record_for_route(route)
        self.detail_label.setText(format_route_summary(record))
        self.copy_summary_button.setEnabled(True)
        self.save_route_button.setEnabled(is_complete_route_record(record))

    def build_route_summary(self, route):
        return format_route_summary(self.route_record_for_route(route))

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
            cargo_scu=self.estimate_for_route(route).effective_cargo_scu,
            buy_cost=self.estimate_for_route(route).estimated_buy_cost,
            total_profit=self.estimate_for_route(route).estimated_total_profit,
            quality=quality.label,
            notes=notes_from_flags(quality.flags, (f"Updated: {format_trade_age(route.date_modified)}",)),
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
            self.status_label.setText("Route summary copied to clipboard. Route is incomplete, so it was not saved.")

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
        cargo_requested = self.parse_number(self.cargo_input.text(), default=None)
        investment = self.parse_number(self.investment_input.text(), default=None)
        estimate = self.estimate_for_route(route)
        full_cargo = None
        if cargo_requested is not None:
            full_cargo = estimate.effective_cargo_scu >= cargo_requested

        affordable = None
        if investment is not None:
            affordable = estimate.estimated_buy_cost <= investment

        return calculate_route_quality(
            total_profit=estimate.estimated_total_profit,
            profit_per_scu=route.profit_per_scu,
            full_cargo=full_cargo,
            affordable=affordable,
            suspicious=self.is_suspicious_route(route),
        )

    def is_suspicious_route(self, route):
        return is_suspicious_margin(route)

    def estimate_for_route(self, route):
        key = id(route)
        if key not in self.route_estimates:
            self.route_estimates[key] = calculate_trade_estimate(
                route,
                self.parse_number(self.cargo_input.text(), default=1),
                self.parse_number(self.investment_input.text(), default=None),
            )
        return self.route_estimates[key]

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

    def format_auec(self, value):
        if value is None:
            return "N/A"
        return f"{self.format_number(value)} aUEC"

    def format_scu(self, value):
        if value is None:
            return "N/A"
        return f"{self.format_number(value)} SCU"

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
