from dataclasses import replace
from datetime import datetime, timedelta

import requests
from PySide6.QtCore import Qt, QTimer, QUrl
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

from app.cstone_client import (
    CSTONE_HOME_URL,
    CStoneError,
    CStoneItem,
    CStoneLocation,
    cstone_category_labels,
    cstone_category_url,
    fetch_cstone_location_inventory,
    fetch_cstone_location_names,
    fetch_cstone_item_locations,
    fetch_cstone_items,
)
from app.scfocus_client import (
    SCFOCUS_SHIPS_URL,
    SPECIAL_ACQUISITION_CATEGORY,
    WIKELO_CATEGORY,
    fetch_scfocus_ship_items,
)
from app.ship_metadata import ship_metadata_for

from .table_utils import configure_readable_table_columns
from .workers import BackgroundTaskMixin


SORT_ROLE = Qt.UserRole + 1
SHIP_SALE_CATEGORY = "Ships for Sale"
SHIP_RENT_CATEGORY = "Ships for Rent"
SHIP_SALE_SOURCE_CATEGORIES = {SHIP_SALE_CATEGORY, WIKELO_CATEGORY, SPECIAL_ACQUISITION_CATEGORY}
SHIP_CATEGORIES = {SHIP_SALE_CATEGORY, SHIP_RENT_CATEGORY, WIKELO_CATEGORY, SPECIAL_ACQUISITION_CATEGORY}


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


class ItemFinderTab(BackgroundTaskMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.finder_items = []
        self.visible_finder_items = []
        self.finder_locations = []
        self.cstone_location_names = []
        self.location_search_cache = {}
        self.item_location_cache = {}
        self.current_finder_item_id = None
        self.finder_last_refresh = None
        self.finder_refresh_interval = timedelta(hours=4)
        self.availability_counts = {}
        self.auto_availability_limit = 25
        self.location_search_limit = 60
        self.location_search_request_id = 0
        self.availability_auto_load_scheduled = False
        self.auto_loading_availability = False
        self.finder_refresh_running = False
        self.location_search_running = False
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
        self.item_search_input.setPlaceholderText("Search gear, ship, city, station, shop or effect...")
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
        configure_readable_table_columns(self.item_results_table, min_width=110, max_width=360, stretch_last=True)
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
        self.selected_ship_metadata_label = QLabel("")
        self.selected_ship_metadata_label.setObjectName("moduleSubtitle")
        self.selected_ship_metadata_label.setWordWrap(True)
        self.selected_item_effect_label = QLabel("")
        self.selected_item_effect_label.setObjectName("valueText")
        self.selected_item_effect_label.setWordWrap(True)
        layout.addWidget(self.selected_item_name_label)
        layout.addWidget(self.selected_item_category_label)
        layout.addWidget(self.selected_ship_metadata_label)
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
        configure_readable_table_columns(self.item_locations_table, min_width=110, max_width=420, stretch_last=True)
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
            cstone_locations = []
            try:
                loaded_items.extend(fetch_cstone_items())
            except (CStoneError, requests.RequestException, ValueError) as exc:
                failed.append(f"Cornerstone: {exc}")

            try:
                cstone_locations = fetch_cstone_location_names()
            except (CStoneError, requests.RequestException, ValueError) as exc:
                failed.append(f"Cornerstone locations: {exc}")

            try:
                loaded_items.extend(fetch_scfocus_ship_items())
            except (requests.RequestException, ValueError) as exc:
                failed.append(f"SC Focus: {exc}")

            return {
                "loaded_items": loaded_items,
                "cstone_locations": cstone_locations,
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
        cstone_locations = result["cstone_locations"]
        failed = result["failed"]
        silent = result["silent"]

        if loaded_items:
            self.finder_items = loaded_items
            self.cstone_location_names = cstone_locations
            self.location_search_cache.clear()
            self.item_location_cache.clear()
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
                f"Loaded {len(self.finder_items)} live rows and {len(self.cstone_location_names)} Cornerstone locations. "
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
        raw_visible_items = []
        visible_keys = set()

        for item in self.finder_items:
            if not self.item_matches_category(item, category_filter):
                continue
            searchable = self.item_search_text(item)
            if query and query not in searchable:
                continue
            raw_visible_items.append(item)
            visible_keys.add(self.finder_item_key(item))

        for item in self.cached_location_search_items(query, category_filter):
            key = self.finder_item_key(item)
            if key in visible_keys:
                continue
            raw_visible_items.append(item)
            visible_keys.add(key)

        self.visible_finder_items = self.deduplicated_visible_items(raw_visible_items, category_filter)
        self.update_item_result_columns(category_filter, self.visible_finder_items)
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
                    self.item_summary_text(item, category_filter),
                ]
                for col_index, value in enumerate(values):
                    table_item = SortableTableWidgetItem(str(value))
                    table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                    table_item.setData(Qt.UserRole, row_index)
                    table_item.setData(SORT_ROLE, self.item_sort_value(item, col_index, value, category_filter))
                    table_item.setToolTip(str(value))
                    if col_index == 3:
                        table_item.setForeground(QColor("#68e6a5" if item.sold else "#7bb9c8"))
                    self.item_results_table.setItem(row_index, col_index, table_item)
            configure_readable_table_columns(self.item_results_table, min_width=110, max_width=360, stretch_last=True)
        finally:
            self.item_results_table.setSortingEnabled(True)
            self.item_results_table.setUpdatesEnabled(True)

        self.item_empty_label.setVisible(not self.visible_finder_items)
        if not self.finder_items:
            self.item_empty_label.setText("No live item data loaded yet.")
        else:
            self.item_empty_label.setText("No items match the current filters.")
        self.update_selected_item_panel()
        self.schedule_location_search_if_needed(query, category_filter)
        self.schedule_availability_autoload()

    def update_item_result_columns(self, category_filter, visible_items):
        summary_header = "Lowest Price" if category_filter in {SHIP_SALE_CATEGORY, SHIP_RENT_CATEGORY} else "Summary"
        self.item_results_table.horizontalHeaderItem(4).setText(summary_header)
        self.item_results_table.setColumnHidden(2, self.hide_type_column_for_category(category_filter, visible_items))

    def hide_type_column_for_category(self, category_filter, visible_items):
        if not category_filter.startswith("Armor - ") or not visible_items:
            return False

        expected = self.normalized_armor_type(category_filter)
        return all(
            self.normalized_armor_type(item.item_type) in {expected, category_filter.lower().replace("armor - ", "")}
            for item in visible_items
        )

    def normalized_armor_type(self, value):
        text = str(value or "").lower().replace("armor - ", "").replace("armor", "").strip()
        if text.endswith("s"):
            text = text[:-1]
        if text == "torso":
            return "core"

        return text

    def item_matches_category(self, item, category_filter):
        if category_filter == "All categories":
            return True
        if category_filter == SHIP_SALE_CATEGORY:
            return self.is_ship_sale_item(item)
        if category_filter == SHIP_RENT_CATEGORY:
            return self.is_ship_rent_item(item)

        return item.category == category_filter

    def deduplicated_visible_items(self, items, category_filter):
        groups = {}
        ordered_items = []

        for item in items:
            group_key = self.ship_group_key(item, category_filter)
            if not group_key:
                ordered_items.append(item)
                continue

            if group_key not in groups:
                groups[group_key] = []
                ordered_items.append(group_key)
            groups[group_key].append(item)

        deduplicated = []
        for entry in ordered_items:
            if isinstance(entry, tuple):
                deduplicated.append(self.merged_ship_item(groups[entry], entry[0]))
            else:
                deduplicated.append(entry)

        return deduplicated

    def ship_group_key(self, item, category_filter):
        if self.is_ship_sale_item(item) and category_filter in {"All categories", SHIP_SALE_CATEGORY}:
            return (SHIP_SALE_CATEGORY, self.normalized_ship_name(item.name))
        if self.is_ship_rent_item(item) and category_filter in {"All categories", SHIP_RENT_CATEGORY}:
            return (SHIP_RENT_CATEGORY, self.normalized_ship_name(item.name))
        if item.category in {WIKELO_CATEGORY, SPECIAL_ACQUISITION_CATEGORY} and category_filter == item.category:
            return (item.category, self.normalized_ship_name(item.name))

        return None

    def merged_ship_item(self, items, category):
        base = items[0]
        locations = self.unique_item_locations(
            location
            for item in items
            for location in getattr(item, "locations", ())
        )
        return replace(
            base,
            item_id=f"{category}:{self.normalized_ship_name(base.name)}",
            category=category,
            sold=category not in {WIKELO_CATEGORY, SPECIAL_ACQUISITION_CATEGORY},
            availability=self.location_availability_text(locations),
            effect=self.ship_detail_summary_text(category, locations),
            locations=tuple(locations),
        )

    def unique_item_locations(self, locations):
        unique_locations = []
        seen = set()
        for location in locations:
            key = (
                str(location.location).strip().lower(),
                str(location.price).strip().lower(),
                str(location.verified).strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            unique_locations.append(location)

        return unique_locations

    def normalized_ship_name(self, name):
        return " ".join(str(name or "").lower().split())

    def is_ship_sale_item(self, item):
        return item.source == "SC Focus" and item.item_type == "Ship" and item.category in SHIP_SALE_SOURCE_CATEGORIES

    def is_ship_rent_item(self, item):
        return item.source == "SC Focus" and item.item_type == "Ship" and item.category == SHIP_RENT_CATEGORY

    def is_ship_item(self, item):
        return item.source == "SC Focus" and item.item_type == "Ship" and item.category in SHIP_CATEGORIES

    def item_summary_text(self, item, category_filter):
        if self.is_ship_item(item) and category_filter in {SHIP_SALE_CATEGORY, SHIP_RENT_CATEGORY}:
            return self.lowest_ship_price_text(item)

        return item.effect

    def item_sort_value(self, item, column, value, category_filter):
        if column == 4 and self.is_ship_item(item) and category_filter in {SHIP_SALE_CATEGORY, SHIP_RENT_CATEGORY}:
            price = self.lowest_ship_price_value(item)
            return price if price is not None else float("inf")
        if column == 3:
            locations = self.known_item_locations(item)
            if locations is not None:
                return len(locations)

        return value

    def lowest_ship_price_text(self, item):
        price = self.lowest_ship_price_value(item)
        if price is not None:
            return f"{price:,} aUEC"

        prices = {location.price for location in getattr(item, "locations", ()) if location.price}
        if WIKELO_CATEGORY in prices:
            return WIKELO_CATEGORY
        if "No aUEC price" in prices:
            return "No aUEC price"

        return "N/A"

    def lowest_ship_price_value(self, item):
        prices = [
            self.price_number(location.price)
            for location in getattr(item, "locations", ())
        ]
        prices = [price for price in prices if price is not None]
        return min(prices) if prices else None

    def price_number(self, value):
        digits = "".join(char for char in str(value or "") if char.isdigit())
        if not digits:
            return None

        try:
            return int(digits)
        except ValueError:
            return None

    def ship_detail_summary_text(self, category, locations):
        lowest_price = self.lowest_ship_price_text_for_locations(locations)
        if lowest_price == "N/A":
            return f"{category} | {self.location_count_text(len(locations))}"

        return f"{category} | Lowest {lowest_price}"

    def lowest_ship_price_text_for_locations(self, locations):
        prices = [
            self.price_number(location.price)
            for location in locations
        ]
        prices = [price for price in prices if price is not None]
        if prices:
            return f"{min(prices):,} aUEC"

        price_texts = {location.price for location in locations if location.price}
        if WIKELO_CATEGORY in price_texts:
            return WIKELO_CATEGORY
        if "No aUEC price" in price_texts:
            return "No aUEC price"

        return "N/A"

    def item_search_text(self, item):
        parts = [
            item.name,
            item.source,
            item.category,
            item.item_type,
            item.availability,
            item.effect,
        ]
        if hasattr(item, "locations"):
            for location in item.locations:
                parts.extend((location.location, location.price, location.verified))

        return " ".join(str(part) for part in parts if part).lower()

    def cached_location_search_items(self, query, category_filter):
        if category_filter != "All categories" or len(query) < 3:
            return []

        return self.location_search_cache.get(query, [])

    def schedule_location_search_if_needed(self, query, category_filter):
        if category_filter != "All categories" or len(query) < 3:
            return
        if not self.cstone_location_names or self.location_search_running:
            return
        if query in self.location_search_cache:
            return

        matching_locations = self.matching_cstone_locations(query)
        if not matching_locations:
            return

        if len(matching_locations) > self.location_search_limit:
            self.finder_status_label.setText(
                f"{len(matching_locations)} Cornerstone locations match '{query}'. "
                f"Keep filtering to {self.location_search_limit} or fewer locations to load shop items."
            )
            return

        self.location_search_running = True
        self.location_search_request_id += 1
        request_id = self.location_search_request_id
        self.finder_status_label.setText(
            f"Loading shop inventory for {len(matching_locations)} location(s) matching '{query}'..."
        )

        def load_location_inventory():
            results = []
            failures = []
            for location in matching_locations:
                try:
                    results.extend(fetch_cstone_location_inventory(location))
                except (CStoneError, requests.RequestException, ValueError) as exc:
                    failures.append(f"{location}: {exc}")

            return {
                "request_id": request_id,
                "query": query,
                "locations": matching_locations,
                "results": results,
                "failures": failures,
            }

        self.start_background_task(
            load_location_inventory,
            self.on_location_search_loaded,
            self.on_location_search_error,
            lambda requested_id=request_id: self.finish_location_search(requested_id),
        )

    def matching_cstone_locations(self, query):
        return [
            location
            for location in self.cstone_location_names
            if query in location.lower()
        ]

    def on_location_search_loaded(self, result):
        request_id = result["request_id"]
        query = result["query"]
        if request_id != self.location_search_request_id:
            return

        items = []
        for inventory_item in result["results"]:
            item = self.location_inventory_to_item(inventory_item)
            key = self.finder_item_key(item)
            self.availability_counts[key] = 1
            self.item_location_cache[key] = [CStoneLocation(
                location=inventory_item.location,
                price=inventory_item.price,
                verified="Cornerstone",
                url=inventory_item.location_url,
            )]
            items.append(item)

        self.location_search_cache[query] = items
        if result["failures"]:
            self.finder_status_label.setText(
                f"Loaded {len(items)} shop rows from {len(result['locations'])} matching location(s), "
                f"with {len(result['failures'])} warning(s)."
            )
        else:
            self.finder_status_label.setText(
                f"Loaded {len(items)} shop rows from {len(result['locations'])} matching location(s)."
            )

        if self.item_search_input.text().strip().lower() == query:
            self.populate_item_results()

    def on_location_search_error(self, exc):
        self.finder_status_label.setText(f"Location inventory lookup failed: {exc}")

    def finish_location_search(self, request_id):
        if request_id != self.location_search_request_id:
            return

        self.location_search_running = False
        query = self.item_search_input.text().strip().lower()
        category_filter = self.item_category_filter.currentText()
        if query and query not in self.location_search_cache:
            self.schedule_location_search_if_needed(query, category_filter)

    def location_inventory_to_item(self, inventory_item):
        return CStoneItem(
            item_id=f"location:{inventory_item.item_id}:{inventory_item.location}",
            name=inventory_item.name,
            category="Location Search",
            size=inventory_item.size,
            sold=True,
            detail_url=inventory_item.detail_url,
            category_url=inventory_item.location_url,
            effect=f"{inventory_item.location} | {inventory_item.price}",
            source="Cornerstone",
            item_type=inventory_item.item_type,
            availability="1 location",
        )

    def on_selected_item_changed(self):
        previous_item_id = self.current_finder_item_id
        item = self.selected_item()
        self.update_selected_item_panel()
        if item and item.item_id != previous_item_id:
            self.load_selected_item_locations()

    def display_item_availability(self, item):
        locations = self.known_item_locations(item)
        if locations is not None:
            return self.location_availability_text(locations)

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
            self.set_item_availability_locations(item, locations)
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
            self.selected_ship_metadata_label.setText("")
            self.selected_ship_metadata_label.setVisible(False)
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
        self.selected_ship_metadata_label.setVisible(self.is_ship_item(item))
        self.selected_ship_metadata_label.setText(self.ship_metadata_text(item) if self.is_ship_item(item) else "")
        self.selected_item_effect_label.setText(item.effect)
        self.update_location_action_state()

    def ship_metadata_text(self, item):
        metadata = ship_metadata_for(item.name)
        if not metadata:
            return "Crew: N/A | Cargo: N/A"

        crew = "N/A"
        if metadata.min_crew is not None and metadata.max_crew is not None:
            if metadata.min_crew == metadata.max_crew:
                crew = str(metadata.min_crew)
            else:
                crew = f"{metadata.min_crew}-{metadata.max_crew}"

        cargo = "N/A"
        if metadata.cargo_scu is not None:
            cargo = f"{metadata.cargo_scu:,} SCU"

        return f"Crew: {crew} | Cargo: {cargo}"

    def load_selected_item_locations(self):
        item = self.selected_item()
        if not item:
            return

        self.item_location_request_id += 1
        request_id = self.item_location_request_id
        self.item_locations_loading = True
        self.load_item_locations_button.setEnabled(False)
        self.load_item_locations_button.setText("Loading...")

        cached_locations = self.item_location_cache.get(self.finder_item_key(item))
        if cached_locations is not None:
            if request_id == self.item_location_request_id:
                self.finder_locations = list(cached_locations)
                self.populate_location_rows()
            self.finish_selected_item_locations_load(request_id)
            return

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

        self.set_item_availability_locations(requested_item, locations)
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
        locations = self.item_location_cache.get(key)
        availability = (
            self.location_availability_text(locations)
            if locations is not None
            else self.location_count_text(location_count)
        )
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
                f"{updated_item.category} | {updated_item.item_type} | {availability} | Source: {updated_item.source}"
            )

    def set_item_availability_locations(self, item, locations):
        key = self.finder_item_key(item)
        self.item_location_cache[key] = list(locations)
        self.set_item_availability_count(item, len(locations))

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

    def known_item_locations(self, item):
        if hasattr(item, "locations"):
            return list(item.locations)

        return self.item_location_cache.get(self.finder_item_key(item))

    def location_availability_text(self, locations):
        if len(locations) == 1:
            return locations[0].location

        return self.location_count_text(len(locations))

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

        configure_readable_table_columns(self.item_locations_table, min_width=110, max_width=420, stretch_last=True)
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
        configure_readable_table_columns(table, stretch_last=True)
        return table

    def create_empty_state(self, text):
        label = QLabel(text)
        label.setObjectName("emptyState")
        label.setAlignment(Qt.AlignCenter)
        return label
