from app.paths import is_packaged_app
from app.version import APP_VERSION

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class NavigationCard(QFrame):
    def __init__(self, title, description, open_callback, target=None, eyebrow=None):
        super().__init__()
        self.target_title = target or title
        self.open_callback = open_callback

        self.setObjectName("homeNavCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(108)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QFrame#homeNavCard {
                background: #0b1820;
                border: 1px solid #1e5060;
                border-radius: 6px;
            }
            QFrame#homeNavCard:hover {
                background: #102735;
                border-color: #34d8f5;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(5)

        if eyebrow:
            eyebrow_label = QLabel(eyebrow.upper())
            eyebrow_label.setObjectName("sectionTitle")
            layout.addWidget(eyebrow_label)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #f5fdff; font-size: 13pt; font-weight: 700;")
        description_label = QLabel(description)
        description_label.setObjectName("moduleSubtitle")
        description_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        self.setLayout(layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.open_target()
        super().mousePressEvent(event)

    def open_target(self):
        if self.open_callback:
            self.open_callback(self.target_title)


class CountdownTimerWidget(QWidget):
    def __init__(self, title, remove_callback=None):
        super().__init__()
        self.remove_callback = remove_callback
        self.default_title = title
        self.remaining_seconds = 0
        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self.tick_timer)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")

        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("Label")
        self.label_input.textChanged.connect(self.update_title_from_label)
        self.timer_input = QLineEdit()
        self.timer_input.setPlaceholderText("10m, 90s or HH:MM:SS")
        input_row.addWidget(self.label_input, 1)
        input_row.addWidget(self.timer_input, 1)

        self.timer_display = QLabel("00:00:00")
        self.timer_display.setObjectName("orgName")
        self.timer_display.setAlignment(Qt.AlignCenter)
        self.timer_display.setStyleSheet("font-size: 14pt;")

        button_row = QHBoxLayout()
        button_row.setSpacing(6)
        self.timer_start_button = QPushButton("Start")
        self.timer_reset_button = QPushButton("Reset")
        self.timer_start_button.clicked.connect(self.start_timer)
        self.timer_reset_button.clicked.connect(self.reset_timer)
        button_row.addWidget(self.timer_start_button)
        button_row.addWidget(self.timer_reset_button)
        if self.remove_callback:
            self.timer_remove_button = QPushButton("Remove")
            self.timer_remove_button.clicked.connect(lambda: self.remove_callback(self))
            button_row.addWidget(self.timer_remove_button)

        self.timer_status_label = QLabel("Ready.")
        self.timer_status_label.setObjectName("moduleSubtitle")
        self.timer_status_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addLayout(input_row)
        layout.addWidget(self.timer_display)
        layout.addLayout(button_row)
        layout.addWidget(self.timer_status_label)
        self.setLayout(layout)

    def set_title(self, title):
        self.default_title = title
        self.update_title_from_label(self.label_input.text())

    def update_title_from_label(self, label_text):
        title = str(label_text or "").strip() or self.default_title
        self.title_label.setText(title)

    def start_timer(self):
        seconds = self.parse_duration_seconds(self.timer_input.text())
        if seconds <= 0:
            self.timer_status_label.setText("Enter a valid duration first.")
            return

        self.remaining_seconds = seconds
        self.update_timer_display()
        self.countdown_timer.start()
        self.timer_status_label.setText("Timer running.")

    def reset_timer(self):
        self.countdown_timer.stop()
        self.remaining_seconds = 0
        self.update_timer_display()
        self.timer_status_label.setText("Timer reset.")

    def tick_timer(self):
        self.remaining_seconds = max(0, self.remaining_seconds - 1)
        self.update_timer_display()
        if self.remaining_seconds <= 0:
            self.countdown_timer.stop()
            self.timer_status_label.setText("Timer complete.")

    def update_timer_display(self):
        seconds = max(0, int(self.remaining_seconds or 0))
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        self.timer_display.setText(f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}")

    def parse_duration_seconds(self, text):
        value = str(text or "").strip().lower()
        if not value:
            return 0

        try:
            if ":" in value:
                parts = [int(part) for part in value.split(":")]
                if len(parts) == 2:
                    minutes, seconds = parts
                    return max(0, minutes * 60 + seconds)
                if len(parts) == 3:
                    hours, minutes, seconds = parts
                    return max(0, hours * 3600 + minutes * 60 + seconds)
                return 0

            if value.endswith("h"):
                return max(0, int(float(value[:-1]) * 3600))
            if value.endswith("m"):
                return max(0, int(float(value[:-1]) * 60))
            if value.endswith("s"):
                return max(0, int(float(value[:-1])))

            return max(0, int(float(value) * 60))
        except ValueError:
            return 0


class HomeTab(QWidget):
    CAPABILITY_CARDS = [
        (
            "Player Intel",
            "RSI lookup, organizations, affiliations, local tags and notes.",
            "Player Lookup",
            "Intel",
        ),
        (
            "Mining & Salvage",
            "Ore finder, refinery tools, scan IDs and salvage resources.",
            "Mining & Salvage",
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

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        page = QWidget()
        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(14, 14, 14, 14)
        page_layout.setSpacing(12)

        page_layout.addWidget(self.create_hero_panel())
        page_layout.addWidget(self.build_status_strip())

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)
        main_layout.addWidget(self.build_left_panel(), 3, Qt.AlignTop)
        main_layout.addWidget(self.build_timer_panel(), 1, Qt.AlignTop)

        page_layout.addLayout(main_layout)
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
        layout.setSpacing(8)

        layout.addWidget(self.build_navigation_panel())
        layout.addWidget(self.build_trust_line())
        layout.addWidget(self.build_feedback_note())
        panel.setLayout(layout)
        return panel

    def build_navigation_panel(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        title_label = QLabel("CAPABILITY OVERVIEW")
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
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
        card.setMinimumWidth(340)
        card.setMaximumWidth(440)
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        outer_layout = card.layout()
        outer_layout.setSpacing(7)

        timer_scroll = QScrollArea()
        timer_scroll.setWidgetResizable(True)
        timer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        timer_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        timer_scroll.setMinimumHeight(210)
        timer_scroll.setMaximumHeight(420)

        timer_content = QWidget()
        self.timer_panel_layout = QVBoxLayout()
        self.timer_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.timer_panel_layout.setSpacing(10)
        timer_content.setLayout(self.timer_panel_layout)
        timer_scroll.setWidget(timer_content)
        outer_layout.addWidget(timer_scroll)

        self.add_countdown_timer(removable=False)
        self.add_timer_button = QPushButton("Add Timer")
        self.add_timer_button.clicked.connect(lambda: self.add_countdown_timer(removable=True))
        outer_layout.addWidget(self.add_timer_button)
        return card

    def build_status_strip(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = card.layout()
        if layout is None:
            layout = QHBoxLayout()
            layout.setContentsMargins(12, 8, 12, 8)
            layout.setSpacing(8)

        build_type = "Packaged build" if is_packaged_app() else "Source/dev run"
        title = QLabel("OPERATIONAL STATUS")
        title.setObjectName("sectionTitle")
        status = QLabel(
            f"Version: {APP_VERSION} | Runtime: {build_type} | "
            "Data: AppData/local | Updates: GitHub Releases"
        )
        status.setObjectName("moduleSubtitle")
        status.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(status, 1)
        card.setLayout(layout)

        return card

    def build_trust_line(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
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
        layout.setContentsMargins(12, 8, 12, 8)
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
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(7)

        title_label = QLabel("SC Intel Tool")
        title_label.setObjectName("moduleHeading")
        subtitle_label = QLabel("One operational companion app for Star Citizen.")
        subtitle_label.setObjectName("moduleSubtitle")
        subtitle_label.setWordWrap(True)
        mission_label = QLabel(
            "Player intel, organization context, mining, salvage, trading, item lookup, "
            "Wikelo tracking and local notes - in one place."
        )
        mission_label.setObjectName("valueText")
        mission_label.setWordWrap(True)

        chip_row = QHBoxLayout()
        chip_row.setSpacing(6)
        chip_row.addWidget(self.create_chip("Alpha Build"))
        chip_row.addWidget(self.create_chip("Tracking-Free"))
        chip_row.addWidget(self.create_chip("Local Data"))
        chip_row.addWidget(self.create_chip("Operational Tool"))
        chip_row.addStretch(1)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addWidget(mission_label)
        layout.addLayout(chip_row)
        card.setLayout(layout)
        return card

    def create_chip(self, text):
        label = QLabel(text)
        label.setObjectName("statusChip")
        label.setStyleSheet("""
            QLabel#statusChip {
                background: #0d2530;
                border: 1px solid #2b7386;
                border-radius: 10px;
                color: #8ff4ff;
                font-size: 8pt;
                font-weight: 700;
                padding: 3px 8px;
            }
        """)
        return label

    def create_filter_card(self, title):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)
        card.setLayout(layout)
        return card
