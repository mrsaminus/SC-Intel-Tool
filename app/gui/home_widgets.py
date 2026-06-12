from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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
        self.setMinimumHeight(102)
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
        layout.setContentsMargins(13, 10, 13, 10)
        layout.setSpacing(4)

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
        self.timer_display.setStyleSheet("font-size: 13pt;")

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
