from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class HomeTab(QWidget):
    NAV_ITEMS = [
        ("Player Lookup", "Look up RSI citizen profiles and local intel notes."),
        ("Search History", "Review previous lookups and open saved profile details."),
        ("Mining & Salvage", "Plan mining, salvage, refining, scan IDs and equipment."),
        ("Trading", "Trading tools and market planning space."),
        ("Item Finder", "Find gear, ships and buy/rental locations."),
        ("Notes", "App notes, changelog and local reference notes."),
        ("Settings", "Update checks, privacy notes and local app settings."),
    ]

    def __init__(self, navigate_callback=None):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.remaining_seconds = 0
        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self.tick_timer)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_module_header(
            "SC Intel Tool",
            "Quick navigation for player intel, mining, trading, item lookup and notes.",
        ))

        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self.build_navigation_panel(), 3)
        content.addWidget(self.build_timer_panel(), 1)
        layout.addLayout(content, 1)

        self.setLayout(layout)
        self.update_timer_display()

    def build_navigation_panel(self):
        card = self.create_filter_card("QUICK NAVIGATION")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        for index, (title, description) in enumerate(self.NAV_ITEMS):
            grid.addWidget(self.create_nav_card(title, description), index // 2, index % 2)

        card.layout().addLayout(grid)
        return card

    def create_nav_card(self, title, description):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(6)

        button = QPushButton(title)
        button.clicked.connect(lambda checked=False, target=title: self.open_target_tab(target))
        description_label = QLabel(description)
        description_label.setObjectName("moduleSubtitle")
        description_label.setWordWrap(True)

        layout.addWidget(button)
        layout.addWidget(description_label)
        card.setLayout(layout)
        return card

    def build_timer_panel(self):
        card = self.create_filter_card("COUNTDOWN TIMER")
        layout = card.layout()

        self.timer_input = QLineEdit()
        self.timer_input.setPlaceholderText("Minutes, seconds or HH:MM:SS")
        self.timer_display = QLabel("00:00:00")
        self.timer_display.setObjectName("orgName")
        self.timer_display.setAlignment(Qt.AlignCenter)
        self.timer_status_label = QLabel("Enter a duration and press Start.")
        self.timer_status_label.setObjectName("moduleSubtitle")
        self.timer_status_label.setWordWrap(True)

        button_row = QHBoxLayout()
        self.timer_start_button = QPushButton("Start")
        self.timer_reset_button = QPushButton("Reset")
        self.timer_start_button.clicked.connect(self.start_timer)
        self.timer_reset_button.clicked.connect(self.reset_timer)
        button_row.addWidget(self.timer_start_button)
        button_row.addWidget(self.timer_reset_button)

        layout.addWidget(self.timer_input)
        layout.addWidget(self.timer_display)
        layout.addLayout(button_row)
        layout.addWidget(self.timer_status_label)
        layout.addStretch(1)
        return card

    def open_target_tab(self, target):
        if self.navigate_callback:
            self.navigate_callback(target)

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
