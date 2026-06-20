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

from ..sortable_table_item import ROW_ROLE, SORT_ROLE, SortableTableWidgetItem
from ..table_utils import configure_readable_table_columns
from ..workers import BackgroundTaskMixin
from .reference_data import get_trading_reference_service
from .route_quality import copy_to_clipboard
from .searchable_combo import configure_searchable_combo, set_combo_items


class CommoditiesTab(BackgroundTaskMixin, QWidget):
    def __init__(self, reference_service=None):
        super().__init__()

        self.reference_service = reference_service or get_trading_reference_service()
        self.commodities = []
        self.commodity_types = []
        self.visible_commodities = []

        self.build_ui()
        self.connect_signals()
        self.connect_reference_service()
        self.populate_table()
        self.update_details()

    def connect_reference_service(self):
        self.reference_service.loaded.connect(self.on_commodities_loaded)
        self.reference_service.error.connect(self.on_commodities_error)
        self.reference_service.state_changed.connect(self.on_reference_state_changed)
        if self.reference_service.data is not None:
            self.on_commodities_loaded(self.reference_service.data)
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
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(4)

        title = QLabel("Commodities")
        title.setObjectName("moduleHeading")
        subtitle = QLabel(
            "UEX commodity reference built from the latest public market price refresh."
        )
        subtitle.setObjectName("moduleSubtitle")
        subtitle.setWordWrap(True)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header.setLayout(header_layout)
        return header

    def create_browser_panel(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        title = QLabel("UEX COMMODITIES")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search commodity...")
        self.type_filter = QComboBox()
        configure_searchable_combo(self.type_filter)
        self.type_filter.addItem("All types")
        self.type_filter.setEnabled(False)
        self.type_filter.setToolTip(
            "Commodity type mapping is not available in current UEX price rows."
        )
        self.refresh_button = QPushButton("Refresh Reference Data")

        controls.addWidget(self.search_input, 1)
        controls.addWidget(self.type_filter)
        controls.addWidget(self.refresh_button)
        layout.addLayout(controls)

        self.status_label = QLabel("Loading UEX commodity data...")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.commodities_table = QTableWidget(0, 4)
        self.commodities_table.setHorizontalHeaderLabels([
            "Commodity Name",
            "Type / Category",
            "Flags",
            "Metadata",
        ])
        self.commodities_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.commodities_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.commodities_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.commodities_table.setAlternatingRowColors(True)
        self.commodities_table.setSortingEnabled(True)
        configure_readable_table_columns(self.commodities_table, min_width=120, max_width=360, stretch_last=True)
        layout.addWidget(self.commodities_table, 1)

        self.empty_label = QLabel("Loading commodity data...")
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

        title = QLabel("COMMODITY DETAILS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.detail_title_label = QLabel("No commodity selected")
        self.detail_title_label.setObjectName("moduleHeading")
        self.detail_title_label.setWordWrap(True)
        layout.addWidget(self.detail_title_label)

        self.detail_body_label = QLabel("")
        self.detail_body_label.setObjectName("valueText")
        self.detail_body_label.setWordWrap(True)
        layout.addWidget(self.detail_body_label)

        self.type_catalog_label = QLabel("Commodity type catalog not loaded.")
        self.type_catalog_label.setObjectName("moduleSubtitle")
        self.type_catalog_label.setWordWrap(True)
        layout.addWidget(self.type_catalog_label)

        self.copy_details_button = QPushButton("Copy Details")
        self.copy_details_button.setEnabled(False)
        layout.addWidget(self.copy_details_button)

        layout.addStretch(1)
        card.setLayout(layout)
        return card

    def connect_signals(self):
        self.refresh_button.clicked.connect(self.refresh_commodities)
        self.copy_details_button.clicked.connect(self.copy_details)
        self.search_input.textChanged.connect(self.populate_table)
        self.commodities_table.itemSelectionChanged.connect(self.update_details)

    def refresh_commodities(self):
        self.reference_service.refresh(force=True)

    def on_commodities_loaded(self, data):
        self.commodities = list(data.commodities)
        self.commodity_types = list(data.commodity_types)
        self.populate_type_catalog()
        source_note = ""
        if getattr(data, "source_error", ""):
            source_note = f" UEX refresh failed: {data.source_error}"
        self.status_label.setText(
            f"Loaded {len(self.commodities)} commodities and {len(self.commodity_types)} "
            f"commodity types from UEX reference rows.{source_note}"
        )
        self.populate_table()

    def on_commodities_error(self, exc):
        self.commodities = []
        self.commodity_types = []
        self.visible_commodities = []
        self.commodities_table.setRowCount(0)
        self.empty_label.setVisible(True)
        self.status_label.setText(f"Failed to load UEX commodities: {exc}")
        self.update_details()

    def on_reference_state_changed(self, state):
        if state == "loading":
            self.refresh_button.setEnabled(False)
            self.refresh_button.setText("Loading...")
            self.status_label.setText("Loading UEX commodity data...")
        else:
            self.refresh_button.setEnabled(True)
            self.refresh_button.setText("Refresh Reference Data")

    def populate_type_catalog(self):
        self.type_filter.blockSignals(True)
        set_combo_items(
            self.type_filter,
            ["All types", *(item_type.display_name for item_type in self.commodity_types)],
            current_text="All types",
        )
        self.type_filter.setEnabled(False)
        self.type_filter.blockSignals(False)

        if self.commodity_types:
            names = ", ".join(item_type.display_name for item_type in self.commodity_types[:8])
            suffix = ""
            if len(self.commodity_types) > 8:
                suffix = f" (+{len(self.commodity_types) - 8} more)"
            self.type_catalog_label.setText(
                f"Type catalog loaded: {names}{suffix}. "
                "The public commodity item data does not map commodities to these types."
            )
        else:
            self.type_catalog_label.setText("Commodity type catalog is not available in current UEX data.")

    def populate_table(self):
        query = self.search_input.text().strip().lower()
        self.visible_commodities = [
            commodity
            for commodity in self.commodities
            if not query or query in commodity.name.lower()
        ]

        sorting_enabled = self.commodities_table.isSortingEnabled()
        self.commodities_table.setSortingEnabled(False)
        self.commodities_table.setRowCount(len(self.visible_commodities))

        for row_index, commodity in enumerate(self.visible_commodities):
            values = [
                commodity.name,
                "N/A",
                "N/A",
                "Name only",
            ]
            for col_index, value in enumerate(values):
                item = SortableTableWidgetItem(value)
                item.setData(SORT_ROLE, value)
                item.setData(ROW_ROLE, row_index)
                self.commodities_table.setItem(row_index, col_index, item)

        self.commodities_table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(self.commodities_table, min_width=120, max_width=360, stretch_last=True)
        self.empty_label.setVisible(not self.visible_commodities)
        if self.visible_commodities:
            self.update_details()
        else:
            self.detail_title_label.setText("No commodity selected")
            if self.commodities:
                self.detail_body_label.setText("No commodities match the current search.")
            else:
                self.detail_body_label.setText("Loading commodity names from UEX reference rows.")
            self.copy_details_button.setEnabled(False)

    def update_details(self):
        commodity = self.selected_commodity()
        if not commodity:
            if not self.commodities:
                self.detail_title_label.setText("No commodity selected")
                self.detail_body_label.setText("Loading commodity names from UEX reference rows.")
            self.copy_details_button.setEnabled(False)
            return

        self.detail_title_label.setText(commodity.name)
        self.detail_body_label.setText(self.build_details_text(commodity))
        self.copy_details_button.setEnabled(True)

    def build_details_text(self, commodity):
        return (
            f"Commodity: {commodity.name}\n"
            "Type / category: N/A\n"
            "Flags: N/A\n"
            "Metadata: UEX price rows expose commodity name and market prices.\n"
            "Source: UEX\n"
            "Note: use UEX Trading, Trade Routes or Best Buyer for current market results."
        )

    def copy_details(self):
        commodity = self.selected_commodity()
        if not commodity:
            return
        copy_to_clipboard(self.build_details_text(commodity))
        self.status_label.setText("Commodity details copied to clipboard.")

    def selected_commodity(self):
        row = self.commodities_table.currentRow()
        if row < 0:
            return self.visible_commodities[0] if self.visible_commodities else None

        item = self.commodities_table.item(row, 0)
        if not item:
            return None

        index = item.data(ROW_ROLE)
        if index is None or index >= len(self.visible_commodities):
            return None

        return self.visible_commodities[index]
