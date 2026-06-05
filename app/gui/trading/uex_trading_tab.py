from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
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
    TradingPresetRecord,
    TradingRouteRecord,
    add_recent_trading_route,
    delete_trading_preset,
    get_trading_presets,
    save_trading_preset,
    save_trading_route,
)
from app.watchlists.service import add_trading_commodity_watch, add_trading_route_watch
from app.trading_data import (
    calculate_trade_estimate,
    fetch_trading_opportunities,
    format_trade_age,
    is_suspicious_margin,
)

from ..table_utils import configure_readable_table_columns
from ..workers import BackgroundTaskMixin
from .reference_data import get_trading_reference_service
from .route_quality import calculate_route_quality, copy_to_clipboard
from .route_summary import format_route_summary, is_complete_route_record, notes_from_flags
from .searchable_combo import configure_searchable_combo, set_combo_items
from .ship_selection import (
    configure_ship_combo,
    fill_cargo_from_ship,
    selected_ship_name,
    update_ship_combo,
)


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


class UEXTradingTab(BackgroundTaskMixin, QWidget):
    def __init__(self, reference_service=None):
        super().__init__()

        self.reference_service = reference_service or get_trading_reference_service()
        self.trading_refresh_running = False
        self.all_opportunities = []
        self.visible_opportunities = []
        self.price_row_count = 0
        self.presets = []

        self.build_ui()
        self.connect_signals()
        self.connect_reference_service()
        self.load_presets()

    def connect_reference_service(self):
        self.reference_service.loaded.connect(self.on_reference_loaded)
        if self.reference_service.data is not None:
            self.on_reference_loaded(self.reference_service.data)
        else:
            self.reference_service.ensure_loaded()

    def on_reference_loaded(self, data):
        update_ship_combo(self.ship_combo, data.ships)

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_header())
        layout.addWidget(self.create_controls())

        self.trade_table = QTableWidget(0, 11)
        self.trade_table.setHorizontalHeaderLabels([
            "Commodity",
            "Buy Location",
            "Buy / SCU",
            "Sell Location",
            "Sell / SCU",
            "Profit / SCU",
            "Cargo SCU",
            "Total Profit",
            "Buy Cost",
            "Quality",
            "Source / Updated",
        ])
        self.trade_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.trade_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.trade_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.trade_table.setAlternatingRowColors(True)
        self.trade_table.setSortingEnabled(True)
        configure_readable_table_columns(self.trade_table, min_width=110, max_width=360, stretch_last=True)
        layout.addWidget(self.trade_table, 1)

        self.empty_label = QLabel("Refresh trading data to load UEX commodity opportunities.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        self.detail_label = QLabel("Select a route to see a short trade summary.")
        self.detail_label.setObjectName("valueText")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

        self.copy_summary_button = QPushButton("Copy Route Summary")
        self.copy_summary_button.setEnabled(False)
        self.save_route_button = QPushButton("Save Route")
        self.save_route_button.setEnabled(False)
        self.watch_route_button = QPushButton("Add Route to Watchlist")
        self.watch_route_button.setEnabled(False)
        self.watch_commodity_button = QPushButton("Add Commodity to Watchlist")
        self.watch_commodity_button.setEnabled(False)
        route_button_row = QHBoxLayout()
        route_button_row.setSpacing(8)
        route_button_row.addWidget(self.copy_summary_button)
        route_button_row.addWidget(self.save_route_button)
        route_button_row.addWidget(self.watch_route_button)
        route_button_row.addWidget(self.watch_commodity_button)
        route_button_row.addStretch(1)
        layout.addLayout(route_button_row)

        self.setLayout(layout)

    def create_header(self):
        header = QFrame()
        header.setObjectName("playerCard")
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(4)

        title = QLabel("Trading")
        title.setObjectName("moduleHeading")
        subtitle = QLabel(
            "Simple commodity buy/sell comparison using live UEX market data. "
            "Complex route planning is deferred to later phases."
        )
        subtitle.setObjectName("moduleSubtitle")
        subtitle.setWordWrap(True)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header.setLayout(header_layout)
        return header

    def create_controls(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        title = QLabel("COMMODITY TRADING")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.refresh_button = QPushButton("Refresh UEX Trading Data")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter commodity, system, location or terminal...")

        self.ship_combo = QComboBox()
        configure_ship_combo(self.ship_combo)
        self.ship_combo.setMaximumWidth(180)

        self.cargo_input = QLineEdit()
        self.cargo_input.setPlaceholderText("Cargo SCU (default 1)")
        self.cargo_input.setMaximumWidth(110)
        self.cargo_input.setToolTip("Cargo capacity in SCU. UEX commodity prices are per SCU.")

        self.max_investment_input = QLineEdit()
        self.max_investment_input.setPlaceholderText("Max aUEC...")
        self.max_investment_input.setMaximumWidth(130)
        self.max_investment_input.setToolTip("Optional max investment. If set, totals use the affordable cargo amount.")

        self.min_profit_input = QLineEdit()
        self.min_profit_input.setPlaceholderText("Min Profit / SCU...")
        self.min_profit_input.setMaximumWidth(145)
        self.min_total_profit_input = QLineEdit()
        self.min_total_profit_input.setPlaceholderText("Min Total...")
        self.min_total_profit_input.setMaximumWidth(120)
        self.show_unprofitable_checkbox = QCheckBox("Show unprofitable")
        self.only_full_cargo_checkbox = QCheckBox("Only full cargo")
        self.only_affordable_checkbox = QCheckBox("Only affordable")
        self.hide_suspicious_checkbox = QCheckBox("Hide suspicious margins")

        controls.addWidget(self.search_input, 1)
        controls.addWidget(self.ship_combo)
        controls.addWidget(self.cargo_input)
        controls.addWidget(self.max_investment_input)
        controls.addWidget(self.refresh_button)
        layout.addLayout(controls)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        filters.addWidget(self.min_profit_input)
        filters.addWidget(self.min_total_profit_input)
        filters.addWidget(self.show_unprofitable_checkbox)
        filters.addWidget(self.only_full_cargo_checkbox)
        filters.addWidget(self.only_affordable_checkbox)
        filters.addWidget(self.hide_suspicious_checkbox)
        filters.addStretch(1)
        layout.addLayout(filters)

        presets = QHBoxLayout()
        presets.setSpacing(8)
        self.preset_combo = QComboBox()
        configure_searchable_combo(self.preset_combo, "Load preset...")
        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText("Preset name...")
        self.preset_name_input.setMaximumWidth(180)
        self.save_preset_button = QPushButton("Save Preset")
        self.load_preset_button = QPushButton("Load Preset")
        self.delete_preset_button = QPushButton("Delete Preset")
        presets.addWidget(self.preset_combo, 1)
        presets.addWidget(self.preset_name_input)
        presets.addWidget(self.save_preset_button)
        presets.addWidget(self.load_preset_button)
        presets.addWidget(self.delete_preset_button)
        presets.addStretch(1)
        layout.addLayout(presets)

        self.status_label = QLabel("Trading data is loaded live from UEX on demand and is not stored locally.")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        card.setLayout(layout)
        return card

    def connect_signals(self):
        self.refresh_button.clicked.connect(self.refresh_trading_data)
        self.ship_combo.currentTextChanged.connect(self.on_ship_changed)
        self.search_input.textChanged.connect(self.populate_trade_table)
        self.cargo_input.textChanged.connect(self.populate_trade_table)
        self.max_investment_input.textChanged.connect(self.populate_trade_table)
        self.min_profit_input.textChanged.connect(self.populate_trade_table)
        self.min_total_profit_input.textChanged.connect(self.populate_trade_table)
        self.show_unprofitable_checkbox.stateChanged.connect(self.populate_trade_table)
        self.only_full_cargo_checkbox.stateChanged.connect(self.populate_trade_table)
        self.only_affordable_checkbox.stateChanged.connect(self.populate_trade_table)
        self.hide_suspicious_checkbox.stateChanged.connect(self.populate_trade_table)
        self.trade_table.itemSelectionChanged.connect(self.update_trade_summary)
        self.copy_summary_button.clicked.connect(self.copy_route_summary)
        self.save_route_button.clicked.connect(self.save_selected_route)
        self.watch_route_button.clicked.connect(self.add_selected_route_to_watchlist)
        self.watch_commodity_button.clicked.connect(self.add_selected_commodity_to_watchlist)
        self.save_preset_button.clicked.connect(self.save_current_preset)
        self.load_preset_button.clicked.connect(self.load_selected_preset)
        self.delete_preset_button.clicked.connect(self.delete_selected_preset)

    def on_ship_changed(self):
        fill_cargo_from_ship(self.ship_combo, self.cargo_input, self.status_label)
        self.populate_trade_table()

    def refresh_trading_data(self):
        if self.trading_refresh_running:
            return

        self.trading_refresh_running = True
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Loading...")
        self.status_label.setText("Loading trading data...")

        self.start_background_task(
            lambda: fetch_trading_opportunities(include_unprofitable=True),
            self.on_trading_data_loaded,
            self.on_trading_data_error,
            self.finish_trading_refresh,
        )

    def on_trading_data_loaded(self, result):
        opportunities, price_row_count = result
        self.all_opportunities = opportunities
        self.price_row_count = price_row_count
        self.populate_trade_table()

    def on_trading_data_error(self, exc):
        self.all_opportunities = []
        self.visible_opportunities = []
        self.trade_table.setRowCount(0)
        self.empty_label.setText("UEX trading data failed to load. Try refreshing again later.")
        self.empty_label.setVisible(True)
        self.status_label.setText(f"Failed to load trading data: {exc}")
        self.detail_label.setText("Trading data failed to load. Try refreshing again later.")
        self.copy_summary_button.setEnabled(False)
        self.save_route_button.setEnabled(False)

    def finish_trading_refresh(self):
        self.trading_refresh_running = False
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh UEX Trading Data")

    def populate_trade_table(self):
        query = self.search_input.text().strip().lower()
        min_profit = self.parse_number(self.min_profit_input.text())
        min_total_profit = self.parse_number(self.min_total_profit_input.text())
        cargo_scu = self.parse_number(self.cargo_input.text(), default=1)
        max_investment = self.parse_number(self.max_investment_input.text())
        show_unprofitable = self.show_unprofitable_checkbox.isChecked()
        only_full_cargo = self.only_full_cargo_checkbox.isChecked()
        only_affordable = self.only_affordable_checkbox.isChecked()
        hide_suspicious = self.hide_suspicious_checkbox.isChecked()

        self.visible_opportunities = []
        estimates = {}
        for opportunity in self.all_opportunities:
            estimate = calculate_trade_estimate(opportunity, cargo_scu, max_investment)
            if self.matches_filters(
                opportunity,
                estimate,
                query,
                min_profit,
                min_total_profit,
                show_unprofitable,
                only_full_cargo,
                only_affordable,
                hide_suspicious,
            ):
                estimates[id(opportunity)] = estimate
                self.visible_opportunities.append(opportunity)

        sorting_enabled = self.trade_table.isSortingEnabled()
        self.trade_table.setSortingEnabled(False)
        self.trade_table.setRowCount(len(self.visible_opportunities))

        for row_index, opportunity in enumerate(self.visible_opportunities):
            estimate = estimates[id(opportunity)]
            quality = self.route_quality(opportunity, estimate)
            values = [
                opportunity.commodity,
                opportunity.buy_location,
                self.format_auec(opportunity.buy_price),
                opportunity.sell_location,
                self.format_auec(opportunity.sell_price),
                self.format_auec(opportunity.profit_per_scu),
                self.format_cargo_scu(estimate.effective_cargo_scu, estimate.investment_limited),
                self.format_auec(estimate.estimated_total_profit),
                self.format_auec(estimate.estimated_buy_cost),
                quality.label,
                f"{opportunity.source} | {format_trade_age(opportunity.date_modified)}",
            ]
            sort_values = [
                opportunity.commodity,
                opportunity.buy_location,
                opportunity.buy_price,
                opportunity.sell_location,
                opportunity.sell_price,
                opportunity.profit_per_scu,
                estimate.effective_cargo_scu,
                estimate.estimated_total_profit,
                estimate.estimated_buy_cost,
                quality.sort_value,
                opportunity.date_modified or 0,
            ]
            for col_index, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setData(SORT_ROLE, sort_values[col_index])
                item.setData(Qt.UserRole, row_index)
                if estimate.investment_limited and col_index in (6, 7, 8):
                    item.setToolTip("Limited by max investment.")
                if quality.flags and col_index == 9:
                    item.setToolTip(" | ".join(quality.flags))
                if col_index in (2, 4, 5, 6, 7, 8):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.trade_table.setItem(row_index, col_index, item)

        self.trade_table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(self.trade_table, min_width=110, max_width=360, stretch_last=True)
        self.empty_label.setVisible(not self.visible_opportunities)
        self.update_status_text()
        if not self.visible_opportunities:
            if self.all_opportunities:
                self.empty_label.setText(
                    "No UEX routes match the current filters. Try lowering profit limits or relaxing filters."
                )
                self.detail_label.setText("No UEX routes match the current filters.")
            else:
                self.empty_label.setText("Refresh trading data to load UEX commodity opportunities.")
                self.detail_label.setText("Refresh UEX Trading Data to load trade routes.")
            self.copy_summary_button.setEnabled(False)
            self.save_route_button.setEnabled(False)
        else:
            self.update_trade_summary()

    def matches_filters(
        self,
        opportunity,
        estimate,
        query,
        min_profit,
        min_total_profit,
        show_unprofitable,
        only_full_cargo,
        only_affordable,
        hide_suspicious,
    ):
        if not show_unprofitable and opportunity.profit_per_scu <= 0:
            return False
        if min_profit is not None and opportunity.profit_per_scu < min_profit:
            return False
        if min_total_profit is not None and estimate.estimated_total_profit < min_total_profit:
            return False
        if only_full_cargo and estimate.investment_limited:
            return False
        if only_affordable and not estimate.full_cargo_affordable:
            return False
        if hide_suspicious and is_suspicious_margin(opportunity):
            return False
        if not query:
            return True

        haystack = " ".join((
            opportunity.commodity,
            opportunity.buy_location,
            opportunity.sell_location,
            opportunity.source,
        )).lower()
        return query in haystack

    def update_trade_summary(self):
        opportunity = self.selected_opportunity()
        if not opportunity:
            self.copy_summary_button.setEnabled(False)
            self.save_route_button.setEnabled(False)
            self.watch_route_button.setEnabled(False)
            self.watch_commodity_button.setEnabled(False)
            return

        record = self.route_record_for_opportunity(opportunity)
        self.detail_label.setText(format_route_summary(record))
        self.copy_summary_button.setEnabled(True)
        self.save_route_button.setEnabled(is_complete_route_record(record))
        self.watch_route_button.setEnabled(is_complete_route_record(record))
        self.watch_commodity_button.setEnabled(bool(opportunity.commodity))

    def build_route_summary(self, opportunity):
        return format_route_summary(self.route_record_for_opportunity(opportunity))

    def route_record_for_opportunity(self, opportunity):
        cargo_scu = self.parse_number(self.cargo_input.text(), default=1)
        max_investment = self.parse_number(self.max_investment_input.text())
        estimate = calculate_trade_estimate(opportunity, cargo_scu, max_investment)
        quality = self.route_quality(opportunity, estimate)

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
            quality=quality.label,
            notes=notes_from_flags(quality.flags, (f"Updated: {format_trade_age(opportunity.date_modified)}",)),
        )

    def copy_route_summary(self):
        opportunity = self.selected_opportunity()
        if not opportunity:
            return

        record = self.route_record_for_opportunity(opportunity)
        copy_to_clipboard(format_route_summary(record))
        if is_complete_route_record(record):
            add_recent_trading_route(record)
            self.status_label.setText("Route summary copied and added to recent routes.")
        else:
            self.status_label.setText("Route summary copied to clipboard.")

    def save_selected_route(self):
        opportunity = self.selected_opportunity()
        if not opportunity:
            return

        record = self.route_record_for_opportunity(opportunity)
        if not is_complete_route_record(record):
            self.status_label.setText("This route is missing required buy/sell data and cannot be saved.")
            return

        save_trading_route(record)
        add_recent_trading_route(record)
        self.status_label.setText("Route saved locally.")

    def add_selected_route_to_watchlist(self):
        opportunity = self.selected_opportunity()
        if not opportunity:
            return

        record = self.route_record_for_opportunity(opportunity)
        if not is_complete_route_record(record):
            self.status_label.setText("This route is missing required buy/sell data and cannot be watched.")
            return

        add_trading_route_watch(record)
        add_recent_trading_route(record)
        self.status_label.setText("Route added to Watchlists.")

    def add_selected_commodity_to_watchlist(self):
        opportunity = self.selected_opportunity()
        if not opportunity:
            return

        metadata = {
            "commodity": opportunity.commodity,
            "buy_location": opportunity.buy_location,
            "sell_location": opportunity.sell_location,
            "buy_price": opportunity.buy_price,
            "sell_price": opportunity.sell_price,
            "profit_per_scu": opportunity.profit_per_scu,
            "source": opportunity.source,
            "date_modified": opportunity.date_modified,
        }
        add_trading_commodity_watch(opportunity.commodity, opportunity.source, metadata)
        self.status_label.setText(f"Commodity added to Watchlists: {opportunity.commodity}")

    def route_quality(self, opportunity, estimate):
        return calculate_route_quality(
            total_profit=estimate.estimated_total_profit,
            profit_per_scu=opportunity.profit_per_scu,
            full_cargo=not estimate.investment_limited,
            affordable=estimate.full_cargo_affordable,
            suspicious=is_suspicious_margin(opportunity),
        )

    def load_presets(self):
        self.presets = get_trading_presets()
        current = self.preset_combo.currentText().strip() if hasattr(self, "preset_combo") else ""
        set_combo_items(self.preset_combo, (preset.name for preset in self.presets), current_text=current)

    def save_current_preset(self):
        name = self.preset_name_input.text().strip() or self.preset_combo.currentText().strip()
        if not name:
            self.status_label.setText("Enter a preset name before saving.")
            return

        save_trading_preset(TradingPresetRecord(
            name=name,
            selected_ship=selected_ship_name(self.ship_combo),
            cargo_scu=self.cargo_input.text().strip(),
            max_investment=self.max_investment_input.text().strip(),
            min_profit_per_scu=self.min_profit_input.text().strip(),
            min_total_profit=self.min_total_profit_input.text().strip(),
            show_unprofitable=self.show_unprofitable_checkbox.isChecked(),
            only_full_cargo=self.only_full_cargo_checkbox.isChecked(),
            only_affordable=self.only_affordable_checkbox.isChecked(),
            hide_suspicious_margins=self.hide_suspicious_checkbox.isChecked(),
        ))
        self.load_presets()
        self.preset_combo.setCurrentText(name)
        self.status_label.setText(f"Preset saved: {name}")

    def load_selected_preset(self):
        preset = self.selected_preset()
        if not preset:
            self.status_label.setText("Choose a preset to load.")
            return

        self.ship_combo.setCurrentText(preset.selected_ship)
        self.cargo_input.setText(preset.cargo_scu)
        self.max_investment_input.setText(preset.max_investment)
        self.min_profit_input.setText(preset.min_profit_per_scu)
        self.min_total_profit_input.setText(preset.min_total_profit)
        self.show_unprofitable_checkbox.setChecked(preset.show_unprofitable)
        self.only_full_cargo_checkbox.setChecked(preset.only_full_cargo)
        self.only_affordable_checkbox.setChecked(preset.only_affordable)
        self.hide_suspicious_checkbox.setChecked(preset.hide_suspicious_margins)
        self.populate_trade_table()
        self.status_label.setText(f"Preset loaded: {preset.name}")

    def delete_selected_preset(self):
        preset = self.selected_preset()
        if not preset:
            self.status_label.setText("Choose a preset to delete.")
            return

        delete_trading_preset(preset.name)
        self.load_presets()
        self.status_label.setText(f"Preset deleted: {preset.name}")

    def selected_preset(self):
        name = self.preset_combo.currentText().strip()
        for preset in self.presets:
            if preset.name.lower() == name.lower():
                return preset
        return None

    def selected_opportunity(self):
        row = self.trade_table.currentRow()
        if row < 0:
            return self.visible_opportunities[0] if self.visible_opportunities else None

        item = self.trade_table.item(row, 0)
        if not item:
            return None

        index = item.data(Qt.UserRole)
        if index is None or index >= len(self.visible_opportunities):
            return None

        return self.visible_opportunities[index]

    def update_status_text(self):
        if not self.all_opportunities:
            return

        self.status_label.setText(
            f"Trading data loaded: showing {len(self.visible_opportunities)} of "
            f"{len(self.all_opportunities)} buy/sell comparisons from "
            f"{self.price_row_count} UEX price rows. Prices are per SCU."
        )

    def parse_number(self, value, default=None):
        value = (value or "").replace(",", "").replace(" ", "").strip()
        if not value:
            return default

        try:
            return float(value)
        except ValueError:
            return default

    def format_auec(self, value):
        return f"{self.format_number(value)} aUEC"

    def format_number(self, value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "N/A"

        if number.is_integer():
            return f"{int(number):,}"

        return f"{number:,.2f}".rstrip("0").rstrip(".")

    def format_cargo_scu(self, value, investment_limited=False):
        suffix = "*" if investment_limited else ""
        return f"{self.format_number(value)} SCU{suffix}"
