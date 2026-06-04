from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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

from app.trading_data import (
    UNITS_PER_SCU,
    calculate_trade_estimate,
    fetch_trading_opportunities,
    format_trade_age,
)

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


class TradingTab(BackgroundTaskMixin, QWidget):
    def __init__(self):
        super().__init__()

        self.trading_refresh_running = False
        self.all_opportunities = []
        self.visible_opportunities = []
        self.price_row_count = 0

        self.build_ui()
        self.connect_signals()

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
            "Buy Price",
            "Sell Location",
            "Sell Price",
            "Profit / Unit",
            "Profit / SCU",
            "Cargo SCU",
            "Total Profit",
            "Buy Cost",
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

        self.cargo_input = QLineEdit()
        self.cargo_input.setPlaceholderText("Cargo SCU (default 1)")
        self.cargo_input.setMaximumWidth(110)
        self.cargo_input.setToolTip(f"Cargo capacity in SCU. Phase 2 assumes 1 SCU = {UNITS_PER_SCU} units.")

        self.max_investment_input = QLineEdit()
        self.max_investment_input.setPlaceholderText("Max aUEC...")
        self.max_investment_input.setMaximumWidth(130)
        self.max_investment_input.setToolTip("Optional max investment. If set, totals use the affordable cargo amount.")

        self.min_profit_input = QLineEdit()
        self.min_profit_input.setPlaceholderText("Min Profit / Unit...")
        self.min_profit_input.setMaximumWidth(145)
        self.show_unprofitable_checkbox = QCheckBox("Show unprofitable")

        controls.addWidget(self.search_input, 1)
        controls.addWidget(self.cargo_input)
        controls.addWidget(self.max_investment_input)
        controls.addWidget(self.min_profit_input)
        controls.addWidget(self.show_unprofitable_checkbox)
        controls.addWidget(self.refresh_button)
        layout.addLayout(controls)

        self.status_label = QLabel(
            f"Trading data is loaded live from UEX on demand and is not stored locally. "
            f"Phase 2 assumes 1 SCU = {UNITS_PER_SCU} units."
        )
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        card.setLayout(layout)
        return card

    def connect_signals(self):
        self.refresh_button.clicked.connect(self.refresh_trading_data)
        self.search_input.textChanged.connect(self.populate_trade_table)
        self.cargo_input.textChanged.connect(self.populate_trade_table)
        self.max_investment_input.textChanged.connect(self.populate_trade_table)
        self.min_profit_input.textChanged.connect(self.populate_trade_table)
        self.show_unprofitable_checkbox.stateChanged.connect(self.populate_trade_table)
        self.trade_table.itemSelectionChanged.connect(self.update_trade_summary)

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
        self.empty_label.setVisible(True)
        self.status_label.setText(f"Failed to load trading data: {exc}")
        self.detail_label.setText("Trading data failed to load. Try refreshing again later.")

    def finish_trading_refresh(self):
        self.trading_refresh_running = False
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh UEX Trading Data")

    def populate_trade_table(self):
        query = self.search_input.text().strip().lower()
        min_profit = self.parse_number(self.min_profit_input.text())
        cargo_scu = self.parse_number(self.cargo_input.text(), default=1)
        max_investment = self.parse_number(self.max_investment_input.text())
        show_unprofitable = self.show_unprofitable_checkbox.isChecked()

        self.visible_opportunities = [
            opportunity
            for opportunity in self.all_opportunities
            if self.matches_filters(opportunity, query, min_profit, show_unprofitable)
        ]

        sorting_enabled = self.trade_table.isSortingEnabled()
        self.trade_table.setSortingEnabled(False)
        self.trade_table.setRowCount(len(self.visible_opportunities))

        for row_index, opportunity in enumerate(self.visible_opportunities):
            estimate = calculate_trade_estimate(opportunity, cargo_scu, max_investment)
            values = [
                opportunity.commodity,
                opportunity.buy_location,
                self.format_auec(opportunity.buy_price),
                opportunity.sell_location,
                self.format_auec(opportunity.sell_price),
                self.format_auec(opportunity.profit_per_unit),
                self.format_auec(estimate.profit_per_scu),
                self.format_cargo_scu(estimate.effective_cargo_scu, estimate.investment_limited),
                self.format_auec(estimate.estimated_total_profit),
                self.format_auec(estimate.estimated_buy_cost),
                f"{opportunity.source} | {format_trade_age(opportunity.date_modified)}",
            ]
            sort_values = [
                opportunity.commodity,
                opportunity.buy_location,
                opportunity.buy_price,
                opportunity.sell_location,
                opportunity.sell_price,
                opportunity.profit_per_unit,
                estimate.profit_per_scu,
                estimate.effective_cargo_scu,
                estimate.estimated_total_profit,
                estimate.estimated_buy_cost,
                opportunity.date_modified or 0,
            ]
            for col_index, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setData(SORT_ROLE, sort_values[col_index])
                item.setData(Qt.UserRole, row_index)
                if estimate.investment_limited and col_index in (7, 8, 9):
                    item.setToolTip("Limited by max investment.")
                if col_index in (2, 4, 5, 6, 7, 8, 9):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.trade_table.setItem(row_index, col_index, item)

        self.trade_table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(self.trade_table, min_width=110, max_width=360, stretch_last=True)
        self.empty_label.setVisible(not self.visible_opportunities)
        self.update_status_text()
        if not self.visible_opportunities:
            self.detail_label.setText("No trading opportunities match the current filters.")
        else:
            self.update_trade_summary()

    def matches_filters(self, opportunity, query, min_profit, show_unprofitable):
        if not show_unprofitable and opportunity.profit_per_unit <= 0:
            return False
        if min_profit is not None and opportunity.profit_per_unit < min_profit:
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
            return

        cargo_scu = self.parse_number(self.cargo_input.text(), default=1)
        max_investment = self.parse_number(self.max_investment_input.text())
        estimate = calculate_trade_estimate(opportunity, cargo_scu, max_investment)
        limit_text = ""
        if estimate.investment_limited:
            limit_text = " Max investment limits this route."

        self.detail_label.setText(
            f"Buy {opportunity.commodity} at {opportunity.buy_location} for "
            f"{self.format_auec(opportunity.buy_price)}, sell at {opportunity.sell_location} "
            f"for {self.format_auec(opportunity.sell_price)}. "
            f"Profit: {self.format_auec(opportunity.profit_per_unit)} per unit / "
            f"{self.format_auec(estimate.profit_per_scu)} per SCU. "
            f"Cargo used: {self.format_number(estimate.effective_cargo_scu)} SCU. "
            f"Buy cost: {self.format_auec(estimate.estimated_buy_cost)}. "
            f"Total profit: {self.format_auec(estimate.estimated_total_profit)}. "
            f"Source: {opportunity.source} | {format_trade_age(opportunity.date_modified)}."
            f"{limit_text}"
        )

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
            f"{self.price_row_count} UEX price rows. "
            f"Assumption: 1 SCU = {UNITS_PER_SCU} units."
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
