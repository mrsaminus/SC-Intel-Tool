import logging
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPalette
from PySide6.QtWidgets import QApplication, QMainWindow, QStyle, QStyleOptionTab, QStylePainter, QTabBar, QTabWidget

from app.database import DB_PATH, init_db
from app.logging_config import configure_logging, install_exception_hook
from app.paths import bundled_path, get_active_data_dir, is_packaged_app
from app.update_checker import check_for_updates as fetch_update_info
from app.version import APP_VERSION

from .bp_overview_tab import BPOverviewTab
from .event_center_tab import EventCenterTab
from .home_tab import HomeTab
from .item_finder_tab import ItemFinderTab
from .mining_tab import MiningTab
from .notes_tab import NotesTab
from .player_lookup_tab import PlayerLookupTab
from .search_history_tab import SearchHistoryTab
from .settings_tab import SettingsTab
from .styles import current_app_style
from .themes import get_current_theme_key, stylesheet_for_theme
from .trading_tab import TradingTab
from .wikelo_tab import WikeloItemsTab
from .watchlists_tab import WatchlistsTab
from .workers import BackgroundTaskMixin

logger = logging.getLogger(__name__)


def app_icon():
    icon_path = bundled_path("app", "assets", "SC-Intel-Tool.ico")
    if icon_path.exists():
        return QIcon(str(icon_path))

    fallback_icon_path = bundled_path("app", "assets", "Balder.ico")
    if fallback_icon_path.exists():
        logger.warning("Primary app icon missing; using fallback icon at %s", fallback_icon_path)
        return QIcon(str(fallback_icon_path))

    logger.warning("No app icon asset found.")
    return QIcon()


class MainWindow(BackgroundTaskMixin, QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"SC Intel Tool {APP_VERSION}")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1120, 780)
        self.setStyleSheet(current_app_style())

        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainNavigationTabs")
        self.tabs.setTabBar(ThemeAwareTabBar())
        self.tabs.tabBar().setObjectName("mainNavigationTabBar")

        self.home_tab = HomeTab(self.open_tab)
        self.event_center_tab = EventCenterTab()
        self.history_tab = SearchHistoryTab()
        self.player_tab = PlayerLookupTab(on_lookup_saved=self.history_tab.refresh_history)
        self.mining_tab = MiningTab()
        self.trading_tab = TradingTab()
        self.item_finder_tab = ItemFinderTab()
        self.watchlists_tab = WatchlistsTab()
        self.wikelo_tab = WikeloItemsTab()
        self.bp_overview_tab = BPOverviewTab()
        self.notes_tab = NotesTab()
        self.settings_tab = SettingsTab(
            update_status_callback=self.home_tab.apply_update_check_result,
            update_error_callback=self.home_tab.apply_update_check_error,
            theme_changed_callback=self.apply_theme,
        )
        self.startup_update_check_running = False

        self.intel_tabs = self.create_group_tabs("intelNavigationTabs")
        self.intel_tabs.addTab(self.player_tab, "Player Lookup")
        self.intel_tabs.addTab(self.history_tab, "Search History")
        self.intel_tabs.addTab(self.watchlists_tab, "Watchlists")

        self.industrial_tabs = self.create_group_tabs("industrialNavigationTabs")
        self.industrial_tabs.addTab(self.mining_tab, "Mining / Salvage")
        self.industrial_tabs.addTab(self.trading_tab, "Trading")
        self.industrial_tabs.addTab(self.bp_overview_tab, "BP Overview")

        self.reference_tabs = self.create_group_tabs("referenceNavigationTabs")
        self.reference_tabs.addTab(self.item_finder_tab, "Item Finder")
        self.reference_tabs.addTab(self.wikelo_tab, "Wikelo Items")

        self.system_tabs = self.create_group_tabs("systemNavigationTabs")
        self.system_tabs.addTab(self.event_center_tab, "Activity Log")
        self.system_tabs.addTab(self.notes_tab, "Notes")
        self.system_tabs.addTab(self.settings_tab, "Settings")

        self.tabs.addTab(self.home_tab, "Home")
        self.tabs.addTab(self.intel_tabs, "Intel")
        self.tabs.addTab(self.industrial_tabs, "Industrial")
        self.tabs.addTab(self.reference_tabs, "Reference")
        self.tabs.addTab(self.system_tabs, "System")

        self.setCentralWidget(self.tabs)
        self.connect_deferred_initial_loads()
        QTimer.singleShot(700, self.start_startup_update_check)

    def create_group_tabs(self, object_name):
        tabs = QTabWidget()
        tabs.setObjectName(object_name)
        tabs.tabBar().setObjectName("groupNavigationTabBar")
        return tabs

    def connect_deferred_initial_loads(self):
        self.tabs.currentChanged.connect(lambda _index: self.run_visible_tab_initial_load())
        for group_tabs in (self.intel_tabs, self.industrial_tabs, self.reference_tabs, self.system_tabs):
            group_tabs.currentChanged.connect(lambda _index: self.run_visible_tab_initial_load())

    def run_visible_tab_initial_load(self):
        widget = self.tabs.currentWidget()
        if isinstance(widget, QTabWidget):
            widget = widget.currentWidget()

        initial_load = getattr(widget, "ensure_initial_load", None)
        if callable(initial_load):
            initial_load()

    def open_tab(self, tab_name):
        aliases = {
            "Event Center": "Activity Log",
        }
        target = aliases.get(tab_name, tab_name)

        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == target:
                self.tabs.setCurrentIndex(index)
                self.run_visible_tab_initial_load()
                return

        for index in range(self.tabs.count()):
            group_tabs = self.tabs.widget(index)
            if not isinstance(group_tabs, QTabWidget):
                continue
            for child_index in range(group_tabs.count()):
                if group_tabs.tabText(child_index) == target:
                    self.tabs.setCurrentIndex(index)
                    group_tabs.setCurrentIndex(child_index)
                    self.run_visible_tab_initial_load()
                    return

    def apply_theme(self, theme):
        self.setStyleSheet(stylesheet_for_theme(theme))
        self.home_tab.refresh_update_status_style()

    def start_startup_update_check(self):
        if self.startup_update_check_running:
            return

        logger.info("Starting background update check.")
        self.startup_update_check_running = True
        self.home_tab.set_update_checking()
        self.start_background_task(
            fetch_update_info,
            self.on_startup_update_check_finished,
            self.on_startup_update_check_error,
            self.finish_startup_update_check,
        )

    def on_startup_update_check_finished(self, result):
        logger.info(
            "Update check finished: current=%s latest=%s available=%s asset=%s",
            result.current_version,
            result.latest_version,
            result.update_available,
            bool(result.asset_url),
        )
        self.home_tab.apply_update_check_result(result)
        self.settings_tab.apply_update_check_result(result, notify=False)

    def on_startup_update_check_error(self, exc):
        logger.warning("Startup update check failed: %s", exc)
        self.home_tab.apply_update_check_error(exc)
        self.settings_tab.apply_update_check_error(exc, show_popup=False, notify=False)

    def finish_startup_update_check(self):
        self.startup_update_check_running = False


class ThemeAwareTabBar(QTabBar):
    def paintEvent(self, _event):
        theme_key = get_current_theme_key()
        if theme_key not in {"windows_xp", "windows_xp_black"}:
            super().paintEvent(_event)
            return

        painter = QStylePainter(self)
        painter.setRenderHint(QStylePainter.Antialiasing, True)
        option = QStyleOptionTab()
        for index in range(self.count()):
            if index == 0:
                continue
            self.initStyleOption(option, index)
            painter.drawControl(QStyle.CE_TabBarTab, option)

        self.initStyleOption(option, 0)
        if self.currentIndex() == 0 and theme_key != "windows_xp_black":
            painter.drawControl(QStyle.CE_TabBarTab, option)
        else:
            self.draw_xp_start_tab(painter, option)

    def draw_xp_start_tab(self, painter, option):
        rect = option.rect.adjusted(0, 3, -1, -1)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.00, QColor("#B6FF9A"))
        gradient.setColorAt(0.16, QColor("#6FD643"))
        gradient.setColorAt(0.54, QColor("#43B72A"))
        gradient.setColorAt(1.00, QColor("#2B8F1B"))

        painter.save()
        painter.setPen(QColor("#1F7D18"))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 9, 9)
        painter.setPen(QColor("#D2FFBF"))
        painter.drawLine(rect.left() + 7, rect.top() + 1, rect.right() - 7, rect.top() + 1)
        painter.setPen(QColor("#176B14"))
        painter.drawLine(rect.left() + 5, rect.bottom(), rect.right() - 5, rect.bottom())
        painter.restore()

        label_option = QStyleOptionTab(option)
        label_option.palette.setColor(QPalette.WindowText, QColor("#FFFFFF"))
        label_option.palette.setColor(QPalette.ButtonText, QColor("#FFFFFF"))
        label_option.palette.setColor(QPalette.Text, QColor("#FFFFFF"))
        label_option.state |= QStyle.State_Raised
        painter.drawControl(QStyle.CE_TabBarTabLabel, label_option)


def run_app():
    configure_logging()
    install_exception_hook()
    logger.info(
        "Starting SC Intel Tool %s runtime=%s data_dir=%s database=%s",
        APP_VERSION,
        "packaged" if is_packaged_app() else "source",
        get_active_data_dir(),
        DB_PATH,
    )
    init_db()

    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
