from .shared import *
from .data_loader import ItemFinderDataMixin
from .details_panel import ItemDetailsPanelMixin
from .item_finder_helpers import ItemFinderHelpersMixin
from .location_helpers import ItemFinderLocationMixin
from .results_table import ItemResultsTableMixin
from .ship_helpers import ItemFinderShipMixin


class ItemFinderTab(
    ItemFinderDataMixin,
    ItemResultsTableMixin,
    ItemFinderShipMixin,
    ItemFinderLocationMixin,
    ItemDetailsPanelMixin,
    ItemFinderHelpersMixin,
    BackgroundTaskMixin,
    QWidget,
):
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
