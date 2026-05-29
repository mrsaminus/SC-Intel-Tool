from dataclasses import replace
from datetime import datetime, timedelta
from itertools import combinations

import requests
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database import (
    clear_lookup_history,
    delete_lookup_history,
    get_lookup_history,
    get_note,
    init_db,
    save_lookup,
    save_note,
)
from app.cstone_client import (
    CSTONE_HOME_URL,
    CStoneError,
    cstone_category_labels,
    cstone_category_url,
    fetch_cstone_item_locations,
    fetch_cstone_items,
)
from app.mining_data import load_mining_data
from app.rsi_lookup import RSILookupError, lookup_player
from app.scfocus_client import SCFOCUS_SHIPS_URL, WIKELO_CATEGORY, fetch_scfocus_ship_items
from app.uex_client import UEXError, fetch_commodity_sell_prices

from .constants import (
    GEM_SELLING_MATERIALS,
    IMAGE_HEADERS,
    REFINERY_METHODS,
    REFINERY_METHOD_YIELD_FALLBACKS,
    REFINERY_STATIONS,
    SALVAGE_REFINERY_DETAILS,
    SALVAGE_REFINERY_MATERIALS,
    SHIP_ORE_MATERIALS,
    SHIP_REFINERY_MATERIALS,
    TAG_COLORS,
)
from .workers import BackgroundTaskMixin


class ItemFinderTab(BackgroundTaskMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.finder_items = []
        self.visible_finder_items = []
        self.finder_locations = []
        self.current_finder_item_id = None
        self.finder_last_refresh = None
        self.finder_refresh_interval = timedelta(hours=4)
        self.availability_counts = {}
        self.auto_availability_limit = 25
        self.availability_auto_load_scheduled = False
        self.auto_loading_availability = False
        self.finder_refresh_running = False
        self.item_locations_loading = False
        self.item_location_request_id = 0
        self.finder_refresh_timer = QTimer(self)
        self.finder_refresh_timer.setInterval(int(self.finder_refresh_interval.total_seconds() * 1000))
        self.finder_refresh_timer.timeout.connect(lambda: self.refresh_finder_items(silent=True))
        self.item_filter_timer = self.create_debounce_timer(self.populate_item_results)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_module_header(
            "Item Finder",
            "Live lookup for equipment, ship sale/rental locations and other SC shopping intel. No source data is stored locally.",
        ))

        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self.build_item_search_panel(), 3)
        content.addWidget(self.build_item_detail_panel(), 2)
        layout.addLayout(content, 1)

        self.setLayout(layout)
        self.connect_signals()
        self.populate_item_results()
        self.update_selected_item_panel()

    def build_item_search_panel(self):
        card = self.create_filter_card("LIVE ITEM SEARCH")
        layout = card.layout()

        row = QHBoxLayout()
        self.item_search_input = QLineEdit()
        self.item_search_input.setPlaceholderText("Search gear, ship, location or effect...")
        self.item_category_filter = self.create_combo([
            "All categories",
            "Ships for Sale",
            "Ships for Rent",
            WIKELO_CATEGORY,
            "Special Acquisition Ships",
            *cstone_category_labels(),
        ])
        row.addWidget(self.item_search_input, 1)
        row.addWidget(self.item_category_filter)
        layout.addLayout(row)

        button_row = QHBoxLayout()
        self.refresh_finder_items_button = QPushButton("Refresh Live Data")
        self.open_source_home_button = QPushButton("Open Source")
        self.open_source_category_button = QPushButton("Open Category")
        button_row.addWidget(self.refresh_finder_items_button)
        button_row.addWidget(self.open_source_home_button)
        button_row.addWidget(self.open_source_category_button)
        layout.addLayout(button_row)

        self.finder_status_label = QLabel(
            "Press Enter to load live data. First load can take a while and the app may look frozen briefly; Not Sold Cornerstone items are skipped."
        )
        self.finder_status_label.setObjectName("moduleSubtitle")
        self.finder_status_label.setWordWrap(True)
        layout.addWidget(self.finder_status_label)

        self.item_results_table = self.create_table([
            "Item",
            "Category",
            "Type",
            "Availability",
            "Summary",
        ])
        self.item_results_table.horizontalHeader().setStretchLastSection(False)
        self.item_results_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        layout.addWidget(self.item_results_table, 1)
        self.item_empty_label = self.create_empty_state("No live item data loaded yet.")
        layout.addWidget(self.item_empty_label)
        return card

    def build_item_detail_panel(self):
        card = self.create_filter_card("BUY LOCATIONS")
        layout = card.layout()

        self.selected_item_name_label = QLabel("No item selected")
        self.selected_item_name_label.setObjectName("orgName")
        self.selected_item_category_label = QLabel("")
        self.selected_item_category_label.setObjectName("moduleSubtitle")
        self.selected_item_effect_label = QLabel("")
        self.selected_item_effect_label.setObjectName("valueText")
        self.selected_item_effect_label.setWordWrap(True)
        layout.addWidget(self.selected_item_name_label)
        layout.addWidget(self.selected_item_category_label)
        layout.addWidget(self.selected_item_effect_label)

        button_row = QHBoxLayout()
        self.load_item_locations_button = QPushButton("Reload Locations")
        self.open_selected_item_button = QPushButton("Open Item")
        self.open_selected_location_button = QPushButton("Open Location")
        button_row.addWidget(self.load_item_locations_button)
        button_row.addWidget(self.open_selected_item_button)
        button_row.addWidget(self.open_selected_location_button)
        layout.addLayout(button_row)

        self.item_locations_table = self.create_table([
            "Location",
            "Price / Method",
            "Verified",
        ])
        layout.addWidget(self.item_locations_table, 1)
        self.item_location_empty_label = self.create_empty_state(
            "Select an item and load buy locations."
        )
        layout.addWidget(self.item_location_empty_label)
        return card

    def connect_signals(self):
        self.item_search_input.textChanged.connect(self.schedule_item_results_refresh)
        self.item_search_input.returnPressed.connect(self.ensure_finder_data_then_search)
        self.item_category_filter.currentTextChanged.connect(self.schedule_item_results_refresh)
        self.refresh_finder_items_button.clicked.connect(self.refresh_finder_items)
        self.open_source_home_button.clicked.connect(self.open_source_home)
        self.open_source_category_button.clicked.connect(self.open_selected_category)
        self.item_results_table.itemSelectionChanged.connect(self.on_selected_item_changed)
        self.item_results_table.cellDoubleClicked.connect(lambda row, column: self.load_selected_item_locations())
        self.item_locations_table.itemSelectionChanged.connect(self.update_location_action_state)
        self.load_item_locations_button.clicked.connect(self.load_selected_item_locations)
        self.open_selected_item_button.clicked.connect(self.open_selected_item)
        self.open_selected_location_button.clicked.connect(self.open_selected_location)

    def ensure_finder_data_then_search(self):
        self.item_filter_timer.stop()
        if self.finder_data_is_stale():
            self.refresh_finder_items()
            return

        self.populate_item_results()

    def finder_data_is_stale(self):
        if not self.finder_items or not self.finder_last_refresh:
            return True

        return datetime.now() - self.finder_last_refresh >= self.finder_refresh_interval

    def refresh_finder_items(self, silent=False):
        if self.finder_refresh_running:
            return

        self.finder_refresh_running = True
        self.refresh_finder_items_button.setEnabled(False)
        self.refresh_finder_items_button.setText("Refreshing...")

        def load_items():
            loaded_items = []
            failed = []
            try:
                loaded_items.extend(fetch_cstone_items())
            except (CStoneError, requests.RequestException, ValueError) as exc:
                failed.append(f"Cornerstone: {exc}")

            try:
                loaded_items.extend(fetch_scfocus_ship_items())
            except (requests.RequestException, ValueError) as exc:
                failed.append(f"SC Focus: {exc}")

            return {
                "loaded_items": loaded_items,
                "failed": failed,
                "silent": silent,
            }

        self.start_background_task(
            load_items,
            self.on_finder_items_refreshed,
            self.on_finder_items_refresh_error,
            self.finish_finder_items_refresh,
        )

    def on_finder_items_refreshed(self, result):
        loaded_items = result["loaded_items"]
        failed = result["failed"]
        silent = result["silent"]

        if loaded_items:
            self.finder_items = loaded_items
            self.finder_last_refresh = datetime.now()
            if not self.finder_refresh_timer.isActive():
                self.finder_refresh_timer.start()

        if failed:
            self.finder_status_label.setText(
                f"Loaded {len(self.finder_items)} rows with {len(failed)} source warning(s). "
                "Data is in-memory only."
            )
            if not silent:
                QMessageBox.warning(self, "Live refresh warning", "\n".join(failed))
        else:
            self.finder_status_label.setText(
                f"Loaded {len(self.finder_items)} live rows from Cornerstone and SC Focus. "
                "Data is in-memory only and will refresh every 4 hours."
            )

        self.populate_item_results()

    def on_finder_items_refresh_error(self, exc):
        self.finder_status_label.setText(f"Live data refresh failed: {exc}")
        QMessageBox.critical(self, "Live refresh failed", str(exc))

    def finish_finder_items_refresh(self):
        self.finder_refresh_running = False
        self.refresh_finder_items_button.setEnabled(True)
        self.refresh_finder_items_button.setText("Refresh Live Data")

    def populate_item_results(self):
        query = self.item_search_input.text().strip().lower()
        category_filter = self.item_category_filter.currentText()
        self.visible_finder_items = []

        for item in self.finder_items:
            if category_filter != "All categories" and item.category != category_filter:
                continue
            searchable = " ".join((
                item.name,
                item.source,
                item.category,
                item.item_type,
                item.availability,
                item.effect,
            )).lower()
            if query and query not in searchable:
                continue
            self.visible_finder_items.append(item)

        self.item_results_table.setUpdatesEnabled(False)
        self.item_results_table.setSortingEnabled(False)
        try:
            self.item_results_table.clearSelection()
            self.item_results_table.setRowCount(len(self.visible_finder_items))
            for row_index, item in enumerate(self.visible_finder_items):
                values = [
                    item.name,
                    item.category,
                    item.item_type,
                    self.display_item_availability(item),
                    item.effect,
                ]
                for col_index, value in enumerate(values):
                    table_item = QTableWidgetItem(str(value))
                    table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                    table_item.setData(Qt.UserRole, row_index)
                    table_item.setToolTip(str(value))
                    if col_index == 3:
                        table_item.setForeground(QColor("#68e6a5" if item.sold else "#7bb9c8"))
                    self.item_results_table.setItem(row_index, col_index, table_item)
            self.item_results_table.resizeColumnsToContents()
        finally:
            self.item_results_table.setSortingEnabled(True)
            self.item_results_table.setUpdatesEnabled(True)

        self.item_empty_label.setVisible(not self.visible_finder_items)
        if not self.finder_items:
            self.item_empty_label.setText("No live item data loaded yet.")
        else:
            self.item_empty_label.setText("No items match the current filters.")
        self.update_selected_item_panel()
        self.schedule_availability_autoload()

    def on_selected_item_changed(self):
        previous_item_id = self.current_finder_item_id
        item = self.selected_item()
        self.update_selected_item_panel()
        if item and item.item_id != previous_item_id:
            self.load_selected_item_locations()

    def display_item_availability(self, item):
        if item.source != "Cornerstone":
            return item.availability

        key = self.finder_item_key(item)
        if key in self.availability_counts:
            return self.location_count_text(self.availability_counts[key])

        pending = self.pending_visible_cornerstone_items()
        if len(pending) <= self.auto_availability_limit:
            return "Checking..."

        return "Filter more"

    def schedule_availability_autoload(self):
        if self.auto_loading_availability or self.availability_auto_load_scheduled:
            return

        pending = self.pending_visible_cornerstone_items()
        if not pending:
            return

        if len(pending) > self.auto_availability_limit:
            self.finder_status_label.setText(
                f"{len(pending)} visible Cornerstone items need location counts. "
                f"Keep filtering to {self.auto_availability_limit} or fewer items to load location counts automatically."
            )
            return

        self.availability_auto_load_scheduled = True
        QTimer.singleShot(0, self.auto_load_visible_availability)

    def auto_load_visible_availability(self):
        self.availability_auto_load_scheduled = False
        pending = self.pending_visible_cornerstone_items()
        if not pending or len(pending) > self.auto_availability_limit:
            return

        self.auto_loading_availability = True
        self.finder_status_label.setText(f"Loading availability for {len(pending)} visible rows...")

        def load_availability():
            results = []
            for item in pending:
                try:
                    locations = fetch_cstone_item_locations(item.detail_url)
                except (CStoneError, requests.RequestException, ValueError):
                    locations = []
                results.append((item, locations))
            return results

        self.start_background_task(
            load_availability,
            self.on_visible_availability_loaded,
            self.on_visible_availability_error,
            self.finish_visible_availability_load,
        )

    def on_visible_availability_loaded(self, results):
        selected = self.selected_item()
        selected_key = self.finder_item_key(selected) if selected else None
        for item, locations in results:
            self.set_item_availability_count(item, len(locations))
            if selected_key == self.finder_item_key(item):
                self.finder_locations = locations
                self.populate_location_rows()

        self.finder_status_label.setText("Availability loaded for visible rows.")

    def on_visible_availability_error(self, exc):
        self.finder_status_label.setText(f"Availability lookup failed: {exc}")

    def finish_visible_availability_load(self):
        self.auto_loading_availability = False
        self.schedule_availability_autoload()

    def pending_visible_cornerstone_items(self):
        pending = []
        seen = set()
        for item in self.visible_finder_items:
            key = self.finder_item_key(item)
            if item.source == "Cornerstone" and key not in self.availability_counts and key not in seen:
                pending.append(item)
                seen.add(key)

        return pending

    def update_selected_item_panel(self):
        item = self.selected_item()
        has_item = item is not None
        self.load_item_locations_button.setEnabled(has_item)
        self.open_selected_item_button.setEnabled(has_item)
        self.open_selected_location_button.setEnabled(bool(self.selected_location_url()))

        if not item:
            self.current_finder_item_id = None
            self.selected_item_name_label.setText("No item selected")
            self.selected_item_category_label.setText("")
            self.selected_item_effect_label.setText("")
            self.finder_locations = []
            self.item_locations_table.setRowCount(0)
            self.item_location_empty_label.setVisible(True)
            self.item_location_empty_label.setText("Select an item and load buy locations.")
            return

        if item.item_id != self.current_finder_item_id:
            self.current_finder_item_id = item.item_id
            self.finder_locations = []
            self.item_locations_table.setRowCount(0)
            self.item_location_empty_label.setVisible(True)
            self.item_location_empty_label.setText("Load buy locations for the selected item.")

        self.selected_item_name_label.setText(item.name)
        self.selected_item_category_label.setText(
            f"{item.category} | {item.item_type} | {self.display_item_availability(item)} | Source: {item.source}"
        )
        self.selected_item_effect_label.setText(item.effect)
        self.update_location_action_state()

    def load_selected_item_locations(self):
        item = self.selected_item()
        if not item:
            return

        self.item_location_request_id += 1
        request_id = self.item_location_request_id
        self.item_locations_loading = True
        self.load_item_locations_button.setEnabled(False)
        self.load_item_locations_button.setText("Loading...")

        if item.source == "SC Focus":
            if request_id == self.item_location_request_id:
                self.finder_locations = list(item.locations)
                self.populate_location_rows()
            self.finish_selected_item_locations_load(request_id)
            return

        def load_locations():
            return fetch_cstone_item_locations(item.detail_url)

        self.start_background_task(
            load_locations,
            lambda locations, requested_item=item, requested_id=request_id: self.on_selected_item_locations_loaded(
                requested_id,
                requested_item,
                locations,
            ),
            lambda exc, requested_item=item, requested_id=request_id: self.on_selected_item_locations_error(
                requested_id,
                requested_item,
                exc,
            ),
            lambda requested_id=request_id: self.finish_selected_item_locations_load(requested_id),
        )

    def on_selected_item_locations_loaded(self, request_id, requested_item, locations):
        if request_id != self.item_location_request_id:
            return

        self.set_item_availability_count(requested_item, len(locations))
        selected = self.selected_item()
        if selected and self.finder_item_key(selected) == self.finder_item_key(requested_item):
            self.finder_locations = locations
            self.populate_location_rows()

    def on_selected_item_locations_error(self, request_id, requested_item, exc):
        if request_id != self.item_location_request_id:
            return

        selected = self.selected_item()
        if selected and self.finder_item_key(selected) == self.finder_item_key(requested_item):
            QMessageBox.warning(self, "Location lookup failed", str(exc))
            self.finder_locations = []
            self.populate_location_rows()

    def finish_selected_item_locations_load(self, request_id=None):
        if request_id is not None and request_id != self.item_location_request_id:
            return

        self.item_locations_loading = False
        self.load_item_locations_button.setEnabled(bool(self.selected_item()))
        self.load_item_locations_button.setText("Reload Locations")

    def set_item_availability_count(self, item, location_count):
        if not item or item.source != "Cornerstone":
            return

        key = self.finder_item_key(item)
        availability = self.location_count_text(location_count)
        self.availability_counts[key] = location_count
        updated_item = replace(item, availability=availability)

        for item_index, visible_item in enumerate(self.visible_finder_items):
            if self.finder_item_key(visible_item) == key:
                self.visible_finder_items[item_index] = updated_item

        for full_index, full_item in enumerate(self.finder_items):
            if self.finder_item_key(full_item) == key:
                self.finder_items[full_index] = updated_item
                break

        self.update_visible_availability_cells(key, availability)
        selected = self.selected_item()
        if selected and self.finder_item_key(selected) == key:
            self.selected_item_category_label.setText(
                f"{updated_item.category} | {updated_item.item_type} | {updated_item.availability} | Source: {updated_item.source}"
            )

    def update_visible_availability_cells(self, key, availability):
        for row in range(self.item_results_table.rowCount()):
            item = self.item_results_table.item(row, 0)
            if not item:
                continue

            index = item.data(Qt.UserRole)
            if index is None or index >= len(self.visible_finder_items):
                continue

            visible_item = self.visible_finder_items[index]
            if self.finder_item_key(visible_item) == key:
                availability_item = self.item_results_table.item(row, 3)
                if availability_item:
                    availability_item.setText(availability)

    def finder_item_key(self, item):
        return (item.source, item.item_id)

    def location_count_text(self, location_count):
        return f"{location_count} location{'s' if location_count != 1 else ''}"

    def populate_location_rows(self):
        self.item_locations_table.setSortingEnabled(False)
        self.item_locations_table.clearSelection()
        self.item_locations_table.setRowCount(len(self.finder_locations))
        for row_index, location in enumerate(self.finder_locations):
            for col_index, value in enumerate((
                location.location,
                location.price,
                location.verified,
            )):
                table_item = QTableWidgetItem(str(value))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                table_item.setData(Qt.UserRole, row_index)
                table_item.setToolTip(str(value))
                if col_index == 1:
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.item_locations_table.setItem(row_index, col_index, table_item)

        self.item_locations_table.resizeColumnsToContents()
        self.item_locations_table.setSortingEnabled(True)
        self.item_location_empty_label.setVisible(not self.finder_locations)
        if self.finder_locations:
            self.item_locations_table.selectRow(0)
        self.update_location_action_state()

    def update_location_action_state(self):
        self.open_selected_location_button.setEnabled(bool(self.selected_location_url()))

    def selected_item(self):
        row = self.item_results_table.currentRow()
        if row < 0:
            return None

        item = self.item_results_table.item(row, 0)
        if not item:
            return None

        index = item.data(Qt.UserRole)
        if index is None or index >= len(self.visible_finder_items):
            return None

        return self.visible_finder_items[index]

    def selected_location_url(self):
        row = self.item_locations_table.currentRow()
        if row < 0:
            return None

        item = self.item_locations_table.item(row, 0)
        if not item:
            return None

        index = item.data(Qt.UserRole)
        if index is None or index >= len(self.finder_locations):
            return None

        return self.finder_locations[index].url

    def open_source_home(self):
        item = self.selected_item()
        if item and item.source == "SC Focus":
            QDesktopServices.openUrl(QUrl(SCFOCUS_SHIPS_URL))
            return

        if not item and self.is_scfocus_ship_category(self.item_category_filter.currentText()):
            QDesktopServices.openUrl(QUrl(SCFOCUS_SHIPS_URL))
            return

        QDesktopServices.openUrl(QUrl(CSTONE_HOME_URL))

    def open_selected_category(self):
        item = self.selected_item()
        if item:
            QDesktopServices.openUrl(QUrl(item.category_url))
            return

        category = self.item_category_filter.currentText()
        if self.is_scfocus_ship_category(category):
            QDesktopServices.openUrl(QUrl(SCFOCUS_SHIPS_URL))
            return

        QDesktopServices.openUrl(QUrl(cstone_category_url(category)))

    def is_scfocus_ship_category(self, category):
        return category in {
            "Ships for Sale",
            "Ships for Rent",
            WIKELO_CATEGORY,
            "Special Acquisition Ships",
        }

    def open_selected_item(self):
        item = self.selected_item()
        if item:
            QDesktopServices.openUrl(QUrl(item.detail_url))

    def open_selected_location(self):
        url = self.selected_location_url()
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def create_debounce_timer(self, callback, interval=180):
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(interval)
        timer.timeout.connect(callback)
        return timer

    def schedule_item_results_refresh(self):
        self.item_filter_timer.start()

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

    def create_combo(self, items):
        combo = QComboBox()
        combo.addItems(items)
        return combo

    def create_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSortingEnabled(True)
        table.setWordWrap(False)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        for index in range(len(headers)):
            table.horizontalHeader().setSectionResizeMode(index, QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def create_empty_state(self, text):
        label = QLabel(text)
        label.setObjectName("emptyState")
        label.setAlignment(Qt.AlignCenter)
        return label
