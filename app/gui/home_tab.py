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
    def __init__(self, title, description, open_callback):
        super().__init__()
        self.target_title = title
        self.open_callback = open_callback

        self.setObjectName("homeNavCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(72)
        self.setMaximumHeight(86)
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
        layout.setContentsMargins(11, 8, 11, 8)
        layout.setSpacing(3)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #f5fdff; font-size: 11pt; font-weight: 700;")
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
    NAV_SECTIONS = [
        (
            "Intel",
            [
                ("Player Lookup", "RSI profiles and local intel notes."),
                ("Search History", "Previous lookups and saved profile details."),
            ],
        ),
        (
            "Industrial Tools",
            [
                ("Mining & Salvage", "Mining, salvage, refining and scan tools."),
                ("Item Finder", "Gear, ships and buy/rental locations."),
                ("Wikelo Items", "Wikelo missions, materials and rewards."),
                ("Trading", "Market planning and trading workspace."),
            ],
        ),
        (
            "Utility",
            [
                ("Notes", "Changelog and local reference notes."),
                ("Settings", "Updates, privacy and app settings."),
            ],
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
        page_layout.setContentsMargins(12, 12, 12, 12)
        page_layout.setSpacing(10)

        page_layout.addWidget(self.create_module_header(
            "SC Intel Tool",
            "One operational companion app for Star Citizen.",
        ))

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        main_layout.addWidget(self.build_navigation_panel(), 3)
        main_layout.addWidget(self.build_side_panel(), 1, Qt.AlignTop)

        page_layout.addLayout(main_layout)
        page.setLayout(page_layout)
        scroll_area.setWidget(page)
        layout.addWidget(scroll_area)

        self.setLayout(layout)
        self.update_first_timer_aliases()

    def create_nav_card(self, title, description):
        return NavigationCard(title, description, self.open_target_tab)

    def build_navigation_panel(self):
        panel = QWidget()
        panel.setMinimumWidth(640)
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for section_title, items in self.NAV_SECTIONS:
            layout.addWidget(self.create_nav_section(section_title, items))

        panel.setLayout(layout)
        return panel

    def create_nav_section(self, section_title, items):
        section = QFrame()
        section.setObjectName("sectionCard")
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(10, 8, 10, 10)
        section_layout.setSpacing(6)

        title_label = QLabel(section_title.upper())
        title_label.setObjectName("sectionTitle")
        section_layout.addWidget(title_label)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(7)
        grid.setVerticalSpacing(7)
        for column in range(2):
            grid.setColumnStretch(column, 1)

        for index, (title, description) in enumerate(items):
            grid.addWidget(self.create_nav_card(title, description), index // 2, index % 2)

        section_layout.addLayout(grid)
        section.setLayout(section_layout)
        return section

    def build_side_panel(self):
        panel = QWidget()
        panel.setMinimumWidth(320)
        panel.setMaximumWidth(420)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.build_timer_panel())
        layout.addWidget(self.build_privacy_panel())
        panel.setLayout(layout)
        return panel

    def build_timer_panel(self):
        card = self.create_filter_card("COUNTDOWN TIMERS")
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        layout = card.layout()
        layout.setSpacing(7)
        self.timer_panel_layout = layout

        self.add_countdown_timer(removable=False)
        self.add_timer_button = QPushButton("Add Timer")
        self.add_timer_button.clicked.connect(lambda: self.add_countdown_timer(removable=True))
        layout.addWidget(self.add_timer_button)
        return card

    def build_privacy_panel(self):
        card = self.create_filter_card("LOCAL STATUS")
        card.setMinimumHeight(82)
        card.setMaximumHeight(116)
        layout = card.layout()

        privacy_lines = [
            "No telemetry",
            "No tracking",
            "Local data stays local",
        ]
        for line in privacy_lines:
            label = QLabel(line)
            label.setObjectName("moduleSubtitle")
            label.setWordWrap(True)
            layout.addWidget(label)

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
            insert_index = self.timer_panel_layout.indexOf(self.add_timer_button)
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

    def create_module_header(self, title, subtitle, secondary_text=None):
        card = QFrame()
        card.setObjectName("playerCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)
        title_label = QLabel(title)
        title_label.setObjectName("moduleHeading")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("moduleSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        if secondary_text:
            secondary_label = QLabel(secondary_text)
            secondary_label.setObjectName("valueText")
            secondary_label.setWordWrap(True)
            layout.addWidget(secondary_label)
        card.setLayout(layout)
        return card

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
