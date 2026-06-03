import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from app.database import init_db
from app.paths import bundled_path
from app.update_checker import check_for_updates as fetch_update_info
from app.version import APP_VERSION

from .home_tab import HomeTab
from .item_finder_tab import ItemFinderTab
from .mining_tab import MiningTab
from .notes_tab import NotesTab
from .player_lookup_tab import PlayerLookupTab
from .search_history_tab import SearchHistoryTab
from .settings_tab import SettingsTab
from .styles import APP_STYLE
from .trading_tab import TradingTab
from .wikelo_tab import WikeloItemsTab
from .workers import BackgroundTaskMixin


def app_icon():
    icon_path = bundled_path("app", "assets", "Balder.ico")
    if icon_path.exists():
        return QIcon(str(icon_path))

    return QIcon()


class MainWindow(BackgroundTaskMixin, QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"SC Intel Tool {APP_VERSION}")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1120, 780)
        self.setStyleSheet(APP_STYLE)

        self.tabs = QTabWidget()

        self.home_tab = HomeTab(self.open_tab)
        self.history_tab = SearchHistoryTab()
        self.player_tab = PlayerLookupTab(on_lookup_saved=self.history_tab.refresh_history)
        self.mining_tab = MiningTab()
        self.trading_tab = TradingTab()
        self.item_finder_tab = ItemFinderTab()
        self.wikelo_tab = WikeloItemsTab()
        self.notes_tab = NotesTab()
        self.settings_tab = SettingsTab(
            update_status_callback=self.home_tab.apply_update_check_result,
            update_error_callback=self.home_tab.apply_update_check_error,
        )
        self.startup_update_check_running = False

        self.tabs.addTab(self.home_tab, "Home")
        self.tabs.addTab(self.player_tab, "Player Lookup")
        self.tabs.addTab(self.history_tab, "Search History")
        self.tabs.addTab(self.mining_tab, "Mining & Salvage")
        self.tabs.addTab(self.trading_tab, "Trading")
        self.tabs.addTab(self.item_finder_tab, "Item Finder")
        self.tabs.addTab(self.wikelo_tab, "Wikelo Items")
        self.tabs.addTab(self.notes_tab, "Notes")
        self.tabs.addTab(self.settings_tab, "Settings")

        self.setCentralWidget(self.tabs)
        QTimer.singleShot(700, self.start_startup_update_check)

    def open_tab(self, tab_name):
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == tab_name:
                self.tabs.setCurrentIndex(index)
                return

    def start_startup_update_check(self):
        if self.startup_update_check_running:
            return

        self.startup_update_check_running = True
        self.home_tab.set_update_checking()
        self.start_background_task(
            fetch_update_info,
            self.on_startup_update_check_finished,
            self.on_startup_update_check_error,
            self.finish_startup_update_check,
        )

    def on_startup_update_check_finished(self, result):
        self.home_tab.apply_update_check_result(result)
        self.settings_tab.apply_update_check_result(result, notify=False)

    def on_startup_update_check_error(self, exc):
        self.home_tab.apply_update_check_error(exc)
        self.settings_tab.apply_update_check_error(exc, show_popup=False, notify=False)

    def finish_startup_update_check(self):
        self.startup_update_check_running = False


def run_app():
    init_db()

    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
