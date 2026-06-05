from PySide6.QtCore import Qt
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

from app.trading_storage import (
    clear_recent_trading_routes,
    delete_saved_trading_route,
    get_recent_trading_routes,
    get_saved_trading_routes,
)

from ..table_utils import configure_readable_table_columns
from .route_quality import copy_to_clipboard
from .route_summary import format_auec, format_route_summary, format_scu


SORT_ROLE = Qt.UserRole + 1
ROW_ROLE = Qt.UserRole + 2


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


class SavedRoutesTab(QWidget):
    def __init__(self):
        super().__init__()

        self.saved_routes = []
        self.recent_routes = []
        self.visible_saved_routes = []
        self.visible_recent_routes = []
        self.current_source = "saved"

        self.build_ui()
        self.connect_signals()
        self.refresh_routes()

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_header())
        layout.addWidget(self.create_controls())

        table_row = QHBoxLayout()
        table_row.setSpacing(12)
        table_row.addWidget(self.create_saved_panel(), 1)
        table_row.addWidget(self.create_recent_panel(), 1)
        layout.addLayout(table_row, 1)

        self.detail_label = QLabel("Select a saved or recent route to see details.")
        self.detail_label.setObjectName("valueText")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.copy_summary_button = QPushButton("Copy Summary")
        self.copy_summary_button.setEnabled(False)
        self.delete_saved_button = QPushButton("Delete Saved")
        self.delete_saved_button.setEnabled(False)
        self.clear_recent_button = QPushButton("Clear Recent")
        button_row.addWidget(self.copy_summary_button)
        button_row.addWidget(self.delete_saved_button)
        button_row.addWidget(self.clear_recent_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.status_label = QLabel("Saved and recent Trading routes are stored locally only.")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def create_header(self):
        header = QFrame()
        header.setObjectName("playerCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title = QLabel("Saved Routes")
        title.setObjectName("moduleHeading")
        subtitle = QLabel(
            "Local saved and recent trade routes. Nothing is synced or sent anywhere."
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
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter saved/recent routes...")
        self.refresh_button = QPushButton("Refresh")
        layout.addWidget(self.search_input, 1)
        layout.addWidget(self.refresh_button)

        card.setLayout(layout)
        return card

    def create_saved_panel(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        title = QLabel("SAVED ROUTES")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.saved_table = self.create_table()
        layout.addWidget(self.saved_table, 1)

        self.saved_empty_label = QLabel("No saved routes yet.")
        self.saved_empty_label.setObjectName("emptyState")
        self.saved_empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.saved_empty_label)

        card.setLayout(layout)
        return card

    def create_recent_panel(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        title = QLabel("RECENT ROUTES")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.recent_table = self.create_table()
        layout.addWidget(self.recent_table, 1)

        self.recent_empty_label = QLabel("No recent routes yet.")
        self.recent_empty_label.setObjectName("emptyState")
        self.recent_empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.recent_empty_label)

        card.setLayout(layout)
        return card

    def create_table(self):
        table = QTableWidget(0, 8)
        table.setHorizontalHeaderLabels([
            "Commodity",
            "Buy",
            "Sell",
            "Profit / SCU",
            "Cargo",
            "Total Profit",
            "Quality",
            "Source",
        ])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        configure_readable_table_columns(table, min_width=110, max_width=360, stretch_last=True)
        return table

    def connect_signals(self):
        self.search_input.textChanged.connect(self.populate_tables)
        self.refresh_button.clicked.connect(self.refresh_routes)
        self.copy_summary_button.clicked.connect(self.copy_summary)
        self.delete_saved_button.clicked.connect(self.delete_selected_saved)
        self.clear_recent_button.clicked.connect(self.clear_recent)
        self.saved_table.itemSelectionChanged.connect(lambda: self.on_selection_changed("saved"))
        self.recent_table.itemSelectionChanged.connect(lambda: self.on_selection_changed("recent"))

    def refresh_routes(self):
        self.saved_routes = get_saved_trading_routes()
        self.recent_routes = get_recent_trading_routes()
        self.populate_tables()
        self.status_label.setText(
            f"Loaded {len(self.saved_routes)} saved routes and {len(self.recent_routes)} recent routes."
        )

    def populate_tables(self):
        query = self.search_input.text().strip().lower()
        self.visible_saved_routes = [
            route for route in self.saved_routes
            if self.matches_query(route, query)
        ]
        self.visible_recent_routes = [
            route for route in self.recent_routes
            if self.matches_query(route, query)
        ]
        self.populate_table(self.saved_table, self.visible_saved_routes)
        self.populate_table(self.recent_table, self.visible_recent_routes)
        self.saved_empty_label.setVisible(not self.visible_saved_routes)
        self.recent_empty_label.setVisible(not self.visible_recent_routes)
        self.update_details()

    def populate_table(self, table, routes):
        sorting_enabled = table.isSortingEnabled()
        table.setSortingEnabled(False)
        table.setRowCount(len(routes))

        for row_index, route in enumerate(routes):
            values = [
                route.commodity,
                route.buy_location,
                route.sell_location,
                format_auec(route.profit_per_scu),
                format_scu(route.cargo_scu),
                format_auec(route.total_profit),
                route.quality,
                route.source,
            ]
            sort_values = [
                route.commodity,
                route.buy_location,
                route.sell_location,
                route.profit_per_scu,
                route.cargo_scu,
                route.total_profit,
                route.quality,
                route.source,
            ]
            for col_index, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setData(SORT_ROLE, sort_values[col_index])
                item.setData(ROW_ROLE, row_index)
                if col_index in (3, 4, 5):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(row_index, col_index, item)

        table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(table, min_width=110, max_width=360, stretch_last=True)

    def on_selection_changed(self, source):
        self.current_source = source
        if source == "saved":
            self.recent_table.blockSignals(True)
            self.recent_table.clearSelection()
            self.recent_table.blockSignals(False)
        else:
            self.saved_table.blockSignals(True)
            self.saved_table.clearSelection()
            self.saved_table.blockSignals(False)
        self.update_details()

    def update_details(self):
        route = self.selected_route()
        if not route:
            self.detail_label.setText("Select a saved or recent route to see details.")
            self.copy_summary_button.setEnabled(False)
            self.delete_saved_button.setEnabled(False)
            return

        self.detail_label.setText(format_route_summary(route))
        self.copy_summary_button.setEnabled(True)
        self.delete_saved_button.setEnabled(self.current_source == "saved")

    def selected_route(self):
        if self.current_source == "saved":
            return self.selected_route_from_table(self.saved_table, self.visible_saved_routes)
        return self.selected_route_from_table(self.recent_table, self.visible_recent_routes)

    def selected_route_from_table(self, table, routes):
        row = table.currentRow()
        if row < 0:
            return None
        item = table.item(row, 0)
        if not item:
            return None
        index = item.data(ROW_ROLE)
        if index is None or index >= len(routes):
            return None
        return routes[index]

    def copy_summary(self):
        route = self.selected_route()
        if not route:
            return
        copy_to_clipboard(format_route_summary(route))
        self.status_label.setText("Route summary copied to clipboard.")

    def delete_selected_saved(self):
        route = self.selected_route_from_table(self.saved_table, self.visible_saved_routes)
        if not route or route.id is None:
            return
        delete_saved_trading_route(route.id)
        self.refresh_routes()
        self.status_label.setText("Saved route deleted.")

    def clear_recent(self):
        count = clear_recent_trading_routes()
        self.refresh_routes()
        self.status_label.setText(f"Cleared {count} recent routes.")

    def matches_query(self, route, query):
        if not query:
            return True
        haystack = " ".join((
            route.source,
            route.commodity,
            route.buy_location,
            route.sell_location,
            route.quality,
            route.notes,
        )).lower()
        return query in haystack
