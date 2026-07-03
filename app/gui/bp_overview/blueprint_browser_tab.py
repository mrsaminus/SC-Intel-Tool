from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.blueprints_client import load_blueprints
from app.blueprints_storage import get_owned_blueprint_keys, get_owned_crafting_materials

from ..safe_combobox import SafeComboBox as QComboBox
from ..workers import BackgroundTaskMixin
from ..responsive import ResponsiveStack, install_scroll_area
from ..table_utils import configure_readable_table_columns
from .blueprint_details_panel import BlueprintDetailsPanel
from .shared import ROW_ROLE, SORT_ROLE, craftability_status, create_card, create_header, create_table, table_item


OWNED_COLUMN = 3


class BlueprintBrowserTab(BackgroundTaskMixin, QWidget):
    def __init__(self, owned_changed_callback=None, blueprints_loaded_callback=None):
        super().__init__()
        self.blueprints = []
        self.visible_blueprints = []
        self.owned_keys = get_owned_blueprint_keys()
        self.owned_changed_callback = owned_changed_callback
        self.blueprints_loaded_callback = blueprints_loaded_callback
        self.refresh_running = False
        self.initial_load_started = False
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(160)
        self.filter_timer.timeout.connect(self.populate_table)

        self.build_ui()
        self.connect_signals()
        self.populate_table()
        self.update_details()

    def build_ui(self):
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(create_header(
            "Blueprint Browser",
            "Browse Star Citizen crafting blueprints, recipes, mission context and local ownership.",
        ))

        content = ResponsiveStack(breakpoint_width=980, spacing=12)
        content.addWidget(self.create_browser_panel(), 3)
        self.details_panel = BlueprintDetailsPanel(self.on_detail_owned_changed)
        content.addWidget(self.details_panel, 2)
        layout.addWidget(content, 1)
        self.blueprint_browser_scroll_area = install_scroll_area(self, content_widget)

    def create_browser_panel(self):
        card = create_card("BLUEPRINTS")
        layout = card.layout()

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search blueprint, material or mission...")
        self.category_filter = QComboBox()
        self.category_filter.addItem("All categories")
        self.category_filter.setMinimumWidth(240)
        self.category_filter.setMinimumContentsLength(24)
        self.owned_only_checkbox = QCheckBox("Owned only")
        self.missing_only_checkbox = QCheckBox("Missing only")
        self.craftable_only_checkbox = QCheckBox("Craftable only")
        controls.addWidget(self.search_input, 1)
        controls.addWidget(self.category_filter)
        controls.addWidget(self.owned_only_checkbox)
        controls.addWidget(self.missing_only_checkbox)
        controls.addWidget(self.craftable_only_checkbox)
        layout.addLayout(controls)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.refresh_button = QPushButton("Refresh / Load Blueprints")
        buttons.addWidget(self.refresh_button)
        layout.addLayout(buttons)

        self.status_label = QLabel("No blueprint data loaded yet. Click Refresh / Load Blueprints.")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.blueprint_table = create_table([
            "Blueprint",
            "Category",
            "Mission / Drop",
            "Owned",
            "Patch / Updated",
        ])
        layout.addWidget(self.blueprint_table, 1)
        self.empty_label = QLabel("No blueprint data loaded yet.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.empty_label)
        return card

    def connect_signals(self):
        self.refresh_button.clicked.connect(lambda: self.refresh_blueprints(force_refresh=True))
        self.search_input.textChanged.connect(self.queue_filter)
        self.category_filter.currentTextChanged.connect(self.populate_table)
        self.owned_only_checkbox.stateChanged.connect(self.on_owned_filter_changed)
        self.missing_only_checkbox.stateChanged.connect(self.on_missing_filter_changed)
        self.craftable_only_checkbox.stateChanged.connect(self.populate_table)
        self.blueprint_table.itemSelectionChanged.connect(self.update_details)

    def ensure_initial_load(self):
        if self.initial_load_started:
            return
        self.initial_load_started = True
        self.refresh_blueprints(force_refresh=False)

    def refresh_blueprints(self, force_refresh=True):
        if self.refresh_running:
            return
        self.initial_load_started = True
        self.refresh_running = True
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Loading...")
        self.status_label.setText("Loading blueprint data...")
        self.start_background_task(
            lambda: load_blueprints(force_refresh=force_refresh, raise_on_missing=False),
            self.on_blueprints_loaded,
            self.on_blueprints_error,
            self.finish_refresh,
        )

    def on_blueprints_loaded(self, snapshot):
        blueprints = snapshot.blueprints if hasattr(snapshot, "blueprints") else snapshot
        self.blueprints = [blueprint for blueprint in blueprints if blueprint.ownable]
        self.owned_keys = get_owned_blueprint_keys()
        self.populate_category_filter()
        self.status_label.setText(self.blueprint_status_text(snapshot, len(self.blueprints)))
        if self.blueprints_loaded_callback:
            self.blueprints_loaded_callback(self.blueprints)
        self.populate_table()

    def blueprint_status_text(self, snapshot, count):
        base = f"Loaded {count} blueprints. Owned state is local-only."
        if not hasattr(snapshot, "cache_status"):
            return base

        if snapshot.cache_status == "fresh" and snapshot.from_cache:
            return f"Loaded {count} cached blueprints. Cache is fresh for up to 6 hours. Owned state is local-only."
        if snapshot.cache_status == "stale":
            return f"Loaded {count} cached blueprints. Cache is stale; refresh available. Owned state is local-only."
        if snapshot.cache_status == "offline":
            return (
                f"SC Craft Tools unavailable; loaded {count} cached blueprints. "
                f"Last refresh warning: {snapshot.source_error}"
            )
        if snapshot.cache_status == "missing" and snapshot.source_error:
            return f"Blueprint refresh failed: {snapshot.source_error}"
        return base

    def on_blueprints_error(self, exc):
        self.status_label.setText(f"Blueprint refresh failed: {exc}")

    def finish_refresh(self):
        self.refresh_running = False
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh / Load Blueprints")

    def populate_category_filter(self):
        current = self.category_filter.currentText()
        categories = sorted({item.category for item in self.blueprints if item.category})
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All categories")
        self.category_filter.addItems(categories)
        self.update_category_filter_width()
        index = self.category_filter.findText(current)
        self.category_filter.setCurrentIndex(index if index >= 0 else 0)
        self.category_filter.blockSignals(False)

    def update_category_filter_width(self):
        labels = [
            self.category_filter.itemText(index)
            for index in range(self.category_filter.count())
        ]
        longest = max(labels, key=len, default="All categories")
        popup_width = min(520, max(260, self.category_filter.fontMetrics().horizontalAdvance(longest) + 48))
        self.category_filter.setMinimumWidth(min(320, popup_width))
        self.category_filter.view().setMinimumWidth(popup_width)
        for index, label in enumerate(labels):
            self.category_filter.setItemData(index, label, Qt.ToolTipRole)

    def queue_filter(self):
        self.filter_timer.start()

    def on_owned_filter_changed(self, *_):
        if self.owned_only_checkbox.isChecked():
            self.missing_only_checkbox.blockSignals(True)
            self.missing_only_checkbox.setChecked(False)
            self.missing_only_checkbox.blockSignals(False)
        self.populate_table()

    def on_missing_filter_changed(self, *_):
        if self.missing_only_checkbox.isChecked():
            self.owned_only_checkbox.blockSignals(True)
            self.owned_only_checkbox.setChecked(False)
            self.owned_only_checkbox.blockSignals(False)
        self.populate_table()

    def populate_table(self, *_, preserve_key=None):
        selected = self.selected_blueprint()
        selected_key = preserve_key or (selected.key if selected else None)
        scroll_value = self.blueprint_table.verticalScrollBar().value()
        query = self.search_input.text().strip().lower()
        category = self.category_filter.currentText()
        owned_only = self.owned_only_checkbox.isChecked()
        missing_only = self.missing_only_checkbox.isChecked()
        craftable_only = self.craftable_only_checkbox.isChecked()
        owned_materials = get_owned_crafting_materials() if craftable_only else {}

        visible = []
        for blueprint in self.blueprints:
            owned = blueprint.key in self.owned_keys
            if category != "All categories" and blueprint.category != category:
                continue
            if owned_only and not owned:
                continue
            if missing_only and owned:
                continue
            if craftable_only and craftability_status(blueprint, owned_materials) != "Craftable":
                continue
            if query and query not in self.search_blob(blueprint):
                continue
            visible.append(blueprint)

        self.visible_blueprints = visible
        self.blueprint_table.setSortingEnabled(False)
        self.blueprint_table.setRowCount(len(visible))
        for row, blueprint in enumerate(visible):
            owned = blueprint.key in self.owned_keys
            values = [
                blueprint.blueprint_name,
                blueprint.category,
                blueprint.source_summary,
                "Yes" if owned else "No",
                blueprint.patch,
            ]
            for column, value in enumerate(values):
                sort_value = 1 if column == OWNED_COLUMN and owned else 0 if column == OWNED_COLUMN else value
                item = table_item(value, sort_value)
                item.setData(ROW_ROLE, row)
                self.blueprint_table.setItem(row, column, item)
        self.blueprint_table.setSortingEnabled(True)
        self.autosize_blueprint_table()
        restored = self.restore_selection(selected_key, scroll_value)
        self.empty_label.setVisible(not visible)
        if not visible:
            self.empty_label.setText(
                "No blueprints match the current filters." if self.blueprints else "No blueprint data loaded yet."
            )
        if not restored:
            self.update_details()

    def autosize_blueprint_table(self):
        configure_readable_table_columns(self.blueprint_table, min_width=100, max_width=420, stretch_last=False)
        preferred_widths = {
            0: 300,
            1: 180,
            2: 260,
            3: 100,
            4: 150,
        }
        for column, width in preferred_widths.items():
            self.blueprint_table.setColumnWidth(column, max(self.blueprint_table.columnWidth(column), width))

    def restore_selection(self, selected_key, scroll_value):
        if not selected_key:
            return False
        for row in range(self.blueprint_table.rowCount()):
            item = self.blueprint_table.item(row, 0)
            if not item:
                continue
            source_row = item.data(ROW_ROLE)
            if source_row is None or source_row >= len(self.visible_blueprints):
                continue
            if self.visible_blueprints[source_row].key == selected_key:
                self.blueprint_table.blockSignals(True)
                self.blueprint_table.setCurrentCell(row, 0)
                self.blueprint_table.verticalScrollBar().setValue(scroll_value)
                self.blueprint_table.blockSignals(False)
                self.update_details()
                return True
        return False

    def search_blob(self, blueprint):
        parts = [
            blueprint.blueprint_name,
            blueprint.category,
            blueprint.patch,
            " ".join(ingredient.name for ingredient in blueprint.ingredients),
            " ".join(mission.name for mission in blueprint.missions),
        ]
        return " ".join(parts).lower()

    def selected_blueprint(self):
        row = self.blueprint_table.currentRow()
        if row < 0:
            return None
        item = self.blueprint_table.item(row, 0)
        if not item:
            return None
        source_row = item.data(ROW_ROLE)
        if source_row is None or source_row >= len(self.visible_blueprints):
            return None
        return self.visible_blueprints[source_row]

    def update_details(self):
        blueprint = self.selected_blueprint()
        owned = blueprint.key in self.owned_keys if blueprint else False
        self.details_panel.set_blueprint(blueprint, owned)

    def on_detail_owned_changed(self, blueprint, owned):
        if owned:
            self.owned_keys.add(blueprint.key)
        else:
            self.owned_keys.discard(blueprint.key)
        if self.owned_only_checkbox.isChecked() or self.missing_only_checkbox.isChecked():
            self.populate_table(preserve_key=blueprint.key)
        else:
            self.refresh_owned_cells()
        if self.owned_changed_callback:
            self.owned_changed_callback()

    def refresh_owned_keys(self):
        self.owned_keys = get_owned_blueprint_keys()
        self.populate_table()

    def refresh_material_context(self):
        self.populate_table()
        self.update_details()

    def refresh_owned_cells(self):
        self.blueprint_table.blockSignals(True)
        for row in range(self.blueprint_table.rowCount()):
            row_item = self.blueprint_table.item(row, 0)
            owned_item = self.blueprint_table.item(row, OWNED_COLUMN)
            if not row_item or not owned_item:
                continue
            source_row = row_item.data(ROW_ROLE)
            if source_row is None or source_row >= len(self.visible_blueprints):
                continue
            owned = self.visible_blueprints[source_row].key in self.owned_keys
            owned_item.setText("Yes" if owned else "No")
            owned_item.setData(SORT_ROLE, 1 if owned else 0)
        self.blueprint_table.blockSignals(False)
