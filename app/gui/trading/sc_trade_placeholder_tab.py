from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget


class SCTradePlaceholderTab(QWidget):
    def __init__(self, title, purpose, source_url):
        super().__init__()
        self.title = title
        self.purpose = purpose
        self.source_url = source_url

        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        card = QFrame()
        card.setObjectName("playerCard")
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 14, 16, 16)
        card_layout.setSpacing(10)

        title_label = QLabel(self.title)
        title_label.setObjectName("moduleHeading")

        purpose_label = QLabel(self.purpose)
        purpose_label.setObjectName("valueText")
        purpose_label.setWordWrap(True)

        planned_label = QLabel(
            "Planned integration. Advanced SC Trade Tools workflows are not available in the public build yet."
        )
        planned_label.setObjectName("moduleSubtitle")
        planned_label.setWordWrap(True)

        source_label = QLabel(f"Source: {self.source_url}")
        source_label.setObjectName("moduleSubtitle")
        source_label.setWordWrap(True)

        open_button = QPushButton("Open SC Trade Tools")
        open_button.clicked.connect(self.open_source)

        card_layout.addWidget(title_label)
        card_layout.addWidget(purpose_label)
        card_layout.addWidget(planned_label)
        card_layout.addWidget(source_label)
        card_layout.addWidget(open_button)
        card_layout.addStretch(1)
        card.setLayout(card_layout)

        layout.addWidget(card)
        layout.addStretch(1)
        self.setLayout(layout)

    def open_source(self):
        QDesktopServices.openUrl(QUrl(self.source_url))
