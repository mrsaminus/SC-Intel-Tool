from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.hauling import (
    HaulingContractParser,
    build_manifest,
    group_by_destination,
    group_by_pickup,
    group_by_route,
)

from .sortable_table_item import SORT_ROLE, SortableTableWidgetItem
from .table_utils import configure_readable_table_columns
from .trading.ship_selection import configure_ship_combo, selected_ship_name


class HaulingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.parser = HaulingContractParser()
        self.parse_result = None
        self.contracts = ()
        self.manifest = build_manifest(())

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self.create_header())
        layout.addWidget(self.create_status_line())

        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        top_row.addWidget(self.create_manual_input_card(), 3)
        top_row.addWidget(self.create_capacity_card(), 2)
        layout.addLayout(top_row)

        layout.addWidget(self.create_manifest_preview(), 1)
        self.setLayout(layout)

        self.update_manifest()

    def create_header(self):
        header = QFrame()
        header.setObjectName("playerCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title = QLabel("Hauling Operations Center")
        title.setObjectName("moduleHeading")
        subtitle = QLabel("Plan hauling contracts, cargo capacity and delivery manifests.")
        subtitle.setObjectName("moduleSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        header.setLayout(layout)
        return header

    def create_status_line(self):
        self.status_label = QLabel("Paste hauling contract text, then parse it into a local manifest.")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        return self.status_label

    def create_manual_input_card(self):
        card = self.create_card("MANUAL CONTRACT TEXT")
        layout = card.layout()

        self.contract_text = QTextEdit()
        self.contract_text.setPlaceholderText(
            "Paste hauling contract or OCR text here.\n\n"
            "Example:\n"
            "Pick up: Checkmate\n"
            "Deliver to: Teasa Spaceport\n"
            "Commodity: Construction Materials\n"
            "Quantity: 32 SCU"
        )
        self.contract_text.setMinimumHeight(150)
        layout.addWidget(self.contract_text, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.parse_button = QPushButton("Parse Contracts")
        self.clear_button = QPushButton("Clear Input")
        self.copy_manifest_button = QPushButton("Copy Manifest")
        self.parse_button.clicked.connect(self.parse_contracts)
        self.clear_button.clicked.connect(self.clear_input)
        self.copy_manifest_button.clicked.connect(self.copy_manifest)
        button_row.addWidget(self.parse_button)
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.copy_manifest_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        return card

    def create_capacity_card(self):
        card = self.create_card("SHIP & CAPACITY")
        layout = card.layout()

        self.ship_combo = QComboBox()
        configure_ship_combo(self.ship_combo)
        self.ship_combo.currentTextChanged.connect(self.on_ship_changed)
        layout.addWidget(self.ship_combo)

        self.capacity_label = QLabel()
        self.capacity_label.setObjectName("valueText")
        self.capacity_label.setWordWrap(True)
        self.total_scu_label = QLabel()
        self.total_scu_label.setObjectName("valueText")
        self.total_scu_label.setWordWrap(True)
        self.remaining_scu_label = QLabel()
        self.remaining_scu_label.setObjectName("valueText")
        self.remaining_scu_label.setWordWrap(True)
        self.capacity_warning_label = QLabel()
        self.capacity_warning_label.setObjectName("moduleSubtitle")
        self.capacity_warning_label.setWordWrap(True)

        layout.addWidget(self.capacity_label)
        layout.addWidget(self.total_scu_label)
        layout.addWidget(self.remaining_scu_label)
        layout.addWidget(self.capacity_warning_label)
        layout.addStretch(1)
        return card

    def create_manifest_preview(self):
        card = self.create_card("MANIFEST PREVIEW")
        layout = card.layout()

        self.preview_tabs = QTabWidget()
        self.contracts_table = self.create_table([
            "Pickup",
            "Delivery",
            "Commodity",
            "SCU",
            "Reward",
            "Confidence",
            "Warnings",
        ])
        self.pickup_table = self.create_table(["Pickup", "Total SCU", "Contracts", "Commodities"])
        self.destination_table = self.create_table(["Destination", "Total SCU", "Contracts", "Commodities"])
        self.route_table = self.create_table(["Route", "Total SCU", "Contracts", "Commodities"])
        self.warnings_text = QTextEdit()
        self.warnings_text.setReadOnly(True)
        self.warnings_text.setPlaceholderText("Warnings and parser notes will appear here.")

        self.preview_tabs.addTab(self.contracts_table, "Contracts")
        self.preview_tabs.addTab(self.pickup_table, "By Pickup")
        self.preview_tabs.addTab(self.destination_table, "By Destination")
        self.preview_tabs.addTab(self.route_table, "By Route")
        self.preview_tabs.addTab(self.warnings_text, "Warnings")
        layout.addWidget(self.preview_tabs, 1)
        return card

    def create_card(self, title):
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
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        configure_readable_table_columns(table, min_width=110, max_width=360, stretch_last=True)
        return table

    def parse_contracts(self):
        text = self.contract_text.toPlainText()
        self.parse_result = self.parser.parse(text)
        self.contracts = self.parse_result.contracts
        self.update_manifest()
        if self.contracts:
            self.status_label.setText(
                f"Parsed {len(self.contracts)} contract candidate"
                f"{'s' if len(self.contracts) != 1 else ''} into the manifest."
            )
        else:
            self.status_label.setText("No hauling contracts parsed. Check the pasted text and try again.")

    def clear_input(self):
        self.contract_text.clear()
        self.parse_result = None
        self.contracts = ()
        self.update_manifest()
        self.status_label.setText("Input cleared. Paste hauling contract text to build a manifest.")

    def on_ship_changed(self):
        self.update_manifest()

    def selected_ship(self):
        return selected_ship_name(self.ship_combo)

    def update_manifest(self):
        ship = self.selected_ship()
        self.manifest = build_manifest(self.contracts, selected_ship=ship)
        self.populate_contracts()
        self.populate_grouped_tables()
        self.update_capacity_summary()
        self.update_warnings()

    def populate_contracts(self):
        table = self.contracts_table
        table.setSortingEnabled(False)
        table.setRowCount(len(self.manifest.contracts))
        for row, contract in enumerate(self.manifest.contracts):
            values = [
                contract.pickup or "Missing",
                contract.delivery or "Missing",
                contract.commodity or "Missing",
                format_number(contract.scu),
                format_money(contract.reward),
                f"{contract.confidence:.0%}",
                "; ".join(contract.warnings),
            ]
            sort_values = [
                contract.pickup,
                contract.delivery,
                contract.commodity,
                contract.scu,
                contract.reward if contract.reward is not None else -1,
                contract.confidence,
                "; ".join(contract.warnings),
            ]
            for column, value in enumerate(values):
                table.setItem(row, column, table_item(value, sort_values[column]))
        table.setSortingEnabled(True)
        configure_readable_table_columns(table, min_width=110, max_width=380, stretch_last=True)

    def populate_grouped_tables(self):
        self.populate_location_table(self.pickup_table, group_by_pickup(self.manifest.contracts))
        self.populate_location_table(
            self.destination_table,
            group_by_destination(self.manifest.contracts),
        )
        self.populate_route_table(group_by_route(self.manifest.contracts))

    def populate_location_table(self, table, groups):
        table.setSortingEnabled(False)
        table.setRowCount(len(groups))
        for row, (location, contracts) in enumerate(groups.items()):
            total = sum(contract.scu for contract in contracts)
            commodities = commodity_summary(contracts)
            table.setItem(row, 0, table_item(location, location))
            table.setItem(row, 1, table_item(format_number(total), total))
            table.setItem(row, 2, table_item(str(len(contracts)), len(contracts)))
            table.setItem(row, 3, table_item(commodities, commodities))
        table.setSortingEnabled(True)
        configure_readable_table_columns(table, min_width=110, max_width=380, stretch_last=True)

    def populate_route_table(self, groups):
        self.route_table.setSortingEnabled(False)
        self.route_table.setRowCount(len(groups))
        for row, ((pickup, delivery), contracts) in enumerate(groups.items()):
            total = sum(contract.scu for contract in contracts)
            route = f"{pickup or 'Missing'} -> {delivery or 'Missing'}"
            commodities = commodity_summary(contracts)
            self.route_table.setItem(row, 0, table_item(route, route))
            self.route_table.setItem(row, 1, table_item(format_number(total), total))
            self.route_table.setItem(row, 2, table_item(str(len(contracts)), len(contracts)))
            self.route_table.setItem(row, 3, table_item(commodities, commodities))
        self.route_table.setSortingEnabled(True)
        configure_readable_table_columns(self.route_table, min_width=110, max_width=420, stretch_last=True)

    def update_capacity_summary(self):
        if self.manifest.selected_ship:
            capacity = self.manifest.ship_capacity_scu
            self.capacity_label.setText(
                f"Ship Capacity: {format_number(capacity)} SCU"
                if capacity is not None
                else "Ship Capacity: Unknown"
            )
        else:
            self.capacity_label.setText("Ship Capacity: Select a ship")

        self.total_scu_label.setText(f"Total Parsed SCU: {format_number(self.manifest.total_scu)}")
        if self.manifest.remaining_scu is None:
            self.remaining_scu_label.setText("Remaining SCU: Select a ship")
        else:
            self.remaining_scu_label.setText(f"Remaining SCU: {format_number(self.manifest.remaining_scu)}")

        capacity_warnings = [warning for warning in self.manifest.warnings if "capacity" in warning.lower()]
        self.capacity_warning_label.setText(capacity_warnings[0] if capacity_warnings else "Capacity status: Ready.")

    def update_warnings(self):
        warnings = self.all_warnings()
        self.warnings_text.setPlainText("\n".join(f"- {warning}" for warning in warnings))
        if not warnings:
            self.warnings_text.setPlainText("- No manifest warnings.")

    def all_warnings(self):
        warnings = []
        if self.parse_result:
            warnings.extend(self.parse_result.warnings)
        if not self.contracts:
            warnings.append("No contracts parsed.")
        for contract in self.contracts:
            for warning in contract.warnings:
                label = contract.commodity or contract.contract_name or contract.id or "Contract"
                warnings.append(f"{label}: {warning}")
        warnings.extend(self.manifest.warnings)
        return tuple(dict.fromkeys(warnings))

    def copy_manifest(self):
        QApplication.clipboard().setText(self.manifest_text())
        self.status_label.setText("Manifest copied to clipboard.")

    def manifest_text(self):
        lines = [
            "Hauling Manifest",
            f"Ship: {self.manifest.selected_ship or 'Not selected'}",
            f"Capacity: {format_number(self.manifest.ship_capacity_scu)} SCU",
            f"Total SCU: {format_number(self.manifest.total_scu)}",
            f"Remaining SCU: {format_number(self.manifest.remaining_scu)}",
            "",
            "Contracts:",
        ]
        if not self.manifest.contracts:
            lines.append("- None parsed")
        for contract in self.manifest.contracts:
            lines.append(
                f"- {contract.commodity or 'Missing commodity'}: "
                f"{contract.pickup or 'Missing pickup'} -> {contract.delivery or 'Missing delivery'} "
                f"({format_number(contract.scu)} SCU)"
            )
        warnings = self.all_warnings()
        if warnings:
            lines.append("")
            lines.append("Warnings:")
            lines.extend(f"- {warning}" for warning in warnings)
        return "\n".join(lines)


def table_item(text, sort_value=None):
    item = SortableTableWidgetItem(str(text or ""))
    item.setData(SORT_ROLE, sort_value if sort_value is not None else str(text or ""))
    return item


def format_number(value):
    if value is None:
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")


def format_money(value):
    if value is None:
        return "N/A"
    return f"{format_number(value)} aUEC"


def commodity_summary(contracts):
    commodities = []
    for contract in contracts:
        name = contract.commodity or "Missing commodity"
        if name not in commodities:
            commodities.append(name)
    return ", ".join(commodities)
