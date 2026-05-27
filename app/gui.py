import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel, QTabWidget, QComboBox,
    QMessageBox
)

from app.database import init_db, save_lookup, save_note, get_note
from app.rsi_lookup import lookup_player, RSILookupError


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SC Intel Tool")
        self.setMinimumSize(1000, 700)

        self.tabs = QTabWidget()

        self.player_tab = PlayerLookupTab()
        self.mining_tab = MiningTab()
        self.notes_tab = NotesTab()
        self.settings_tab = SettingsTab()

        self.tabs.addTab(self.player_tab, "Player Lookup")
        self.tabs.addTab(self.mining_tab, "Mining")
        self.tabs.addTab(self.notes_tab, "Notes")
        self.tabs.addTab(self.settings_tab, "Settings")

        self.setCentralWidget(self.tabs)


class PlayerLookupTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        search_row = QHBoxLayout()
        self.handle_input = QLineEdit()
        self.handle_input.setPlaceholderText("Enter RSI handle...")
        self.search_button = QPushButton("Lookup Player")

        search_row.addWidget(self.handle_input)
        search_row.addWidget(self.search_button)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)

        self.tag_box = QComboBox()
        self.tag_box.addItems([
            "Unmarked",
            "Friendly",
            "Neutral",
            "Hostile",
            "Pirate",
            "Scammer",
            "NOVA",
            "NAF",
            "Core",
            "B.A.L.D.E.R."
        ])

        self.notes_box = QTextEdit()
        self.notes_box.setPlaceholderText("Local notes about this player...")

        self.save_note_button = QPushButton("Save Note")

        layout.addLayout(search_row)
        layout.addWidget(QLabel("Lookup Result"))
        layout.addWidget(self.result_box)
        layout.addWidget(QLabel("Tag"))
        layout.addWidget(self.tag_box)
        layout.addWidget(QLabel("Notes"))
        layout.addWidget(self.notes_box)
        layout.addWidget(self.save_note_button)

        self.setLayout(layout)

        self.current_handle = None

        self.search_button.clicked.connect(self.search_player)
        self.save_note_button.clicked.connect(self.save_current_note)

    def search_player(self):
        handle = self.handle_input.text().strip()

        try:
            data = lookup_player(handle)

            self.current_handle = data["handle"]

            save_lookup(
                data["handle"],
                data["display_name"],
                data["main_org"],
                data["profile_url"]
            )

            saved_note = get_note(data["handle"])
            if saved_note:
                tag, notes = saved_note
                self.tag_box.setCurrentText(tag or "Unmarked")
                self.notes_box.setPlainText(notes or "")
            else:
                self.tag_box.setCurrentText("Unmarked")
                self.notes_box.clear()

            output = f"""
HANDLE: {data['handle']}
DISPLAY NAME: {data['display_name']}
CITIZEN RECORD: {data['citizen_record']}
ENLISTED: {data['enlisted']}
LOCATION: {data['location']}
FLUENCY: {data['fluency']}
MAIN ORG: {data['main_org']}

PROFILE:
{data['profile_url']}
            """.strip()

            self.result_box.setPlainText(output)

        except RSILookupError as e:
            QMessageBox.warning(self, "Lookup failed", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_current_note(self):
        if not self.current_handle:
            QMessageBox.warning(self, "No player", "Lookup a player first.")
            return

        save_note(
            self.current_handle,
            self.tag_box.currentText(),
            self.notes_box.toPlainText()
        )

        QMessageBox.information(self, "Saved", "Note saved.")


class MiningTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        title = QLabel("Mining Intelligence")
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Mining module placeholder.\n\n"
            "Neste steg:\n"
            "- Importere mineral locations\n"
            "- Søke etter ores\n"
            "- Vise beste steder i Stanton/Pyro\n"
            "- Refinery calculator\n"
            "- Rock breaking calculator"
        )

        layout.addWidget(title)
        layout.addWidget(text)

        self.setLayout(layout)


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
            "- NOVA/NAF/Core/BALDER tagging"
        )

        layout.addWidget(text)
        self.setLayout(layout)


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Settings kommer her.\n\n"
            "Planlagt:\n"
            "- Theme\n"
            "- Default scan region\n"
            "- RSI lookup timeout\n"
            "- Local data folders\n"
            "- Export/import"
        )

        layout.addWidget(text)
        self.setLayout(layout)


def run_app():
    init_db()

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())