from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .shared import create_card


class SourceMissionsTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        card = create_card("MISSION CONTEXT")
        text = QLabel(
            "Some blueprints include mission drop names and drop-chance text. "
            "When mission context is not available, SC Intel Tool says so directly instead of guessing."
        )
        text.setObjectName("valueText")
        text.setWordWrap(True)
        card.layout().addWidget(text)

        layout.addWidget(card)
        layout.addStretch(1)
        self.setLayout(layout)
