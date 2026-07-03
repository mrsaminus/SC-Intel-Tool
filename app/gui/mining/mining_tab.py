from .shared import *
from .equipment_panel import MiningEquipmentMixin
from .locations_panel import MiningLocationsMixin
from .mining_helpers import MiningHelpersMixin
from .ore_finder_panel import MiningOreFinderMixin
from .overview_panel import MiningOverviewMixin
from .quality_bands_panel import MiningQualityBandsMixin
from .refinery_panel import MiningRefineryMixin
from .rock_breaker_panel import MiningRockBreakerMixin
from .scan_id_panel import MiningScanIdMixin


class MiningTab(
    MiningOverviewMixin,
    MiningOreFinderMixin,
    MiningLocationsMixin,
    MiningScanIdMixin,
    MiningQualityBandsMixin,
    MiningRefineryMixin,
    MiningRockBreakerMixin,
    MiningEquipmentMixin,
    MiningHelpersMixin,
    BackgroundTaskMixin,
    QWidget,
):
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
        self._initial_load_started = False
        self._initial_load_done = False

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = self.create_module_header(
            "Mining / Salvage Intelligence",
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

        self.mining_scroll_area = install_scroll_area(self, content_widget)
        self.connect_signals()
        self.mining_status_label.setText("Mining reference tables will populate when opened.")

    def ensure_initial_load(self):
        if self._initial_load_done:
            return
        self.populate_mining_tables()

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

