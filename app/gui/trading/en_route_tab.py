from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database import get_app_setting
from app.sc_trade_tools_client import (
    SC_TRADE_TOOLS_TOKEN_SETTING,
    fetch_en_route,
)

from ..table_utils import configure_readable_table_columns
from ..workers import BackgroundTaskMixin
from .reference_data import get_trading_reference_service
from .route_quality import calculate_route_quality, copy_to_clipboard
from .searchable_combo import configure_searchable_combo, selected_combo_text, set_combo_items
from .ship_selection import configure_ship_combo, fill_cargo_from_ship, selected_ship_name, update_ship_combo


SORT_ROLE = Qt.UserRole + 1
ROW_ROLE = Qt.UserRole + 2
SC_TRADE_EN_ROUTE_URL = "https://sc-trade.tools/en-route"


class SortableTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        left = self.data(SORT_ROLE)
        right = other.data(SORT_ROLE) if isinstance(other, QTableWidgetItem) else None
        if left is not None or right is not None:
            return self.sort_key(left) < self.sort_key(right)
        return super().__lt__(other)

    @staticmethod
    def sort_key(value):
        if value is None:
            return (2, "")
        if isinstance(value, (int, float)):
            return (0, float(value))
        return (1, str(value).lower())


class EnRouteTab(BackgroundTaskMixin, QWidget):
    def __init__(self, reference_service=None):
        super().__init__()

        self.reference_service = reference_service or get_trading_reference_service()
        self.route_refresh_running = False
        self.locations = []
        self.commodities = []
        self.routes = []

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
        else:
            self.reference_service.ensure_loaded()

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_header())
        layout.addWidget(self.create_controls())
        layout.addWidget(self.create_results_table(), 1)

        self.empty_label = QLabel("Load lists, enter a route, then search en-route opportunities.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        self.detail_label = QLabel("Select a route opportunity to see details.")
        self.detail_label.setObjectName("valueText")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

        self.copy_summary_button = QPushButton("Copy Route Summary")
        self.copy_summary_button.setEnabled(False)
        layout.addWidget(self.copy_summary_button)

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
            "Find SC Trade Tools itinerary opportunities between a start and destination. "
            "This workflow requires an optional local API token."
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
        configure_searchable_combo(self.origin_combo, "Start shop...")
        self.destination_combo = QComboBox()
        configure_searchable_combo(self.destination_combo, "Destination shop...")
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
        self.ship_combo.setMaximumWidth(180)
        self.cargo_input = QLineEdit("1")
        self.cargo_input.setPlaceholderText("Cargo SCU")
        self.cargo_input.setMaximumWidth(100)
        self.investment_input = QLineEdit("100000")
        self.investment_input.setPlaceholderText("Investment aUEC")
        self.investment_input.setMaximumWidth(140)
        self.detour_input = QLineEdit("25")
        self.detour_input.setPlaceholderText("Detour %")
        self.detour_input.setMaximumWidth(100)
        self.load_locations_button = QPushButton("Refresh Reference Data")
        self.find_routes_button = QPushButton("Find En Route")
        self.open_source_button = QPushButton("Open Source")
        second_row.addWidget(self.ship_combo)
        second_row.addWidget(self.cargo_input)
        second_row.addWidget(self.investment_input)
        second_row.addWidget(self.detour_input)
        second_row.addWidget(self.load_locations_button)
        second_row.addWidget(self.find_routes_button)
        second_row.addWidget(self.open_source_button)
        second_row.addStretch(1)
        layout.addLayout(second_row)

        self.status_label = QLabel("Loading SC Trade Tools reference data...")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        card.setLayout(layout)
        return card

    def create_results_table(self):
        self.routes_table = QTableWidget(0, 7)
        self.routes_table.setHorizontalHeaderLabels([
            "Commodity",
            "Origin",
            "Destination",
            "Profit",
            "Profit / Min",
            "Time",
            "Quality",
        ])
        self.routes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.routes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.routes_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.routes_table.setAlternatingRowColors(True)
        self.routes_table.setSortingEnabled(True)
        configure_readable_table_columns(self.routes_table, min_width=110, max_width=380, stretch_last=True)
        return self.routes_table

    def connect_signals(self):
        self.load_locations_button.clicked.connect(self.load_locations)
        self.find_routes_button.clicked.connect(self.find_routes)
        self.open_source_button.clicked.connect(self.open_source)
        self.ship_combo.currentTextChanged.connect(self.on_ship_changed)
        self.routes_table.itemSelectionChanged.connect(self.update_details)
        self.copy_summary_button.clicked.connect(self.copy_route_summary)

    def on_ship_changed(self):
        fill_cargo_from_ship(self.ship_combo, self.cargo_input, self.status_label)

    def load_locations(self):
        self.reference_service.refresh(force=True)

    def on_reference_loaded(self, data):
        self.locations = list(data.shops)
        self.commodities = list(data.commodities)
        self.populate_location_combo(self.origin_combo)
        self.populate_location_combo(self.destination_combo)
        set_combo_items(self.commodity_combo, (commodity.name for commodity in self.commodities))
        update_ship_combo(self.ship_combo, data.ships)
        self.status_label.setText(
            f"Loaded {len(self.locations)} commodity shops and {len(self.commodities)} commodities. "
            "En Route lookup requires a configured token."
        )

    def populate_location_combo(self, combo):
        set_combo_items(combo, (location.name for location in self.locations))

    def on_reference_state_changed(self, state):
        if state == "loading":
            self.load_locations_button.setEnabled(False)
            self.load_locations_button.setText("Loading...")
            self.status_label.setText("Loading SC Trade Tools reference data...")
        else:
            self.load_locations_button.setEnabled(True)
            self.load_locations_button.setText("Refresh Reference Data")

    def on_reference_error(self, exc):
        self.status_label.setText(f"Reference data failed to load: {exc}")

    def find_routes(self):
        if self.route_refresh_running:
            return

        token = get_app_setting(SC_TRADE_TOOLS_TOKEN_SETTING, "")
        if not token.strip():
            self.status_label.setText(
                "SC Trade Tools token is not configured. Add it in Settings to use En Route."
            )
            self.empty_label.setText("Token required: configure a SC Trade Tools API token in Settings, then search.")
            self.routes = []
            self.populate_routes_table()
            return

        origin = selected_combo_text(self.origin_combo, allow_free_text=not self.locations)
        destination = selected_combo_text(self.destination_combo, allow_free_text=not self.locations)
        if not origin or not destination:
            self.status_label.setText("Choose start and destination shops from the searchable dropdowns.")
            return
        commodity = selected_combo_text(self.commodity_combo, allow_free_text=False)
        ship = selected_ship_name(self.ship_combo)
        if not ship:
            self.status_label.setText("Choose a ship from the searchable dropdown before searching.")
            return

        self.route_refresh_running = True
        self.find_routes_button.setEnabled(False)
        self.find_routes_button.setText("Searching...")
        self.status_label.setText("Searching SC Trade Tools itinerary opportunities...")

        self.start_background_task(
            lambda: fetch_en_route(
                token=token,
                origin=origin,
                destination=destination,
                commodity_name=commodity,
                ship=ship,
                max_volume=self.parse_number(self.cargo_input.text(), default=1),
                investment=self.parse_number(self.investment_input.text(), default=100000),
                allowable_detour=self.parse_number(self.detour_input.text(), default=25),
            ),
            self.on_routes_loaded,
            self.on_error,
            self.finish_route_refresh,
        )

    def on_routes_loaded(self, routes):
        self.routes = sorted(
            routes,
            key=lambda route: route.profit if route.profit is not None else -1,
            reverse=True,
        )
        self.status_label.setText(f"Loaded {len(self.routes)} en-route opportunities from SC Trade Tools.")
        if not self.routes:
            self.empty_label.setText("No en-route opportunities were returned for the selected route.")
        self.populate_routes_table()

    def finish_route_refresh(self):
        self.route_refresh_running = False
        self.find_routes_button.setEnabled(True)
        self.find_routes_button.setText("Find En Route")

    def on_error(self, exc):
        self.status_label.setText(f"SC Trade Tools request failed: {exc}")
        self.empty_label.setText("SC Trade Tools en-route lookup failed. Check token/network and try again.")
        self.routes = []
        self.populate_routes_table()

    def populate_routes_table(self):
        sorting_enabled = self.routes_table.isSortingEnabled()
        self.routes_table.setSortingEnabled(False)
        self.routes_table.setRowCount(len(self.routes))

        for row_index, route in enumerate(self.routes):
            quality = self.route_quality(route)
            values = [
                route.commodity,
                route.origin,
                route.destination,
                self.format_auec(route.profit),
                self.format_auec(route.profit_per_minute),
                self.format_seconds(route.time_seconds),
                quality.label,
            ]
            sort_values = [
                route.commodity,
                route.origin,
                route.destination,
                route.profit,
                route.profit_per_minute,
                route.time_seconds,
                quality.sort_value,
            ]
            for col_index, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setData(SORT_ROLE, sort_values[col_index])
                item.setData(ROW_ROLE, row_index)
                if quality.flags and col_index == 6:
                    item.setToolTip(" | ".join(quality.flags))
                if col_index in (3, 4, 5):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.routes_table.setItem(row_index, col_index, item)

        self.routes_table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(self.routes_table, min_width=110, max_width=380, stretch_last=True)
        self.empty_label.setVisible(not self.routes)
        self.update_details()

    def update_details(self):
        route = self.selected_route()
        if not route:
            self.detail_label.setText(
                "Itinerary results require a SC Trade Tools token. Configure it in Settings, then search a route."
            )
            self.copy_summary_button.setEnabled(False)
            return

        self.detail_label.setText(self.build_route_summary(route))
        self.copy_summary_button.setEnabled(True)

    def build_route_summary(self, route):
        quality = self.route_quality(route)
        notes = list(quality.flags)
        if not notes:
            notes.append("SC Trade Tools itinerary data does not include buy/sell price details.")

        return (
            f"Commodity: {route.commodity}\n"
            f"Buy from: {route.origin}\n"
            f"Sell to: {route.destination}\n"
            f"Profit: {self.format_auec(route.profit)}\n"
            f"Profit / minute: {self.format_auec(route.profit_per_minute)}\n"
            f"Estimated time: {self.format_seconds(route.time_seconds)}\n"
            f"Quality: {quality.label}\n"
            "Source: SC Trade Tools\n"
            f"Notes: {', '.join(notes)}"
        )

    def copy_route_summary(self):
        route = self.selected_route()
        if not route:
            return

        copy_to_clipboard(self.build_route_summary(route))
        self.status_label.setText("Route summary copied to clipboard.")

    def route_quality(self, route):
        return calculate_route_quality(
            total_profit=route.profit,
            profit_per_minute=route.profit_per_minute,
            suspicious=False,
        )

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

    def format_seconds(self, value):
        if value is None:
            return "N/A"
        total = int(value)
        hours = total // 3600
        minutes = (total % 3600) // 60
        seconds = total % 60
        if hours:
            return f"{hours}h {minutes}m {seconds}s"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def open_source(self):
        QDesktopServices.openUrl(QUrl(SC_TRADE_EN_ROUTE_URL))
