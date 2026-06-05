from PySide6.QtCore import Qt, QTimer
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
    QVBoxLayout,
    QWidget,
)

from app.event_center.service import copy_event_summary_text
from app.event_center.storage import (
    delete_read_notification_events,
    get_notification_event,
    list_notification_events,
    mark_notification_events_read,
    notification_event_counts,
)

from .table_utils import configure_readable_table_columns


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


class EventCenterTab(QWidget):
    def __init__(self):
        super().__init__()

        self.events = []
        self.visible_events = []
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(160)
        self.filter_timer.timeout.connect(self.refresh_events)

        self.build_ui()
        self.refresh_events()

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self.create_header())
        layout.addWidget(self.create_controls())

        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self.create_table_card(), 3)
        content.addWidget(self.create_details_card(), 2)
        layout.addLayout(content, 1)
        self.setLayout(layout)

    def create_header(self):
        header = QFrame()
        header.setObjectName("playerCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title = QLabel("Event Center")
        title.setObjectName("moduleHeading")
        subtitle = QLabel(
            "Persistent local event history for Watchlists, Player Intel, Trading and system changes. "
            "No OS notifications, no telemetry and no cloud sync."
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
        layout.setSpacing(8)

        title = QLabel("EVENT FILTERS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search events, source, entity or metadata...")
        self.category_filter = QComboBox()
        self.category_filter.addItems([
            "All",
            "Trading",
            "Watchlists",
            "Player",
            "Organization",
            "Item",
            "System",
            "Errors",
        ])
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All", "Info", "Change", "Warning", "Important"])
        self.unread_only_checkbox = QCheckBox("Unread only")
        row.addWidget(self.search_input, 1)
        row.addWidget(self.category_filter)
        row.addWidget(self.severity_filter)
        row.addWidget(self.unread_only_checkbox)
        layout.addLayout(row)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.refresh_button = QPushButton("Refresh")
        self.mark_selected_read_button = QPushButton("Mark Selected Read")
        self.mark_all_read_button = QPushButton("Mark All Read")
        self.clear_read_button = QPushButton("Clear Read Events")
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.mark_selected_read_button)
        button_row.addWidget(self.mark_all_read_button)
        button_row.addWidget(self.clear_read_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.search_input.textChanged.connect(self.schedule_refresh)
        self.category_filter.currentTextChanged.connect(self.refresh_events)
        self.severity_filter.currentTextChanged.connect(self.refresh_events)
        self.unread_only_checkbox.stateChanged.connect(self.refresh_events)
        self.refresh_button.clicked.connect(self.refresh_events)
        self.mark_selected_read_button.clicked.connect(self.mark_selected_read)
        self.mark_all_read_button.clicked.connect(self.mark_all_read)
        self.clear_read_button.clicked.connect(self.clear_read_events)

        card.setLayout(layout)
        return card

    def create_table_card(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        self.events_table = QTableWidget(0, 6)
        self.events_table.setHorizontalHeaderLabels([
            "Time",
            "Category",
            "Source",
            "Event",
            "Severity",
            "Read",
        ])
        self.events_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.events_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.events_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.events_table.setAlternatingRowColors(True)
        self.events_table.setSortingEnabled(True)
        self.events_table.itemSelectionChanged.connect(self.update_details)
        configure_readable_table_columns(self.events_table, min_width=110, max_width=360, stretch_last=True)
        self.empty_label = QLabel("Nothing new yet.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.events_table, 1)
        layout.addWidget(self.empty_label)
        card.setLayout(layout)
        return card

    def create_details_card(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        title = QLabel("EVENT DETAILS")
        title.setObjectName("sectionTitle")
        self.details_label = QLabel("Select an event to see details.")
        self.details_label.setObjectName("valueText")
        self.details_label.setWordWrap(True)

        button_row = QHBoxLayout()
        self.copy_summary_button = QPushButton("Copy Summary")
        self.copy_summary_button.setEnabled(False)
        self.mark_detail_read_button = QPushButton("Mark Read")
        self.mark_detail_read_button.setEnabled(False)
        self.copy_summary_button.clicked.connect(self.copy_selected_summary)
        self.mark_detail_read_button.clicked.connect(self.mark_selected_read)
        button_row.addWidget(self.copy_summary_button)
        button_row.addWidget(self.mark_detail_read_button)
        button_row.addStretch(1)

        layout.addWidget(title)
        layout.addWidget(self.details_label)
        layout.addLayout(button_row)
        layout.addStretch(1)
        card.setLayout(layout)
        return card

    def schedule_refresh(self):
        self.filter_timer.start()

    def refresh_events(self):
        query = self.search_input.text().strip()
        category = self.category_filter.currentText()
        severity = self.severity_filter.currentText()
        unread_only = self.unread_only_checkbox.isChecked()
        self.events = list_notification_events(
            query=query,
            category=category,
            severity=severity,
            unread_only=unread_only,
        )
        self.visible_events = self.events
        self.populate_table()
        self.update_status()

    def populate_table(self):
        sorting_enabled = self.events_table.isSortingEnabled()
        self.events_table.setSortingEnabled(False)
        self.events_table.setRowCount(len(self.visible_events))
        for row, event in enumerate(self.visible_events):
            values = [
                event.created_at,
                event.category,
                event.source,
                event.event_type,
                event.severity,
                "Read" if event.is_read else "Unread",
            ]
            sort_values = [
                event.created_at,
                event.category,
                event.source,
                event.event_type,
                event.severity,
                1 if event.is_read else 0,
            ]
            for col, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(SORT_ROLE, sort_values[col])
                item.setData(ROW_ROLE, row)
                item.setToolTip(str(value))
                if not event.is_read:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.events_table.setItem(row, col, item)
        self.events_table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(self.events_table, min_width=110, max_width=360, stretch_last=True)
        self.empty_label.setVisible(not self.visible_events)
        self.update_details()

    def selected_event(self):
        row = self.events_table.currentRow()
        if row < 0:
            return None
        item = self.events_table.item(row, 0)
        if not item:
            return None
        index = item.data(ROW_ROLE)
        if index is None or index >= len(self.visible_events):
            return None
        return self.visible_events[index]

    def update_details(self):
        event = self.selected_event()
        has_event = event is not None
        self.copy_summary_button.setEnabled(has_event)
        self.mark_detail_read_button.setEnabled(has_event and not event.is_read if event else False)
        self.mark_selected_read_button.setEnabled(has_event and not event.is_read if event else False)
        if not event:
            self.details_label.setText("Select an event to see details.")
            return

        metadata_lines = []
        for key, value in event.metadata.items():
            metadata_lines.append(f"{key}: {value}")

        details = [
            f"Time: {event.created_at}",
            f"Category: {event.category}",
            f"Source: {event.source or 'N/A'}",
            f"Entity: {event.entity_name or 'N/A'}",
            f"Event: {event.event_type}",
            f"Severity: {event.severity}",
            f"Read: {'Yes' if event.is_read else 'No'}",
            "",
            event.message,
        ]
        if metadata_lines:
            details.extend(("", "Metadata:", *metadata_lines))
        self.details_label.setText("\n".join(details))

    def mark_selected_read(self):
        event = self.selected_event()
        if not event or event.id is None:
            return
        mark_notification_events_read(event.id)
        self.refresh_events()
        self.status_label.setText("Event marked as read.")

    def mark_all_read(self):
        count = mark_notification_events_read()
        self.refresh_events()
        self.status_label.setText(f"Marked {count} event(s) as read.")

    def clear_read_events(self):
        answer = QMessageBox.question(
            self,
            "Clear Read Events",
            "Delete all read Event Center entries?\n\nUnread events are kept.",
            QMessageBox.Cancel | QMessageBox.Yes,
            QMessageBox.Cancel,
        )
        if answer != QMessageBox.Yes:
            return
        count = delete_read_notification_events()
        self.refresh_events()
        self.status_label.setText(f"Cleared {count} read event(s).")

    def copy_selected_summary(self):
        event = self.selected_event()
        if not event:
            return
        latest = get_notification_event(event.id) or event
        QApplication.clipboard().setText(copy_event_summary_text(latest))
        self.status_label.setText("Event summary copied to clipboard.")

    def update_status(self):
        counts = notification_event_counts()
        category_parts = [
            f"{category}: {count}"
            for category, count in counts["categories"].items()
        ]
        categories = " | ".join(category_parts) if category_parts else "no unread categories"
        self.status_label.setText(
            f"Showing {len(self.visible_events)} event(s). "
            f"Unread: {counts['unread']} / {counts['total']} total. {categories}."
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_events()
