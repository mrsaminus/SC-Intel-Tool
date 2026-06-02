from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.wikelo_client import WIKELO_SOURCE_URL, fetch_wikelo_items

from .table_utils import configure_readable_table_columns
from .workers import BackgroundTaskMixin


SORT_ROLE = Qt.UserRole + 1


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


class WikeloItemsTab(BackgroundTaskMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.wikelo_items = []
        self.visible_wikelo_items = []
        self.wikelo_refresh_running = False

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_module_header(
            "Wikelo Items",
            "Live Wikelo mission, trade-in and reward browser from the public Wikelo spreadsheet.",
        ))

        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self.build_wikelo_search_panel(), 3)
        content.addWidget(self.build_wikelo_detail_panel(), 2)
        layout.addLayout(content, 1)

        self.setLayout(layout)
        self.connect_signals()
        self.populate_wikelo_results()
        self.update_selected_wikelo_panel()
        self.refresh_wikelo_items(silent=True)

    def build_wikelo_search_panel(self):
        card = self.create_filter_card("WIKELO ITEM SEARCH")
        layout = card.layout()

        row = QHBoxLayout()
        self.wikelo_search_input = QLineEdit()
        self.wikelo_search_input.setPlaceholderText("Search Wikelo item, mission, material or reward...")
        self.wikelo_category_filter = QComboBox()
        self.wikelo_category_filter.addItem("All categories")
        row.addWidget(self.wikelo_search_input, 1)
        row.addWidget(self.wikelo_category_filter)
        layout.addLayout(row)

        button_row = QHBoxLayout()
        self.refresh_wikelo_button = QPushButton("Refresh Wikelo Data")
        self.open_wikelo_source_button = QPushButton("Open Wikelo Source")
        button_row.addWidget(self.refresh_wikelo_button)
        button_row.addWidget(self.open_wikelo_source_button)
        layout.addLayout(button_row)

        self.wikelo_status_label = QLabel("Loading Wikelo spreadsheet data...")
        self.wikelo_status_label.setObjectName("moduleSubtitle")
        self.wikelo_status_label.setWordWrap(True)
        layout.addWidget(self.wikelo_status_label)

        self.wikelo_results_table = self.create_table([
            "Item Name",
            "Category",
            "Type",
            "Reward / Method",
            "Required Materials",
        ])
        configure_readable_table_columns(self.wikelo_results_table, min_width=120, max_width=360, stretch_last=True)
        layout.addWidget(self.wikelo_results_table, 1)

        self.wikelo_empty_label = self.create_empty_state("No Wikelo items loaded yet.")
        layout.addWidget(self.wikelo_empty_label)
        return card

    def build_wikelo_detail_panel(self):
        card = self.create_filter_card("WIKELO DETAILS")
        layout = card.layout()

        self.selected_wikelo_name_label = QLabel("No Wikelo item selected")
        self.selected_wikelo_name_label.setObjectName("orgName")
        self.selected_wikelo_meta_label = QLabel("")
        self.selected_wikelo_meta_label.setObjectName("moduleSubtitle")
        self.selected_wikelo_mission_label = QLabel("")
        self.selected_wikelo_mission_label.setObjectName("valueText")
        self.selected_wikelo_mission_label.setWordWrap(True)
        self.selected_wikelo_reward_label = QLabel("")
        self.selected_wikelo_reward_label.setObjectName("valueText")
        self.selected_wikelo_reward_label.setWordWrap(True)
        self.selected_wikelo_location_label = QLabel("")
        self.selected_wikelo_location_label.setObjectName("moduleSubtitle")
        self.selected_wikelo_location_label.setWordWrap(True)

        layout.addWidget(self.selected_wikelo_name_label)
        layout.addWidget(self.selected_wikelo_meta_label)
        layout.addWidget(self.selected_wikelo_mission_label)
        layout.addWidget(self.selected_wikelo_reward_label)
        layout.addWidget(self.selected_wikelo_location_label)

        button_row = QHBoxLayout()
        self.open_selected_wikelo_source_button = QPushButton("Open Selected Item Source")
        self.open_selected_wikelo_source_button.clicked.connect(self.open_selected_wikelo_source)
        button_row.addWidget(self.open_selected_wikelo_source_button)
        layout.addLayout(button_row)

        self.wikelo_requirements_table = self.create_table([
            "Required Item / Material",
            "Qty",
            "Source",
        ])
        configure_readable_table_columns(self.wikelo_requirements_table, min_width=110, max_width=420, stretch_last=True)
        layout.addWidget(self.wikelo_requirements_table, 1)

        self.wikelo_notes_label = QLabel("")
        self.wikelo_notes_label.setObjectName("moduleSubtitle")
        self.wikelo_notes_label.setWordWrap(True)
        layout.addWidget(self.wikelo_notes_label)
        return card

    def connect_signals(self):
        self.wikelo_search_input.textChanged.connect(self.populate_wikelo_results)
        self.wikelo_category_filter.currentTextChanged.connect(self.populate_wikelo_results)
        self.refresh_wikelo_button.clicked.connect(self.refresh_wikelo_items)
        self.open_wikelo_source_button.clicked.connect(self.open_wikelo_source)
        self.wikelo_results_table.itemSelectionChanged.connect(self.update_selected_wikelo_panel)

    def refresh_wikelo_items(self, silent=False):
        if self.wikelo_refresh_running:
            return

        self.wikelo_refresh_running = True
        self.refresh_wikelo_button.setEnabled(False)
        self.refresh_wikelo_button.setText("Refreshing...")
        self.wikelo_status_label.setText("Loading current Wikelo spreadsheet data...")

        self.start_background_task(
            fetch_wikelo_items,
            self.on_wikelo_items_loaded,
            lambda exc: self.on_wikelo_items_error(exc, silent),
            self.finish_wikelo_refresh,
        )

    def on_wikelo_items_loaded(self, items):
        self.wikelo_items = list(items)
        self.refresh_category_filter()
        self.wikelo_status_label.setText(
            f"Loaded {len(self.wikelo_items)} Wikelo rows from the public spreadsheet. Data is in-memory only."
        )
        self.populate_wikelo_results()

    def on_wikelo_items_error(self, exc, silent=False):
        self.wikelo_status_label.setText(f"Wikelo data refresh failed: {exc}")
        if not silent:
            QMessageBox.warning(self, "Wikelo refresh failed", str(exc))

    def finish_wikelo_refresh(self):
        self.wikelo_refresh_running = False
        self.refresh_wikelo_button.setEnabled(True)
        self.refresh_wikelo_button.setText("Refresh Wikelo Data")

    def refresh_category_filter(self):
        current = self.wikelo_category_filter.currentText()
        categories = ["All categories", *sorted({item.category for item in self.wikelo_items})]
        self.wikelo_category_filter.blockSignals(True)
        self.wikelo_category_filter.clear()
        self.wikelo_category_filter.addItems(categories)
        if current in categories:
            self.wikelo_category_filter.setCurrentText(current)
        self.wikelo_category_filter.blockSignals(False)

    def populate_wikelo_results(self):
        query = self.wikelo_search_input.text().strip().lower()
        category = self.wikelo_category_filter.currentText()
        self.visible_wikelo_items = [
            item
            for item in self.wikelo_items
            if self.matches_wikelo_filters(item, query, category)
        ]

        self.wikelo_results_table.setUpdatesEnabled(False)
        self.wikelo_results_table.setSortingEnabled(False)
        try:
            self.wikelo_results_table.clearSelection()
            self.wikelo_results_table.setRowCount(len(self.visible_wikelo_items))
            for row_index, item in enumerate(self.visible_wikelo_items):
                values = [
                    item.item_name,
                    item.category,
                    item.item_type,
                    item.reward_method,
                    len(item.requirements),
                ]
                for column_index, value in enumerate(values):
                    table_item = SortableTableWidgetItem(str(value))
                    table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                    table_item.setData(Qt.UserRole, row_index)
                    table_item.setData(SORT_ROLE, value)
                    table_item.setToolTip(str(value))
                    if column_index == 4:
                        table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        table_item.setForeground(QColor("#68e6a5" if value else "#7bb9c8"))
                    self.wikelo_results_table.setItem(row_index, column_index, table_item)
            configure_readable_table_columns(self.wikelo_results_table, min_width=120, max_width=360, stretch_last=True)
        finally:
            self.wikelo_results_table.setSortingEnabled(True)
            self.wikelo_results_table.setUpdatesEnabled(True)

        self.wikelo_empty_label.setVisible(not self.visible_wikelo_items)
        self.wikelo_empty_label.setText(
            "No Wikelo items match the current filters." if self.wikelo_items else "No Wikelo items loaded yet."
        )
        self.update_selected_wikelo_panel()

    def matches_wikelo_filters(self, item, query, category):
        if category != "All categories" and item.category != category:
            return False
        if not query:
            return True

        parts = [
            item.item_name,
            item.category,
            item.item_type,
            item.reward_method,
            item.mission_name,
            item.reward_item,
            item.location,
            item.source_sheet,
            item.notes,
        ]
        parts.extend(requirement.name for requirement in item.requirements)
        return query in " ".join(str(part) for part in parts if part).lower()

    def update_selected_wikelo_panel(self):
        item = self.selected_wikelo_item()
        self.open_selected_wikelo_source_button.setEnabled(item is not None)
        if not item:
            self.selected_wikelo_name_label.setText("No Wikelo item selected")
            self.selected_wikelo_meta_label.setText("")
            self.selected_wikelo_mission_label.setText("")
            self.selected_wikelo_reward_label.setText("")
            self.selected_wikelo_location_label.setText("")
            self.wikelo_requirements_table.setRowCount(0)
            self.wikelo_notes_label.setText("")
            return

        self.selected_wikelo_name_label.setText(item.item_name)
        self.selected_wikelo_meta_label.setText(
            f"{item.category} | {item.item_type} | Source: {item.source_sheet}"
        )
        self.selected_wikelo_mission_label.setText(f"Mission: {item.mission_name or 'N/A'}")
        self.selected_wikelo_reward_label.setText(f"Reward item: {item.reward_item or item.item_name}")
        location_text = f"Location/System: {item.location}"
        if item.updated:
            location_text = f"{location_text} | Updated: {item.updated}"
        self.selected_wikelo_location_label.setText(location_text)
        self.populate_requirement_rows(item)
        self.wikelo_notes_label.setText(item.notes[:900] if item.notes else "")

    def populate_requirement_rows(self, item):
        self.wikelo_requirements_table.setSortingEnabled(False)
        self.wikelo_requirements_table.setRowCount(len(item.requirements))
        for row_index, requirement in enumerate(item.requirements):
            values = [
                requirement.name,
                requirement.quantity,
                requirement.source or "N/A",
            ]
            for column_index, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                table_item.setToolTip(str(value))
                if column_index == 1:
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.wikelo_requirements_table.setItem(row_index, column_index, table_item)

        configure_readable_table_columns(
            self.wikelo_requirements_table,
            min_width=110,
            max_width=420,
            stretch_last=True,
        )
        self.wikelo_requirements_table.setSortingEnabled(True)

    def selected_wikelo_item(self):
        row = self.wikelo_results_table.currentRow()
        if row < 0:
            return None
        table_item = self.wikelo_results_table.item(row, 0)
        if not table_item:
            return None
        index = table_item.data(Qt.UserRole)
        if index is None or index >= len(self.visible_wikelo_items):
            return None

        return self.visible_wikelo_items[index]

    def open_wikelo_source(self):
        QDesktopServices.openUrl(QUrl(WIKELO_SOURCE_URL))

    def open_selected_wikelo_source(self):
        item = self.selected_wikelo_item()
        QDesktopServices.openUrl(QUrl(item.source_url if item else WIKELO_SOURCE_URL))

    def create_module_header(self, title, subtitle):
        card = QFrame()
        card.setObjectName("playerCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("moduleHeading")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("moduleSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        card.setLayout(layout)
        return card

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

    def create_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSortingEnabled(True)
        configure_readable_table_columns(table, stretch_last=True)
        return table

    def create_empty_state(self, text):
        label = QLabel(text)
        label.setObjectName("emptyState")
        label.setAlignment(Qt.AlignCenter)
        return label
