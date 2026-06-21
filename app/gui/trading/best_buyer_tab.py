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

from app.trading_best_buyer import fetch_uex_best_buyers, format_best_buyer_age

from ..sortable_table_item import ROW_ROLE, SORT_ROLE, SortableTableWidgetItem
from ..table_utils import configure_readable_table_columns
from ..workers import BackgroundTaskMixin
from .reference_data import get_trading_reference_service
from .route_quality import copy_to_clipboard
from .searchable_combo import configure_searchable_combo, selected_combo_text, set_combo_items
from .ship_selection import configure_ship_combo, fill_cargo_from_ship, update_ship_combo


class BestBuyerTab(BackgroundTaskMixin, QWidget):
    def __init__(self, reference_service=None):
        super().__init__()

        self.reference_service = reference_service or get_trading_reference_service()
        self.buyer_refresh_running = False
        self.commodities = []
        self.buyers = []

        self.build_ui()
        self.connect_signals()
        self.connect_reference_service()
        self.populate_buyers_table()
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
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_header())
        layout.addWidget(self.create_controls())
        layout.addWidget(self.create_results_table(), 1)

        self.empty_label = QLabel("Load commodities, choose one, then find buyers.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        self.detail_label = QLabel("Select a buyer to see details.")
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

        title = QLabel("Best Buyer")
        title.setObjectName("moduleHeading")
        subtitle = QLabel(
            "Find the strongest public UEX buyer locations for a selected commodity."
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

        title = QLabel("BUYER SEARCH")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.commodity_combo = QComboBox()
        configure_searchable_combo(self.commodity_combo, "Commodity...")
        self.ship_combo = QComboBox()
        configure_ship_combo(self.ship_combo)
        self.ship_combo.setMaximumWidth(180)
        self.quantity_input = QLineEdit("1")
        self.quantity_input.setPlaceholderText("Quantity SCU")
        self.quantity_input.setMaximumWidth(120)
        self.load_commodities_button = QPushButton("Refresh Reference Data")
        self.find_buyers_button = QPushButton("Find Buyers")

        controls.addWidget(self.commodity_combo, 1)
        controls.addWidget(self.ship_combo)
        controls.addWidget(self.quantity_input)
        controls.addWidget(self.load_commodities_button)
        controls.addWidget(self.find_buyers_button)
        layout.addLayout(controls)

        self.status_label = QLabel("Loading UEX reference data...")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        card.setLayout(layout)
        return card

    def create_results_table(self):
        self.buyers_table = QTableWidget(0, 5)
        self.buyers_table.setHorizontalHeaderLabels([
            "Buyer Location",
            "Terminal",
            "Sell / SCU",
            "Quantity SCU",
            "Source / Updated",
        ])
        self.buyers_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.buyers_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.buyers_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.buyers_table.setAlternatingRowColors(True)
        self.buyers_table.setSortingEnabled(True)
        configure_readable_table_columns(self.buyers_table, min_width=110, max_width=360, stretch_last=True)
        return self.buyers_table

    def connect_signals(self):
        self.load_commodities_button.clicked.connect(self.load_commodities)
        self.find_buyers_button.clicked.connect(self.find_buyers)
        self.ship_combo.currentTextChanged.connect(self.on_ship_changed)
        self.buyers_table.itemSelectionChanged.connect(self.update_details)
        self.copy_summary_button.clicked.connect(self.copy_route_summary)

    def on_ship_changed(self):
        fill_cargo_from_ship(self.ship_combo, self.quantity_input, self.status_label)

    def load_commodities(self):
        self.reference_service.refresh(force=True)

    def on_reference_loaded(self, data):
        self.commodities = list(data.commodities)
        set_combo_items(self.commodity_combo, (commodity.name for commodity in self.commodities))
        update_ship_combo(self.ship_combo, data.ships)
        source_note = ""
        if getattr(data, "source_error", ""):
            source_note = f" UEX reference refresh failed: {data.source_error}"
        self.status_label.setText(
            f"Loaded {len(self.commodities)} UEX commodities from latest refresh.{source_note}"
        )

    def on_reference_state_changed(self, state):
        if state == "loading":
            self.load_commodities_button.setEnabled(False)
            self.load_commodities_button.setText("Loading...")
            self.status_label.setText("Loading UEX reference data...")
        else:
            self.load_commodities_button.setEnabled(True)
            self.load_commodities_button.setText("Refresh Reference Data")

    def on_reference_error(self, exc):
        self.status_label.setText(f"Reference data failed to load: {exc}")

    def find_buyers(self):
        if self.buyer_refresh_running:
            return

        commodity = selected_combo_text(self.commodity_combo, allow_free_text=not self.commodities)
        if not commodity:
            self.status_label.setText("Choose a commodity from the searchable dropdown before finding buyers.")
            return

        quantity_scu = self.parse_number(self.quantity_input.text(), default=1)
        self.buyer_refresh_running = True
        self.find_buyers_button.setEnabled(False)
        self.find_buyers_button.setText("Searching...")
        self.status_label.setText("Searching UEX buyer locations...")

        self.start_background_task(
            lambda: fetch_uex_best_buyers(commodity, quantity_scu),
            self.on_buyers_loaded,
            self.on_error,
            self.finish_buyer_refresh,
        )

    def on_buyers_loaded(self, result):
        buyers, price_row_count = result
        self.buyers = buyers
        self.status_label.setText(
            f"Loaded {len(self.buyers)} UEX buyer results from {price_row_count} price rows."
        )
        if not self.buyers:
            self.empty_label.setText(
                "No UEX sell prices were found for the selected commodity. Try another commodity or refresh later."
            )
        self.populate_buyers_table()

    def finish_buyer_refresh(self):
        self.buyer_refresh_running = False
        self.find_buyers_button.setEnabled(True)
        self.find_buyers_button.setText("Find Buyers")

    def on_error(self, exc):
        self.status_label.setText(f"UEX buyer lookup failed: {exc}")
        self.empty_label.setText(
            "UEX buyer data failed to load. Try refreshing again later."
        )
        self.buyers = []
        self.populate_buyers_table()

    def populate_buyers_table(self):
        sorting_enabled = self.buyers_table.isSortingEnabled()
        self.buyers_table.setSortingEnabled(False)
        self.buyers_table.setRowCount(len(self.buyers))

        for row_index, buyer in enumerate(self.buyers):
            values = [
                buyer.location,
                buyer.terminal,
                self.format_auec(buyer.sell_price),
                self.format_number(buyer.quantity_scu),
                f"{buyer.source} | {format_best_buyer_age(buyer)}",
            ]
            sort_values = [
                buyer.location,
                buyer.terminal,
                buyer.sell_price,
                buyer.quantity_scu,
                buyer.date_modified or 0,
            ]
            for col_index, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setData(SORT_ROLE, sort_values[col_index])
                item.setData(ROW_ROLE, row_index)
                if col_index in (2, 3):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.buyers_table.setItem(row_index, col_index, item)

        self.buyers_table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(self.buyers_table, min_width=110, max_width=360, stretch_last=True)
        self.empty_label.setVisible(not self.buyers)
        self.update_details()

    def update_details(self):
        buyer = self.selected_buyer()
        if not buyer:
            self.detail_label.setText(
                "Choose a commodity and click Find Buyers to load UEX buyer locations."
            )
            self.copy_summary_button.setEnabled(False)
            return

        self.detail_label.setText(self.build_route_summary(buyer))
        self.copy_summary_button.setEnabled(True)

    def build_route_summary(self, buyer):
        return (
            f"Commodity: {buyer.commodity}\n"
            f"Sell to: {buyer.location}\n"
            f"Terminal: {buyer.terminal}\n"
            f"Sell price: {self.format_auec(buyer.sell_price)} / SCU\n"
            f"Quantity context: {self.format_number(buyer.quantity_scu)} SCU\n"
            "Quality: N/A\n"
            f"Source: {buyer.source}\n"
            f"Updated: {format_best_buyer_age(buyer)}\n"
            "Notes: Best Buyer ranks public sell prices only. It does not invent buy-side cost or profit data."
        )

    def copy_route_summary(self):
        buyer = self.selected_buyer()
        if not buyer:
            return

        copy_to_clipboard(self.build_route_summary(buyer))
        self.status_label.setText("Buyer summary copied to clipboard.")

    def selected_buyer(self):
        row = self.buyers_table.currentRow()
        if row < 0:
            return self.buyers[0] if self.buyers else None

        item = self.buyers_table.item(row, 0)
        if not item:
            return None

        index = item.data(ROW_ROLE)
        if index is None or index >= len(self.buyers):
            return None

        return self.buyers[index]

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
