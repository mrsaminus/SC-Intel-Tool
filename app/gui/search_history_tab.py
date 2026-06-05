import requests
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database import (
    clear_lookup_history,
    delete_lookup_history,
    get_lookup_history,
    save_lookup,
    set_lookup_history_flag,
)
from app.event_center.service import record_event
from app.player_intel import (
    main_org_snapshot_from_lookup,
    player_change_events,
    player_change_summary,
    player_snapshot_from_history,
    player_snapshot_from_lookup,
)
from app.rsi_lookup import RSILookupError, lookup_player
from app.watchlists.service import add_org_watch, add_player_snapshot_watch, add_player_watch

from .constants import IMAGE_HEADERS
from .table_utils import configure_readable_table_columns
from .workers import BackgroundTaskMixin


class SearchHistoryTab(BackgroundTaskMixin, QWidget):
    def __init__(self):
        super().__init__()

        self.history_rows = []
        self.history_lookup_running = False
        self.current_profile_url = None
        self.current_organizations_url = None
        self.current_main_org_url = None
        self.current_lookup_data = None
        self.detail_player_facts = {}
        self.detail_org_facts = {}
        self.history_sort_column = None
        self.history_sort_order = Qt.AscendingOrder
        self.history_lookup_request_id = 0
        self.history_filter_timer = QTimer(self)
        self.history_filter_timer.setSingleShot(True)
        self.history_filter_timer.setInterval(180)
        self.history_filter_timer.timeout.connect(self.apply_history_filters)

        self.build_ui()
        self.reset_detail_panel()
        self.refresh_history()

    def build_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        list_card = QFrame()
        list_card.setObjectName("sectionCard")
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(16, 14, 16, 16)
        list_layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("SEARCH HISTORY")
        title.setObjectName("sectionTitle")
        self.refresh_button = QPushButton("Refresh")
        self.remove_selected_button = QPushButton("Remove Selected")
        self.clear_history_button = QPushButton("Clear History")
        self.rerun_lookup_button = QPushButton("Re-run Lookup")
        self.pin_selected_button = QPushButton("Toggle Pin")
        self.favorite_selected_button = QPushButton("Toggle Favorite")
        self.watch_player_button = QPushButton("Watch Player")
        self.watch_org_button = QPushButton("Watch Org")
        header.addWidget(title, 1)
        header.addWidget(self.refresh_button)
        list_layout.addLayout(header)

        history_actions = QHBoxLayout()
        history_actions.addWidget(self.rerun_lookup_button)
        history_actions.addWidget(self.pin_selected_button)
        history_actions.addWidget(self.favorite_selected_button)
        history_actions.addWidget(self.watch_player_button)
        history_actions.addWidget(self.watch_org_button)
        history_actions.addWidget(self.remove_selected_button)
        history_actions.addWidget(self.clear_history_button)
        list_layout.addLayout(history_actions)

        filter_row = QHBoxLayout()
        self.history_filter_input = QLineEdit()
        self.history_filter_input.setPlaceholderText("Filter name/org/SID...")
        self.piracy_filter_box = QComboBox()
        self.piracy_filter_box.addItems(["All", "Piracy YES", "Piracy NO"])
        filter_row.addWidget(self.history_filter_input, 1)
        filter_row.addWidget(self.piracy_filter_box)
        list_layout.addLayout(filter_row)

        filter_meta_row = QHBoxLayout()
        self.history_count_label = QLabel("0 shown")
        self.history_count_label.setObjectName("labelText")
        self.clear_filters_button = QPushButton("Clear Filters")
        filter_meta_row.addWidget(self.history_count_label, 1)
        filter_meta_row.addWidget(self.clear_filters_button)
        list_layout.addLayout(filter_meta_row)

        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(["Name", "Org", "Piracy", "Flags"])
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        configure_readable_table_columns(self.history_table, min_width=95, max_width=260)
        self.history_table.horizontalHeader().setSectionsClickable(True)
        self.history_table.horizontalHeader().setSortIndicatorShown(False)
        list_layout.addWidget(self.history_table)

        list_card.setLayout(list_layout)
        layout.addWidget(list_card, 2)

        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_content = QWidget()
        self.detail_layout = QVBoxLayout()
        self.detail_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_layout.setSpacing(12)
        detail_content.setLayout(self.detail_layout)
        detail_scroll.setWidget(detail_content)

        self.build_history_player_card()
        self.build_history_main_org_card()
        self.build_history_affiliations_card()
        self.detail_layout.addStretch(1)

        layout.addWidget(detail_scroll, 3)
        self.setLayout(layout)

        self.refresh_button.clicked.connect(lambda: self.refresh_history())
        self.rerun_lookup_button.clicked.connect(self.rerun_selected_lookup)
        self.pin_selected_button.clicked.connect(self.toggle_selected_pin)
        self.favorite_selected_button.clicked.connect(self.toggle_selected_favorite)
        self.watch_player_button.clicked.connect(self.add_selected_player_to_watchlist)
        self.watch_org_button.clicked.connect(self.add_selected_org_to_watchlist)
        self.remove_selected_button.clicked.connect(self.remove_selected_history)
        self.clear_history_button.clicked.connect(self.clear_all_history)
        self.history_filter_input.textChanged.connect(self.schedule_history_filter_refresh)
        self.piracy_filter_box.currentTextChanged.connect(self.schedule_history_filter_refresh)
        self.clear_filters_button.clicked.connect(self.clear_history_filters)
        self.history_table.horizontalHeader().sectionClicked.connect(self.sort_history_by_column)
        self.history_table.cellClicked.connect(self.open_history_row)
        self.detail_open_profile_button.clicked.connect(
            lambda: self.open_url(self.current_profile_url, "No profile URL available.")
        )
        self.detail_open_orgs_button.clicked.connect(
            lambda: self.open_url(self.current_organizations_url, "No organizations URL available.")
        )
        self.detail_open_main_org_button.clicked.connect(
            lambda: self.open_url(self.current_main_org_url, "No main org URL available.")
        )

    def reset_detail_panel(self):
        self.current_profile_url = None
        self.current_organizations_url = None
        self.current_main_org_url = None

        self.detail_handle.setText("No history row selected")
        self.detail_display_name.setText("Click a lookup row to open a dossier here.")
        self.current_lookup_data = None
        self.set_fact_values(self.detail_player_facts, {
            "citizen_record": "N/A",
            "enlisted": "N/A",
            "location": "N/A",
            "fluency": "N/A",
        })

        self.detail_main_org_name.setText("No main organization loaded")
        self.detail_main_org_name.setStyleSheet("")
        self.detail_main_org_sid.setText("SID: N/A")
        self.set_fact_values(self.detail_org_facts, {
            "rank": "N/A",
            "member_count": "N/A",
            "type": "N/A",
            "commitment": "N/A",
            "exclusivity": "N/A",
        })
        self.detail_main_org_piracy.setText("Piracy: N/A")
        self.detail_main_org_piracy.setStyleSheet("color: #6a8894; font-weight: 700;")

        self.load_image_into_label(self.detail_avatar, None, "NO\nIMAGE")
        self.load_image_into_label(self.detail_main_org_logo, None, "ORG\nLOGO")
        self.clear_layout(self.detail_affiliations_grid)
        self.detail_affiliation_count_label.setText("0 linked orgs")
        self.detail_affiliations_empty.setText("No profile selected.")
        self.detail_affiliations_empty.setStyleSheet("")
        self.detail_affiliations_empty.show()
        self.set_detail_actions_enabled(False)

    def build_history_player_card(self):
        card = QFrame()
        card.setObjectName("playerCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self.detail_avatar = self.create_image_label("NO\nIMAGE", 112)
        layout.addWidget(self.detail_avatar)

        info_column = QVBoxLayout()
        self.detail_handle = QLabel("No history row selected")
        self.detail_handle.setObjectName("heroHandle")
        self.detail_handle.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.detail_display_name = QLabel("Click a lookup row to open a dossier here.")
        self.detail_display_name.setObjectName("heroSubtitle")
        self.detail_display_name.setTextInteractionFlags(Qt.TextSelectableByMouse)

        info_column.addWidget(self.detail_handle)
        info_column.addWidget(self.detail_display_name)

        facts_grid = QGridLayout()
        facts_grid.setHorizontalSpacing(18)
        facts_grid.setVerticalSpacing(7)
        fields = [
            ("citizen_record", "Citizen Record"),
            ("enlisted", "Enlisted"),
            ("location", "Location"),
            ("fluency", "Fluency"),
        ]
        for row, (key, label) in enumerate(fields):
            self.add_fact_pair(facts_grid, row, 0, label, self.detail_player_facts, key)

        info_column.addLayout(facts_grid)
        self.detail_change_summary_label = QLabel("Change summary: Select a row to compare fresh RSI data.")
        self.detail_change_summary_label.setObjectName("moduleSubtitle")
        self.detail_change_summary_label.setWordWrap(True)
        self.detail_change_summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_column.addWidget(self.detail_change_summary_label)
        layout.addLayout(info_column, 1)

        action_column = QVBoxLayout()
        self.detail_open_profile_button = QPushButton("Open Profile")
        self.detail_open_orgs_button = QPushButton("Open Organizations")
        self.detail_open_main_org_button = QPushButton("Open Main Org")
        action_column.addWidget(self.detail_open_profile_button)
        action_column.addWidget(self.detail_open_orgs_button)
        action_column.addWidget(self.detail_open_main_org_button)
        layout.addLayout(action_column)

        card.setLayout(layout)
        self.detail_layout.addWidget(card)

    def build_history_main_org_card(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        title = QLabel("MAIN ORGANIZATION")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        body = QHBoxLayout()
        body.setSpacing(14)
        self.detail_main_org_logo = self.create_image_label("ORG\nLOGO", 104)
        body.addWidget(self.detail_main_org_logo)

        details_column = QVBoxLayout()
        details_column.setSpacing(12)

        header = QHBoxLayout()
        org_identity = QVBoxLayout()
        self.detail_main_org_name = QLabel("No main organization loaded")
        self.detail_main_org_name.setObjectName("orgName")
        self.detail_main_org_sid = QLabel("SID: N/A")
        self.detail_main_org_sid.setObjectName("orgSid")
        org_identity.addWidget(self.detail_main_org_name)
        org_identity.addWidget(self.detail_main_org_sid)
        header.addLayout(org_identity, 1)

        self.detail_main_org_piracy = QLabel("Piracy: N/A")
        self.detail_main_org_piracy.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.detail_main_org_piracy)
        details_column.addLayout(header)

        facts_grid = QGridLayout()
        facts_grid.setHorizontalSpacing(18)
        facts_grid.setVerticalSpacing(7)
        fields = [
            ("rank", "Rank"),
            ("member_count", "Members"),
            ("type", "Type"),
            ("commitment", "Commitment"),
            ("exclusivity", "Exclusivity"),
        ]
        for index, (key, label) in enumerate(fields):
            row = index // 3
            col = (index % 3) * 2
            self.add_fact_pair(facts_grid, row, col, label, self.detail_org_facts, key)

        details_column.addLayout(facts_grid)
        body.addLayout(details_column, 1)
        layout.addLayout(body)

        card.setLayout(layout)
        self.detail_layout.addWidget(card)

    def build_history_affiliations_card(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("AFFILIATIONS")
        title.setObjectName("sectionTitle")
        self.detail_affiliation_count_label = QLabel("0 linked orgs")
        self.detail_affiliation_count_label.setObjectName("labelText")
        self.detail_affiliation_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(title)
        header.addWidget(self.detail_affiliation_count_label, 1)
        layout.addLayout(header)

        self.detail_affiliations_grid = QGridLayout()
        self.detail_affiliations_grid.setHorizontalSpacing(12)
        self.detail_affiliations_grid.setVerticalSpacing(12)
        layout.addLayout(self.detail_affiliations_grid)

        self.detail_affiliations_empty = QLabel("No profile selected.")
        self.detail_affiliations_empty.setObjectName("emptyState")
        self.detail_affiliations_empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.detail_affiliations_empty)

        card.setLayout(layout)
        self.detail_layout.addWidget(card)

    def refresh_history(self, selected_handle=None):
        if selected_handle is None:
            selected = self.selected_history_row()
            if selected:
                selected_handle = selected["handle"]

        self.history_rows = get_lookup_history()
        self.apply_history_filters(selected_handle=selected_handle)

    def apply_history_filters(self, selected_handle=None):
        if selected_handle is None:
            selected = self.selected_history_row()
            if selected:
                selected_handle = selected["handle"]

        query = self.history_filter_input.text().strip().lower()
        piracy_filter = self.piracy_filter_box.currentText()
        filtered_rows = [
            (row_index, row)
            for row_index, row in enumerate(self.history_rows)
            if self.history_row_matches_filter(row, query, piracy_filter)
        ]

        if self.history_sort_column is not None:
            reverse = self.history_sort_order == Qt.DescendingOrder
            filtered_rows.sort(
                key=lambda item: self.history_sort_key(item[1], self.history_sort_column),
                reverse=reverse,
            )

        self.history_table.setUpdatesEnabled(False)
        self.history_table.clearSelection()
        self.history_table.setRowCount(len(filtered_rows))

        for table_row, (row_index, row) in enumerate(filtered_rows):
            name = row.get("display_name") or row["handle"]
            org = row.get("main_org") or "N/A"
            has_piracy = self.history_row_has_piracy(row)
            piracy = "YES" if has_piracy else "NO"

            flags = self.history_flags_text(row)
            for col, value in enumerate((name, org, piracy, flags)):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, row_index)
                if col == 2:
                    item.setForeground(QColor("#ff8a65" if has_piracy else "#68e6a5"))
                self.history_table.setItem(table_row, col, item)

        self.history_table.setUpdatesEnabled(True)
        configure_readable_table_columns(self.history_table, min_width=95, max_width=260)
        self.history_count_label.setText(f"{len(filtered_rows)} / {len(self.history_rows)} shown")

        if self.history_sort_column is None:
            self.history_table.horizontalHeader().setSortIndicatorShown(False)
        else:
            self.history_table.horizontalHeader().setSortIndicatorShown(True)
            self.history_table.horizontalHeader().setSortIndicator(
                self.history_sort_column,
                self.history_sort_order,
            )

        if selected_handle:
            self.select_history_handle(selected_handle)

    def history_row_matches_filter(self, row, query, piracy_filter):
        has_piracy = self.history_row_has_piracy(row)
        if piracy_filter == "Piracy YES" and not has_piracy:
            return False
        if piracy_filter == "Piracy NO" and has_piracy:
            return False

        if not query:
            return True

        searchable = " ".join(
            str(row.get(field) or "")
            for field in ("handle", "display_name", "main_org", "org_sid")
        ).lower()
        return query in searchable

    def history_sort_key(self, row, column):
        if column == 0:
            return (row.get("display_name") or row["handle"]).lower()
        if column == 1:
            return (row.get("main_org") or "").lower()
        if column == 2:
            return 1 if self.history_row_has_piracy(row) else 0
        if column == 3:
            return self.history_flags_text(row)

        return ""

    def sort_history_by_column(self, column):
        if self.history_sort_column == column:
            self.history_sort_order = (
                Qt.DescendingOrder
                if self.history_sort_order == Qt.AscendingOrder
                else Qt.AscendingOrder
            )
        else:
            self.history_sort_column = column
            self.history_sort_order = Qt.DescendingOrder if column == 2 else Qt.AscendingOrder

        self.apply_history_filters()

    def clear_history_filters(self):
        self.history_filter_input.blockSignals(True)
        self.piracy_filter_box.blockSignals(True)
        self.history_filter_input.clear()
        self.piracy_filter_box.setCurrentIndex(0)
        self.history_filter_input.blockSignals(False)
        self.piracy_filter_box.blockSignals(False)
        self.apply_history_filters()

    def schedule_history_filter_refresh(self):
        self.history_filter_timer.start()

    def select_history_handle(self, handle):
        handle_key = handle.lower()
        for table_row in range(self.history_table.rowCount()):
            row = self.history_row_from_table_row(table_row)
            if row and row["handle"].lower() == handle_key:
                self.history_table.selectRow(table_row)
                return

    def history_row_has_piracy(self, row):
        if row.get("any_org_piracy") is not None:
            return bool(row.get("any_org_piracy"))

        return bool(row.get("org_piracy"))

    def history_row_from_table_row(self, table_row):
        if table_row < 0 or table_row >= self.history_table.rowCount():
            return None

        item = self.history_table.item(table_row, 0)
        if not item:
            return None

        row_index = item.data(Qt.UserRole)
        if row_index is None or row_index < 0 or row_index >= len(self.history_rows):
            return None

        return self.history_rows[row_index]

    def selected_history_row(self):
        selection = self.history_table.selectionModel()
        if not selection:
            return None

        selected_rows = selection.selectedRows()
        if not selected_rows:
            return None

        table_row = selected_rows[0].row()
        return self.history_row_from_table_row(table_row)

    def remove_selected_history(self):
        row = self.selected_history_row()
        if not row:
            QMessageBox.information(
                self,
                "No selection",
                "Select a history row to remove.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Remove history entry",
            f"Remove {row['handle']} from search history?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        delete_lookup_history(row["handle"])
        self.refresh_history()
        self.reset_detail_panel()

    def clear_all_history(self):
        if not self.history_rows:
            QMessageBox.information(
                self,
                "History empty",
                "Search history is already empty.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Clear search history",
            "Remove all search history entries? Notes and tags will be kept.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        clear_lookup_history()
        self.refresh_history()
        self.reset_detail_panel()

    def open_history_row(self, row_index, _column):
        row = self.history_row_from_table_row(row_index)
        if not row:
            return

        self.history_lookup_request_id += 1
        request_id = self.history_lookup_request_id
        self.history_lookup_running = True
        self.detail_handle.setText(row["handle"])
        self.detail_display_name.setText("Loading fresh profile intel...")
        self.clear_layout(self.detail_affiliations_grid)
        self.detail_affiliations_empty.setText("Loading affiliations...")
        self.detail_affiliations_empty.show()

        self.start_background_task(
            lambda: lookup_player(row["handle"]),
            lambda data, source_row=row, requested_id=request_id: self.on_history_lookup_finished(
                requested_id,
                source_row,
                data,
            ),
            lambda exc, source_row=row, requested_id=request_id: self.on_history_lookup_error(
                requested_id,
                source_row,
                exc,
            ),
            lambda requested_id=request_id: self.finish_history_lookup(requested_id),
        )

    def on_history_lookup_finished(self, request_id, row, data):
        if request_id != self.history_lookup_request_id:
            return

        previous_snapshot = player_snapshot_from_history(row)
        self.display_lookup_detail(data)
        self.update_detail_change_summary(previous_snapshot, data)
        self.update_stored_history_detail(data)

    def on_history_lookup_error(self, request_id, row, exc):
        if request_id != self.history_lookup_request_id:
            return

        self.display_stored_detail(row)
        record_event(
            "Errors",
            "RSI Lookup",
            row["handle"],
            "lookup_failed",
            str(exc),
            severity="Warning",
        )
        if isinstance(exc, RSILookupError):
            QMessageBox.warning(self, "Lookup failed", str(exc))
        else:
            QMessageBox.critical(self, "Error", str(exc))

    def finish_history_lookup(self, request_id=None):
        if request_id is not None and request_id != self.history_lookup_request_id:
            return

        self.history_lookup_running = False

    def display_lookup_detail(self, data):
        self.current_lookup_data = data
        self.current_profile_url = data["profile_url"]
        self.current_organizations_url = data["organizations_url"]
        self.current_main_org_url = data["org_url"]

        self.detail_handle.setText(data["handle"])
        self.detail_display_name.setText(data["display_name"])
        self.set_fact_values(self.detail_player_facts, {
            "citizen_record": data["citizen_record"],
            "enlisted": data["enlisted"],
            "location": data["location"],
            "fluency": data["fluency"],
        })
        main_org_redacted = bool(data.get("main_org_redacted"))
        if main_org_redacted:
            self.detail_main_org_name.setText("REDACTED")
            self.detail_main_org_name.setStyleSheet("color: #ffb86b; letter-spacing: 2px;")
            self.detail_main_org_sid.setText("Hidden organization affiliation")
        else:
            self.detail_main_org_name.setText(data["main_org"])
            self.detail_main_org_name.setStyleSheet("")
            self.detail_main_org_sid.setText(f"SID: {data['org_sid']}")

        self.set_fact_values(self.detail_org_facts, {
            "rank": data["org_rank"],
            "member_count": data["org_member_count"],
            "type": data["org_type"],
            "commitment": data["org_commitment"],
            "exclusivity": data["org_exclusivity"],
        })
        if main_org_redacted:
            self.set_piracy_unknown(self.detail_main_org_piracy)
        else:
            self.set_piracy_badge(self.detail_main_org_piracy, data["org_piracy"])
        self.load_image_into_label(self.detail_avatar, data.get("avatar"), "NO\nIMAGE")
        self.load_image_into_label(
            self.detail_main_org_logo,
            data.get("org_logo"),
            "ORG\nLOGO",
        )
        self.render_detail_affiliations(data["affiliations"], data.get("affiliations_redacted", False))
        self.set_detail_actions_enabled(True)

    def update_stored_history_detail(self, data):
        save_lookup(
            data["handle"],
            data["display_name"],
            data["main_org"],
            data["profile_url"],
            org_sid=data["org_sid"],
            org_piracy=data["org_piracy"],
            any_org_piracy=data["any_org_piracy"],
            refresh_timestamp=False,
        )
        self.refresh_history(selected_handle=data["handle"])

    def display_stored_detail(self, row):
        self.current_lookup_data = None
        self.current_profile_url = row.get("profile_url")
        self.current_organizations_url = None
        self.current_main_org_url = None

        self.detail_handle.setText(row["handle"])
        self.detail_display_name.setText(row.get("display_name") or row["handle"])
        self.detail_change_summary_label.setText("Change summary: Fresh lookup failed; stored history only.")
        self.set_fact_values(self.detail_player_facts, {
            "citizen_record": "N/A",
            "enlisted": "N/A",
            "location": "N/A",
            "fluency": "N/A",
        })
        stored_main_org = row.get("main_org") or "N/A"
        if stored_main_org.upper() == "REDACTED":
            self.detail_main_org_name.setText("REDACTED")
            self.detail_main_org_name.setStyleSheet("color: #ffb86b; letter-spacing: 2px;")
            self.detail_main_org_sid.setText("Hidden organization affiliation")
        else:
            self.detail_main_org_name.setText(stored_main_org)
            self.detail_main_org_name.setStyleSheet("")
            self.detail_main_org_sid.setText(f"SID: {row.get('org_sid') or 'N/A'}")
        self.set_fact_values(self.detail_org_facts, {
            "rank": "N/A",
            "member_count": "N/A",
            "type": "N/A",
            "commitment": "N/A",
            "exclusivity": "N/A",
        })
        self.set_piracy_badge(self.detail_main_org_piracy, bool(row.get("org_piracy")))
        self.clear_layout(self.detail_affiliations_grid)
        self.detail_affiliation_count_label.setText("0 linked orgs")
        self.detail_affiliations_empty.setText("Live lookup failed; showing stored history only.")
        self.detail_affiliations_empty.setStyleSheet("")
        self.detail_affiliations_empty.show()
        self.load_image_into_label(self.detail_avatar, None, "NO\nIMAGE")
        self.load_image_into_label(self.detail_main_org_logo, None, "ORG\nLOGO")
        self.set_detail_actions_enabled(True)

    def add_fact_pair(self, layout, row, col, label, registry, key):
        label_widget = QLabel(label.upper())
        label_widget.setObjectName("labelText")
        value_widget = QLabel("N/A")
        value_widget.setObjectName("valueText")
        value_widget.setWordWrap(True)
        value_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
        registry[key] = value_widget

        layout.addWidget(label_widget, row, col)
        layout.addWidget(value_widget, row, col + 1)

    def set_fact_values(self, registry, values):
        for key, value in values.items():
            registry[key].setText(str(value or "N/A"))

    def render_detail_affiliations(self, affiliations, redacted=False):
        self.clear_layout(self.detail_affiliations_grid)

        if not affiliations:
            if redacted:
                self.detail_affiliation_count_label.setText("REDACTED")
                self.detail_affiliations_empty.setText(
                    "REDACTED\n"
                    "Hidden organization affiliation\n"
                    "Organization affiliations are REDACTED by RSI.\n"
                    "Piracy: Unknown"
                )
                self.detail_affiliations_empty.setStyleSheet("color: #ffb86b; font-weight: 700;")
            else:
                self.detail_affiliation_count_label.setText("0 linked orgs")
                self.detail_affiliations_empty.setText("No affiliations loaded.")
                self.detail_affiliations_empty.setStyleSheet("")
            self.detail_affiliations_empty.show()
            return

        self.detail_affiliations_empty.setStyleSheet("")
        self.detail_affiliations_empty.hide()
        self.detail_affiliation_count_label.setText(f"{len(affiliations)} linked orgs")

        for index, org in enumerate(affiliations):
            row = index // 2
            col = index % 2
            self.detail_affiliations_grid.addWidget(
                self.create_detail_affiliation_card(org),
                row,
                col,
            )

    def create_detail_affiliation_card(self, org):
        card = QFrame()
        card.setObjectName("affiliationCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        logo = self.create_image_label("ORG\nLOGO", 72)
        self.load_image_into_label(logo, org.get("logo_url"), "ORG\nLOGO")
        layout.addWidget(logo)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        name = QLabel(org["name"])
        name.setObjectName("orgName")
        name.setWordWrap(True)
        sid = QLabel(f"SID: {org['sid']}")
        sid.setObjectName("orgSid")
        details = QLabel(
            f"Rank: {org['rank']}  |  Members: {org['member_count']}  |  "
            f"{org['type']} / {org['commitment']} / {org['exclusivity']}"
        )
        details.setObjectName("valueText")
        details.setWordWrap(True)
        piracy = QLabel()
        self.set_piracy_badge(piracy, org["piracy"])

        text_layout.addWidget(name)
        text_layout.addWidget(sid)
        text_layout.addWidget(details)
        text_layout.addWidget(piracy)
        layout.addLayout(text_layout, 1)
        card.setLayout(layout)
        return card

    def create_image_label(self, placeholder, size):
        label = QLabel(placeholder)
        label.setObjectName("avatarBox")
        label.setFixedSize(size, size)
        label.setAlignment(Qt.AlignCenter)
        return label

    def load_image_into_label(self, label, image_url, placeholder):
        label.setPixmap(QPixmap())
        label.setText(placeholder)
        label.setProperty("image_url", image_url or "")

        if not image_url:
            return

        def fetch_image():
            response = requests.get(image_url, headers=IMAGE_HEADERS, timeout=10)
            response.raise_for_status()
            return response.content

        self.start_background_task(
            fetch_image,
            lambda content, target=label, url=image_url: self.apply_loaded_image(target, url, content),
            None,
        )

    def apply_loaded_image(self, label, image_url, content):
        if label.property("image_url") != image_url:
            return

        pixmap = QPixmap()
        if not pixmap.loadFromData(content):
            return

        scaled = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setText("")
        label.setPixmap(scaled)

    def set_piracy_badge(self, label, has_piracy):
        if has_piracy:
            label.setText("Piracy: YES")
            label.setStyleSheet("color: #ff8a65; font-weight: 700;")
        else:
            label.setText("Piracy: No")
            label.setStyleSheet("color: #68e6a5; font-weight: 700;")

    def set_piracy_unknown(self, label):
        label.setText("Piracy: Unknown")
        label.setStyleSheet("color: #ffb86b; font-weight: 700;")

    def set_detail_actions_enabled(self, enabled):
        self.detail_open_profile_button.setEnabled(enabled and bool(self.current_profile_url))
        self.detail_open_orgs_button.setEnabled(enabled and bool(self.current_organizations_url))
        self.detail_open_main_org_button.setEnabled(enabled and bool(self.current_main_org_url))

    def history_flags_text(self, row):
        flags = []
        if row.get("is_pinned"):
            flags.append("Pinned")
        if row.get("is_favorite"):
            flags.append("Favorite")
        return ", ".join(flags) if flags else ""

    def rerun_selected_lookup(self):
        row = self.selected_history_row()
        if not row:
            QMessageBox.information(self, "No selection", "Select a history row first.")
            return
        table_row = self.history_table.currentRow()
        if hasattr(lookup_player, "cache_clear"):
            lookup_player.cache_clear()
        self.open_history_row(table_row, 0)

    def toggle_selected_pin(self):
        self.toggle_history_flag("is_pinned", "Pinned")

    def toggle_selected_favorite(self):
        self.toggle_history_flag("is_favorite", "Favorite")

    def toggle_history_flag(self, flag, label):
        row = self.selected_history_row()
        if not row:
            QMessageBox.information(self, "No selection", "Select a history row first.")
            return
        new_value = not bool(row.get(flag))
        set_lookup_history_flag(row["handle"], flag, new_value)
        self.refresh_history(selected_handle=row["handle"])
        self.detail_display_name.setText(f"{label} {'enabled' if new_value else 'disabled'} for {row['handle']}.")

    def add_selected_player_to_watchlist(self):
        row = self.selected_history_row()
        if not row:
            QMessageBox.information(self, "No selection", "Select a history row first.")
            return

        if self.current_lookup_data and self.current_lookup_data.get("handle", "").lower() == row["handle"].lower():
            entry = add_player_watch(self.current_lookup_data)
        else:
            entry = add_player_snapshot_watch(player_snapshot_from_history(row))

        QMessageBox.information(self, "Watchlist", f"Player added to Watchlists: {entry.name}")

    def add_selected_org_to_watchlist(self):
        row = self.selected_history_row()
        if not row:
            QMessageBox.information(self, "No selection", "Select a history row first.")
            return

        if self.current_lookup_data and self.current_lookup_data.get("handle", "").lower() == row["handle"].lower():
            org = main_org_snapshot_from_lookup(self.current_lookup_data)
        else:
            org = {
                "relationship": "Main organization",
                "name": row.get("main_org") or "",
                "sid": row.get("org_sid") or "",
                "piracy": "YES" if row.get("org_piracy") else "NO",
                "redacted": (row.get("main_org") or "").upper() == "REDACTED",
            }

        if org.get("redacted") or not org.get("sid") or org.get("sid") == "N/A":
            QMessageBox.warning(
                self,
                "Organization unavailable",
                "This organization is hidden or has no SID available.",
            )
            return

        entry = add_org_watch(org, "RSI")
        QMessageBox.information(self, "Watchlist", f"Organization added to Watchlists: {entry.name}")

    def update_detail_change_summary(self, previous_snapshot, data):
        current_snapshot = player_snapshot_from_lookup(data)
        summary = player_change_summary(previous_snapshot, current_snapshot)
        self.detail_change_summary_label.setText(f"Change summary: {summary}")
        for event_type, severity, message in player_change_events(previous_snapshot, current_snapshot):
            record_event(
                "Player",
                "Search History",
                data["handle"],
                event_type,
                message,
                metadata={
                    "profile_url": data.get("profile_url"),
                    "organizations_url": data.get("organizations_url"),
                },
                severity=severity,
            )

    def open_url(self, url, message):
        if not url:
            QMessageBox.warning(self, "No link", message)
            return

        QDesktopServices.openUrl(QUrl(url))

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
