from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
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

from app.database import (
    get_wikelo_checklist_state,
    reset_all_wikelo_checklist_state,
    reset_wikelo_checklist_reward,
    set_wikelo_checklist_state,
)
from app.local_cache import (
    WIKELO_CACHE_KEY,
    WIKELO_SCHEMA_VERSION,
    cache_is_fresh,
    load_wikelo_cache,
    mark_cache_error,
    save_wikelo_cache,
)
from app.wikelo_client import fetch_wikelo_items, normalized_key

from .safe_combobox import SafeComboBox as QComboBox
from .sortable_table_item import SORT_ROLE, SortableTableWidgetItem
from .responsive import ResponsiveStack, install_scroll_area, stabilize_table
from .table_utils import configure_readable_table_columns
from .workers import BackgroundTaskMixin


CHECKLIST_ROLE = Qt.UserRole + 2


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


class WikeloItemsTab(BackgroundTaskMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.wikelo_items = []
        self.visible_wikelo_items = []
        self.wikelo_refresh_running = False
        self.initial_refresh_started = False
        self.loading_wikelo_requirements_table = False

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_module_header(
            "Wikelo Items",
            "Wikelo mission, trade-in and reward browser from the public Wikelo spreadsheet, cached locally after first load.",
        ))

        content = ResponsiveStack(breakpoint_width=980, spacing=12)
        content.addWidget(self.build_wikelo_search_panel(), 3)
        content.addWidget(self.build_wikelo_detail_panel(), 2)
        layout.addWidget(content, 1)

        self.wikelo_scroll_area = install_scroll_area(self, content_widget)
        self.connect_signals()
        self.populate_wikelo_results()
        self.update_selected_wikelo_panel()

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
        button_row.addWidget(self.refresh_wikelo_button)
        layout.addLayout(button_row)

        self.wikelo_status_label = QLabel("Wikelo data will load when this tab is opened or Refresh Wikelo Data is clicked.")
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
        stabilize_table(self.wikelo_results_table, minimum_height=260)
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
        self.reset_selected_wikelo_button = QPushButton("Reset Selected Reward")
        self.reset_all_wikelo_button = QPushButton("Reset All Wikelo Progress")
        self.reset_selected_wikelo_button.clicked.connect(self.reset_selected_wikelo_reward)
        self.reset_all_wikelo_button.clicked.connect(self.reset_all_wikelo_progress)
        button_row.addWidget(self.reset_selected_wikelo_button)
        button_row.addWidget(self.reset_all_wikelo_button)
        layout.addLayout(button_row)

        self.wikelo_requirements_table = self.create_table([
            "Done",
            "Qty",
            "Required Item / Material",
            "Source",
        ])
        self.wikelo_requirements_table.setSortingEnabled(False)
        stabilize_table(self.wikelo_requirements_table, minimum_height=220)
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
        self.wikelo_results_table.itemSelectionChanged.connect(self.update_selected_wikelo_panel)
        self.wikelo_requirements_table.itemChanged.connect(self.on_wikelo_requirement_item_changed)

    def refresh_wikelo_items(self, silent=False):
        if self.wikelo_refresh_running:
            return

        self.initial_refresh_started = True
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
        save_wikelo_cache(self.wikelo_items)
        self.refresh_category_filter()
        self.wikelo_status_label.setText(
            f"Loaded {len(self.wikelo_items)} Wikelo rows from the public spreadsheet. Cached locally for faster reuse."
        )
        self.populate_wikelo_results()

    def on_wikelo_items_error(self, exc, silent=False):
        mark_cache_error(WIKELO_CACHE_KEY, "Public Wikelo spreadsheet", WIKELO_SCHEMA_VERSION, str(exc))
        self.wikelo_status_label.setText(f"Wikelo data refresh failed: {exc}")
        if not silent:
            QMessageBox.warning(self, "Wikelo refresh failed", str(exc))

    def finish_wikelo_refresh(self):
        self.wikelo_refresh_running = False
        self.refresh_wikelo_button.setEnabled(True)
        self.refresh_wikelo_button.setText("Refresh Wikelo Data")

    def ensure_initial_load(self):
        if self.initial_refresh_started:
            return

        self.initial_refresh_started = True
        if self.load_wikelo_cache_if_available():
            return

        self.refresh_wikelo_items(silent=True)

    def load_wikelo_cache_if_available(self):
        items, metadata = load_wikelo_cache()
        if not items:
            return False

        self.wikelo_items = list(items)
        self.refresh_category_filter()
        if metadata and cache_is_fresh(WIKELO_CACHE_KEY):
            self.wikelo_status_label.setText(
                f"Loaded {len(self.wikelo_items)} cached Wikelo rows. Cache is fresh for up to 6 hours."
            )
        else:
            self.wikelo_status_label.setText(
                f"Loaded {len(self.wikelo_items)} cached Wikelo rows. Refresh Wikelo Data when you want the latest spreadsheet."
            )
        self.populate_wikelo_results()
        return True

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
        self.reset_selected_wikelo_button.setEnabled(item is not None)
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
        self.loading_wikelo_requirements_table = True
        self.wikelo_requirements_table.clearContents()
        if hasattr(self.wikelo_requirements_table, "clearSpans"):
            self.wikelo_requirements_table.clearSpans()
        reward_key = self.checklist_reward_key(item)
        checklist_state = get_wikelo_checklist_state(reward_key)
        rows = self.grouped_requirement_rows(item, reward_key, checklist_state)
        self.wikelo_requirements_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            if row["type"] == "option":
                option_item = QTableWidgetItem(row["label"])
                option_item.setFlags(option_item.flags() & ~Qt.ItemIsEditable)
                option_item.setForeground(QColor("#33dfff"))
                self.wikelo_requirements_table.setItem(row_index, 0, option_item)
                self.wikelo_requirements_table.setSpan(row_index, 0, 1, 4)
                continue

            if row["type"] == "empty":
                values = ["", "", row["name"], row["source"]]
                for column_index, value in enumerate(values):
                    table_item = QTableWidgetItem(str(value))
                    table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                    table_item.setToolTip(str(value))
                    self.wikelo_requirements_table.setItem(row_index, column_index, table_item)
                continue

            check_item = QTableWidgetItem("")
            check_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            check_item.setCheckState(Qt.Checked if row["checked"] else Qt.Unchecked)
            check_item.setData(CHECKLIST_ROLE, (
                row["reward_key"],
                row["option_key"],
                row["material_key"],
            ))
            self.wikelo_requirements_table.setItem(row_index, 0, check_item)

            values = [
                row["quantity"],
                row["name"],
                row["source"],
            ]
            for column_index, value in enumerate(values, start=1):
                table_item = QTableWidgetItem(str(value))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                table_item.setToolTip(str(value))
                if column_index == 1:
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.wikelo_requirements_table.setItem(row_index, column_index, table_item)

        configure_readable_table_columns(
            self.wikelo_requirements_table,
            min_width=110,
            max_width=420,
            stretch_last=True,
        )
        self.loading_wikelo_requirements_table = False

    def grouped_requirement_rows(self, item, reward_key, checklist_state):
        rows = []
        for option_index, option in enumerate(item.options, start=1):
            mission = option.mission_name or option.source_sheet
            source = option.source_sheet
            if option.updated:
                source = f"{source} | {option.updated}"
            if option.retired:
                source = f"{source} | Retired"
            option_key = self.checklist_option_key(option)
            option_label = f"Option {option_index} - {mission}"
            if source:
                option_label = f"{option_label} ({source})"
            rows.append({
                "type": "option",
                "label": option_label,
            })
            if not option.requirements:
                rows.append({
                    "type": "empty",
                    "name": "No required materials parsed",
                    "source": source,
                })
                continue

            for requirement in option.requirements:
                material_key = self.checklist_material_key(requirement)
                rows.append({
                    "type": "material",
                    "reward_key": reward_key,
                    "option_key": option_key,
                    "material_key": material_key,
                    "quantity": requirement.quantity,
                    "name": requirement.name,
                    "source": requirement.source or source,
                    "checked": checklist_state.get((option_key, material_key), False),
                })

        return rows

    def on_wikelo_requirement_item_changed(self, item):
        if self.loading_wikelo_requirements_table or item.column() != 0:
            return

        checklist_keys = item.data(CHECKLIST_ROLE)
        if not checklist_keys:
            return

        reward_key, option_key, material_key = checklist_keys
        set_wikelo_checklist_state(
            reward_key,
            option_key,
            material_key,
            item.checkState() == Qt.Checked,
        )

    def checklist_reward_key(self, item):
        return normalized_key(item.item_name)

    def checklist_option_key(self, option):
        return normalized_key("|".join((
            option.mission_name,
            option.source_sheet,
            option.updated,
        )))

    def checklist_material_key(self, requirement):
        return normalized_key(f"{requirement.quantity}|{requirement.name}")

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

    def reset_selected_wikelo_reward(self):
        item = self.selected_wikelo_item()
        if not item:
            return

        message = QMessageBox(self)
        message.setIcon(QMessageBox.Warning)
        message.setWindowTitle("Reset Reward Progress")
        message.setText("Reset checklist progress for this reward?\n\nThis cannot be undone.")
        cancel_button = message.addButton("Cancel", QMessageBox.RejectRole)
        reset_button = message.addButton("Reset", QMessageBox.DestructiveRole)
        message.setDefaultButton(cancel_button)
        message.exec()
        if message.clickedButton() != reset_button:
            return

        reset_wikelo_checklist_reward(self.checklist_reward_key(item))
        self.populate_requirement_rows(item)

    def reset_all_wikelo_progress(self):
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Warning)
        message.setWindowTitle("Reset All Wikelo Progress")
        message.setText(
            "Reset ALL Wikelo checklist progress?\n\n"
            "Use this after game wipes or if you want to start fresh.\n\n"
            "This cannot be undone."
        )
        cancel_button = message.addButton("Cancel", QMessageBox.RejectRole)
        reset_button = message.addButton("Reset All", QMessageBox.DestructiveRole)
        message.setDefaultButton(cancel_button)
        message.exec()
        if message.clickedButton() != reset_button:
            return

        reset_all_wikelo_checklist_state()
        item = self.selected_wikelo_item()
        if item:
            self.populate_requirement_rows(item)

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
