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
    fetch_trade_routes,
)

from ..table_utils import configure_readable_table_columns
from ..workers import BackgroundTaskMixin
from .reference_data import get_trading_reference_service
from .searchable_combo import configure_searchable_combo, selected_combo_text, set_combo_items
from .ship_selection import configure_ship_combo, fill_cargo_from_ship, selected_ship_name, update_ship_combo


SORT_ROLE = Qt.UserRole + 1
ROW_ROLE = Qt.UserRole + 2
SC_TRADE_ROUTES_URL = "https://sc-trade.tools/trade-routes"


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


class TradeRoutesTab(BackgroundTaskMixin, QWidget):
    def __init__(self, reference_service=None):
        super().__init__()

        self.reference_service = reference_service or get_trading_reference_service()
        self.routes_refresh_running = False
        self.shops = []
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

        self.empty_label = QLabel("Load lists, choose route filters, then find trade routes.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        self.detail_label = QLabel("Select a trade route to see details.")
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

        title = QLabel("Trade Routes")
        title.setObjectName("moduleHeading")
        subtitle = QLabel(
            "SC Trade Tools-backed profitable trade routes. Requires an optional local API token."
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
        self.open_source_button = QPushButton("Open Source")
        second_row.addWidget(self.ship_combo)
        second_row.addWidget(self.cargo_input)
        second_row.addWidget(self.investment_input)
        second_row.addWidget(self.load_lists_button)
        second_row.addWidget(self.search_button)
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
        self.routes_table = QTableWidget(0, 10)
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
            "Source / Updated",
        ])
        self.routes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.routes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.routes_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.routes_table.setAlternatingRowColors(True)
        self.routes_table.setSortingEnabled(True)
        configure_readable_table_columns(self.routes_table, min_width=110, max_width=380, stretch_last=True)
        return self.routes_table

    def connect_signals(self):
        self.load_lists_button.clicked.connect(self.load_reference_data)
        self.search_button.clicked.connect(self.find_routes)
        self.open_source_button.clicked.connect(self.open_source)
        self.ship_combo.currentTextChanged.connect(self.on_ship_changed)
        self.routes_table.itemSelectionChanged.connect(self.update_details)

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
        self.status_label.setText(
            f"Loaded {len(self.shops)} shops, {len(self.locations)} locations and "
            f"{len(self.commodities)} commodities. Route lookup requires a configured token."
        )

    def on_reference_state_changed(self, state):
        if state == "loading":
            self.load_lists_button.setEnabled(False)
            self.load_lists_button.setText("Loading...")
            self.status_label.setText("Loading SC Trade Tools reference data...")
        else:
            self.load_lists_button.setEnabled(True)
            self.load_lists_button.setText("Refresh Reference Data")

    def on_reference_error(self, exc):
        self.status_label.setText(f"Reference data failed to load: {exc}")

    def find_routes(self):
        if self.routes_refresh_running:
            return

        token = get_app_setting(SC_TRADE_TOOLS_TOKEN_SETTING, "")
        if not token.strip():
            self.status_label.setText("SC Trade Tools token required for Trade Routes.")
            self.routes = []
            self.populate_routes_table()
            return

        if not self.shops or not self.locations or not self.commodities:
            self.status_label.setText("Reference data is still loading or failed to load. Refresh reference data first.")
            return

        ship = selected_ship_name(self.ship_combo)
        if not ship:
            self.status_label.setText("Choose a ship from the searchable dropdown before finding routes.")
            return

        self.routes_refresh_running = True
        self.search_button.setEnabled(False)
        self.search_button.setText("Searching...")
        self.status_label.setText("Searching SC Trade Tools trade routes...")

        self.start_background_task(
            lambda: fetch_trade_routes(
                token=token,
                origin=selected_combo_text(self.origin_combo, allow_free_text=False),
                location_filter=selected_combo_text(self.location_filter_combo, allow_free_text=False),
                commodity_name=selected_combo_text(self.commodity_combo, allow_free_text=False),
                ship=ship,
                cargo_scu=self.parse_number(self.cargo_input.text(), default=1),
                investment=self.parse_number(self.investment_input.text(), default=100000),
            ),
            self.on_routes_loaded,
            self.on_error,
            self.finish_routes_refresh,
        )

    def on_routes_loaded(self, routes):
        self.routes = sorted(
            routes,
            key=lambda route: route.total_profit if route.total_profit is not None else -1,
            reverse=True,
        )
        self.status_label.setText(f"Loaded {len(self.routes)} trade routes from SC Trade Tools.")
        self.populate_routes_table()

    def finish_routes_refresh(self):
        self.routes_refresh_running = False
        self.search_button.setEnabled(True)
        self.search_button.setText("Find Routes")

    def on_error(self, exc):
        self.status_label.setText(f"SC Trade Tools request failed: {exc}")

    def populate_routes_table(self):
        sorting_enabled = self.routes_table.isSortingEnabled()
        self.routes_table.setSortingEnabled(False)
        self.routes_table.setRowCount(len(self.routes))

        for row_index, route in enumerate(self.routes):
            values = [
                route.commodity,
                route.buy_location,
                self.format_auec(route.buy_price),
                route.sell_location,
                self.format_auec(route.sell_price),
                self.format_auec(route.profit_per_scu),
                self.format_scu(route.cargo_scu),
                self.format_auec(route.total_profit),
                self.format_auec(route.buy_cost),
                "SC Trade Tools",
            ]
            sort_values = [
                route.commodity,
                route.buy_location,
                route.buy_price,
                route.sell_location,
                route.sell_price,
                route.profit_per_scu,
                route.cargo_scu,
                route.total_profit,
                route.buy_cost,
                "SC Trade Tools",
            ]
            for col_index, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setData(SORT_ROLE, sort_values[col_index])
                item.setData(ROW_ROLE, row_index)
                if col_index in (2, 4, 5, 6, 7, 8):
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
                "Trade Routes requires a SC Trade Tools token. Configure it in Settings, then search routes."
            )
            return

        self.detail_label.setText(
            f"Commodity: {route.commodity}\n"
            f"Buy: {route.buy_location} @ {self.format_auec(route.buy_price)} / SCU\n"
            f"Sell: {route.sell_location} @ {self.format_auec(route.sell_price)} / SCU\n"
            f"Profit / SCU: {self.format_auec(route.profit_per_scu)}\n"
            f"Cargo used: {self.format_scu(route.cargo_scu)}\n"
            f"Investment / buy cost: {self.format_auec(route.buy_cost)}\n"
            f"Estimated total profit: {self.format_auec(route.total_profit)}\n"
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

    def open_source(self):
        QDesktopServices.openUrl(QUrl(SC_TRADE_ROUTES_URL))
