from PySide6.QtWidgets import (
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class NotesTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Global notes/watchlist kommer her.\n\n"
            "Dette blir brukt til:\n"
            "- Watchlist\n"
            "- Hostile list\n"
            "- Friendly list\n"
            "- NOVA/Defence/Relief/Skyline/Frontiers/Core/BALDER tagging"
        )

        layout.addWidget(text)
        self.setLayout(layout)
