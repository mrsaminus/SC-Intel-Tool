import requests
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication,
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database import (
    get_lookup_history,
    get_note,
    save_lookup,
    save_note,
)
from app.event_center.service import record_event
from app.player_intel import (
    player_change_events,
    player_change_summary,
    player_snapshot_from_history,
    player_snapshot_from_lookup,
)
from app.rsi_lookup import RSILookupError, lookup_player
from app.watchlists.service import add_main_org_watch_from_lookup, add_player_watch

from .constants import (
    IMAGE_HEADERS,
    TAG_COLORS,
)
from .workers import BackgroundTaskMixin


class PlayerLookupTab(BackgroundTaskMixin, QWidget):
    def __init__(self, on_lookup_saved=None):
        super().__init__()

        self.on_lookup_saved = on_lookup_saved
        self.lookup_running = False
        self.current_handle = None
        self.current_profile_url = None
        self.current_organizations_url = None
        self.current_main_org_url = None
        self.current_lookup_data = None

        self.player_facts = {}
        self.main_org_facts = {}

        self.build_ui()
        self.connect_signals()
        self.set_actions_enabled(False)
        self.update_tag_badge(self.tag_box.currentText())

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        search_row = QHBoxLayout()
        self.handle_input = QLineEdit()
        self.handle_input.setPlaceholderText("Enter RSI handle...")
        self.search_button = QPushButton("Lookup")
        self.copy_handle_button = QPushButton("Copy Handle")
        self.copy_handle_button.setEnabled(False)

        search_row.addWidget(self.handle_input, 1)
        search_row.addWidget(self.search_button)
        search_row.addWidget(self.copy_handle_button)
        layout.addLayout(search_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        scroll_content.setLayout(self.content_layout)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        self.build_player_card()
        self.build_main_org_card()
        self.build_affiliations_section()
        self.build_notes_section()

        self.setLayout(layout)

    def build_player_card(self):
        card = QFrame()
        card.setObjectName("playerCard")
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self.avatar_label = QLabel("NO\nIMAGE")
        self.avatar_label.setObjectName("avatarBox")
        self.avatar_label.setFixedSize(146, 146)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.avatar_label)

        info_column = QVBoxLayout()
        self.handle_title = QLabel("No Player Loaded")
        self.handle_title.setObjectName("heroHandle")
        self.handle_title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.display_subtitle = QLabel("Search an RSI handle to load citizen intel.")
        self.display_subtitle.setObjectName("heroSubtitle")
        self.display_subtitle.setTextInteractionFlags(Qt.TextSelectableByMouse)

        info_column.addWidget(self.handle_title)
        info_column.addWidget(self.display_subtitle)

        facts_grid = QGridLayout()
        facts_grid.setHorizontalSpacing(18)
        facts_grid.setVerticalSpacing(6)
        fields = [
            ("citizen_record", "Citizen Record"),
            ("enlisted", "Enlisted"),
            ("location", "Location"),
            ("fluency", "Fluency"),
        ]
        for row, (key, label) in enumerate(fields):
            self.add_fact_row(facts_grid, row, label, self.player_facts, key)

        info_column.addLayout(facts_grid)
        self.change_summary_label = QLabel("Change summary: No player loaded.")
        self.change_summary_label.setObjectName("moduleSubtitle")
        self.change_summary_label.setWordWrap(True)
        self.change_summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_column.addWidget(self.change_summary_label)
        info_column.addStretch(1)
        layout.addLayout(info_column, 2)

        action_column = QVBoxLayout()
        action_column.setSpacing(8)

        self.tag_badge = QLabel("Unmarked")
        self.tag_badge.setAlignment(Qt.AlignCenter)
        action_column.addWidget(self.tag_badge)

        tag_label = QLabel("Local Tag")
        tag_label.setObjectName("labelText")
        self.tag_box = QComboBox()
        self.tag_box.addItems([
            "Unmarked",
            "Friendly",
            "Neutral",
            "Hostile",
            "Pirate",
            "Scammer",
        ])

        self.open_profile_button = QPushButton("Open Profile")
        self.open_orgs_button = QPushButton("Open Organizations")
        self.open_main_org_button = QPushButton("Open Main Org")
        self.recheck_button = QPushButton("Re-check")
        self.add_player_watch_button = QPushButton("Add Player to Watchlist")
        self.add_main_org_watch_button = QPushButton("Add Main Org to Watchlist")

        action_column.addWidget(tag_label)
        action_column.addWidget(self.tag_box)
        action_column.addSpacing(8)
        action_column.addWidget(self.recheck_button)
        action_column.addWidget(self.open_profile_button)
        action_column.addWidget(self.open_orgs_button)
        action_column.addWidget(self.open_main_org_button)
        action_column.addWidget(self.add_player_watch_button)
        action_column.addWidget(self.add_main_org_watch_button)
        action_column.addStretch(1)

        layout.addLayout(action_column, 1)
        card.setLayout(layout)
        self.content_layout.addWidget(card)

    def build_main_org_card(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        title = QLabel("MAIN ORGANIZATION")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        body = QHBoxLayout()
        body.setSpacing(14)
        self.main_org_logo_label = self.create_image_label("ORG\nLOGO", 112)
        body.addWidget(self.main_org_logo_label)

        details_column = QVBoxLayout()
        details_column.setSpacing(12)

        header = QHBoxLayout()
        org_identity = QVBoxLayout()
        self.main_org_name = QLabel("No main organization loaded")
        self.main_org_name.setObjectName("orgName")
        self.main_org_sid = QLabel("SID: N/A")
        self.main_org_sid.setObjectName("orgSid")
        org_identity.addWidget(self.main_org_name)
        org_identity.addWidget(self.main_org_sid)
        header.addLayout(org_identity, 1)

        self.main_org_piracy = QLabel("Piracy: N/A")
        self.main_org_piracy.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.main_org_piracy)
        details_column.addLayout(header)

        facts_grid = QGridLayout()
        facts_grid.setHorizontalSpacing(24)
        facts_grid.setVerticalSpacing(8)
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
            self.add_fact_pair(facts_grid, row, col, label, self.main_org_facts, key)

        details_column.addLayout(facts_grid)
        body.addLayout(details_column, 1)
        layout.addLayout(body)
        card.setLayout(layout)
        self.content_layout.addWidget(card)

    def build_affiliations_section(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("AFFILIATIONS")
        title.setObjectName("sectionTitle")
        self.affiliation_count_label = QLabel("0 linked orgs")
        self.affiliation_count_label.setObjectName("labelText")
        self.affiliation_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(title)
        header.addWidget(self.affiliation_count_label, 1)
        layout.addLayout(header)

        self.affiliations_grid = QGridLayout()
        self.affiliations_grid.setHorizontalSpacing(12)
        self.affiliations_grid.setVerticalSpacing(12)
        layout.addLayout(self.affiliations_grid)

        self.affiliations_empty = QLabel("No affiliations loaded.")
        self.affiliations_empty.setObjectName("emptyState")
        self.affiliations_empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.affiliations_empty)

        card.setLayout(layout)
        self.content_layout.addWidget(card)

    def build_notes_section(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        title = QLabel("LOCAL INTEL NOTES")
        title.setObjectName("sectionTitle")
        self.notes_box = QTextEdit()
        self.notes_box.setPlaceholderText("Local notes about this player...")
        self.notes_box.setMinimumHeight(130)
        self.save_note_button = QPushButton("Save Note")

        layout.addWidget(title)
        layout.addWidget(self.notes_box)
        layout.addWidget(self.save_note_button)
        card.setLayout(layout)
        self.content_layout.addWidget(card)

    def connect_signals(self):
        self.search_button.clicked.connect(self.search_player)
        self.handle_input.returnPressed.connect(self.search_player)
        self.save_note_button.clicked.connect(self.save_current_note)
        self.copy_handle_button.clicked.connect(self.copy_current_handle)
        self.open_profile_button.clicked.connect(self.open_current_profile)
        self.open_orgs_button.clicked.connect(self.open_current_organizations)
        self.open_main_org_button.clicked.connect(self.open_current_main_org)
        self.recheck_button.clicked.connect(self.recheck_current_player)
        self.add_player_watch_button.clicked.connect(self.add_current_player_to_watchlist)
        self.add_main_org_watch_button.clicked.connect(self.add_current_main_org_to_watchlist)
        self.tag_box.currentTextChanged.connect(self.update_tag_badge)

    def add_fact_row(self, layout, row, label, registry, key):
        self.add_fact_pair(layout, row, 0, label, registry, key)

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

    def search_player(self):
        if self.lookup_running:
            return

        handle = self.handle_input.text().strip()
        if not handle:
            return

        self.lookup_running = True
        self.search_button.setEnabled(False)
        self.search_button.setText("Looking up...")

        self.start_background_task(
            lambda: lookup_player(handle),
            self.on_player_lookup_finished,
            self.on_player_lookup_error,
            self.finish_player_lookup,
        )

    def on_player_lookup_finished(self, data):
        previous_snapshot = self.previous_lookup_snapshot(data["handle"])
        self.display_player(data)
        self.load_saved_note(data["handle"])
        self.update_lookup_change_summary(previous_snapshot, data)

        save_lookup(
            data["handle"],
            data["display_name"],
            data["main_org"],
            data["profile_url"],
            org_sid=data["org_sid"],
            org_piracy=data["org_piracy"],
            any_org_piracy=data["any_org_piracy"],
        )
        if self.on_lookup_saved:
            self.on_lookup_saved()

    def on_player_lookup_error(self, exc):
        self.set_actions_enabled(False)
        handle = self.handle_input.text().strip()
        if handle:
            record_event(
                "Errors",
                "RSI Lookup",
                handle,
                "lookup_failed",
                str(exc),
                severity="Warning",
            )
        if isinstance(exc, RSILookupError):
            QMessageBox.warning(self, "Lookup failed", str(exc))
        else:
            QMessageBox.critical(self, "Error", str(exc))

    def finish_player_lookup(self):
        self.lookup_running = False
        self.search_button.setEnabled(True)
        self.search_button.setText("Lookup")

    def display_player(self, data):
        self.current_lookup_data = data
        self.current_handle = data["handle"]
        self.current_profile_url = data["profile_url"]
        self.current_organizations_url = data["organizations_url"]
        self.current_main_org_url = data["org_url"]

        self.handle_title.setText(data["handle"])
        self.display_subtitle.setText(data["display_name"])
        self.set_fact_values(self.player_facts, {
            "citizen_record": data["citizen_record"],
            "enlisted": data["enlisted"],
            "location": data["location"],
            "fluency": data["fluency"],
        })

        main_org_redacted = bool(data.get("main_org_redacted"))
        if main_org_redacted:
            self.main_org_name.setText("REDACTED")
            self.main_org_name.setStyleSheet("color: #ffb86b; letter-spacing: 2px;")
            self.main_org_sid.setText("Hidden organization affiliation")
        else:
            self.main_org_name.setText(data["main_org"])
            self.main_org_name.setStyleSheet("")
            self.main_org_sid.setText(f"SID: {data['org_sid']}")

        self.set_fact_values(self.main_org_facts, {
            "rank": data["org_rank"],
            "member_count": data["org_member_count"],
            "type": data["org_type"],
            "commitment": data["org_commitment"],
            "exclusivity": data["org_exclusivity"],
        })
        if main_org_redacted:
            self.set_piracy_unknown(self.main_org_piracy)
        else:
            self.set_piracy_badge(self.main_org_piracy, data["org_piracy"])

        self.load_avatar(data["avatar"])
        self.load_image_into_label(
            self.main_org_logo_label,
            data.get("org_logo"),
            "ORG\nLOGO",
        )
        self.render_affiliations(data["affiliations"], data.get("affiliations_redacted", False))
        self.set_actions_enabled(True)

    def set_fact_values(self, registry, values):
        for key, value in values.items():
            registry[key].setText(str(value or "N/A"))

    def render_affiliations(self, affiliations, redacted=False):
        self.clear_layout(self.affiliations_grid)

        if not affiliations:
            if redacted:
                self.affiliation_count_label.setText("REDACTED")
                self.affiliations_empty.setText(
                    "REDACTED\n"
                    "Hidden organization affiliation\n"
                    "Organization affiliations are REDACTED by RSI.\n"
                    "Piracy: Unknown"
                )
                self.affiliations_empty.setStyleSheet("color: #ffb86b; font-weight: 700;")
            else:
                self.affiliation_count_label.setText("0 linked orgs")
                self.affiliations_empty.setText("No affiliations loaded.")
                self.affiliations_empty.setStyleSheet("")
            self.affiliations_empty.show()
            return

        self.affiliations_empty.setStyleSheet("")
        self.affiliations_empty.hide()
        self.affiliation_count_label.setText(f"{len(affiliations)} linked orgs")

        for index, org in enumerate(affiliations):
            row = index // 2
            col = index % 2
            self.affiliations_grid.addWidget(self.create_affiliation_card(org), row, col)

    def create_affiliation_card(self, org):
        card = QFrame()
        card.setObjectName("affiliationCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        logo = self.create_image_label("ORG\nLOGO", 78)
        self.load_image_into_label(logo, org.get("logo_url"), "ORG\nLOGO")
        layout.addWidget(logo)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)

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

    def load_saved_note(self, handle):
        saved_note = get_note(handle)
        if saved_note:
            tag, notes = saved_note
            self.tag_box.setCurrentText(tag if tag in TAG_COLORS else "Unmarked")
            self.notes_box.setPlainText(notes or "")
        else:
            self.tag_box.setCurrentText("Unmarked")
            self.notes_box.clear()

    def load_avatar(self, avatar_url):
        self.load_image_into_label(self.avatar_label, avatar_url, "NO\nIMAGE")

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

        scaled = pixmap.scaled(
            label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        label.setText("")
        label.setPixmap(scaled)

    def update_tag_badge(self, tag):
        foreground, background = TAG_COLORS.get(tag, TAG_COLORS["Unmarked"])
        self.tag_badge.setText(tag.upper())
        self.tag_badge.setStyleSheet(
            f"""
            QLabel {{
                color: {foreground};
                background: {background};
                border: 1px solid {foreground};
                border-radius: 4px;
                padding: 7px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            """
        )

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

    def set_actions_enabled(self, enabled):
        self.copy_handle_button.setEnabled(enabled)
        self.recheck_button.setEnabled(enabled)
        self.open_profile_button.setEnabled(enabled)
        self.open_orgs_button.setEnabled(enabled)
        self.open_main_org_button.setEnabled(enabled and bool(self.current_main_org_url))
        self.add_player_watch_button.setEnabled(enabled)
        self.add_main_org_watch_button.setEnabled(
            enabled
            and bool(self.current_lookup_data)
            and not bool(self.current_lookup_data.get("main_org_redacted"))
            and bool(self.current_lookup_data.get("org_sid"))
            and self.current_lookup_data.get("org_sid") != "N/A"
        )

    def open_current_profile(self):
        self.open_url(self.current_profile_url, "No profile", "Lookup a player first.")

    def open_current_organizations(self):
        self.open_url(
            self.current_organizations_url,
            "No organizations",
            "Lookup a player first.",
        )

    def open_current_main_org(self):
        self.open_url(
            self.current_main_org_url,
            "No main org",
            "No main organization URL is available for this player.",
        )

    def open_url(self, url, title, message):
        if not url:
            QMessageBox.warning(self, title, message)
            return

        QDesktopServices.openUrl(QUrl(url))

    def copy_current_handle(self):
        if not self.current_handle:
            QMessageBox.warning(self, "No player", "Lookup a player first.")
            return

        QApplication.clipboard().setText(self.current_handle)

    def recheck_current_player(self):
        if not self.current_handle:
            QMessageBox.warning(self, "No player", "Lookup a player first.")
            return
        if hasattr(lookup_player, "cache_clear"):
            lookup_player.cache_clear()
        self.handle_input.setText(self.current_handle)
        self.search_player()

    def add_current_player_to_watchlist(self):
        if not self.current_lookup_data:
            QMessageBox.warning(self, "No player", "Lookup a player first.")
            return
        add_player_watch(
            self.current_lookup_data,
            tag=self.tag_box.currentText(),
            notes=self.notes_box.toPlainText(),
        )
        QMessageBox.information(self, "Watchlist", f"Player added to Watchlists: {self.current_handle}")

    def add_current_main_org_to_watchlist(self):
        if not self.current_lookup_data:
            QMessageBox.warning(self, "No player", "Lookup a player first.")
            return
        try:
            entry = add_main_org_watch_from_lookup(self.current_lookup_data)
        except ValueError as exc:
            QMessageBox.warning(self, "Organization unavailable", str(exc))
            return
        QMessageBox.information(self, "Watchlist", f"Organization added to Watchlists: {entry.name}")

    def previous_lookup_snapshot(self, handle):
        handle_key = handle.strip().lower()
        for row in get_lookup_history(limit=500):
            if row["handle"].strip().lower() == handle_key:
                return player_snapshot_from_history(row)
        return None

    def update_lookup_change_summary(self, previous_snapshot, data):
        current_snapshot = player_snapshot_from_lookup(data)
        summary = player_change_summary(previous_snapshot, current_snapshot)
        self.change_summary_label.setText(f"Change summary: {summary}")
        for event_type, severity, message in player_change_events(previous_snapshot, current_snapshot):
            record_event(
                "Player",
                "RSI Lookup",
                data["handle"],
                event_type,
                message,
                metadata={
                    "profile_url": data.get("profile_url"),
                    "organizations_url": data.get("organizations_url"),
                },
                severity=severity,
            )

    def save_current_note(self):
        if not self.current_handle:
            QMessageBox.warning(self, "No player", "Lookup a player first.")
            return

        save_note(
            self.current_handle,
            self.tag_box.currentText(),
            self.notes_box.toPlainText(),
        )

        QMessageBox.information(self, "Saved", "Note saved.")

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
