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
    fetch_commodity_shops,
    fetch_en_route,
)

from ..table_utils import configure_readable_table_columns
from ..workers import BackgroundTaskMixin


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
    def __init__(self):
        super().__init__()

        self.location_refresh_running = False
        self.route_refresh_running = False
        self.locations = []
        self.routes = []

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

        self.empty_label = QLabel("Load shops, enter a route, then search en-route opportunities.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        self.detail_label = QLabel("Select a route opportunity to see details.")
        self.detail_label.setObjectName("valueText")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

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
        self.origin_combo.setEditable(True)
        self.origin_combo.setPlaceholderText("Start shop...")
        self.destination_combo = QComboBox()
        self.destination_combo.setEditable(True)
        self.destination_combo.setPlaceholderText("Destination shop...")
        self.commodity_input = QLineEdit()
        self.commodity_input.setPlaceholderText("Commodity optional...")
        first_row.addWidget(self.origin_combo, 1)
        first_row.addWidget(self.destination_combo, 1)
        first_row.addWidget(self.commodity_input, 1)
        layout.addLayout(first_row)

        second_row = QHBoxLayout()
        second_row.setSpacing(8)
        self.ship_input = QLineEdit("Freelancer")
        self.ship_input.setPlaceholderText("Ship")
        self.ship_input.setMaximumWidth(140)
        self.investment_input = QLineEdit("100000")
        self.investment_input.setPlaceholderText("Investment aUEC")
        self.investment_input.setMaximumWidth(140)
        self.detour_input = QLineEdit("25")
        self.detour_input.setPlaceholderText("Detour %")
        self.detour_input.setMaximumWidth(100)
        self.load_locations_button = QPushButton("Load Shops")
        self.find_routes_button = QPushButton("Find En Route")
        self.open_source_button = QPushButton("Open Source")
        second_row.addWidget(self.ship_input)
        second_row.addWidget(self.investment_input)
        second_row.addWidget(self.detour_input)
        second_row.addWidget(self.load_locations_button)
        second_row.addWidget(self.find_routes_button)
        second_row.addWidget(self.open_source_button)
        second_row.addStretch(1)
        layout.addLayout(second_row)

        self.status_label = QLabel(
            "Token required for itinerary results. Configure SC Trade Tools API Token in Settings."
        )
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        card.setLayout(layout)
        return card

    def create_results_table(self):
        self.routes_table = QTableWidget(0, 6)
        self.routes_table.setHorizontalHeaderLabels([
            "Commodity",
            "Origin",
            "Destination",
            "Profit",
            "Profit / Min",
            "Time",
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
        self.routes_table.itemSelectionChanged.connect(self.update_details)

    def load_locations(self):
        if self.location_refresh_running:
            return

        self.location_refresh_running = True
        self.load_locations_button.setEnabled(False)
        self.load_locations_button.setText("Loading...")
        self.status_label.setText("Loading token-free location list...")

        self.start_background_task(
            fetch_commodity_shops,
            self.on_locations_loaded,
            self.on_error,
            self.finish_location_refresh,
        )

    def on_locations_loaded(self, locations):
        self.locations = sorted(locations, key=lambda item: item.name.lower())
        self.populate_location_combo(self.origin_combo)
        self.populate_location_combo(self.destination_combo)
        self.status_label.setText(
            f"Loaded {len(self.locations)} commodity shops. En Route lookup requires a configured token."
        )

    def populate_location_combo(self, combo):
        current_text = combo.currentText().strip()
        combo.blockSignals(True)
        combo.clear()
        for location in self.locations:
            combo.addItem(location.name)
        if current_text:
            combo.setCurrentText(current_text)
        combo.blockSignals(False)

    def finish_location_refresh(self):
        self.location_refresh_running = False
        self.load_locations_button.setEnabled(True)
        self.load_locations_button.setText("Load Shops")

    def find_routes(self):
        if self.route_refresh_running:
            return

        token = get_app_setting(SC_TRADE_TOOLS_TOKEN_SETTING, "")
        if not token.strip():
            self.status_label.setText(
                "SC Trade Tools token is not configured. Add it in Settings to use En Route."
            )
            self.routes = []
            self.populate_routes_table()
            return

        origin = self.origin_combo.currentText().strip()
        destination = self.destination_combo.currentText().strip()
        if not origin or not destination:
            self.status_label.setText("Start location and destination are required.")
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
                commodity_name=self.commodity_input.text(),
                ship=self.ship_input.text(),
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
        self.populate_routes_table()

    def finish_route_refresh(self):
        self.route_refresh_running = False
        self.find_routes_button.setEnabled(True)
        self.find_routes_button.setText("Find En Route")

    def on_error(self, exc):
        self.status_label.setText(f"SC Trade Tools request failed: {exc}")

    def populate_routes_table(self):
        sorting_enabled = self.routes_table.isSortingEnabled()
        self.routes_table.setSortingEnabled(False)
        self.routes_table.setRowCount(len(self.routes))

        for row_index, route in enumerate(self.routes):
            values = [
                route.commodity,
                route.origin,
                route.destination,
                self.format_auec(route.profit),
                self.format_auec(route.profit_per_minute),
                self.format_seconds(route.time_seconds),
            ]
            sort_values = [
                route.commodity,
                route.origin,
                route.destination,
                route.profit,
                route.profit_per_minute,
                route.time_seconds,
            ]
            for col_index, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setData(SORT_ROLE, sort_values[col_index])
                item.setData(ROW_ROLE, row_index)
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
            return

        self.detail_label.setText(
            f"Commodity: {route.commodity}\n"
            f"Origin: {route.origin}\n"
            f"Destination: {route.destination}\n"
            f"Profit: {self.format_auec(route.profit)}\n"
            f"Profit / minute: {self.format_auec(route.profit_per_minute)}\n"
            f"Estimated time: {self.format_seconds(route.time_seconds)}\n"
            "Source: SC Trade Tools"
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
