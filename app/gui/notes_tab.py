from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.paths import bundled_path


class NotesTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.build_notes_card())
        layout.addWidget(self.build_changelog_card(), 1)
        self.setLayout(layout)

    def build_notes_card(self):
        card = self.create_card("NOTES")
        text = self.create_read_only_text()
        text.setPlainText(
            "Global notes and watchlists will be available here.\n\n"
            "Planned uses:\n"
            "- Watchlist\n"
            "- Hostile list\n"
            "- Friendly list\n"
            "- Custom tags"
        )
        card.layout().addWidget(text)
        return card

    def build_changelog_card(self):
        card = self.create_card("CHANGELOG")
        subtitle = QLabel("Release notes loaded from the bundled CHANGELOG.md file.")
        subtitle.setObjectName("moduleSubtitle")
        card.layout().addWidget(subtitle)

        text = self.create_read_only_text()
        text.setPlainText(load_changelog_text())
        card.layout().addWidget(text, 1)
        return card

    def create_card(self, title):
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

    def create_read_only_text(self):
        text = QTextEdit()
        text.setReadOnly(True)
        text.setMinimumHeight(130)
        return text


def load_changelog_text():
    changelog_path = bundled_path("CHANGELOG.md")
    if not changelog_path.exists():
        return "No bundled changelog was found for this build."

    return changelog_path.read_text(encoding="utf-8").strip()
