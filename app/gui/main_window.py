import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from app.database import init_db
from app.paths import bundled_path
from app.version import APP_VERSION

from .item_finder_tab import ItemFinderTab
from .mining_tab import MiningTab
from .notes_tab import NotesTab
from .player_lookup_tab import PlayerLookupTab
from .search_history_tab import SearchHistoryTab
from .settings_tab import SettingsTab
from .styles import APP_STYLE
from .trading_tab import TradingTab


def app_icon():
    icon_path = bundled_path("app", "assets", "Balder.ico")
    if icon_path.exists():
        return QIcon(str(icon_path))

    return QIcon()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"SC Intel Tool {APP_VERSION}")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1120, 780)
        self.setStyleSheet(APP_STYLE)

        self.tabs = QTabWidget()

        self.history_tab = SearchHistoryTab()
        self.player_tab = PlayerLookupTab(on_lookup_saved=self.history_tab.refresh_history)
        self.mining_tab = MiningTab()
        self.trading_tab = TradingTab()
        self.item_finder_tab = ItemFinderTab()
        self.notes_tab = NotesTab()
        self.settings_tab = SettingsTab()

        self.tabs.addTab(self.player_tab, "Player Lookup")
        self.tabs.addTab(self.history_tab, "Search History")
        self.tabs.addTab(self.mining_tab, "Mining & Salvage")
        self.tabs.addTab(self.trading_tab, "Trading")
        self.tabs.addTab(self.item_finder_tab, "Item Finder")
        self.tabs.addTab(self.notes_tab, "Notes")
        self.tabs.addTab(self.settings_tab, "Settings")

        self.setCentralWidget(self.tabs)


def run_app():
    init_db()

    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
