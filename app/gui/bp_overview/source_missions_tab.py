from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from app.blueprints_client import SC_CRAFT_TOOLS_BASE_URL

from .shared import create_card, source_attribution_text


class SourceMissionsTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        card = create_card("MISSION / SOURCE CONTEXT")
        text = QLabel(
            "SC Craft Tools currently exposes mission drop names and drop-chance text for many "
            "blueprints through its public blueprint endpoint. When a blueprint does not include "
            "mission/source fields, SC Intel Tool says so directly instead of guessing."
        )
        text.setObjectName("valueText")
        text.setWordWrap(True)
        card.layout().addWidget(text)

        attribution = QLabel(source_attribution_text())
        attribution.setObjectName("moduleSubtitle")
        attribution.setWordWrap(True)
        card.layout().addWidget(attribution)

        self.open_button = QPushButton("Open SC Craft Tools")
        self.open_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(SC_CRAFT_TOOLS_BASE_URL)))
        card.layout().addWidget(self.open_button)

        layout.addWidget(card)
        layout.addStretch(1)
        self.setLayout(layout)
