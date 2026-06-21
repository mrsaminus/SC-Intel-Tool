import json

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database import get_app_setting, set_app_setting
from app.trading_data import fetch_trading_opportunities
from app.trading_storage import TradingRouteRecord, add_recent_trading_route, save_trading_route
from app.watchlists.service import add_trading_route_watch

from ..sortable_table_item import ROW_ROLE, SORT_ROLE, SortableTableWidgetItem
from ..table_utils import configure_readable_table_columns
from ..workers import BackgroundTaskMixin
from .create_routes_engine import (
    DEFAULT_LOCATION_TYPES,
    DEFAULT_SYSTEMS,
    LOCATION_TYPE_OPTIONS,
    OPTIMIZATION_MODES,
    SYSTEM_OPTIONS,
    TOP_ROUTE_OPTIONS,
    CreateRoutesSettings,
    generate_create_routes,
    notes_text,
)
from .create_routes_filters import MultiSelectFilter
from .reference_data import get_trading_reference_service
from .route_quality import copy_to_clipboard
from .route_summary import (
    format_auec,
    format_route_summary,
    is_complete_route_record,
)
from .ship_selection import configure_ship_combo, fill_cargo_from_ship, selected_ship_name, update_ship_combo


SETTINGS_KEY = "trading.create_routes.settings"


class CreateRoutesTab(BackgroundTaskMixin, QWidget):
    def __init__(self, reference_service=None):
        super().__init__()
        self.reference_service = reference_service or get_trading_reference_service()
        self.refresh_running = False
        self.route_generation_running = False
        self.route_generation_request_id = 0
        self.pending_route_generation = False
        self.all_opportunities = []
        self.visible_results = []
        self.price_row_count = 0
        self.loading_settings = False

        self.settings_save_timer = QTimer(self)
        self.settings_save_timer.setSingleShot(True)
        self.settings_save_timer.setInterval(350)
        self.settings_save_timer.timeout.connect(self.save_current_settings)

        self.route_generation_timer = QTimer(self)
        self.route_generation_timer.setSingleShot(True)
        self.route_generation_timer.setInterval(120)
        self.route_generation_timer.timeout.connect(self.request_route_generation)

        self.build_ui()
        self.connect_signals()
        self.load_saved_settings()
        self.connect_reference_service()
        self.update_details()

    def connect_reference_service(self):
        self.reference_service.loaded.connect(self.on_reference_loaded)
        if self.reference_service.data is not None:
            self.on_reference_loaded(self.reference_service.data)

    def on_reference_loaded(self, data):
        current_ship = self.ship_combo.currentText().strip()
        update_ship_combo(self.ship_combo, data.ships)
        if current_ship:
            self.ship_combo.setCurrentText(current_ship)

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_header())
        layout.addWidget(self.create_controls())
        layout.addWidget(self.create_results_table(), 1)

        self.empty_label = QLabel("Choose a ship and generate routes to load smart UEX trade suggestions.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        self.detail_label = QLabel("Select a generated route to see cargo, profit and safety notes.")
        self.detail_label.setObjectName("valueText")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.copy_summary_button = QPushButton("Copy Route Summary")
        self.copy_summary_button.setEnabled(False)
        self.save_route_button = QPushButton("Save Route")
        self.save_route_button.setEnabled(False)
        self.watch_route_button = QPushButton("Add To Watchlist")
        self.watch_route_button.setEnabled(False)
        button_row.addWidget(self.copy_summary_button)
        button_row.addWidget(self.save_route_button)
        button_row.addWidget(self.watch_route_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.setLayout(layout)

    def create_header(self):
        header = QFrame()
        header.setObjectName("playerCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title = QLabel("Create Routes")
        title.setObjectName("moduleHeading")
        subtitle = QLabel(
            "Smart route generation for the ship, cargo, budget and safety profile you actually plan to fly."
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

        title = QLabel("ROUTE ASSISTANT")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        primary = QHBoxLayout()
        primary.setSpacing(8)

        self.ship_combo = QComboBox()
        configure_ship_combo(self.ship_combo)
        self.ship_combo.setMinimumWidth(180)

        self.cargo_input = QLineEdit()
        self.cargo_input.setPlaceholderText("Cargo SCU")
        self.cargo_input.setMaximumWidth(110)
        self.cargo_input.setToolTip("Cargo capacity in SCU. Selecting a known ship fills this automatically.")

        self.max_investment_input = QLineEdit()
        self.max_investment_input.setPlaceholderText("Max investment...")
        self.max_investment_input.setMaximumWidth(145)
        self.max_investment_input.setToolTip("Optional max aUEC budget. Blank means unlimited.")

        self.optimization_combo = QComboBox()
        self.optimization_combo.addItems(OPTIMIZATION_MODES)
        self.optimization_combo.setMinimumWidth(150)

        self.top_count_combo = QComboBox()
        self.top_count_combo.addItems([str(value) for value in TOP_ROUTE_OPTIONS])
        self.top_count_combo.setCurrentText("10")
        self.top_count_combo.setMaximumWidth(90)

        self.generate_button = QPushButton("Generate Routes")
        primary.addWidget(self.ship_combo)
        primary.addWidget(self.cargo_input)
        primary.addWidget(self.max_investment_input)
        primary.addWidget(self.optimization_combo)
        primary.addWidget(QLabel("Top"))
        primary.addWidget(self.top_count_combo)
        primary.addWidget(self.generate_button)
        layout.addLayout(primary)

        systems_row = QHBoxLayout()
        systems_row.setSpacing(8)
        self.system_filter = MultiSelectFilter("Systems", SYSTEM_OPTIONS, DEFAULT_SYSTEMS)
        self.select_all_systems_button = QPushButton("Select All Systems")
        self.deselect_all_systems_button = QPushButton("Deselect Systems")
        systems_row.addWidget(QLabel("Systems"))
        systems_row.addWidget(self.system_filter, 1)
        systems_row.addWidget(self.select_all_systems_button)
        systems_row.addWidget(self.deselect_all_systems_button)
        layout.addLayout(systems_row)

        locations_row = QHBoxLayout()
        locations_row.setSpacing(8)
        self.location_type_filter = MultiSelectFilter(
            "Location Types",
            LOCATION_TYPE_OPTIONS,
            DEFAULT_LOCATION_TYPES,
        )
        self.select_all_location_types_button = QPushButton("Select All Types")
        self.deselect_all_location_types_button = QPushButton("Deselect Types")
        locations_row.addWidget(QLabel("Location Types"))
        locations_row.addWidget(self.location_type_filter, 1)
        locations_row.addWidget(self.select_all_location_types_button)
        locations_row.addWidget(self.deselect_all_location_types_button)
        layout.addLayout(locations_row)

        checkbox_grid = QGridLayout()
        checkbox_grid.setContentsMargins(0, 2, 0, 0)
        checkbox_grid.setHorizontalSpacing(14)
        checkbox_grid.setVerticalSpacing(4)
        self.avoid_dangerous_checkbox = QCheckBox("Avoid dangerous routes")
        self.avoid_hidden_checkbox = QCheckBox("Avoid hidden locations")
        self.avoid_non_armistice_checkbox = QCheckBox("Avoid non-armistice")
        self.allow_pyro_checkbox = QCheckBox("Allow Pyro")
        self.allow_contested_checkbox = QCheckBox("Allow contested areas")
        self.include_illegal_checkbox = QCheckBox("Include illegal commodities")
        self.legal_goods_checkbox = QCheckBox("Legal goods")
        self.stable_routes_checkbox = QCheckBox("Stable routes")
        self.high_profit_checkbox = QCheckBox("High profit")
        self.high_volatility_checkbox = QCheckBox("High volatility")
        self.high_volatility_checkbox.setToolTip(
            "No dedicated volatility feed is available yet; this allows high-margin outlier routes."
        )
        self.mission_goods_checkbox = QCheckBox("Mission goods")
        self.mission_goods_checkbox.setToolTip("Mission-good tagging is not available in current UEX route data.")

        defaults_checked = (
            self.avoid_dangerous_checkbox,
            self.avoid_hidden_checkbox,
            self.avoid_non_armistice_checkbox,
            self.legal_goods_checkbox,
            self.stable_routes_checkbox,
            self.high_profit_checkbox,
        )
        for checkbox in defaults_checked:
            checkbox.setChecked(True)

        checkboxes = (
            self.avoid_dangerous_checkbox,
            self.avoid_hidden_checkbox,
            self.avoid_non_armistice_checkbox,
            self.allow_pyro_checkbox,
            self.allow_contested_checkbox,
            self.include_illegal_checkbox,
            self.legal_goods_checkbox,
            self.stable_routes_checkbox,
            self.high_profit_checkbox,
            self.high_volatility_checkbox,
            self.mission_goods_checkbox,
        )
        for index, checkbox in enumerate(checkboxes):
            checkbox_grid.addWidget(checkbox, index // 4, index % 4)
        layout.addLayout(checkbox_grid)

        self.faction_note_label = QLabel(
            "Faction filters: planned only when route data exposes reliable faction ownership."
        )
        self.faction_note_label.setObjectName("moduleSubtitle")
        layout.addWidget(self.faction_note_label)

        self.status_label = QLabel("UEX market data is loaded on demand. Settings are stored locally.")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        card.setLayout(layout)
        return card

    def create_results_table(self):
        self.routes_table = QTableWidget(0, 10)
        self.routes_table.setHorizontalHeaderLabels([
            "Rank",
            "Commodity",
            "Buy Location",
            "Sell Location",
            "Cargo SCU",
            "Investment",
            "Expected Profit",
            "Profit / SCU",
            "Quality",
            "Notes",
        ])
        self.routes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.routes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.routes_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.routes_table.setAlternatingRowColors(True)
        self.routes_table.setSortingEnabled(True)
        configure_readable_table_columns(self.routes_table, min_width=95, max_width=390, stretch_last=True)
        return self.routes_table

    def connect_signals(self):
        self.generate_button.clicked.connect(self.generate_routes)
        self.ship_combo.currentTextChanged.connect(self.on_ship_changed)
        self.cargo_input.textChanged.connect(self.on_options_changed)
        self.max_investment_input.textChanged.connect(self.on_options_changed)
        self.optimization_combo.currentTextChanged.connect(self.on_options_changed)
        self.top_count_combo.currentTextChanged.connect(self.on_options_changed)
        self.system_filter.changed.connect(self.on_options_changed)
        self.location_type_filter.changed.connect(self.on_options_changed)
        self.select_all_systems_button.clicked.connect(self.system_filter.select_all)
        self.deselect_all_systems_button.clicked.connect(self.system_filter.deselect_all)
        self.select_all_location_types_button.clicked.connect(self.location_type_filter.select_all)
        self.deselect_all_location_types_button.clicked.connect(self.location_type_filter.deselect_all)

        for checkbox in self.preference_checkboxes():
            checkbox.stateChanged.connect(self.on_options_changed)

        self.routes_table.itemSelectionChanged.connect(self.update_details)
        self.routes_table.itemDoubleClicked.connect(self.show_selected_route_dialog)
        self.copy_summary_button.clicked.connect(self.copy_route_summary)
        self.save_route_button.clicked.connect(self.save_selected_route)
        self.watch_route_button.clicked.connect(self.add_selected_route_to_watchlist)

    def preference_checkboxes(self):
        return (
            self.avoid_dangerous_checkbox,
            self.avoid_hidden_checkbox,
            self.avoid_non_armistice_checkbox,
            self.allow_pyro_checkbox,
            self.allow_contested_checkbox,
            self.include_illegal_checkbox,
            self.legal_goods_checkbox,
            self.stable_routes_checkbox,
            self.high_profit_checkbox,
            self.high_volatility_checkbox,
            self.mission_goods_checkbox,
        )

    def on_ship_changed(self):
        if not self.loading_settings:
            fill_cargo_from_ship(self.ship_combo, self.cargo_input, self.status_label)
        self.on_options_changed()

    def on_options_changed(self):
        if self.loading_settings:
            return
        self.settings_save_timer.start()
        if self.all_opportunities:
            self.route_generation_timer.start()

    def generate_routes(self):
        if self.refresh_running or self.route_generation_running:
            return

        self.save_current_settings()
        self.refresh_running = True
        self.generate_button.setEnabled(False)
        self.generate_button.setText("Loading...")
        self.status_label.setText("Loading UEX market data for smart route generation...")
        self.empty_label.setText("Loading route data...")
        self.empty_label.setVisible(True)

        self.start_background_task(
            lambda: fetch_trading_opportunities(include_unprofitable=False),
            self.on_trading_data_loaded,
            self.on_trading_data_error,
            self.finish_refresh,
        )

    def on_trading_data_loaded(self, result):
        opportunities, price_row_count = result
        self.all_opportunities = opportunities
        self.price_row_count = price_row_count
        self.request_route_generation()

    def on_trading_data_error(self, exc):
        self.all_opportunities = []
        self.visible_results = []
        self.pending_route_generation = False
        self.route_generation_request_id += 1
        self.routes_table.setRowCount(0)
        self.empty_label.setText("UEX trading data failed to load. Try again later.")
        self.empty_label.setVisible(True)
        self.detail_label.setText("Route generation failed because market data could not be loaded.")
        self.status_label.setText(f"Failed to load UEX trading data: {exc}")
        self.set_route_buttons_enabled(False)

    def finish_refresh(self):
        self.refresh_running = False
        if not self.route_generation_running:
            self.generate_button.setEnabled(True)
            self.generate_button.setText("Generate Routes")

    def populate_routes(self):
        self.request_route_generation()

    def request_route_generation(self):
        if not self.all_opportunities:
            self.visible_results = []
            self.render_routes_table()
            return
        if self.route_generation_running:
            self.pending_route_generation = True
            return

        self.start_route_generation()

    def start_route_generation(self):
        if not self.all_opportunities:
            return
        settings = self.current_settings()
        opportunities = tuple(self.all_opportunities)
        self.route_generation_running = True
        self.pending_route_generation = False
        self.route_generation_request_id += 1
        request_id = self.route_generation_request_id
        self.generate_button.setEnabled(False)
        self.generate_button.setText("Calculating...")
        self.status_label.setText("Calculating route suggestions from loaded UEX data...")
        self.empty_label.setText("Calculating route suggestions...")
        self.empty_label.setVisible(True)

        self.start_background_task(
            lambda: generate_create_routes(opportunities, settings),
            lambda results, current_request=request_id: self.on_routes_generated(current_request, results),
            lambda exc, current_request=request_id: self.on_route_generation_error(current_request, exc),
            lambda current_request=request_id: self.finish_route_generation(current_request),
        )

    def on_routes_generated(self, request_id, results):
        if request_id != self.route_generation_request_id:
            return
        self.visible_results = list(results or [])
        self.render_routes_table()

    def on_route_generation_error(self, request_id, exc):
        if request_id != self.route_generation_request_id:
            return
        self.visible_results = []
        self.routes_table.setRowCount(0)
        self.empty_label.setText("Route generation failed. Adjust filters or reload UEX data.")
        self.empty_label.setVisible(True)
        self.detail_label.setText("Route generation failed before results could be built.")
        self.status_label.setText(f"Route generation failed: {exc}")
        self.set_route_buttons_enabled(False)

    def finish_route_generation(self, request_id):
        if request_id != self.route_generation_request_id:
            return
        self.route_generation_running = False
        if self.pending_route_generation:
            self.pending_route_generation = False
            self.start_route_generation()
            return
        if not self.refresh_running:
            self.generate_button.setEnabled(True)
            self.generate_button.setText("Generate Routes")

    def render_routes_table(self):

        sorting_enabled = self.routes_table.isSortingEnabled()
        self.routes_table.setSortingEnabled(False)
        self.routes_table.setRowCount(len(self.visible_results))

        for row_index, result in enumerate(self.visible_results):
            opportunity = result.opportunity
            estimate = result.estimate
            values = [
                result.rank,
                opportunity.commodity,
                opportunity.buy_location,
                opportunity.sell_location,
                self.format_number(estimate.effective_cargo_scu),
                format_auec(estimate.estimated_buy_cost),
                format_auec(estimate.estimated_total_profit),
                format_auec(opportunity.profit_per_scu),
                result.quality.label,
                ", ".join(result.notes[:4]),
            ]
            sort_values = [
                result.rank,
                opportunity.commodity,
                opportunity.buy_location,
                opportunity.sell_location,
                estimate.effective_cargo_scu,
                estimate.estimated_buy_cost,
                estimate.estimated_total_profit,
                opportunity.profit_per_scu,
                result.quality.sort_value,
                result.risk_score,
            ]
            for column, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setData(SORT_ROLE, sort_values[column])
                item.setData(ROW_ROLE, row_index)
                if column in (0, 4, 5, 6, 7):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if column == 8 and result.quality.flags:
                    item.setToolTip(" | ".join(result.quality.flags))
                if column == 9:
                    item.setToolTip(notes_text(result))
                self.routes_table.setItem(row_index, column, item)

        self.routes_table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(self.routes_table, min_width=95, max_width=390, stretch_last=True)
        self.empty_label.setVisible(not self.visible_results)

        if self.visible_results:
            self.status_label.setText(
                f"Generated {len(self.visible_results)} routes from {len(self.all_opportunities)} "
                f"UEX buy/sell comparisons and {self.price_row_count} price rows."
            )
            self.update_details()
        elif self.all_opportunities:
            self.empty_label.setText(
                "No routes matched your filters. Try enabling more systems, allowing more location types, "
                "or reducing safety restrictions."
            )
            self.detail_label.setText("No routes matched the current Create Routes filters.")
            self.set_route_buttons_enabled(False)
            self.status_label.setText("No smart routes matched the current filter profile.")
        else:
            self.empty_label.setText("Generate routes to load UEX commodity opportunities.")
            self.set_route_buttons_enabled(False)

    def update_details(self):
        result = self.selected_result()
        if not result:
            self.detail_label.setText("Select a generated route to see cargo, profit and safety notes.")
            self.set_route_buttons_enabled(False)
            return

        record = self.route_record_for_result(result)
        self.detail_label.setText(self.details_text(result, record))
        self.set_route_buttons_enabled(is_complete_route_record(record))

    def set_route_buttons_enabled(self, enabled):
        self.copy_summary_button.setEnabled(enabled)
        self.save_route_button.setEnabled(enabled)
        self.watch_route_button.setEnabled(enabled)

    def selected_result(self):
        row = self.routes_table.currentRow()
        if row < 0:
            return self.visible_results[0] if self.visible_results else None
        item = self.routes_table.item(row, 0)
        if not item:
            return None
        index = item.data(ROW_ROLE)
        if index is None or index >= len(self.visible_results):
            return None
        return self.visible_results[index]

    def route_record_for_result(self, result):
        opportunity = result.opportunity
        estimate = result.estimate
        return TradingRouteRecord(
            source=opportunity.source,
            commodity=opportunity.commodity,
            buy_location=opportunity.buy_location,
            sell_location=opportunity.sell_location,
            buy_price=opportunity.buy_price,
            sell_price=opportunity.sell_price,
            profit_per_scu=opportunity.profit_per_scu,
            cargo_scu=estimate.effective_cargo_scu,
            buy_cost=estimate.estimated_buy_cost,
            total_profit=estimate.estimated_total_profit,
            quality=result.quality.label,
            notes=notes_text(result),
        )

    def details_text(self, result, record):
        return "\n".join((
            format_route_summary(record),
            "",
            f"Rank: {result.rank}",
            f"Systems: {result.buy_system} -> {result.sell_system}",
            f"Location types: {result.buy_location_type} -> {result.sell_location_type}",
            f"Risk score: {result.risk_score} (explainable keyword/location heuristic)",
            f"Restrictions matched: {notes_text(result)}",
        ))

    def copy_route_summary(self):
        result = self.selected_result()
        if not result:
            return
        record = self.route_record_for_result(result)
        copy_to_clipboard(self.details_text(result, record))
        add_recent_trading_route(record)
        self.status_label.setText("Route summary copied and added to recent routes.")

    def save_selected_route(self):
        result = self.selected_result()
        if not result:
            return
        record = self.route_record_for_result(result)
        if not is_complete_route_record(record):
            self.status_label.setText("This route is missing required data and cannot be saved.")
            return
        save_trading_route(record)
        add_recent_trading_route(record)
        self.status_label.setText("Route saved locally.")

    def add_selected_route_to_watchlist(self):
        result = self.selected_result()
        if not result:
            return
        record = self.route_record_for_result(result)
        if not is_complete_route_record(record):
            self.status_label.setText("This route is missing required data and cannot be watched.")
            return
        add_trading_route_watch(record)
        add_recent_trading_route(record)
        self.status_label.setText("Route added to Watchlists.")

    def show_selected_route_dialog(self):
        result = self.selected_result()
        if not result:
            return
        record = self.route_record_for_result(result)
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Routes - Route Details")
        layout = QVBoxLayout()
        details = QTextEdit()
        details.setReadOnly(True)
        details.setPlainText(self.details_text(result, record))
        layout.addWidget(details)
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.setLayout(layout)
        dialog.resize(700, 420)
        dialog.exec()

    def current_settings(self):
        return CreateRoutesSettings(
            cargo_scu=self.parse_number(self.cargo_input.text(), default=1) or 1,
            max_investment=self.parse_number(self.max_investment_input.text()),
            systems=self.system_filter.checked_values(),
            location_types=self.location_type_filter.checked_values(),
            avoid_dangerous=self.avoid_dangerous_checkbox.isChecked(),
            avoid_hidden=self.avoid_hidden_checkbox.isChecked(),
            avoid_non_armistice=self.avoid_non_armistice_checkbox.isChecked(),
            allow_pyro=self.allow_pyro_checkbox.isChecked(),
            allow_contested=self.allow_contested_checkbox.isChecked(),
            include_illegal=self.include_illegal_checkbox.isChecked(),
            legal_goods=self.legal_goods_checkbox.isChecked(),
            stable_routes=self.stable_routes_checkbox.isChecked(),
            high_profit=self.high_profit_checkbox.isChecked(),
            allow_high_volatility=self.high_volatility_checkbox.isChecked(),
            include_mission_goods=self.mission_goods_checkbox.isChecked(),
            optimization_mode=self.optimization_combo.currentText().strip() or "Balanced",
            top_count=int(self.top_count_combo.currentText() or 10),
        )

    def load_saved_settings(self):
        raw = get_app_setting(SETTINGS_KEY, "")
        if not raw:
            return
        try:
            settings = json.loads(raw)
        except json.JSONDecodeError:
            return

        self.loading_settings = True
        self.ship_combo.setCurrentText(settings.get("selected_ship", ""))
        self.cargo_input.setText(settings.get("cargo_scu", ""))
        self.max_investment_input.setText(settings.get("max_investment", ""))
        self.optimization_combo.setCurrentText(settings.get("optimization_mode", "Balanced"))
        self.top_count_combo.setCurrentText(str(settings.get("top_count", 10)))
        self.system_filter.set_checked_values(settings.get("systems", DEFAULT_SYSTEMS))
        self.location_type_filter.set_checked_values(settings.get("location_types", DEFAULT_LOCATION_TYPES))

        for key, checkbox in self.checkbox_settings_map().items():
            if key in settings:
                checkbox.setChecked(bool(settings[key]))

        self.loading_settings = False

    def save_current_settings(self):
        if self.loading_settings:
            return
        data = {
            "selected_ship": selected_ship_name(self.ship_combo),
            "cargo_scu": self.cargo_input.text().strip(),
            "max_investment": self.max_investment_input.text().strip(),
            "optimization_mode": self.optimization_combo.currentText().strip(),
            "top_count": int(self.top_count_combo.currentText() or 10),
            "systems": list(self.system_filter.checked_values()),
            "location_types": list(self.location_type_filter.checked_values()),
        }
        for key, checkbox in self.checkbox_settings_map().items():
            data[key] = checkbox.isChecked()
        set_app_setting(SETTINGS_KEY, json.dumps(data, sort_keys=True))

    def checkbox_settings_map(self):
        return {
            "avoid_dangerous": self.avoid_dangerous_checkbox,
            "avoid_hidden": self.avoid_hidden_checkbox,
            "avoid_non_armistice": self.avoid_non_armistice_checkbox,
            "allow_pyro": self.allow_pyro_checkbox,
            "allow_contested": self.allow_contested_checkbox,
            "include_illegal": self.include_illegal_checkbox,
            "legal_goods": self.legal_goods_checkbox,
            "stable_routes": self.stable_routes_checkbox,
            "high_profit": self.high_profit_checkbox,
            "allow_high_volatility": self.high_volatility_checkbox,
            "include_mission_goods": self.mission_goods_checkbox,
        }

    def parse_number(self, value, default=None):
        value = (value or "").replace(",", "").replace(" ", "").strip()
        if not value:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def format_number(self, value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "N/A"
        if number.is_integer():
            return f"{int(number):,}"
        return f"{number:,.2f}".rstrip("0").rstrip(".")
