from datetime import datetime
from itertools import combinations

import requests
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.mining_data import load_mining_data
from app.uex_client import UEXError, fetch_commodity_sell_prices

from .constants import (
    GEM_SELLING_MATERIALS,
    REFINERY_METHODS,
    REFINERY_METHOD_YIELD_FALLBACKS,
    REFINERY_STATIONS,
    SALVAGE_REFINERY_DETAILS,
    SALVAGE_REFINERY_MATERIALS,
    SHIP_ORE_MATERIALS,
    SHIP_REFINERY_MATERIALS,
)
from .workers import BackgroundTaskMixin


class MiningTab(BackgroundTaskMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.mining_data = load_mining_data()
        self.refinery_station_lookup = {
            self.refinery_option_key(station.display_name): station
            for station in self.mining_data.refinery_stations
        }
        self.refinery_method_lookup = {
            self.refinery_option_key(method.name): method
            for method in self.mining_data.refinery_methods
        }
        self.uex_prices = {}
        self.uex_price_lists = {}
        self.refinery_sessions = {}
        self.refinery_completed_sessions = []
        self.refinery_tab_session_ids = []
        self.loading_refinery_tabs = False
        self.refinery_session_counter = 0
        self.current_refinery_session = None
        self.loading_refinery_table = False
        self.uex_refresh_running = False
        self.refinery_uex_refresh_running = False
        self.refinery_timer_remaining_seconds = 0
        self.refinery_timer = QTimer(self)
        self.refinery_timer.setInterval(1000)
        self.refinery_timer.timeout.connect(self.tick_refinery_timer)
        self.ore_filter_timer = self.create_debounce_timer(self.populate_ore_results, 250)
        self.location_filter_timer = self.create_debounce_timer(self.populate_location_results)
        self.scan_filter_timer = self.create_debounce_timer(self.populate_scan_identifier)
        self.quality_filter_timer = self.create_debounce_timer(self.populate_quality_bands)
        self.equipment_filter_timer = self.create_debounce_timer(self.populate_equipment_results)
        self.rock_filter_timer = self.create_debounce_timer(self.populate_rock_breaker_results)
        self.ore_results_columns_sized = False

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = self.create_module_header(
            "Mining & Salvage Intelligence",
            "Ore search, salvage resources, refining, rock breaking, equipment and profit tools.",
        )
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_overview_tab(), "Overview")
        self.tabs.addTab(self.build_ore_finder_tab(), "Ore Finder")
        self.tabs.addTab(self.build_locations_tab(), "Locations")
        self.tabs.addTab(self.build_scan_identifier_tab(), "Scan ID")
        self.tabs.addTab(self.build_quality_bands_tab(), "Quality Bands")
        self.tabs.addTab(self.build_refinery_tab(), "Refinery")
        self.tabs.addTab(self.build_rock_breaker_tab(), "Rock Breaker")
        self.tabs.addTab(self.build_equipment_tab(), "Equipment")
        layout.addWidget(self.tabs, 1)

        self.setLayout(layout)
        self.connect_signals()
        self.populate_mining_tables()

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

    def build_overview_tab(self):
        widget = QWidget()
        layout = QGridLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        layout.addWidget(self.create_data_status_card(), 0, 0, 1, 2)

        cards = [
            (
                "ORE FINDER",
                "Search minerals and see where they can be found.",
                "Static locations with optional live UEX prices on demand.",
                "Ore Finder",
            ),
            (
                "BEST LOCATIONS",
                "Filter by Stanton, Pyro, body, cave, asteroid or surface mining.",
                "Live data: grouped body/location view for planning mining ops.",
                "Locations",
            ),
            (
                "REFINERY",
                "Build refining sessions with ore input, yield and value totals.",
                "Session data and UEX prices stay in memory only.",
                "Refinery",
            ),
            (
                "ROCK BREAKER",
                "Compare mass, resistance, instability, lasers and modules.",
                "Planned data: rock-breaking calculator JSON.",
                "Rock Breaker",
            ),
            (
                "SCAN ID",
                "Identify possible resources from scan signature values.",
                "Live data: resource scan signature values from the provided chart.",
                "Scan ID",
            ),
            (
                "QUALITY BANDS",
                "Compare resource quality thresholds by score band.",
                "Live data: quality quantization JSON matching the uploaded HTML.",
                "Quality Bands",
            ),
            (
                "EQUIPMENT",
                "Find mining lasers, modules, gadgets and shops.",
                "Live data: lasers, modules and gadgets from rock-breaking JSON.",
                "Equipment",
            ),
            (
                "PROFIT",
                "Turn ore, refinery and market data into a quick value readout.",
                "This can later link into the Trading tab.",
                "Refinery",
            ),
        ]

        for index, (title, summary, detail, tab_name) in enumerate(cards):
            layout.addWidget(
                self.create_overview_card(title, summary, detail, tab_name),
                index // 2 + 1,
                index % 2,
            )

        layout.setRowStretch(5, 1)
        widget.setLayout(layout)
        return widget

    def create_data_status_card(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        title = QLabel("DATA STATUS")
        title.setObjectName("sectionTitle")
        self.mining_status_label = QLabel("Loading mining data...")
        self.mining_status_label.setObjectName("valueText")
        self.mining_source_label = QLabel("")
        self.mining_source_label.setObjectName("moduleSubtitle")
        self.mining_source_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.mining_status_label)
        layout.addWidget(self.mining_source_label)
        card.setLayout(layout)
        return card

    def create_overview_card(self, title, summary, detail, tab_name):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setCursor(Qt.PointingHandCursor)
        card.setToolTip(f"Open {tab_name}")
        card.mousePressEvent = lambda event, name=tab_name: self.open_mining_tab(name)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        summary_label = QLabel(summary)
        summary_label.setObjectName("valueText")
        summary_label.setWordWrap(True)
        detail_label = QLabel(detail)
        detail_label.setObjectName("moduleSubtitle")
        detail_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(summary_label)
        layout.addWidget(detail_label)
        layout.addStretch(1)
        card.setLayout(layout)
        return card

    def open_mining_tab(self, tab_name):
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == tab_name:
                self.tabs.setCurrentIndex(index)
                return

    def refinery_station_options(self):
        return self.unique_options(
            ["Any refinery", "No Refinery (Sell Raw Ore)"]
            + [station.display_name for station in self.mining_data.refinery_stations]
            + REFINERY_STATIONS
        )

    def refinery_method_options(self):
        return self.unique_options(
            [method.name for method in self.mining_data.refinery_methods]
            + REFINERY_METHODS
        )

    def unique_options(self, values):
        options = []
        seen = set()
        for value in values:
            key = self.refinery_option_key(value)
            if not value or key in seen:
                continue
            seen.add(key)
            options.append(value)
        return options

    def build_ore_finder_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("ORE SEARCH")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.ore_search_input = QLineEdit()
        self.ore_search_input.setPlaceholderText("Search mineral...")
        self.ore_system_filter = self.create_combo(["All systems", "Stanton", "Pyro", "Nyx", "Unknown"])
        self.ore_type_filter = self.create_combo(["All deposits", "Surface", "Asteroid", "General"])
        row.addWidget(self.ore_search_input, 1)
        row.addWidget(self.ore_system_filter)
        row.addWidget(self.ore_type_filter)
        filter_layout.addLayout(row)

        uex_row = QHBoxLayout()
        self.uex_status_label = QLabel("UEX prices are live/in-memory only. No local price cache is used.")
        self.uex_status_label.setObjectName("moduleSubtitle")
        self.refresh_uex_prices_button = QPushButton("Refresh Visible UEX Prices")
        uex_row.addWidget(self.uex_status_label, 1)
        uex_row.addWidget(self.refresh_uex_prices_button)
        filter_layout.addLayout(uex_row)
        layout.addWidget(filter_card)

        self.ore_results_table = self.create_table([
            "Mineral",
            "System",
            "Body / Area",
            "Deposit",
            "UEX Sell",
            "Best UEX Terminal",
            "Notes",
        ])
        self.ore_results_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.ore_results_table, 1)
        self.ore_empty_label = self.create_empty_state("No ore results match the current filters.")
        layout.addWidget(self.ore_empty_label)
        widget.setLayout(layout)
        return widget

    def build_locations_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("LOCATION FILTERS")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.location_system_filter = self.create_combo(["All systems", "Stanton", "Pyro", "Nyx", "Unknown"])
        self.location_search_input = QLineEdit()
        self.location_search_input.setPlaceholderText("Filter body/mineral...")
        self.location_focus_filter = self.create_combo(["All mining types", "Surface", "Asteroid", "General"])
        row.addWidget(self.location_system_filter)
        row.addWidget(self.location_search_input, 1)
        row.addWidget(self.location_focus_filter)
        filter_layout.addLayout(row)
        layout.addWidget(filter_card)

        self.location_table = self.create_table([
            "System",
            "Body / Area",
            "Deposit",
            "Minerals",
            "Count",
            "Notes",
        ])
        self.location_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.location_table, 1)
        self.location_empty_label = self.create_empty_state("No locations match the current filters.")
        layout.addWidget(self.location_empty_label)
        widget.setLayout(layout)
        return widget

    def build_scan_identifier_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("SCAN SIGNATURE IDENTIFIER")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.scan_value_input = QLineEdit()
        self.scan_value_input.setPlaceholderText("Exact value, ~value for +/-10%, or min-max...")
        self.scan_category_filter = self.create_combo([
            "All categories",
            "Legendary",
            "Epic",
            "Rare",
            "Uncommon",
            "Common",
            "ROC Mineables",
            "FPS Mineables",
            "Salvage",
        ])
        row.addWidget(self.scan_value_input, 1)
        row.addWidget(self.scan_category_filter)
        filter_layout.addLayout(row)

        hint = QLabel("Examples: 8600 | ~5000 | 8000-9000 | comma-separated values")
        hint.setObjectName("moduleSubtitle")
        filter_layout.addWidget(hint)
        layout.addWidget(filter_card)

        self.scan_signature_table = self.create_table([
            "Resource",
            "Category",
            "Max",
            "Matches",
            "All Signatures",
        ])
        self.scan_signature_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.scan_signature_table, 1)
        self.scan_empty_label = self.create_empty_state("No scan signatures match the current input.")
        layout.addWidget(self.scan_empty_label)
        widget.setLayout(layout)
        return widget

    def build_quality_bands_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("RESOURCE QUALITY BANDS")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.quality_search_input = QLineEdit()
        self.quality_search_input.setPlaceholderText("Filter resource...")
        self.quality_score_input = QLineEdit()
        self.quality_score_input.setPlaceholderText("Quality score...")
        row.addWidget(self.quality_search_input, 1)
        row.addWidget(self.quality_score_input)
        filter_layout.addLayout(row)

        hint = QLabel("Quality score columns show the mapped resource value for each score band.")
        hint.setObjectName("moduleSubtitle")
        filter_layout.addWidget(hint)
        layout.addWidget(filter_card)

        self.quality_bands_table = self.create_table([
            "Resource",
            "Matched Band",
            *self.mining_data.quality_band_labels,
        ])
        layout.addWidget(self.quality_bands_table, 1)
        self.quality_empty_label = self.create_empty_state("No quality bands match the current filters.")
        layout.addWidget(self.quality_empty_label)
        widget.setLayout(layout)
        return widget

    def build_refinery_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.refinery_session_tabs = QTabWidget()
        self.refinery_session_tabs.setMaximumHeight(44)
        layout.addWidget(self.refinery_session_tabs)

        self.refinery_stack = QStackedWidget()

        work_widget = QWidget()
        work_layout = QVBoxLayout()
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(12)

        content = QHBoxLayout()
        content.setSpacing(12)

        input_card = self.create_filter_card("SHIP ORES / REFINING")
        input_layout = input_card.layout()

        session_row = QHBoxLayout()
        self.refinery_session_name_input = QLineEdit()
        self.refinery_session_name_input.setPlaceholderText("Session name...")
        self.refinery_new_session_button = QPushButton("New Session")
        self.refinery_save_session_button = QPushButton("Save To History")
        self.refinery_close_session_button = QPushButton("Close Session")
        session_row.addWidget(self.refinery_session_name_input, 1)
        session_row.addWidget(self.refinery_new_session_button)
        session_row.addWidget(self.refinery_save_session_button)
        session_row.addWidget(self.refinery_close_session_button)
        input_layout.addLayout(session_row)

        setup_row = QHBoxLayout()
        self.refinery_station_filter = self.create_combo(self.refinery_station_options())
        self.refinery_method_filter = self.create_combo(self.refinery_method_options())
        setup_row.addWidget(self.refinery_station_filter, 1)
        setup_row.addWidget(self.refinery_method_filter, 1)
        input_layout.addLayout(setup_row)

        self.add_refinery_material_section(input_layout, "ORE CHOOSER", SHIP_ORE_MATERIALS, columns=6)
        self.add_refinery_material_section(input_layout, "SALVAGE", SALVAGE_REFINERY_MATERIALS, columns=3)
        self.add_refinery_material_section(
            input_layout,
            "GEM SELLING (NO REFINING)",
            GEM_SELLING_MATERIALS,
            columns=5,
        )

        material_actions = QHBoxLayout()
        all_button = QPushButton("ALL")
        all_button.clicked.connect(self.add_all_refinery_materials)
        none_button = QPushButton("NONE")
        none_button.clicked.connect(self.clear_refinery_session)
        material_actions.addWidget(all_button)
        material_actions.addWidget(none_button)
        material_actions.addStretch(1)
        input_layout.addLayout(material_actions)

        table_actions = QHBoxLayout()
        self.refinery_remove_material_button = QPushButton("Remove Selected Material")
        self.refinery_refresh_uex_button = QPushButton("Refresh UEX For Session")
        table_actions.addWidget(self.refinery_remove_material_button)
        table_actions.addWidget(self.refinery_refresh_uex_button)
        input_layout.addLayout(table_actions)

        self.refinery_table = self.create_table([
            "Material",
            "QTY (cSCU)",
            "QTY (SCU)",
            "Yield (cSCU)",
            "Yield (SCU)",
            "UEX Sell",
            "Sell Value",
        ])
        self.refinery_table.setSortingEnabled(False)
        self.refinery_table.horizontalHeader().setStretchLastSection(True)
        self.refinery_table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.EditKeyPressed
        )
        input_layout.addWidget(self.refinery_table, 1)
        self.refinery_empty_label = self.create_empty_state("No material selected for this refining session.")
        input_layout.addWidget(self.refinery_empty_label)

        summary_card = self.create_filter_card("SELLING / PROFIT SUMMARY")
        summary_layout = summary_card.layout()
        self.refinery_price_status_label = QLabel(
            "UEX prices are fetched live for this session and are not stored locally."
        )
        self.refinery_price_status_label.setObjectName("moduleSubtitle")
        self.refinery_price_status_label.setWordWrap(True)
        summary_layout.addWidget(self.refinery_price_status_label)

        totals_grid = QGridLayout()
        totals_grid.setHorizontalSpacing(12)
        totals_grid.setVerticalSpacing(8)
        self.refinery_total_qty_label = QLabel("0 cSCU / 0 SCU")
        self.refinery_total_yield_label = QLabel("0 cSCU / 0 SCU")
        self.refinery_gross_value_label = QLabel("0 aUEC")
        self.refinery_net_value_label = QLabel("0 aUEC")
        self.refinery_time_left_label = QLabel("00:00:00")
        for value_label in (
            self.refinery_total_qty_label,
            self.refinery_total_yield_label,
            self.refinery_gross_value_label,
            self.refinery_net_value_label,
            self.refinery_time_left_label,
        ):
            value_label.setObjectName("valueText")

        self.refinery_fee_input = QLineEdit("0")
        self.refinery_fee_input.setPlaceholderText("Refinery fee...")
        self.refinery_time_input = QLineEdit()
        self.refinery_time_input.setPlaceholderText("HH:MM:SS or minutes...")
        totals = [
            ("TOTAL QTY", self.refinery_total_qty_label),
            ("TOTAL YIELD", self.refinery_total_yield_label),
            ("SELL VALUE", self.refinery_gross_value_label),
            ("REFINERY FEE", self.refinery_fee_input),
            ("NET VALUE", self.refinery_net_value_label),
            ("REFINERY TIME", self.refinery_time_input),
            ("TIME LEFT", self.refinery_time_left_label),
        ]
        for row_index, (label_text, widget_item) in enumerate(totals):
            label = QLabel(label_text)
            label.setObjectName("labelText")
            totals_grid.addWidget(label, row_index, 0)
            totals_grid.addWidget(widget_item, row_index, 1)

        summary_layout.addLayout(totals_grid)
        timer_row = QHBoxLayout()
        self.refinery_timer_start_button = QPushButton("Start")
        self.refinery_timer_reset_button = QPushButton("Reset")
        timer_row.addWidget(self.refinery_timer_start_button)
        timer_row.addWidget(self.refinery_timer_reset_button)
        summary_layout.addLayout(timer_row)

        sell_locations_label = QLabel("SELL LOCATION OPTIONS")
        sell_locations_label.setObjectName("sectionTitle")
        summary_layout.addWidget(sell_locations_label)
        self.refinery_sell_locations_table = self.create_table([
            "Location",
            "Sell Value",
            "Materials",
        ])
        self.refinery_sell_locations_table.setSortingEnabled(False)
        self.refinery_sell_locations_table.setMinimumHeight(150)
        self.refinery_sell_locations_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.refinery_sell_locations_table.horizontalHeader().setStretchLastSection(False)
        summary_layout.addWidget(self.refinery_sell_locations_table, 1)
        self.refinery_sell_locations_empty_label = self.create_empty_state(
            "Refresh UEX For Session to see matching sell locations."
        )
        summary_layout.addWidget(self.refinery_sell_locations_empty_label)

        hint = QLabel(
            "Enter ore QTY in either cSCU or SCU. Yield is auto-estimated from refinery station and method; "
            "you can still edit Yield if the in-game quote differs. Gems use QTY directly because they are sold, not refined. "
            "Sell value uses the best live UEX sell price in memory."
        )
        hint.setObjectName("moduleSubtitle")
        hint.setWordWrap(True)
        summary_layout.addWidget(hint)

        content.addWidget(input_card, 2)
        content.addWidget(summary_card, 1)
        work_layout.addLayout(content, 1)
        work_widget.setLayout(work_layout)

        self.refinery_history_widget = self.build_refinery_history_widget()
        self.refinery_stack.addWidget(work_widget)
        self.refinery_stack.addWidget(self.refinery_history_widget)
        layout.addWidget(self.refinery_stack, 1)
        widget.setLayout(layout)
        return widget

    def add_refinery_material_section(self, parent_layout, title, materials, columns=6):
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        parent_layout.addWidget(label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        for index, (code, material) in enumerate(materials):
            button = QPushButton(code)
            button.setToolTip(self.refinery_material_tooltip(material))
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(lambda checked=False, selected=material: self.add_refinery_material(selected))
            grid.addWidget(button, index // columns, index % columns)

        parent_layout.addLayout(grid)

    def build_refinery_history_widget(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        history_card = self.create_filter_card("REFINERY SESSION HISTORY")
        history_layout = history_card.layout()
        actions = QHBoxLayout()
        self.refinery_history_remove_button = QPushButton("Remove Selected")
        self.refinery_history_clear_button = QPushButton("Clear History")
        actions.addStretch(1)
        actions.addWidget(self.refinery_history_remove_button)
        actions.addWidget(self.refinery_history_clear_button)
        history_layout.addLayout(actions)
        self.refinery_history_table = self.create_table([
            "Name",
            "Station",
            "Method",
            "QTY",
            "Yield",
            "Sell Value",
            "Net",
            "Saved",
        ])
        self.refinery_history_table.horizontalHeader().setStretchLastSection(True)
        history_layout.addWidget(self.refinery_history_table, 1)
        self.refinery_history_empty_label = self.create_empty_state("No saved refinery sessions yet.")
        history_layout.addWidget(self.refinery_history_empty_label)
        layout.addWidget(history_card, 1)
        widget.setLayout(layout)
        return widget

    def build_rock_breaker_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        input_card = self.create_filter_card("ROCK PROFILE")
        input_layout = input_card.layout()
        row = QHBoxLayout()
        self.rock_mass_input = QLineEdit()
        self.rock_mass_input.setPlaceholderText("Mass...")
        self.rock_resistance_input = QLineEdit()
        self.rock_resistance_input.setPlaceholderText("Resistance...")
        self.rock_instability_input = QLineEdit()
        self.rock_instability_input.setPlaceholderText("Instability...")
        self.rock_laser_filter = self.create_combo(["Any laser", "Ship mining", "Vehicle mining", "Hand mining"])
        self.rock_calculate_button = QPushButton("Analyze")
        row.addWidget(self.rock_mass_input)
        row.addWidget(self.rock_resistance_input)
        row.addWidget(self.rock_instability_input)
        row.addWidget(self.rock_laser_filter)
        row.addWidget(self.rock_calculate_button)
        input_layout.addLayout(row)
        layout.addWidget(input_card)

        self.rock_table = self.create_table([
            "Setup",
            "Laser",
            "Modules",
            "Power Window",
            "Risk",
            "Notes",
        ])
        self.rock_table.setSortingEnabled(False)
        self.rock_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.rock_table, 1)
        self.rock_empty_label = self.create_empty_state("No rock-breaking setups match the current filters.")
        layout.addWidget(self.rock_empty_label)
        widget.setLayout(layout)
        return widget

    def build_equipment_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("EQUIPMENT FILTERS")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.equipment_search_input = QLineEdit()
        self.equipment_search_input.setPlaceholderText("Search equipment...")
        self.equipment_type_filter = self.create_combo(["All equipment", "Laser", "Module", "Gadget", "Salvage"])
        self.equipment_size_filter = self.create_combo(["Any size", "FPS", "S0", "S1", "S2", "S3", "N/A"])
        row.addWidget(self.equipment_search_input, 1)
        row.addWidget(self.equipment_type_filter)
        row.addWidget(self.equipment_size_filter)
        filter_layout.addLayout(row)
        layout.addWidget(filter_card)

        self.equipment_table = self.create_table([
            "Item",
            "Type",
            "Size",
            "Price",
            "Shops",
            "Best Shop",
            "Best Location",
            "Effect",
            "Notes",
        ])
        layout.addWidget(self.equipment_table, 1)
        self.equipment_empty_label = self.create_empty_state("No equipment matches the current filters.")
        layout.addWidget(self.equipment_empty_label)
        widget.setLayout(layout)
        return widget

    def connect_signals(self):
        self.ore_search_input.textChanged.connect(self.schedule_ore_results_refresh)
        self.ore_system_filter.currentTextChanged.connect(self.schedule_ore_results_refresh)
        self.ore_type_filter.currentTextChanged.connect(self.schedule_ore_results_refresh)
        self.refresh_uex_prices_button.clicked.connect(self.refresh_visible_uex_prices)

        self.location_search_input.textChanged.connect(self.schedule_location_results_refresh)
        self.location_system_filter.currentTextChanged.connect(self.schedule_location_results_refresh)
        self.location_focus_filter.currentTextChanged.connect(self.schedule_location_results_refresh)

        self.scan_value_input.textChanged.connect(self.schedule_scan_identifier_refresh)
        self.scan_category_filter.currentTextChanged.connect(self.schedule_scan_identifier_refresh)

        self.quality_search_input.textChanged.connect(self.schedule_quality_bands_refresh)
        self.quality_score_input.textChanged.connect(self.schedule_quality_bands_refresh)

        self.refinery_session_tabs.currentChanged.connect(self.on_refinery_session_tab_changed)
        self.refinery_session_name_input.editingFinished.connect(self.rename_current_refinery_session)
        self.refinery_new_session_button.clicked.connect(self.create_refinery_session)
        self.refinery_save_session_button.clicked.connect(self.save_refinery_session_to_history)
        self.refinery_close_session_button.clicked.connect(self.close_refinery_session)
        self.refinery_history_remove_button.clicked.connect(self.remove_selected_refinery_history)
        self.refinery_history_clear_button.clicked.connect(self.clear_refinery_history)
        self.refinery_remove_material_button.clicked.connect(self.remove_selected_refinery_material)
        self.refinery_refresh_uex_button.clicked.connect(self.refresh_refinery_uex_prices)
        self.refinery_fee_input.textChanged.connect(self.on_refinery_fee_changed)
        self.refinery_time_input.textChanged.connect(self.on_refinery_time_changed)
        self.refinery_station_filter.currentTextChanged.connect(self.on_refinery_setup_changed)
        self.refinery_method_filter.currentTextChanged.connect(self.on_refinery_setup_changed)
        self.refinery_timer_start_button.clicked.connect(self.toggle_refinery_timer)
        self.refinery_timer_reset_button.clicked.connect(self.reset_refinery_timer)
        self.refinery_table.itemChanged.connect(self.on_refinery_item_changed)

        self.equipment_search_input.textChanged.connect(self.schedule_equipment_results_refresh)
        self.equipment_type_filter.currentTextChanged.connect(self.schedule_equipment_results_refresh)
        self.equipment_size_filter.currentTextChanged.connect(self.schedule_equipment_results_refresh)
        self.rock_mass_input.textChanged.connect(self.schedule_rock_breaker_refresh)
        self.rock_resistance_input.textChanged.connect(self.schedule_rock_breaker_refresh)
        self.rock_instability_input.textChanged.connect(self.schedule_rock_breaker_refresh)
        self.rock_laser_filter.currentTextChanged.connect(self.schedule_rock_breaker_refresh)
        self.rock_calculate_button.clicked.connect(self.populate_rock_breaker_results)

    def create_debounce_timer(self, callback, interval=180):
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(interval)
        timer.timeout.connect(callback)
        return timer

    def schedule_ore_results_refresh(self):
        self.ore_filter_timer.start()

    def schedule_location_results_refresh(self):
        self.location_filter_timer.start()

    def schedule_scan_identifier_refresh(self):
        self.scan_filter_timer.start()

    def schedule_quality_bands_refresh(self):
        self.quality_filter_timer.start()

    def schedule_equipment_results_refresh(self):
        self.equipment_filter_timer.start()

    def schedule_rock_breaker_refresh(self):
        self.rock_filter_timer.start()

    def populate_mining_tables(self):
        self.populate_overview_summary()
        self.populate_ore_results()
        self.populate_location_results()
        self.populate_scan_identifier()
        self.populate_quality_bands()
        self.ensure_refinery_session()
        self.populate_refinery_table()
        self.populate_rock_breaker_results()
        self.populate_equipment_results()

    def populate_overview_summary(self):
        data = self.mining_data
        self.mining_status_label.setText(
            f"Loaded {len(data.minerals)} minerals, "
            f"{len(data.locations)} location rows, "
            f"{len(data.equipment)} equipment items. "
            f"Also loaded {len(data.quality_bands)} quality-band rows and "
            f"{len(data.scan_signatures)} scan signatures, "
            f"{len(data.refinery_stations)} refineries and "
            f"{len(data.refinery_methods)} refinery methods. "
            "Market prices are fetched live from UEX and are not stored locally."
        )

        if data.errors:
            self.mining_source_label.setText("Data warnings: " + " | ".join(data.errors))
        else:
            self.mining_source_label.setText(
                "Static mining reference data is loaded from the app/reference bundle. "
                "Live market prices use UEX on demand."
            )

    def populate_ore_results(self):
        query = self.ore_search_input.text().strip().lower()
        system_filter = self.ore_system_filter.currentText()
        deposit_filter = self.ore_type_filter.currentText()
        rows = []

        for location in self.mining_data.locations:
            if system_filter != "All systems" and location.system != system_filter:
                continue
            if deposit_filter != "All deposits" and location.deposit_type != deposit_filter:
                continue
            if query and query not in self.location_search_text(location):
                continue

            price = self.uex_prices.get(location.mineral.lower())
            rows.append([
                location.mineral,
                location.system,
                location.body,
                location.deposit_type,
                self.format_price(price.price_sell if price else None),
                self.format_uex_terminal(price),
                location.notes or "",
            ])

        rows.sort(key=lambda row: (row[0].lower(), row[1], row[2].lower(), row[3]))
        self.set_table_rows(self.ore_results_table, rows, resize_columns=not self.ore_results_columns_sized)
        self.ore_results_columns_sized = True
        self.ore_empty_label.setVisible(not rows)

    def refresh_visible_uex_prices(self):
        if self.uex_refresh_running:
            return

        minerals = self.visible_ore_minerals()
        if not minerals:
            QMessageBox.information(
                self,
                "No visible ores",
                "No visible ore rows to refresh.",
            )
            return

        self.uex_refresh_running = True
        self.refresh_uex_prices_button.setEnabled(False)
        self.refresh_uex_prices_button.setText("Refreshing UEX...")

        def load_prices():
            refreshed = 0
            failed = []
            prices_by_mineral = {}
            for mineral in minerals:
                try:
                    prices = fetch_commodity_sell_prices(mineral)
                except (UEXError, requests.RequestException, ValueError) as exc:
                    failed.append(f"{mineral}: {exc}")
                    continue

                prices_by_mineral[mineral.lower()] = prices[0] if prices else None
                refreshed += 1

            return {
                "minerals": minerals,
                "prices": prices_by_mineral,
                "refreshed": refreshed,
                "failed": failed,
            }

        self.start_background_task(
            load_prices,
            self.on_visible_uex_prices_refreshed,
            self.on_visible_uex_prices_error,
            self.finish_visible_uex_prices_refresh,
        )

    def on_visible_uex_prices_refreshed(self, result):
        self.uex_prices.update(result["prices"])
        self.ore_results_columns_sized = False
        self.populate_ore_results()
        failed = result["failed"]
        minerals = result["minerals"]
        refreshed = result["refreshed"]
        if failed:
            self.uex_status_label.setText(
                f"UEX refreshed {refreshed}/{len(minerals)} minerals; "
                f"{len(failed)} failed. Prices are not stored locally."
            )
            QMessageBox.warning(
                self,
                "UEX refresh incomplete",
                "\n".join(failed[:5]),
            )
        else:
            self.uex_status_label.setText(
                f"UEX refreshed {refreshed} visible minerals. Prices are not stored locally."
            )

    def on_visible_uex_prices_error(self, exc):
        self.uex_status_label.setText(f"UEX refresh failed: {exc}")
        QMessageBox.critical(self, "UEX refresh failed", str(exc))

    def finish_visible_uex_prices_refresh(self):
        self.uex_refresh_running = False
        self.refresh_uex_prices_button.setEnabled(True)
        self.refresh_uex_prices_button.setText("Refresh Visible UEX Prices")

    def visible_ore_minerals(self):
        minerals = {
            self.ore_results_table.item(row, 0).text()
            for row in range(self.ore_results_table.rowCount())
            if self.ore_results_table.item(row, 0)
        }
        return sorted(minerals)

    def format_uex_terminal(self, price):
        if not price:
            return "Refresh UEX"

        location = price.location_name if price.location_name != "N/A" else price.star_system_name
        if location and location != "N/A":
            return f"{location} / {price.terminal_name}"

        return price.terminal_name

    def populate_rock_breaker_results(self):
        lasers = [
            laser
            for laser in self.mining_data.rock_lasers
            if self.rock_laser_matches_filter(laser)
        ]
        mass = self.parse_float(self.rock_mass_input.text())
        resistance = self.parse_float(self.rock_resistance_input.text())
        instability = self.parse_float(self.rock_instability_input.text())
        has_power_stats = mass > 0 and resistance > 0

        if not has_power_stats:
            rows = [
                [
                    "Baseline",
                    f"{laser.name} S{laser.size}",
                    f"{laser.module_slots} slots",
                    f"{self.format_number(laser.min_power)}-{self.format_number(laser.max_power)}",
                    "Enter rock stats",
                    (
                        f"Price {self.format_auec_amount(laser.price or 0)} | "
                        f"Res x{laser.resistance_factor:g} | Instab x{laser.instability_factor:g} | "
                        f"Window x{laser.optimal_charge_window:g}"
                    ),
                ]
                for laser in sorted(lasers, key=lambda item: (item.size, item.name.lower()))
            ]
            self.set_table_rows(self.rock_table, rows)
            self.color_rock_risk_cells()
            self.rock_empty_label.setVisible(not rows)
            return

        module_candidates = self.rock_module_candidates()
        gadgets = [None, *self.mining_data.rock_gadgets]
        setups = []
        for laser in lasers:
            for modules in self.rock_module_combinations(module_candidates, laser.module_slots):
                for gadget in gadgets:
                    setups.append(self.evaluate_rock_setup(laser, modules, gadget, mass, resistance, instability))

        setups.sort(key=lambda item: item["score"])
        rows = []
        for rank, setup in enumerate(setups[:120], start=1):
            rows.append([
                f"#{rank} {setup['setup']}",
                setup["laser"],
                setup["modules"],
                setup["power_window"],
                setup["risk"],
                setup["notes"],
            ])

        self.set_table_rows(self.rock_table, rows)
        self.color_rock_risk_cells()
        self.rock_empty_label.setVisible(not rows)

    def rock_laser_matches_filter(self, laser):
        selected = self.rock_laser_filter.currentText()
        if selected == "Ship mining":
            return laser.size >= 1
        if selected in {"Vehicle mining", "Hand mining"}:
            return laser.size == 0
        return True

    def rock_module_candidates(self):
        return [
            module
            for module in self.mining_data.rock_modules
            if any(
                abs(value - 1) > 0.001
                for value in (
                    module.mining_laser_power,
                    module.resistance_factor,
                    module.instability_factor,
                    module.optimal_charge_rate,
                    module.optimal_charge_window,
                )
            )
        ]

    def rock_module_combinations(self, modules, slots):
        if slots <= 0:
            return [()]

        combos = [()]
        for size in range(1, min(slots, 3) + 1):
            combos.extend(combinations(modules, size))
        return combos

    def evaluate_rock_setup(self, laser, modules, gadget, mass, resistance, instability):
        power_factor = self.multiply_factors([module.mining_laser_power for module in modules])
        resistance_factor = laser.resistance_factor * self.multiply_factors(
            [module.resistance_factor for module in modules]
        )
        instability_factor = laser.instability_factor * self.multiply_factors(
            [module.instability_factor for module in modules]
        )
        charge_rate = laser.optimal_charge_rate * self.multiply_factors(
            [module.optimal_charge_rate for module in modules]
        )
        charge_window = laser.optimal_charge_window * self.multiply_factors(
            [module.optimal_charge_window for module in modules]
        )

        if gadget:
            resistance_factor *= gadget.resistance_factor
            instability_factor *= gadget.instability_factor
            charge_window *= gadget.optimal_charge_window
            charge_rate *= gadget.optimal_charge_rate

        min_power = laser.min_power * power_factor
        max_power = laser.max_power * power_factor
        required_power = mass * resistance * resistance_factor
        rock_instability = instability if instability > 0 else 1
        effective_instability = rock_instability * instability_factor
        risk_score = effective_instability / max(charge_window, 0.1)

        if required_power > max_power:
            risk = "Too weak"
            score = 100000 + ((required_power / max(max_power, 1)) * 1000) + risk_score
            setup = "Needs more power"
        elif required_power < min_power:
            risk = "Overpowered"
            score = 50000 + ((min_power / max(required_power, 1)) * 250) + risk_score
            setup = "Throttle carefully"
        else:
            if risk_score >= 1.35 or effective_instability >= 1.5 or charge_window < 0.7:
                risk = "High"
            elif risk_score >= 0.85 or effective_instability >= 1.1 or charge_window < 1:
                risk = "Medium"
            else:
                risk = "Low"

            score = (
                risk_score * 100
                - min(max_power - required_power, max_power) / max(max_power, 1) * 20
                + len(modules) * 4
                + (6 if gadget else 0)
            )
            setup = "Recommended" if risk == "Low" else "Workable"

        module_text = ", ".join(module.name for module in modules) or "None"
        if gadget:
            module_text = f"{module_text} + {gadget.name} gadget"

        notes = (
            f"S{laser.size} | Slots {laser.module_slots} | "
            f"Res x{resistance_factor:.2f} | Instab x{effective_instability:.2f} | "
            f"Window x{charge_window:.2f} | Rate x{charge_rate:.2f}"
        )
        if required_power > max_power:
            notes += f" | Needs {required_power / max(max_power, 1):.1f}x max power"

        return {
            "score": score,
            "setup": setup,
            "laser": f"{laser.name} S{laser.size}",
            "modules": module_text,
            "power_window": (
                f"Need {self.format_number(required_power)} / "
                f"{self.format_number(min_power)}-{self.format_number(max_power)}"
            ),
            "risk": risk,
            "notes": notes,
        }

    def multiply_factors(self, values):
        result = 1.0
        for value in values:
            result *= value
        return result

    def color_rock_risk_cells(self):
        colors = {
            "Low": QColor("#5cffbd"),
            "Medium": QColor("#ffd166"),
            "High": QColor("#ff8f66"),
            "Too weak": QColor("#ff5c5c"),
            "Overpowered": QColor("#ffb86b"),
        }
        for row in range(self.rock_table.rowCount()):
            item = self.rock_table.item(row, 4)
            if item and item.text() in colors:
                item.setForeground(colors[item.text()])

    def ensure_refinery_session(self):
        if not self.current_refinery_session:
            self.create_refinery_session()

    def create_refinery_session(self):
        self.refinery_session_counter += 1
        session_id = f"session-{self.refinery_session_counter}"
        session_name = f"Session {self.refinery_session_counter}"
        session_name = self.unique_refinery_session_name(session_name)
        self.refinery_sessions[session_id] = {
            "name": session_name,
            "materials": {},
            "fee": 0.0,
            "station": self.refinery_station_filter.currentText() if hasattr(self, "refinery_station_filter") else "",
            "method": self.refinery_method_filter.currentText() if hasattr(self, "refinery_method_filter") else "",
            "time_text": "",
            "time_remaining": 0,
            "timer_running": False,
        }
        self.current_refinery_session = session_id

        self.load_refinery_session_fields()
        self.refresh_refinery_session_tabs()
        self.populate_refinery_table()

    def on_refinery_session_tab_changed(self, index):
        if self.loading_refinery_tabs or index < 0:
            return

        if index >= len(self.refinery_tab_session_ids):
            self.refinery_stack.setCurrentWidget(self.refinery_history_widget)
            self.populate_refinery_history_table()
            return

        session_id = self.refinery_tab_session_ids[index]
        if session_id not in self.refinery_sessions:
            return

        self.current_refinery_session = session_id
        self.refinery_stack.setCurrentIndex(0)
        self.load_refinery_session_fields()
        self.populate_refinery_table()

    def load_refinery_session_fields(self):
        session = self.refinery_session()

        self.refinery_session_name_input.blockSignals(True)
        self.refinery_session_name_input.setText(session.get("name", ""))
        self.refinery_session_name_input.blockSignals(False)
        self.refinery_station_filter.blockSignals(True)
        self.refinery_station_filter.setCurrentText(session.get("station", "Any refinery"))
        self.refinery_station_filter.blockSignals(False)
        self.refinery_method_filter.blockSignals(True)
        self.refinery_method_filter.setCurrentText(session.get("method", REFINERY_METHODS[0]))
        self.refinery_method_filter.blockSignals(False)
        self.refinery_fee_input.blockSignals(True)
        self.refinery_fee_input.setText(self.format_number(session.get("fee", 0)))
        self.refinery_fee_input.blockSignals(False)
        self.load_refinery_timer_fields()

    def refresh_refinery_session_tabs(self):
        if not hasattr(self, "refinery_session_tabs"):
            return

        self.loading_refinery_tabs = True
        self.refinery_session_tabs.clear()
        self.refinery_tab_session_ids = list(self.refinery_sessions.keys())
        for session_id in self.refinery_tab_session_ids:
            session = self.refinery_sessions[session_id]
            self.refinery_session_tabs.addTab(QWidget(), self.refinery_tab_label(session))

        self.refinery_session_tabs.addTab(QWidget(), "History")

        if self.current_refinery_session in self.refinery_tab_session_ids:
            self.refinery_session_tabs.setCurrentIndex(self.refinery_tab_session_ids.index(self.current_refinery_session))
            self.refinery_stack.setCurrentIndex(0)
        else:
            self.refinery_session_tabs.setCurrentIndex(len(self.refinery_tab_session_ids))
            self.refinery_stack.setCurrentWidget(self.refinery_history_widget)
            self.populate_refinery_history_table()

        self.loading_refinery_tabs = False

    def refinery_tab_label(self, session):
        label = session.get("name", "Session")
        if session.get("timer_running"):
            label = f"{label} ({self.format_duration(session.get('time_remaining', 0))})"
        return label

    def unique_refinery_session_name(self, name):
        base_name = name.strip() or f"Session {self.refinery_session_counter}"
        existing = {
            session.get("name", "").lower()
            for session in self.refinery_sessions.values()
        }
        if base_name.lower() not in existing:
            return base_name

        suffix = 2
        while f"{base_name} {suffix}".lower() in existing:
            suffix += 1
        return f"{base_name} {suffix}"

    def rename_current_refinery_session(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        session = self.refinery_sessions[self.current_refinery_session]
        new_name = self.refinery_session_name_input.text().strip()
        if not new_name or new_name == session.get("name"):
            self.refinery_session_name_input.setText(session.get("name", ""))
            return

        existing = {
            other.get("name", "").lower()
            for session_id, other in self.refinery_sessions.items()
            if session_id != self.current_refinery_session
        }
        if new_name.lower() in existing:
            new_name = self.unique_refinery_session_name(new_name)

        session["name"] = new_name
        self.refinery_session_name_input.setText(new_name)
        self.refresh_refinery_session_tabs()

    def refinery_session(self):
        self.ensure_refinery_session()
        return self.refinery_sessions[self.current_refinery_session]

    def add_refinery_material(self, material):
        session = self.refinery_session()
        materials = session["materials"]
        if material not in materials:
            materials[material] = {
                "code": self.refinery_material_code(material),
                "qty_cscu": 0.0,
                "yield_cscu": 0.0,
            }
            self.populate_refinery_table()

        self.select_refinery_material(material)

    def add_all_refinery_materials(self):
        session = self.refinery_session()
        for code, material in SHIP_REFINERY_MATERIALS:
            session["materials"].setdefault(material, {
                "code": code,
                "qty_cscu": 0.0,
                "yield_cscu": 0.0,
            })

        self.populate_refinery_table()

    def clear_refinery_session(self):
        session = self.refinery_session()
        session["materials"].clear()
        session["fee"] = 0.0
        session["time_text"] = ""
        session["time_remaining"] = 0
        session["timer_running"] = False
        self.refinery_fee_input.blockSignals(True)
        self.refinery_fee_input.setText("0")
        self.refinery_fee_input.blockSignals(False)
        self.refinery_timer_start_button.setText("Start")
        self.load_refinery_timer_fields()
        self.refresh_refinery_session_tabs()
        self.update_refinery_timer_activity()
        self.populate_refinery_table()

    def close_refinery_session(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        closing_id = self.current_refinery_session
        session_ids = list(self.refinery_sessions.keys())
        closing_index = session_ids.index(closing_id)
        self.refinery_sessions.pop(closing_id, None)

        if self.refinery_sessions:
            remaining_ids = list(self.refinery_sessions.keys())
            self.current_refinery_session = remaining_ids[min(closing_index, len(remaining_ids) - 1)]
            self.load_refinery_session_fields()
            self.populate_refinery_table()
        else:
            self.current_refinery_session = None
            self.create_refinery_session()

        self.refresh_refinery_session_tabs()
        self.update_refinery_timer_activity()

    def save_refinery_session_to_history(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        session_id = self.current_refinery_session
        session = self.refinery_sessions[session_id]
        self.refinery_completed_sessions.append(self.refinery_history_snapshot(session))
        self.close_refinery_session()
        self.populate_refinery_history_table()
        if hasattr(self, "refinery_session_tabs"):
            self.refinery_session_tabs.setCurrentIndex(len(self.refinery_tab_session_ids))

    def refinery_history_snapshot(self, session):
        total_qty, total_yield, gross_value, net_value = self.refinery_session_totals(session)
        return {
            "name": session.get("name", "Session"),
            "station": session.get("station", ""),
            "method": session.get("method", ""),
            "total_qty": total_qty,
            "total_yield": total_yield,
            "gross_value": gross_value,
            "net_value": net_value,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    def populate_refinery_history_table(self):
        if not hasattr(self, "refinery_history_table"):
            return

        sorting_enabled = self.refinery_history_table.isSortingEnabled()
        self.refinery_history_table.setSortingEnabled(False)
        self.refinery_history_table.setRowCount(len(self.refinery_completed_sessions))

        for row_index, (history_index, session) in enumerate(reversed(list(enumerate(self.refinery_completed_sessions)))):
            row_values = [
                session.get("name", "Session"),
                session.get("station", ""),
                session.get("method", ""),
                self.format_cscu_and_scu(session.get("total_qty", 0)),
                self.format_cscu_and_scu(session.get("total_yield", 0)),
                self.format_auec_amount(session.get("gross_value", 0)),
                self.format_auec_amount(session.get("net_value", 0)),
                session.get("saved_at", ""),
            ]
            for column_index, value in enumerate(row_values):
                item = QTableWidgetItem(str(value))
                if column_index == 0:
                    item.setData(Qt.UserRole, history_index)
                self.refinery_history_table.setItem(row_index, column_index, item)

        self.refinery_history_table.setSortingEnabled(sorting_enabled)
        self.refinery_history_empty_label.setVisible(not self.refinery_completed_sessions)

    def remove_selected_refinery_history(self):
        row = self.refinery_history_table.currentRow()
        if row < 0:
            return

        item = self.refinery_history_table.item(row, 0)
        if not item:
            return

        history_index = item.data(Qt.UserRole)
        if not isinstance(history_index, int):
            return

        if 0 <= history_index < len(self.refinery_completed_sessions):
            self.refinery_completed_sessions.pop(history_index)
            self.populate_refinery_history_table()

    def clear_refinery_history(self):
        self.refinery_completed_sessions.clear()
        self.populate_refinery_history_table()

    def remove_selected_refinery_material(self):
        row = self.refinery_table.currentRow()
        if row < 0:
            return

        material_item = self.refinery_table.item(row, 0)
        if not material_item:
            return

        material = material_item.data(Qt.UserRole) or material_item.text()
        session = self.refinery_session()
        session["materials"].pop(material, None)
        self.populate_refinery_table()

    def on_refinery_fee_changed(self):
        session = self.refinery_session()
        session["fee"] = self.parse_float(self.refinery_fee_input.text())
        self.update_refinery_summary()

    def on_refinery_setup_changed(self):
        session = self.refinery_session()
        session["station"] = self.refinery_station_filter.currentText()
        session["method"] = self.refinery_method_filter.currentText()
        self.recalculate_refinery_yields()

    def on_refinery_item_changed(self, item):
        if self.loading_refinery_table or item.column() not in (1, 2, 3, 4):
            return

        material_item = self.refinery_table.item(item.row(), 0)
        if not material_item:
            return

        material = material_item.data(Qt.UserRole) or material_item.text()
        session = self.refinery_session()
        if material not in session["materials"]:
            return

        if item.column() in (1, 2):
            field_name = "qty_cscu"
        else:
            field_name = "yield_cscu"

        value = self.parse_float(item.text())
        if item.column() in (2, 4):
            value = round(value * 100, 4)

        session["materials"][material][field_name] = value
        if field_name == "qty_cscu":
            session["materials"][material]["yield_cscu"] = self.calculate_refinery_yield(material, value)
        else:
            session["materials"][material]["yield_manual"] = True

        self.update_refinery_row_value(item.row(), material)
        self.update_refinery_summary()

    def recalculate_refinery_yields(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        session = self.refinery_session()
        for material, entry in session["materials"].items():
            entry["yield_cscu"] = self.calculate_refinery_yield(material, entry.get("qty_cscu", 0))
            entry["yield_manual"] = False

        self.populate_refinery_table()

    def populate_refinery_table(self):
        session = self.refinery_session()
        materials = session["materials"]
        self.loading_refinery_table = True
        self.refinery_table.setRowCount(len(materials))

        for row_index, material in enumerate(sorted(materials)):
            entry = materials[material]
            price = self.uex_prices.get(material.lower())
            sell_only = self.is_sell_only_refinery_material(material, session)
            sell_value = self.refinery_material_value(
                material,
                self.refinery_sell_quantity_cscu(material, entry, session),
            )
            yield_cscu_item = self.read_only_item("N/A") if sell_only else self.editable_number_item(
                entry.get("yield_cscu", 0)
            )
            yield_scu_item = self.read_only_item("N/A") if sell_only else self.editable_number_item(
                self.format_scu_from_cscu(entry.get("yield_cscu", 0))
            )
            row_items = [
                self.read_only_item(material, material),
                self.editable_number_item(entry.get("qty_cscu", 0)),
                self.editable_number_item(self.format_scu_from_cscu(entry.get("qty_cscu", 0))),
                yield_cscu_item,
                yield_scu_item,
                self.read_only_item(self.format_price(price.price_sell if price else None)),
                self.read_only_item(self.format_auec_amount(sell_value)),
            ]
            row_items[0].setToolTip(entry.get("code", material))
            for col_index, table_item in enumerate(row_items):
                if col_index in (1, 2, 3, 4, 5, 6):
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.refinery_table.setItem(row_index, col_index, table_item)

        self.loading_refinery_table = False
        self.refinery_empty_label.setVisible(not materials)
        self.update_refinery_summary()

    def update_refinery_row_value(self, row, material):
        session = self.refinery_session()
        entry = session["materials"].get(material, {})
        sell_only = self.is_sell_only_refinery_material(material, session)
        sell_value = self.refinery_material_value(
            material,
            self.refinery_sell_quantity_cscu(material, entry, session),
        )
        qty_cscu_item = self.refinery_table.item(row, 1)
        qty_scu_item = self.refinery_table.item(row, 2)
        yield_cscu_item = self.refinery_table.item(row, 3)
        yield_scu_item = self.refinery_table.item(row, 4)
        gross_item = self.refinery_table.item(row, 6)
        if not gross_item:
            return

        self.loading_refinery_table = True
        if qty_cscu_item:
            qty_cscu_item.setText(self.format_number(entry.get("qty_cscu", 0)))
        if qty_scu_item:
            qty_scu_item.setText(self.format_scu_from_cscu(entry.get("qty_cscu", 0)))
        if yield_cscu_item:
            yield_cscu_item.setText("N/A" if sell_only else self.format_number(entry.get("yield_cscu", 0)))
        if yield_scu_item:
            yield_scu_item.setText("N/A" if sell_only else self.format_scu_from_cscu(entry.get("yield_cscu", 0)))
        gross_item.setText(self.format_auec_amount(sell_value))
        self.loading_refinery_table = False

    def update_refinery_summary(self):
        session = self.refinery_session()
        materials = session["materials"]
        total_qty, total_yield, gross_value, net_value = self.refinery_session_totals(session)

        self.refinery_total_qty_label.setText(self.format_cscu_and_scu(total_qty))
        self.refinery_total_yield_label.setText(self.format_cscu_and_scu(total_yield))
        self.refinery_gross_value_label.setText(self.format_auec_amount(gross_value))
        self.refinery_net_value_label.setText(self.format_auec_amount(net_value))
        self.refinery_timer_start_button.setText("Pause" if session.get("timer_running") else "Start")

        missing_prices = [
            material
            for material in materials
            if not self.uex_prices.get(material.lower())
        ]
        if not materials:
            self.refinery_price_status_label.setText(
                "Create a session, click ore buttons, then enter QTY and Yield. "
                "Nothing here is saved locally."
            )
        elif missing_prices:
            self.refinery_price_status_label.setText(
                f"{len(missing_prices)} selected materials need a live UEX refresh. "
                "Prices stay in memory only."
            )
        else:
            self.refinery_price_status_label.setText(
                "All selected materials have live UEX prices in memory only."
            )
        self.populate_refinery_sell_locations(session)

    def refinery_session_totals(self, session):
        materials = session.get("materials", {})
        total_qty = sum(entry.get("qty_cscu", 0) for entry in materials.values())
        total_yield = sum(
            0 if self.is_sell_only_refinery_material(material, session) else entry.get("yield_cscu", 0)
            for material, entry in materials.items()
        )
        gross_value = sum(
            self.refinery_material_value(
                material,
                self.refinery_sell_quantity_cscu(material, entry, session),
            )
            for material, entry in materials.items()
        )
        fee = session.get("fee", 0)
        return total_qty, total_yield, gross_value, gross_value - fee

    def populate_refinery_sell_locations(self, session=None):
        if not hasattr(self, "refinery_sell_locations_table"):
            return

        session = session or self.refinery_session()
        grouped_locations = {}
        has_sell_quantity = False
        has_price_rows = False
        for material, entry in session.get("materials", {}).items():
            sell_quantity = self.refinery_sell_quantity_cscu(material, entry, session)
            if sell_quantity <= 0:
                continue

            has_sell_quantity = True
            prices = self.uex_price_lists.get(material.lower(), [])
            has_price_rows = has_price_rows or bool(prices)
            for price in prices:
                if not price.price_sell:
                    continue

                key = (
                    price.star_system_name,
                    price.location_name,
                    price.terminal_name,
                )
                location = grouped_locations.setdefault(key, {
                    "label": self.format_uex_terminal(price),
                    "materials": [],
                    "value": 0.0,
                })
                value = self.refinery_material_value_from_price(sell_quantity, price.price_sell)
                location["value"] += value
                location["materials"].append(f"{material} ({self.format_auec_amount(value)})")

        rows = sorted(
            grouped_locations.values(),
            key=lambda location: location["value"],
            reverse=True,
        )[:12]

        self.refinery_sell_locations_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            row_values = [
                row["label"],
                self.format_auec_amount(row["value"]),
                ", ".join(row["materials"]),
            ]
            for column_index, value in enumerate(row_values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column_index == 1:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.refinery_sell_locations_table.setItem(row_index, column_index, item)

        if not rows:
            if not session.get("materials"):
                empty_text = "Add materials to see sell location options."
            elif not has_sell_quantity:
                empty_text = "Enter QTY to calculate sell location values."
            elif not has_price_rows:
                empty_text = "Refresh UEX For Session to see matching sell locations."
            else:
                empty_text = "No matching UEX sell locations found for the selected materials."
            self.refinery_sell_locations_empty_label.setText(empty_text)

        self.refinery_sell_locations_empty_label.setVisible(not rows)
        self.refinery_sell_locations_table.setVisible(bool(rows))
        if rows:
            self.resize_refinery_sell_location_columns()

    def resize_refinery_sell_location_columns(self):
        header = self.refinery_sell_locations_table.horizontalHeader()
        for column in range(self.refinery_sell_locations_table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)

        self.refinery_sell_locations_table.resizeColumnsToContents()
        padding = 18
        for column in range(self.refinery_sell_locations_table.columnCount()):
            width = self.refinery_sell_locations_table.columnWidth(column) + padding
            self.refinery_sell_locations_table.setColumnWidth(column, width)
            header.setSectionResizeMode(column, QHeaderView.Interactive)

    def refresh_refinery_uex_prices(self):
        if self.refinery_uex_refresh_running:
            return

        materials = sorted(self.refinery_session()["materials"])
        if not materials:
            QMessageBox.information(
                self,
                "No ores selected",
                "Add one or more refinery materials before refreshing UEX prices.",
            )
            return

        self.refinery_uex_refresh_running = True
        self.refinery_refresh_uex_button.setEnabled(False)
        self.refinery_refresh_uex_button.setText("Refreshing UEX...")

        def load_prices():
            refreshed = 0
            failed = []
            prices_by_material = {}
            price_lists_by_material = {}
            for material in materials:
                try:
                    prices = fetch_commodity_sell_prices(material)
                except (UEXError, requests.RequestException, ValueError) as exc:
                    failed.append(f"{material}: {exc}")
                    continue

                key = material.lower()
                price_lists_by_material[key] = prices
                prices_by_material[key] = prices[0] if prices else None
                refreshed += 1

            return {
                "materials": materials,
                "prices": prices_by_material,
                "price_lists": price_lists_by_material,
                "refreshed": refreshed,
                "failed": failed,
            }

        self.start_background_task(
            load_prices,
            self.on_refinery_uex_prices_refreshed,
            self.on_refinery_uex_prices_error,
            self.finish_refinery_uex_prices_refresh,
        )

    def on_refinery_uex_prices_refreshed(self, result):
        self.uex_prices.update(result["prices"])
        self.uex_price_lists.update(result["price_lists"])
        self.populate_refinery_table()
        failed = result["failed"]
        materials = result["materials"]
        refreshed = result["refreshed"]
        if failed:
            self.refinery_price_status_label.setText(
                f"UEX refreshed {refreshed}/{len(materials)} materials; "
                f"{len(failed)} failed. Prices were not stored locally."
            )
            QMessageBox.warning(
                self,
                "UEX refresh incomplete",
                "\n".join(failed[:5]),
            )
        else:
            self.refinery_price_status_label.setText(
                f"UEX refreshed {refreshed} session materials. Prices were not stored locally."
            )

    def on_refinery_uex_prices_error(self, exc):
        self.refinery_price_status_label.setText(f"UEX refresh failed: {exc}")
        QMessageBox.critical(self, "UEX refresh failed", str(exc))

    def finish_refinery_uex_prices_refresh(self):
        self.refinery_uex_refresh_running = False
        self.refinery_refresh_uex_button.setEnabled(True)
        self.refinery_refresh_uex_button.setText("Refresh UEX For Session")

    def on_refinery_time_changed(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        session = self.refinery_session()
        if session.get("timer_running"):
            return

        remaining_seconds = self.parse_duration_seconds(self.refinery_time_input.text())
        session["time_text"] = self.refinery_time_input.text()
        session["time_remaining"] = remaining_seconds
        self.refinery_timer_remaining_seconds = remaining_seconds
        self.refinery_time_left_label.setText(self.format_duration(remaining_seconds))
        self.update_refinery_session_tab_labels()

    def toggle_refinery_timer(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        session = self.refinery_session()
        if session.get("timer_running"):
            session["timer_running"] = False
            self.refinery_timer_start_button.setText("Start")
            self.update_refinery_timer_activity()
            self.update_refinery_session_tab_labels()
            return

        remaining_seconds = session.get("time_remaining", 0)
        if remaining_seconds <= 0:
            remaining_seconds = self.parse_duration_seconds(self.refinery_time_input.text())

        if remaining_seconds <= 0:
            QMessageBox.information(
                self,
                "No refinery time",
                "Enter a refinery time first. Use HH:MM:SS, MM:SS, or minutes.",
            )
            return

        session["time_text"] = self.refinery_time_input.text()
        session["time_remaining"] = remaining_seconds
        session["timer_running"] = True
        self.refinery_timer_remaining_seconds = remaining_seconds
        self.refinery_time_left_label.setText(self.format_duration(remaining_seconds))
        self.refinery_timer_start_button.setText("Pause")
        self.update_refinery_timer_activity()
        self.update_refinery_session_tab_labels()

    def reset_refinery_timer(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        session = self.refinery_session()
        remaining_seconds = self.parse_duration_seconds(self.refinery_time_input.text())
        session["time_text"] = self.refinery_time_input.text()
        session["time_remaining"] = remaining_seconds
        session["timer_running"] = False
        self.refinery_timer_remaining_seconds = remaining_seconds
        self.refinery_timer_start_button.setText("Start")
        self.refinery_time_left_label.setText(self.format_duration(remaining_seconds))
        self.update_refinery_timer_activity()
        self.update_refinery_session_tab_labels()

    def tick_refinery_timer(self):
        any_running = False
        for session in self.refinery_sessions.values():
            if not session.get("timer_running"):
                continue

            remaining_seconds = max(0, int(session.get("time_remaining", 0)) - 1)
            session["time_remaining"] = remaining_seconds
            if remaining_seconds <= 0:
                session["timer_running"] = False
            else:
                any_running = True

        if self.current_refinery_session in self.refinery_sessions:
            current = self.refinery_sessions[self.current_refinery_session]
            self.refinery_timer_remaining_seconds = current.get("time_remaining", 0)
            self.refinery_time_left_label.setText(self.format_duration(self.refinery_timer_remaining_seconds))
            self.refinery_timer_start_button.setText("Pause" if current.get("timer_running") else "Start")

        self.update_refinery_session_tab_labels()
        if not any_running:
            self.refinery_timer.stop()

    def update_refinery_timer_activity(self):
        if any(session.get("timer_running") for session in self.refinery_sessions.values()):
            if not self.refinery_timer.isActive():
                self.refinery_timer.start()
            return

        if self.refinery_timer.isActive():
            self.refinery_timer.stop()

    def update_refinery_session_tab_labels(self):
        if not hasattr(self, "refinery_session_tabs"):
            return

        for index, session_id in enumerate(self.refinery_tab_session_ids):
            session = self.refinery_sessions.get(session_id)
            if session:
                self.refinery_session_tabs.setTabText(index, self.refinery_tab_label(session))

    def load_refinery_timer_fields(self):
        session = self.refinery_session()
        self.refinery_time_input.blockSignals(True)
        self.refinery_time_input.setText(session.get("time_text", ""))
        self.refinery_time_input.blockSignals(False)
        self.refinery_timer_remaining_seconds = session.get("time_remaining", 0)
        self.refinery_time_left_label.setText(self.format_duration(self.refinery_timer_remaining_seconds))
        self.refinery_timer_start_button.setText("Pause" if session.get("timer_running") else "Start")

    def parse_duration_seconds(self, value):
        text = str(value or "").strip()
        if not text:
            return 0

        if ":" in text:
            parts = [part.strip() for part in text.split(":")]
            if len(parts) not in (2, 3):
                return 0
            try:
                numbers = [int(part) for part in parts]
            except ValueError:
                return 0

            if len(numbers) == 2:
                minutes, seconds = numbers
                return max(0, minutes * 60 + seconds)

            hours, minutes, seconds = numbers
            return max(0, hours * 3600 + minutes * 60 + seconds)

        return max(0, int(self.parse_float(text) * 60))

    def format_duration(self, seconds):
        seconds = max(0, int(seconds or 0))
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"

    def refinery_material_code(self, material):
        for code, candidate in SHIP_REFINERY_MATERIALS:
            if candidate == material:
                return code

        return material[:4].upper()

    def refinery_material_tooltip(self, material):
        if self.is_gem_selling_material(material):
            return f"{material}\nGem selling only. Cannot be refined; value uses QTY."

        details = SALVAGE_REFINERY_DETAILS.get(material)
        if not details:
            return material

        return (
            f"{material}\n"
            f"{details['density']} | {details['yield']} | {details['time']}"
        )

    def select_refinery_material(self, material):
        for row in range(self.refinery_table.rowCount()):
            item = self.refinery_table.item(row, 0)
            if item and item.data(Qt.UserRole) == material:
                self.refinery_table.selectRow(row)
                return

    def is_gem_selling_material(self, material):
        return any(candidate == material for _, candidate in GEM_SELLING_MATERIALS)

    def is_no_refinery_session(self, session=None):
        if session is not None:
            station_text = session.get("station", "")
        elif hasattr(self, "refinery_station_filter"):
            station_text = self.refinery_station_filter.currentText()
        else:
            station_text = ""

        return str(station_text).startswith("No Refinery")

    def is_sell_only_refinery_material(self, material, session=None):
        return self.is_gem_selling_material(material) or self.is_no_refinery_session(session)

    def refinery_sell_quantity_cscu(self, material, entry, session=None):
        if self.is_sell_only_refinery_material(material, session):
            return self.parse_float(entry.get("qty_cscu", 0))

        return self.parse_float(entry.get("yield_cscu", 0))

    def refinery_material_value(self, material, yield_cscu):
        price = self.uex_prices.get(material.lower())
        if not price or not price.price_sell:
            return 0.0

        return self.refinery_material_value_from_price(yield_cscu, price.price_sell)

    def refinery_material_value_from_price(self, quantity_cscu, price_sell):
        return (self.parse_float(quantity_cscu) / 100) * self.parse_float(price_sell)

    def calculate_refinery_yield(self, material, qty_cscu):
        qty = self.parse_float(qty_cscu)
        if qty <= 0 or self.is_sell_only_refinery_material(material):
            return 0.0

        method = self.selected_refinery_method()
        method_yield = method.yield_factor if method else REFINERY_METHOD_YIELD_FALLBACKS.get(
            self.refinery_method_filter.currentText(),
            0.0,
        )
        if method_yield <= 0:
            return 0.0

        station = self.selected_refinery_station()
        bonus = station.bonuses.get(self.canonical_refinery_material(material), 0.0) if station else 0.0
        salvage_multiplier = SALVAGE_REFINERY_DETAILS.get(material, {}).get("yield_multiplier", 1.0)
        return max(0.0, float(round(qty * method_yield * (1 + bonus) * salvage_multiplier)))

    def selected_refinery_station(self):
        return self.refinery_station_lookup.get(
            self.refinery_option_key(self.refinery_station_filter.currentText())
        )

    def selected_refinery_method(self):
        return self.refinery_method_lookup.get(
            self.refinery_option_key(self.refinery_method_filter.currentText())
        )

    def canonical_refinery_material(self, material):
        aliases = {
            "Quantanium": "Quantainium",
        }
        return aliases.get(material, material)

    def refinery_option_key(self, value):
        return " ".join(str(value or "").lower().replace(":", " ").replace("-", " ").split())

    def format_scu_from_cscu(self, cscu):
        return self.format_number(self.parse_float(cscu) / 100)

    def format_cscu_and_scu(self, cscu):
        return f"{self.format_number(cscu)} cSCU / {self.format_scu_from_cscu(cscu)} SCU"

    def read_only_item(self, value, user_data=None):
        item = QTableWidgetItem(str(value))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        if user_data is not None:
            item.setData(Qt.UserRole, user_data)
        return item

    def editable_number_item(self, value):
        item = QTableWidgetItem(self.format_number(value))
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

    def populate_location_results(self):
        query = self.location_search_input.text().strip().lower()
        system_filter = self.location_system_filter.currentText()
        deposit_filter = self.location_focus_filter.currentText()
        grouped = {}

        for location in self.mining_data.locations:
            if system_filter != "All systems" and location.system != system_filter:
                continue
            if deposit_filter != "All mining types" and location.deposit_type != deposit_filter:
                continue
            if query and query not in self.location_search_text(location):
                continue

            key = (location.system, location.body, location.deposit_type)
            group = grouped.setdefault(key, {"minerals": set(), "notes": set()})
            group["minerals"].add(location.mineral)
            if location.notes:
                group["notes"].add(location.notes)

        rows = []
        for (system, body, deposit_type), group in grouped.items():
            minerals = sorted(group["minerals"])
            rows.append([
                system,
                body,
                deposit_type,
                ", ".join(minerals),
                str(len(minerals)),
                ", ".join(sorted(group["notes"])),
            ])

        rows.sort(key=lambda row: (row[0], row[1].lower(), row[2]))
        self.set_table_rows(self.location_table, rows)
        self.location_empty_label.setVisible(not rows)

    def populate_scan_identifier(self):
        tokens = self.parse_scan_tokens(self.scan_value_input.text())
        category_filter = self.scan_category_filter.currentText()
        rows = []

        for signature in self.mining_data.scan_signatures:
            if category_filter != "All categories" and signature.category != category_filter:
                continue

            matches = self.match_scan_values(signature.values, tokens)
            if tokens and not matches:
                continue

            rows.append([
                signature.resource,
                signature.category,
                f"{signature.max_multiplier}x",
                self.format_signature_values(matches) if matches else "",
                self.format_signature_values(signature.values),
            ])

        rows.sort(key=lambda row: (self.scan_category_rank(row[1]), row[0].lower()))
        self.set_table_rows(self.scan_signature_table, rows)
        self.scan_empty_label.setVisible(not rows)

    def populate_quality_bands(self):
        query = self.quality_search_input.text().strip().lower()
        score = self.parse_int(self.quality_score_input.text())
        rows = []

        for row in self.mining_data.quality_bands:
            if query and query not in row.resource.lower():
                continue

            matched_band = self.quality_match_text(row, score)
            rows.append([
                row.resource,
                matched_band,
                *[
                    self.format_quality_value(value)
                    for value in row.values
                ],
            ])

        rows.sort(key=lambda values: values[0].lower())
        self.set_table_rows(self.quality_bands_table, rows)
        self.quality_empty_label.setVisible(not rows)

    def populate_equipment_results(self):
        query = self.equipment_search_input.text().strip().lower()
        type_filter = self.equipment_type_filter.currentText()
        size_filter = self.equipment_size_filter.currentText()
        rows = []

        for item in self.mining_data.equipment:
            if type_filter != "All equipment" and item.equipment_type != type_filter:
                continue
            if size_filter != "Any size" and item.size != size_filter:
                continue
            searchable = " ".join((
                item.name,
                item.equipment_type,
                item.size,
                str(item.shop_count),
                item.best_shop,
                item.best_location,
                item.effect,
                item.notes,
            )).lower()
            if query and query not in searchable:
                continue

            rows.append([
                item.name,
                item.equipment_type,
                item.size,
                self.format_price(item.price),
                f"{item.shop_count} locations" if item.shop_count else "No known shops",
                item.best_shop,
                item.best_location,
                item.effect,
                item.notes,
            ])

        rows.sort(key=lambda row: (row[1], row[2], row[0].lower()))
        self.set_table_rows(self.equipment_table, rows)
        self.equipment_empty_label.setVisible(not rows)

    def location_search_text(self, location):
        return " ".join((
            location.mineral,
            location.system,
            location.body,
            location.deposit_type,
            location.notes,
        )).lower()

    def set_table_rows(self, table, rows, resize_columns=True):
        sorting_enabled = table.isSortingEnabled()
        table.setUpdatesEnabled(False)
        table.setSortingEnabled(False)
        try:
            table.setRowCount(len(rows))

            for row_index, row_values in enumerate(rows):
                for col_index, value in enumerate(row_values):
                    item = QTableWidgetItem(str(value))
                    table.setItem(row_index, col_index, item)

            if resize_columns:
                table.resizeColumnsToContents()
        finally:
            table.setSortingEnabled(sorting_enabled)
            table.setUpdatesEnabled(True)

    def parse_scan_tokens(self, text):
        tokens = []
        for raw_token in text.split(","):
            token = raw_token.strip().replace(" ", "")
            if not token:
                continue

            if token.startswith("~"):
                center = self.parse_int(token[1:])
                if center is None:
                    continue
                tokens.append((int(center * 0.9), int(center * 1.1)))
                continue

            if "-" in token:
                left, right = token.split("-", 1)
                low = self.parse_int(left)
                high = self.parse_int(right)
                if low is None or high is None:
                    continue
                tokens.append((min(low, high), max(low, high)))
                continue

            value = self.parse_int(token)
            if value is not None:
                tokens.append((value, value))

        return tokens

    def match_scan_values(self, values, tokens):
        if not tokens:
            return []

        matches = []
        for value in values:
            for low, high in tokens:
                if low <= value <= high:
                    matches.append(value)
                    break

        return matches

    def scan_category_rank(self, category):
        order = {
            "Legendary": 0,
            "Epic": 1,
            "Rare": 2,
            "Uncommon": 3,
            "Common": 4,
            "ROC Mineables": 5,
            "FPS Mineables": 6,
            "Salvage": 7,
        }
        return order.get(category, 99)

    def quality_match_text(self, row, score):
        if score is None:
            return ""

        for label, value in zip(self.mining_data.quality_band_labels, row.values):
            bounds = label.rstrip("Q").split("-", 1)
            if len(bounds) != 2:
                continue
            low = self.parse_int(bounds[0])
            high = self.parse_int(bounds[1])
            if low is None or high is None:
                continue
            if low <= score <= high:
                return f"{label}: {self.format_quality_value(value)}"

        return "Out of range"

    def parse_int(self, value):
        cleaned = "".join(char for char in str(value) if char.isdigit())
        if not cleaned:
            return None

        try:
            return int(cleaned)
        except ValueError:
            return None

    def parse_float(self, value):
        text = str(value or "").strip().replace(" ", "")
        if not text:
            return 0.0

        if "," in text and "." not in text:
            parts = text.split(",")
            if len(parts[-1]) == 3 and all(part.isdigit() for part in parts):
                text = "".join(parts)
            else:
                text = text.replace(",", ".")
        else:
            text = text.replace(",", "")

        cleaned = "".join(char for char in text if char.isdigit() or char in ".-")
        if cleaned in ("", "-", ".", "-."):
            return 0.0

        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def format_signature_values(self, values):
        return " | ".join(f"{value:,}" for value in values)

    def format_quality_value(self, value):
        if value is None:
            return "-"

        return str(value)

    def format_price(self, value):
        if value in (None, "", 0):
            return "N/A"

        try:
            return f"{float(value):,.0f} aUEC"
        except (TypeError, ValueError):
            return str(value)

    def format_number(self, value):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)

        if abs(numeric - round(numeric)) < 0.001:
            return f"{numeric:,.0f}"

        return f"{numeric:,.2f}"

    def format_auec_amount(self, value):
        return f"{self.format_number(value)} aUEC"

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
            table.horizontalHeader().setSectionResizeMode(index, QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(False)
        return table

    def create_empty_state(self, text):
        label = QLabel(text)
        label.setObjectName("emptyState")
        label.setAlignment(Qt.AlignCenter)
        return label
