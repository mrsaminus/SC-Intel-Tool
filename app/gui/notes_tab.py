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
            "Global notes and watchlists will be available here.\n\n"
            "Planned uses:\n"
            "- Watchlist\n"
            "- Hostile list\n"
            "- Friendly list\n"
            "- Custom tags"
        )

        layout.addWidget(text)
        self.setLayout(layout)
