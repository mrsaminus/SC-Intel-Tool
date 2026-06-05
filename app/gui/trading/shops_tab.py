from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from ..table_utils import configure_readable_table_columns
from ..workers import BackgroundTaskMixin
from .reference_data import get_trading_reference_service
from .route_quality import copy_to_clipboard


SORT_ROLE = Qt.UserRole + 1
ROW_ROLE = Qt.UserRole + 2
SC_TRADE_SHOPS_URL = "https://sc-trade.tools/shops"


class SortableTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        left = self.data(SORT_ROLE)
        right = other.data(SORT_ROLE) if isinstance(other, QTableWidgetItem) else None
        if left is not None or right is not None:
            return str(left).lower() < str(right).lower()

        return super().__lt__(other)


class ShopsTab(BackgroundTaskMixin, QWidget):
    def __init__(self, reference_service=None):
        super().__init__()

        self.reference_service = reference_service or get_trading_reference_service()
        self.shops = []
        self.locations = []
        self.visible_shops = []

        self.build_ui()
        self.connect_signals()
        self.connect_reference_service()
        self.populate_table()
        self.update_details()

    def connect_reference_service(self):
        self.reference_service.loaded.connect(self.on_shops_loaded)
        self.reference_service.error.connect(self.on_shops_error)
        self.reference_service.state_changed.connect(self.on_reference_state_changed)
        if self.reference_service.data is not None:
            self.on_shops_loaded(self.reference_service.data)
        elif self.reference_service.is_loading:
            self.on_reference_state_changed("loading")
        else:
            self.reference_service.ensure_loaded()

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_header())

        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self.create_browser_panel(), 3)
        content.addWidget(self.create_details_panel(), 2)
        layout.addLayout(content, 1)

        self.setLayout(layout)

    def create_header(self):
        header = QFrame()
        header.setObjectName("playerCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title = QLabel("Shops")
        title.setObjectName("moduleHeading")
        subtitle = QLabel(
            "Token-free SC Trade Tools commodity shop and location reference."
        )
        subtitle.setObjectName("moduleSubtitle")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        header.setLayout(layout)
        return header

    def create_browser_panel(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        title = QLabel("SC TRADE TOOLS SHOPS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search shop, system, location or type...")
        self.refresh_button = QPushButton("Refresh Reference Data")
        self.open_source_button = QPushButton("Open Source")
        controls.addWidget(self.search_input, 1)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.open_source_button)
        layout.addLayout(controls)

        self.status_label = QLabel("Loading token-free SC Trade Tools shop data...")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.shops_table = QTableWidget(0, 5)
        self.shops_table.setHorizontalHeaderLabels([
            "Shop",
            "System",
            "Location",
            "Type",
            "Hierarchy / Path",
        ])
        self.shops_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.shops_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.shops_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.shops_table.setAlternatingRowColors(True)
        self.shops_table.setSortingEnabled(True)
        configure_readable_table_columns(self.shops_table, min_width=120, max_width=420, stretch_last=True)
        layout.addWidget(self.shops_table, 1)

        self.empty_label = QLabel("Loading shop data...")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        card.setLayout(layout)
        return card

    def create_details_panel(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        title = QLabel("SHOP DETAILS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.detail_title_label = QLabel("No shop selected")
        self.detail_title_label.setObjectName("moduleHeading")
        self.detail_title_label.setWordWrap(True)
        layout.addWidget(self.detail_title_label)

        self.detail_body_label = QLabel("")
        self.detail_body_label.setObjectName("valueText")
        self.detail_body_label.setWordWrap(True)
        layout.addWidget(self.detail_body_label)

        self.copy_details_button = QPushButton("Copy Details")
        self.copy_details_button.setEnabled(False)
        layout.addWidget(self.copy_details_button)

        layout.addStretch(1)
        card.setLayout(layout)
        return card

    def connect_signals(self):
        self.refresh_button.clicked.connect(self.refresh_shops)
        self.open_source_button.clicked.connect(self.open_source)
        self.copy_details_button.clicked.connect(self.copy_details)
        self.search_input.textChanged.connect(self.populate_table)
        self.shops_table.itemSelectionChanged.connect(self.update_details)

    def refresh_shops(self):
        self.reference_service.refresh(force=True)

    def on_shops_loaded(self, data):
        self.shops = list(data.shops)
        self.locations = list(data.locations)
        self.status_label.setText(
            f"Loaded {len(self.shops)} commodity shops and {len(self.locations)} "
            "known trade locations from SC Trade Tools."
        )
        self.populate_table()

    def on_shops_error(self, exc):
        self.shops = []
        self.locations = []
        self.visible_shops = []
        self.shops_table.setRowCount(0)
        self.empty_label.setVisible(True)
        self.status_label.setText(f"Failed to load SC Trade Tools shops: {exc}")
        self.update_details()

    def on_reference_state_changed(self, state):
        if state == "loading":
            self.refresh_button.setEnabled(False)
            self.refresh_button.setText("Loading...")
            self.status_label.setText("Loading token-free SC Trade Tools shop data...")
        else:
            self.refresh_button.setEnabled(True)
            self.refresh_button.setText("Refresh Reference Data")

    def populate_table(self):
        query = self.search_input.text().strip().lower()
        self.visible_shops = [
            shop
            for shop in self.shops
            if not query or query in self.shop_haystack(shop)
        ]

        sorting_enabled = self.shops_table.isSortingEnabled()
        self.shops_table.setSortingEnabled(False)
        self.shops_table.setRowCount(len(self.visible_shops))

        for row_index, shop in enumerate(self.visible_shops):
            values = [
                shop.display_name,
                shop.system,
                shop.location,
                shop.category,
                shop.hierarchy,
            ]
            for col_index, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setData(SORT_ROLE, value)
                item.setData(ROW_ROLE, row_index)
                self.shops_table.setItem(row_index, col_index, item)

        self.shops_table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(self.shops_table, min_width=120, max_width=420, stretch_last=True)
        self.empty_label.setVisible(not self.visible_shops)
        self.update_details()

    def update_details(self):
        shop = self.selected_shop()
        if not shop:
            self.detail_title_label.setText("No shop selected")
            if self.shops:
                self.detail_body_label.setText("No shops match the current search.")
            else:
                self.detail_body_label.setText("Loading commodity shop names from SC Trade Tools.")
            self.copy_details_button.setEnabled(False)
            return

        self.detail_title_label.setText(shop.display_name)
        self.detail_body_label.setText(self.build_details_text(shop))
        self.copy_details_button.setEnabled(True)

    def build_details_text(self, shop):
        return (
            f"Shop: {shop.display_name}\n"
            f"Full path: {shop.name}\n"
            f"System: {shop.system}\n"
            f"Location: {shop.location}\n"
            f"Type: {shop.category}\n"
            f"Hierarchy: {shop.hierarchy}\n"
            "Source: SC Trade Tools\n"
            "Note: detailed shop transaction data requires a SC Trade Tools token."
        )

    def copy_details(self):
        shop = self.selected_shop()
        if not shop:
            return
        copy_to_clipboard(self.build_details_text(shop))
        self.status_label.setText("Shop details copied to clipboard.")

    def selected_shop(self):
        row = self.shops_table.currentRow()
        if row < 0:
            return self.visible_shops[0] if self.visible_shops else None

        item = self.shops_table.item(row, 0)
        if not item:
            return None

        index = item.data(ROW_ROLE)
        if index is None or index >= len(self.visible_shops):
            return None

        return self.visible_shops[index]

    def shop_haystack(self, shop):
        return " ".join((
            shop.name,
            shop.display_name,
            shop.system,
            shop.location,
            shop.category,
            shop.hierarchy,
        )).lower()

    def open_source(self):
        QDesktopServices.openUrl(QUrl(SC_TRADE_SHOPS_URL))
