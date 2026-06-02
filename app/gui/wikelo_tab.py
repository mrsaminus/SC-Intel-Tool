from dataclasses import dataclass

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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

from app.wikelo_client import WIKELO_SOURCE_URL, fetch_wikelo_items, normalized_key

from .table_utils import configure_readable_table_columns
from .workers import BackgroundTaskMixin


SORT_ROLE = Qt.UserRole + 1


@dataclass(frozen=True)
class WikeloItemGroup:
    item_name: str
    category: str
    item_type: str
    reward_method: str
    requirements: tuple
    options: tuple
    retired: bool
    source_url: str


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


class WikeloItemsTab(BackgroundTaskMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.wikelo_items = []
        self.visible_wikelo_items = []
        self.wikelo_refresh_running = False

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_module_header(
            "Wikelo Items",
            "Live Wikelo mission, trade-in and reward browser from the public Wikelo spreadsheet.",
        ))

        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self.build_wikelo_search_panel(), 3)
        content.addWidget(self.build_wikelo_detail_panel(), 2)
        layout.addLayout(content, 1)

        self.setLayout(layout)
        self.connect_signals()
        self.populate_wikelo_results()
        self.update_selected_wikelo_panel()
        self.refresh_wikelo_items(silent=True)

    def build_wikelo_search_panel(self):
        card = self.create_filter_card("WIKELO ITEM SEARCH")
        layout = card.layout()

        row = QHBoxLayout()
        self.wikelo_search_input = QLineEdit()
        self.wikelo_search_input.setPlaceholderText("Search Wikelo item, mission, material or reward...")
        self.wikelo_category_filter = QComboBox()
        self.wikelo_category_filter.addItem("All categories")
        self.show_retired_checkbox = QCheckBox("Show retired items")
        row.addWidget(self.wikelo_search_input, 1)
        row.addWidget(self.wikelo_category_filter)
        row.addWidget(self.show_retired_checkbox)
        layout.addLayout(row)

        button_row = QHBoxLayout()
        self.refresh_wikelo_button = QPushButton("Refresh Wikelo Data")
        self.open_wikelo_source_button = QPushButton("Open Wikelo Source")
        button_row.addWidget(self.refresh_wikelo_button)
        button_row.addWidget(self.open_wikelo_source_button)
        layout.addLayout(button_row)

        self.wikelo_status_label = QLabel("Loading Wikelo spreadsheet data...")
        self.wikelo_status_label.setObjectName("moduleSubtitle")
        self.wikelo_status_label.setWordWrap(True)
        layout.addWidget(self.wikelo_status_label)

        self.wikelo_results_table = self.create_table([
            "Item Name",
            "Category",
            "Type",
            "Reward / Method",
            "Required Materials",
        ])
        configure_readable_table_columns(self.wikelo_results_table, min_width=120, max_width=360, stretch_last=True)
        layout.addWidget(self.wikelo_results_table, 1)

        self.wikelo_empty_label = self.create_empty_state("No Wikelo items loaded yet.")
        layout.addWidget(self.wikelo_empty_label)
        return card

    def build_wikelo_detail_panel(self):
        card = self.create_filter_card("WIKELO DETAILS")
        layout = card.layout()

        self.selected_wikelo_name_label = QLabel("No Wikelo item selected")
        self.selected_wikelo_name_label.setObjectName("orgName")
        self.selected_wikelo_meta_label = QLabel("")
        self.selected_wikelo_meta_label.setObjectName("moduleSubtitle")
        self.selected_wikelo_mission_label = QLabel("")
        self.selected_wikelo_mission_label.setObjectName("valueText")
        self.selected_wikelo_mission_label.setWordWrap(True)
        self.selected_wikelo_reward_label = QLabel("")
        self.selected_wikelo_reward_label.setObjectName("valueText")
        self.selected_wikelo_reward_label.setWordWrap(True)
        self.selected_wikelo_location_label = QLabel("")
        self.selected_wikelo_location_label.setObjectName("moduleSubtitle")
        self.selected_wikelo_location_label.setWordWrap(True)

        layout.addWidget(self.selected_wikelo_name_label)
        layout.addWidget(self.selected_wikelo_meta_label)
        layout.addWidget(self.selected_wikelo_mission_label)
        layout.addWidget(self.selected_wikelo_reward_label)
        layout.addWidget(self.selected_wikelo_location_label)

        button_row = QHBoxLayout()
        self.open_selected_wikelo_source_button = QPushButton("Open Selected Item Source")
        self.open_selected_wikelo_source_button.clicked.connect(self.open_selected_wikelo_source)
        button_row.addWidget(self.open_selected_wikelo_source_button)
        layout.addLayout(button_row)

        self.wikelo_requirements_table = self.create_table([
            "Option",
            "Mission / Source",
            "Required Item / Material",
            "Qty",
            "Source",
        ])
        configure_readable_table_columns(self.wikelo_requirements_table, min_width=110, max_width=420, stretch_last=True)
        layout.addWidget(self.wikelo_requirements_table, 1)

        self.wikelo_notes_label = QLabel("")
        self.wikelo_notes_label.setObjectName("moduleSubtitle")
        self.wikelo_notes_label.setWordWrap(True)
        layout.addWidget(self.wikelo_notes_label)
        return card

    def connect_signals(self):
        self.wikelo_search_input.textChanged.connect(self.populate_wikelo_results)
        self.wikelo_category_filter.currentTextChanged.connect(self.populate_wikelo_results)
        self.show_retired_checkbox.stateChanged.connect(self.populate_wikelo_results)
        self.refresh_wikelo_button.clicked.connect(self.refresh_wikelo_items)
        self.open_wikelo_source_button.clicked.connect(self.open_wikelo_source)
        self.wikelo_results_table.itemSelectionChanged.connect(self.update_selected_wikelo_panel)

    def refresh_wikelo_items(self, silent=False):
        if self.wikelo_refresh_running:
            return

        self.wikelo_refresh_running = True
        self.refresh_wikelo_button.setEnabled(False)
        self.refresh_wikelo_button.setText("Refreshing...")
        self.wikelo_status_label.setText("Loading current Wikelo spreadsheet data...")

        self.start_background_task(
            fetch_wikelo_items,
            self.on_wikelo_items_loaded,
            lambda exc: self.on_wikelo_items_error(exc, silent),
            self.finish_wikelo_refresh,
        )

    def on_wikelo_items_loaded(self, items):
        self.wikelo_items = list(items)
        self.refresh_category_filter()
        self.wikelo_status_label.setText(
            f"Loaded {len(self.wikelo_items)} Wikelo rows from the public spreadsheet. Data is in-memory only."
        )
        self.populate_wikelo_results()

    def on_wikelo_items_error(self, exc, silent=False):
        self.wikelo_status_label.setText(f"Wikelo data refresh failed: {exc}")
        if not silent:
            QMessageBox.warning(self, "Wikelo refresh failed", str(exc))

    def finish_wikelo_refresh(self):
        self.wikelo_refresh_running = False
        self.refresh_wikelo_button.setEnabled(True)
        self.refresh_wikelo_button.setText("Refresh Wikelo Data")

    def refresh_category_filter(self):
        current = self.wikelo_category_filter.currentText()
        categories = ["All categories", *sorted({item.category for item in self.wikelo_items})]
        self.wikelo_category_filter.blockSignals(True)
        self.wikelo_category_filter.clear()
        self.wikelo_category_filter.addItems(categories)
        if current in categories:
            self.wikelo_category_filter.setCurrentText(current)
        self.wikelo_category_filter.blockSignals(False)

    def populate_wikelo_results(self):
        query = self.wikelo_search_input.text().strip().lower()
        category = self.wikelo_category_filter.currentText()
        eligible_items = [
            item
            for item in self.wikelo_items
            if self.matches_wikelo_static_filters(item, category)
        ]
        matching_keys = {
            self.wikelo_group_key(item)
            for item in eligible_items
            if self.matches_wikelo_query(item, query)
        }
        grouped_items = [
            item
            for item in eligible_items
            if self.wikelo_group_key(item) in matching_keys
        ]
        self.visible_wikelo_items = self.group_wikelo_items(grouped_items)

        self.wikelo_results_table.setUpdatesEnabled(False)
        self.wikelo_results_table.setSortingEnabled(False)
        try:
            self.wikelo_results_table.clearSelection()
            self.wikelo_results_table.setRowCount(len(self.visible_wikelo_items))
            for row_index, item in enumerate(self.visible_wikelo_items):
                values = [
                    self.display_wikelo_group_name(item),
                    item.category,
                    item.item_type,
                    item.reward_method,
                    len(item.requirements),
                ]
                for column_index, value in enumerate(values):
                    table_item = SortableTableWidgetItem(str(value))
                    table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                    table_item.setData(Qt.UserRole, row_index)
                    table_item.setData(SORT_ROLE, value)
                    table_item.setToolTip(str(value))
                    if column_index == 4:
                        table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        table_item.setForeground(QColor("#68e6a5" if value else "#7bb9c8"))
                    self.wikelo_results_table.setItem(row_index, column_index, table_item)
            configure_readable_table_columns(self.wikelo_results_table, min_width=120, max_width=360, stretch_last=True)
        finally:
            self.wikelo_results_table.setSortingEnabled(True)
            self.wikelo_results_table.setUpdatesEnabled(True)

        self.wikelo_empty_label.setVisible(not self.visible_wikelo_items)
        self.wikelo_empty_label.setText(
            "No Wikelo items match the current filters." if self.wikelo_items else "No Wikelo items loaded yet."
        )
        self.update_selected_wikelo_panel()

    def matches_wikelo_static_filters(self, item, category):
        if category != "All categories" and item.category != category:
            return False
        if item.retired and not self.show_retired_checkbox.isChecked():
            return False

        return True

    def matches_wikelo_query(self, item, query):
        if not query:
            return True

        parts = [
            item.item_name,
            item.category,
            item.item_type,
            item.reward_method,
            item.mission_name,
            item.reward_item,
            item.location,
            item.source_sheet,
            item.notes,
        ]
        parts.extend(requirement.name for requirement in item.requirements)
        return query in " ".join(str(part) for part in parts if part).lower()

    def group_wikelo_items(self, items):
        groups = {}
        order = []
        for item in items:
            key = self.wikelo_group_key(item)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(item)

        grouped_items = []
        for key in order:
            options = tuple(groups[key])
            grouped_items.append(self.build_wikelo_group(options))

        return grouped_items

    def build_wikelo_group(self, options):
        primary = sorted(
            options,
            key=lambda item: (item.retired, item.category, item.item_name.lower(), item.source_sheet.lower()),
        )[0]
        requirements = self.unique_group_requirements(options)
        reward_method = primary.reward_method
        if len(options) > 1:
            reward_method = f"{len(options)} trade-in options"

        return WikeloItemGroup(
            item_name=primary.item_name,
            category=primary.category,
            item_type=primary.item_type,
            reward_method=reward_method,
            requirements=tuple(requirements),
            options=options,
            retired=all(option.retired for option in options),
            source_url=primary.source_url,
        )

    def unique_group_requirements(self, options):
        requirements = []
        seen = set()
        for item in options:
            for requirement in item.requirements:
                key = (requirement.name.strip().lower(), requirement.quantity.strip().lower())
                if key in seen:
                    continue
                seen.add(key)
                requirements.append(requirement)

        return requirements

    def wikelo_group_key(self, item):
        return normalized_key(item.item_name.strip())

    def display_wikelo_group_name(self, item):
        name = item.item_name.strip()
        if item.retired and "retired" not in name.lower():
            return f"{name} (Retired)"
        return name

    def update_selected_wikelo_panel(self):
        item = self.selected_wikelo_item()
        self.open_selected_wikelo_source_button.setEnabled(item is not None)
        if not item:
            self.selected_wikelo_name_label.setText("No Wikelo item selected")
            self.selected_wikelo_meta_label.setText("")
            self.selected_wikelo_mission_label.setText("")
            self.selected_wikelo_reward_label.setText("")
            self.selected_wikelo_location_label.setText("")
            self.wikelo_requirements_table.setRowCount(0)
            self.wikelo_notes_label.setText("")
            return

        self.selected_wikelo_name_label.setText(self.display_wikelo_group_name(item))
        option_count = len(item.options)
        retired_text = " | Retired" if item.retired else ""
        self.selected_wikelo_meta_label.setText(
            f"{item.category} | {item.item_type} | {option_count} option{'s' if option_count != 1 else ''}{retired_text}"
        )
        self.selected_wikelo_mission_label.setText(f"Trade-in options: {option_count}")
        self.selected_wikelo_reward_label.setText(f"Reward item: {self.display_wikelo_group_name(item)}")
        locations = self.unique_option_values(item.options, "location")
        updates = self.unique_option_values(item.options, "updated")
        location_text = f"Location/System: {', '.join(locations) if locations else 'N/A'}"
        if updates:
            location_text = f"{location_text} | Updated: {', '.join(updates[:3])}"
        self.selected_wikelo_location_label.setText(location_text)
        self.populate_requirement_rows(item)
        self.wikelo_notes_label.setText(self.group_notes_text(item))

    def populate_requirement_rows(self, item):
        self.wikelo_requirements_table.setSortingEnabled(False)
        rows = []
        for option_index, option in enumerate(item.options, start=1):
            option_label = f"{option_index}."
            mission = option.mission_name or option.source_sheet
            source = option.source_sheet
            if option.updated:
                source = f"{source} | {option.updated}"
            if option.retired:
                source = f"{source} | Retired"
            if not option.requirements:
                rows.append((option_label, mission, "N/A", "", source))
                continue

            for requirement in option.requirements:
                rows.append((
                    option_label,
                    mission,
                    requirement.name,
                    requirement.quantity,
                    requirement.source or source,
                ))

        self.wikelo_requirements_table.setRowCount(len(rows))
        for row_index, values in enumerate(rows):
            for column_index, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                table_item.setToolTip(str(value))
                if column_index == 3:
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.wikelo_requirements_table.setItem(row_index, column_index, table_item)

        configure_readable_table_columns(
            self.wikelo_requirements_table,
            min_width=110,
            max_width=420,
            stretch_last=True,
        )
        self.wikelo_requirements_table.setSortingEnabled(True)

    def unique_option_values(self, options, field_name):
        values = []
        seen = set()
        for option in options:
            value = str(getattr(option, field_name, "") or "").strip()
            key = value.lower()
            if not value or key in seen:
                continue
            seen.add(key)
            values.append(value)
        return values

    def group_notes_text(self, item):
        lines = []
        for option_index, option in enumerate(item.options, start=1):
            requirements = ", ".join(
                f"{requirement.quantity} {requirement.name}"
                for requirement in option.requirements
            ) or "No required materials parsed"
            suffix = " (Retired)" if option.retired else ""
            lines.append(f"{option_index}. {option.mission_name or option.source_sheet}{suffix}: {requirements}")

        notes = []
        seen = set()
        for option in item.options:
            note = str(option.notes or "").strip()
            key = note.lower()
            if not note or key in seen:
                continue
            seen.add(key)
            notes.append(note)

        text = "\n".join(lines)
        if notes:
            text = f"{text}\n\nNotes: {notes[0]}"
        return text[:1200]

    def selected_wikelo_item(self):
        row = self.wikelo_results_table.currentRow()
        if row < 0:
            return None
        table_item = self.wikelo_results_table.item(row, 0)
        if not table_item:
            return None
        index = table_item.data(Qt.UserRole)
        if index is None or index >= len(self.visible_wikelo_items):
            return None

        return self.visible_wikelo_items[index]

    def open_wikelo_source(self):
        QDesktopServices.openUrl(QUrl(WIKELO_SOURCE_URL))

    def open_selected_wikelo_source(self):
        item = self.selected_wikelo_item()
        QDesktopServices.openUrl(QUrl(item.source_url if item else WIKELO_SOURCE_URL))

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
