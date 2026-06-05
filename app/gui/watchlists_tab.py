from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.watchlists import service
from app.watchlists.storage import (
    delete_watchlist_entry,
    get_latest_snapshot,
    list_watchlist_entries,
    list_watchlist_events,
    mark_watchlist_events_read,
    overview_counts,
    set_watchlist_active,
)

from .table_utils import configure_readable_table_columns
from .workers import BackgroundTaskMixin


SORT_ROLE = Qt.UserRole + 1
ROW_ROLE = Qt.UserRole + 2


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


class WatchlistsTab(BackgroundTaskMixin, QWidget):
    def __init__(self):
        super().__init__()

        self.refresh_running = False
        self.panels = []

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self.create_header())

        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_overview_tab(), "Overview")

        self.trading_panel = WatchlistPanel(
            self,
            ("trading_commodity", "trading_route"),
            "Trading Watchlists",
            "Track UEX commodities and complete buy/sell routes. Refresh is manual only.",
        )
        self.tabs.addTab(self.trading_panel, "Trading")
        self.panels.append(self.trading_panel)

        self.items_panel = WatchlistPanel(
            self,
            ("item", "ship"),
            "Items & Ships",
            "Track Item Finder items and ships locally. Live refresh is planned for a later pass.",
        )
        self.tabs.addTab(self.items_panel, "Items & Ships")
        self.panels.append(self.items_panel)

        self.intel_panel = WatchlistPanel(
            self,
            ("player", "org"),
            "Intel Watchlists",
            "Track RSI player and organization changes manually. No scheduled polling is used.",
            empty_text="No tracked players or organizations yet. Add them from Player Lookup or Search History.",
        )
        self.tabs.addTab(self.intel_panel, "Intel")
        self.panels.append(self.intel_panel)
        layout.addWidget(self.tabs, 1)

        self.setLayout(layout)
        self.reload_all()

    def create_header(self):
        header = QFrame()
        header.setObjectName("playerCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title = QLabel("Watchlists")
        title.setObjectName("moduleHeading")
        subtitle = QLabel(
            "Local-only tracking for Trading routes, commodities, items and ships. "
            "No telemetry, no cloud sync, no background polling."
        )
        subtitle.setObjectName("moduleSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        header.setLayout(layout)
        return header

    def create_overview_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        stats = QFrame()
        stats.setObjectName("sectionCard")
        stats_layout = QVBoxLayout()
        stats_layout.setContentsMargins(16, 14, 16, 16)
        stats_layout.setSpacing(8)
        title = QLabel("OVERVIEW")
        title.setObjectName("sectionTitle")
        self.overview_counts_label = QLabel("")
        self.overview_counts_label.setObjectName("valueText")
        self.overview_counts_label.setWordWrap(True)
        self.overview_categories_label = QLabel("")
        self.overview_categories_label.setObjectName("moduleSubtitle")
        self.overview_categories_label.setWordWrap(True)
        stats_layout.addWidget(title)
        stats_layout.addWidget(self.overview_counts_label)
        stats_layout.addWidget(self.overview_categories_label)
        stats.setLayout(stats_layout)
        layout.addWidget(stats)

        events_card = QFrame()
        events_card.setObjectName("sectionCard")
        events_layout = QVBoxLayout()
        events_layout.setContentsMargins(16, 14, 16, 16)
        events_layout.setSpacing(8)
        events_title = QLabel("RECENT EVENTS")
        events_title.setObjectName("sectionTitle")
        self.overview_events_table = QTableWidget(0, 4)
        self.overview_events_table.setHorizontalHeaderLabels(["When", "Watch", "Type", "Message"])
        self.overview_events_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.overview_events_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.overview_events_table.setAlternatingRowColors(True)
        self.overview_events_table.setSortingEnabled(True)
        configure_readable_table_columns(self.overview_events_table, min_width=110, max_width=420, stretch_last=True)
        self.overview_empty_label = QLabel("No watchlist events yet.")
        self.overview_empty_label.setObjectName("emptyState")
        self.overview_empty_label.setAlignment(Qt.AlignCenter)
        events_layout.addWidget(events_title)
        events_layout.addWidget(self.overview_events_table, 1)
        events_layout.addWidget(self.overview_empty_label)
        events_card.setLayout(events_layout)
        layout.addWidget(events_card, 1)

        button_row = QHBoxLayout()
        self.overview_refresh_button = QPushButton("Refresh Overview")
        self.overview_mark_read_button = QPushButton("Mark All Events Read")
        self.overview_refresh_button.clicked.connect(self.reload_all)
        self.overview_mark_read_button.clicked.connect(self.mark_all_events_read)
        button_row.addWidget(self.overview_refresh_button)
        button_row.addWidget(self.overview_mark_read_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        widget.setLayout(layout)
        return widget

    def reload_all(self):
        self.refresh_overview()
        for panel in self.panels:
            panel.reload_entries()

    def refresh_overview(self):
        counts = overview_counts()
        self.overview_counts_label.setText(
            f"Active watches: {counts['active_count']} | "
            f"Unread events: {counts['unread_count']} | "
            f"Last checked: {counts['last_checked']}"
        )
        categories = counts["categories"]
        if categories:
            parts = [
                f"{service.display_category(category)}: {count}"
                for category, count in categories.items()
            ]
            self.overview_categories_label.setText("Categories: " + " | ".join(parts))
        else:
            self.overview_categories_label.setText("Categories: none yet.")

        events = list_watchlist_events(limit=20)
        entries = {entry.id: entry for entry in list_watchlist_entries(include_inactive=True)}
        self.overview_events_table.setSortingEnabled(False)
        self.overview_events_table.setRowCount(len(events))
        for row, event in enumerate(events):
            entry = entries.get(event.watchlist_id)
            values = [
                event.created_at,
                entry.name if entry else f"Watch #{event.watchlist_id}",
                event.event_type,
                event.message,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setToolTip(str(value))
                self.overview_events_table.setItem(row, col, item)
        self.overview_events_table.setSortingEnabled(True)
        configure_readable_table_columns(self.overview_events_table, min_width=110, max_width=420, stretch_last=True)
        self.overview_empty_label.setVisible(not events)

    def mark_all_events_read(self):
        count = mark_watchlist_events_read()
        self.reload_all()
        self.overview_counts_label.setText(f"Marked {count} event(s) as read.")

    def refresh_entries(self, entries, panel):
        entries = [entry for entry in entries if entry and entry.id is not None]
        if not entries or self.refresh_running:
            return

        self.refresh_running = True
        panel.set_status(f"Refreshing {len(entries)} watch(es)...")
        self.start_background_task(
            lambda: service.refresh_watchlist_entries(entries),
            lambda _result, target=panel: self.on_refresh_finished(target),
            lambda exc, target=panel: self.on_refresh_error(target, exc),
            lambda: self.finish_refresh(),
        )

    def on_refresh_finished(self, panel):
        panel.set_status("Watchlist refresh complete.")
        self.reload_all()

    def on_refresh_error(self, panel, exc):
        panel.set_status(f"Watchlist refresh failed: {exc}")

    def finish_refresh(self):
        self.refresh_running = False


class WatchlistPanel(QWidget):
    def __init__(self, owner, categories, title, subtitle, empty_text="No watchlist entries yet."):
        super().__init__()
        self.owner = owner
        self.categories = tuple(categories)
        self.empty_text = empty_text
        self.entries = []
        self.visible_entries = []

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self.create_controls(title, subtitle))

        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self.create_table_card(), 3)
        content.addWidget(self.create_details_card(), 2)
        layout.addLayout(content, 1)

        self.setLayout(layout)

    def create_controls(self, title_text, subtitle_text):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        title = QLabel(title_text.upper())
        title.setObjectName("sectionTitle")
        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("moduleSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search watchlists...")
        self.category_filter = QComboBox()
        self.category_filter.addItem("All categories")
        for category in self.categories:
            self.category_filter.addItem(service.display_category(category), category)
        self.show_inactive_checkbox = QCheckBox("Show inactive")
        row.addWidget(self.search_input, 1)
        row.addWidget(self.category_filter)
        row.addWidget(self.show_inactive_checkbox)
        layout.addLayout(row)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.refresh_selected_button = QPushButton("Refresh Selected")
        self.refresh_all_button = QPushButton("Refresh All")
        self.mark_read_button = QPushButton("Mark Events Read")
        self.toggle_active_button = QPushButton("Disable Watch")
        self.delete_button = QPushButton("Delete Watch")
        self.copy_button = QPushButton("Copy Summary")
        button_row.addWidget(self.refresh_selected_button)
        button_row.addWidget(self.refresh_all_button)
        button_row.addWidget(self.mark_read_button)
        button_row.addWidget(self.toggle_active_button)
        button_row.addWidget(self.delete_button)
        button_row.addWidget(self.copy_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.search_input.textChanged.connect(self.populate_table)
        self.category_filter.currentTextChanged.connect(self.populate_table)
        self.show_inactive_checkbox.stateChanged.connect(self.reload_entries)
        self.refresh_selected_button.clicked.connect(self.refresh_selected)
        self.refresh_all_button.clicked.connect(self.refresh_all)
        self.mark_read_button.clicked.connect(self.mark_selected_read)
        self.toggle_active_button.clicked.connect(self.toggle_selected_active)
        self.delete_button.clicked.connect(self.delete_selected)
        self.copy_button.clicked.connect(self.copy_selected_summary)

        card.setLayout(layout)
        return card

    def create_table_card(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Category",
            "Name",
            "Source",
            "Last Status",
            "Last Checked",
            "Unread",
        ])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.itemSelectionChanged.connect(self.update_details)
        configure_readable_table_columns(self.table, min_width=100, max_width=360, stretch_last=True)
        self.empty_label = QLabel(self.empty_text)
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty_label)
        card.setLayout(layout)
        return card

    def create_details_card(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        title = QLabel("DETAILS")
        title.setObjectName("sectionTitle")
        self.details_label = QLabel("Select a watch to see details.")
        self.details_label.setObjectName("valueText")
        self.details_label.setWordWrap(True)

        events_title = QLabel("RECENT EVENTS")
        events_title.setObjectName("sectionTitle")
        self.events_table = QTableWidget(0, 3)
        self.events_table.setHorizontalHeaderLabels(["When", "Type", "Message"])
        self.events_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.events_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.events_table.setAlternatingRowColors(True)
        self.events_table.setSortingEnabled(True)
        configure_readable_table_columns(self.events_table, min_width=110, max_width=360, stretch_last=True)
        self.events_empty_label = QLabel("No events for this watch.")
        self.events_empty_label.setObjectName("emptyState")
        self.events_empty_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(self.details_label)
        layout.addWidget(events_title)
        layout.addWidget(self.events_table, 1)
        layout.addWidget(self.events_empty_label)
        card.setLayout(layout)
        return card

    def reload_entries(self):
        self.entries = list_watchlist_entries(
            self.categories,
            include_inactive=self.show_inactive_checkbox.isChecked(),
        )
        self.populate_table()

    def populate_table(self):
        query = self.search_input.text().strip().lower()
        category_data = self.category_filter.currentData()

        self.visible_entries = [
            entry
            for entry in self.entries
            if self.entry_matches(entry, query, category_data)
        ]

        sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.visible_entries))
        for row, entry in enumerate(self.visible_entries):
            values = [
                service.display_category(entry.category),
                entry.name,
                entry.source,
                service.status_text(entry.last_status),
                entry.last_checked_at or "Never",
                entry.unread_events,
            ]
            sort_values = [
                values[0],
                entry.name,
                entry.source,
                entry.last_status,
                entry.last_checked_at or "",
                entry.unread_events,
            ]
            for col, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(SORT_ROLE, sort_values[col])
                item.setData(ROW_ROLE, row)
                item.setToolTip(str(value))
                if col == 5:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, item)

        self.table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(self.table, min_width=100, max_width=360, stretch_last=True)
        self.empty_label.setVisible(not self.visible_entries)
        self.update_details()

    def entry_matches(self, entry, query, category_data):
        if category_data and entry.category != category_data:
            return False
        if not query:
            return True

        haystack = " ".join((
            entry.category,
            entry.name,
            entry.source,
            entry.last_status,
            str(entry.metadata),
        )).lower()
        return query in haystack

    def selected_entry(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        index = item.data(ROW_ROLE)
        if index is None or index >= len(self.visible_entries):
            return None
        return self.visible_entries[index]

    def update_details(self):
        entry = self.selected_entry()
        has_entry = entry is not None
        self.refresh_selected_button.setEnabled(has_entry)
        self.mark_read_button.setEnabled(has_entry)
        self.toggle_active_button.setEnabled(has_entry)
        self.delete_button.setEnabled(has_entry)
        self.copy_button.setEnabled(has_entry)
        if not entry:
            self.details_label.setText("Select a watch to see details.")
            self.events_table.setRowCount(0)
            self.events_empty_label.setVisible(True)
            self.toggle_active_button.setText("Disable Watch")
            return

        self.toggle_active_button.setText("Disable Watch" if entry.is_active else "Enable Watch")
        snapshot = get_latest_snapshot(entry.id)
        details = [
            f"Name: {entry.name}",
            f"Category: {service.display_category(entry.category)}",
            f"Source: {entry.source or 'N/A'}",
            f"Active: {'Yes' if entry.is_active else 'No'}",
            f"Last status: {service.status_text(entry.last_status)}",
            f"Last checked: {entry.last_checked_at or 'Never'}",
        ]
        if snapshot:
            details.append("")
            details.append(f"Latest snapshot: {service.status_text(snapshot.status)}")
            if snapshot.notes:
                details.append(f"Notes: {snapshot.notes}")
            for key, value in snapshot.value.items():
                details.append(f"{key}: {value}")
        elif entry.metadata:
            details.append("")
            details.append("Stored metadata:")
            for key, value in entry.metadata.items():
                details.append(f"{key}: {value}")

        self.details_label.setText("\n".join(details))
        self.populate_events(entry)

    def populate_events(self, entry):
        events = list_watchlist_events(entry.id, limit=20)
        self.events_table.setSortingEnabled(False)
        self.events_table.setRowCount(len(events))
        for row, event in enumerate(events):
            for col, value in enumerate((event.created_at, event.event_type, event.message)):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setToolTip(str(value))
                self.events_table.setItem(row, col, item)
        self.events_table.setSortingEnabled(True)
        configure_readable_table_columns(self.events_table, min_width=110, max_width=360, stretch_last=True)
        self.events_empty_label.setVisible(not events)

    def refresh_selected(self):
        entry = self.selected_entry()
        if entry:
            self.owner.refresh_entries([entry], self)

    def refresh_all(self):
        entries = [entry for entry in self.visible_entries if entry.is_active]
        if not entries:
            self.set_status("No active visible watches to refresh.")
            return
        self.owner.refresh_entries(entries, self)

    def mark_selected_read(self):
        entry = self.selected_entry()
        if not entry:
            return
        count = mark_watchlist_events_read(entry.id)
        self.owner.reload_all()
        self.set_status(f"Marked {count} event(s) as read.")

    def toggle_selected_active(self):
        entry = self.selected_entry()
        if not entry:
            return
        set_watchlist_active(entry.id, not entry.is_active)
        self.owner.reload_all()
        self.set_status(f"{'Enabled' if not entry.is_active else 'Disabled'} watch: {entry.name}")

    def delete_selected(self):
        entry = self.selected_entry()
        if not entry:
            return
        response = QMessageBox.question(
            self,
            "Delete Watch",
            f"Delete watchlist entry for {entry.name}?\n\nThis removes its snapshots and events.",
            QMessageBox.Cancel | QMessageBox.Yes,
            QMessageBox.Cancel,
        )
        if response != QMessageBox.Yes:
            return
        delete_watchlist_entry(entry.id)
        self.owner.reload_all()
        self.set_status(f"Deleted watch: {entry.name}")

    def copy_selected_summary(self):
        entry = self.selected_entry()
        if not entry:
            return
        QApplication.clipboard().setText(service.copy_watchlist_summary_text(entry))
        self.set_status("Watch summary copied to clipboard.")

    def set_status(self, text):
        self.status_label.setText(text)
