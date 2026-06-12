from app.paths import is_packaged_app
from app.update_checker import is_newer_version
from app.version import APP_VERSION

from .community_branding import AppLogoLabel, CommunityLogoLabel

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .home_widgets import CountdownTimerWidget, NavigationCard


class HomeTab(QWidget):
    CAPABILITY_CARDS = [
        (
            "Player Intel",
            "RSI lookup, organizations, affiliations, local tags and notes.",
            "Player Lookup",
            "Intel",
        ),
        (
            "Mining / Salvage",
            "Ore finder, refinery tools, scan IDs and salvage resources.",
            "Mining / Salvage",
            "Industrial",
        ),
        (
            "Item Finder",
            "Gear, ships, buy/rental locations and live source lookup.",
            "Item Finder",
            "Lookup",
        ),
        (
            "Wikelo Tracking",
            "Missions, required materials and reward checklist progress.",
            "Wikelo Items",
            "Progress",
        ),
        (
            "Trading",
            "Market planning and future commodity workflow.",
            "Trading",
            "Market",
        ),
        (
            "Local Tools",
            "Notes, history, settings and AppData persistence.",
            "Notes",
            "Local",
        ),
    ]

    def __init__(self, navigate_callback=None):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.countdown_timers = []
        self.timer_panel_layout = None
        self.update_status_chip = None
        self.update_status_dot = None
        self.update_status_text = None

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        page = QWidget()
        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(12, 12, 12, 12)
        page_layout.setSpacing(10)

        page_layout.addWidget(self.create_hero_panel())
        page_layout.addWidget(self.build_status_strip())

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        main_layout.addWidget(self.build_left_panel(), 3, Qt.AlignTop)
        main_layout.addWidget(self.build_timer_panel(), 1, Qt.AlignTop)

        page_layout.addLayout(main_layout)
        page_layout.addWidget(self.build_community_footer())
        page.setLayout(page_layout)
        scroll_area.setWidget(page)
        layout.addWidget(scroll_area)

        self.setLayout(layout)
        self.update_first_timer_aliases()

    def create_nav_card(self, title, description, target=None, eyebrow=None):
        return NavigationCard(title, description, self.open_target_tab, target=target, eyebrow=eyebrow)

    def build_left_panel(self):
        panel = QWidget()
        panel.setMinimumWidth(640)
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        layout.addWidget(self.build_navigation_panel())
        layout.addWidget(self.build_trust_line())
        layout.addWidget(self.build_feedback_note())
        panel.setLayout(layout)
        return panel

    def build_navigation_panel(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 9, 12, 11)
        layout.setSpacing(7)

        title_label = QLabel("CAPABILITY OVERVIEW")
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(7)
        grid.setVerticalSpacing(7)
        for column in range(2):
            grid.setColumnStretch(column, 1)

        for index, (title, description, target, eyebrow) in enumerate(self.CAPABILITY_CARDS):
            grid.addWidget(
                self.create_nav_card(title, description, target=target, eyebrow=eyebrow),
                index // 2,
                index % 2,
            )

        layout.addLayout(grid)
        card.setLayout(layout)
        return card

    def build_timer_panel(self):
        card = self.create_filter_card("COUNTDOWN TIMERS")
        card.setMinimumWidth(286)
        card.setMaximumWidth(354)
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        layout = card.layout()
        layout.setSpacing(8)
        self.timer_panel_layout = layout

        self.add_countdown_timer(removable=False)
        self.add_timer_button = QPushButton("Add Timer")
        self.add_timer_button.clicked.connect(lambda: self.add_countdown_timer(removable=True))
        layout.addWidget(self.add_timer_button)
        return card

    def build_status_strip(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = card.layout()
        if layout is None:
            layout = QHBoxLayout()
            layout.setContentsMargins(12, 6, 12, 6)
            layout.setSpacing(8)

        build_type = "Packaged build" if is_packaged_app() else "Source/dev run"
        title = QLabel("OPERATIONAL STATUS")
        title.setObjectName("sectionTitle")
        info_panel = QWidget()
        info_panel.setObjectName("statusInfoPanel")
        info_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        runtime_status = QLabel(f"Version: {APP_VERSION} | Runtime: {build_type}")
        runtime_status.setObjectName("moduleSubtitle")
        runtime_status.setWordWrap(True)
        data_status = QLabel("Data: AppData/local | Updates: GitHub Releases")
        data_status.setObjectName("moduleSubtitle")
        data_status.setWordWrap(True)

        info_layout.addWidget(runtime_status)
        info_layout.addWidget(data_status)
        info_panel.setLayout(info_layout)

        layout.addWidget(title)
        layout.addWidget(info_panel, 1)
        layout.addWidget(self.create_update_status_chip(), 0, Qt.AlignVCenter)
        card.setLayout(layout)

        return card

    def create_update_status_chip(self):
        chip = QFrame()
        chip.setObjectName("updateStatusChip")
        chip.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        chip.setMaximumHeight(22)
        chip_layout = QHBoxLayout()
        chip_layout.setContentsMargins(6, 2, 7, 2)
        chip_layout.setSpacing(5)

        self.update_status_dot = QFrame()
        self.update_status_dot.setFixedSize(7, 7)
        self.update_status_text = QLabel()
        self.update_status_text.setObjectName("updateStatusText")

        chip_layout.addWidget(self.update_status_dot)
        chip_layout.addWidget(self.update_status_text)
        chip.setLayout(chip_layout)
        self.update_status_chip = chip
        self.set_update_status("Not checked", "neutral")
        return chip

    def set_update_status(self, text, state="neutral"):
        if not self.update_status_chip or not self.update_status_dot or not self.update_status_text:
            return

        colors = {
            "neutral": ("#83a9b8", "#18333d", "#081820"),
            "checking": ("#55d6e8", "#18333d", "#081820"),
            "current": ("#70dfaa", "#1b4e43", "#0a1d19"),
            "available": ("#ffb56a", "#5d3c20", "#1b130c"),
            "error": ("#e48168", "#4a2d23", "#1a1110"),
        }
        color, border, background = colors.get(state, colors["neutral"])
        self.update_status_chip.setStyleSheet(f"""
            QFrame#updateStatusChip {{
                background: {background};
                border: 1px solid {border};
                border-radius: 9px;
            }}
        """)
        self.update_status_dot.setStyleSheet(f"""
            QFrame {{
                background: {color};
                border: none;
                border-radius: 3px;
            }}
        """)
        self.update_status_text.setText(text)
        self.update_status_text.setStyleSheet(f"""
            QLabel#updateStatusText {{
                background: transparent;
                border: none;
                color: {color};
                font-size: 8pt;
                font-weight: 700;
                padding: 0;
            }}
        """)

    def set_update_checking(self):
        self.set_update_status("Checking...", "checking")

    def apply_update_check_result(self, result):
        update_available = result.update_available or is_newer_version(
            result.latest_version,
            result.current_version,
        )
        if update_available:
            self.set_update_status(f"Update available {chr(8226)} {result.latest_version}", "available")
        else:
            self.set_update_status("Up to date", "current")

    def apply_update_check_error(self, _exc):
        self.set_update_status("Check failed", "error")

    def build_trust_line(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(8)

        title = QLabel("TRUST")
        title.setObjectName("sectionTitle")
        trust = QLabel("No telemetry | No analytics | No tracking | Local data stays local")
        trust.setObjectName("moduleSubtitle")
        trust.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(trust, 1)
        card.setLayout(layout)
        return card

    def build_feedback_note(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(8)

        title = QLabel("ALPHA FEEDBACK")
        title.setObjectName("sectionTitle")
        note = QLabel("Report bugs and feature requests through GitHub Issues.")
        note.setObjectName("moduleSubtitle")
        note.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(note, 1)
        card.setLayout(layout)
        return card

    def build_community_footer(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = QHBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        title = QLabel("SC Intel Tool")
        title.setObjectName("appTitle")
        subtitle = QLabel("Community-made companion app for Star Citizen")
        subtitle.setObjectName("valueText")
        subtitle.setWordWrap(True)
        legal = QLabel(
            "Unofficial fan-made application. Not affiliated with Cloud Imperium Games. "
            "All trademarks belong to their respective owners."
        )
        legal.setObjectName("moduleSubtitle")
        legal.setWordWrap(True)

        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        text_layout.addWidget(legal)

        layout.addLayout(text_layout, 1)
        layout.addWidget(CommunityLogoLabel(max_size=78, min_size=54), 0, Qt.AlignRight | Qt.AlignVCenter)
        card.setLayout(layout)
        return card

    def open_target_tab(self, target):
        if self.navigate_callback:
            self.navigate_callback(target)

    def update_first_timer_aliases(self):
        if not self.countdown_timers:
            return

        first_timer = self.countdown_timers[0]
        self.timer_input = first_timer.timer_input
        self.timer_display = first_timer.timer_display
        self.timer_status_label = first_timer.timer_status_label
        self.timer_start_button = first_timer.timer_start_button
        self.timer_reset_button = first_timer.timer_reset_button

    def add_countdown_timer(self, removable=True):
        if self.timer_panel_layout is None:
            return

        timer = CountdownTimerWidget(
            f"Timer {len(self.countdown_timers) + 1}",
            remove_callback=self.remove_countdown_timer if removable else None,
        )
        self.countdown_timers.append(timer)
        insert_index = self.timer_panel_layout.count()
        if hasattr(self, "add_timer_button"):
            add_button_index = self.timer_panel_layout.indexOf(self.add_timer_button)
            if add_button_index >= 0:
                insert_index = add_button_index
        self.timer_panel_layout.insertWidget(insert_index, timer)
        self.renumber_timers()
        self.update_first_timer_aliases()

    def remove_countdown_timer(self, timer):
        if timer not in self.countdown_timers or len(self.countdown_timers) <= 1:
            return

        timer.reset_timer()
        self.countdown_timers.remove(timer)
        self.timer_panel_layout.removeWidget(timer)
        timer.deleteLater()
        self.renumber_timers()
        self.update_first_timer_aliases()

    def renumber_timers(self):
        for index, timer in enumerate(self.countdown_timers, start=1):
            timer.set_title(f"Timer {index}")

    def start_timer(self):
        self.countdown_timers[0].start_timer()

    def reset_timer(self):
        self.countdown_timers[0].reset_timer()

    def tick_timer(self):
        self.countdown_timers[0].tick_timer()

    def update_timer_display(self):
        self.countdown_timers[0].update_timer_display()

    def parse_duration_seconds(self, text):
        return self.countdown_timers[0].parse_duration_seconds(text)

    def create_hero_panel(self):
        card = QFrame()
        card.setObjectName("playerCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = QHBoxLayout()
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(13)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)

        title_label = QLabel("SC Intel Tool")
        title_label.setObjectName("moduleHeading")
        subtitle_label = QLabel("Operational companion app for Star Citizen.")
        subtitle_label.setObjectName("moduleSubtitle")
        subtitle_label.setWordWrap(True)
        mission_label = QLabel(
            "Player intel, mining, trading, crafting, item lookup, watchlists and local notes in one place."
        )
        mission_label.setObjectName("valueText")
        mission_label.setWordWrap(True)

        chip_row = QHBoxLayout()
        chip_row.setSpacing(5)
        chip_row.addWidget(self.create_chip("Alpha Build"))
        chip_row.addWidget(self.create_chip("Tracking-Free"))
        chip_row.addWidget(self.create_chip("Local Data"))
        chip_row.addWidget(self.create_chip("Operational Tool"))
        chip_row.addStretch(1)

        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)
        text_layout.addWidget(mission_label)
        text_layout.addLayout(chip_row)

        layout.addWidget(AppLogoLabel(max_size=148, min_size=104), 0, Qt.AlignLeft | Qt.AlignVCenter)
        layout.addLayout(text_layout, 1)
        card.setLayout(layout)
        return card

    def create_chip(self, text):
        label = QLabel(text)
        label.setObjectName("statusChip")
        return label

    def create_filter_card(self, title):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(5)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)
        card.setLayout(layout)
        return card
