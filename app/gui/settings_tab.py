from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.database import DB_PATH, get_app_setting, set_app_setting
from app.diagnostics import safe_diagnostics_text
from app.paths import get_active_data_dir, is_packaged_app
from app.sc_trade_tools_client import (
    SC_TRADE_TOOLS_TOKEN_SETTING,
    SCTradeToolsError,
    test_token_connection,
)
from app.update_checker import (
    UpdateCheckError,
    check_for_updates as fetch_update_info,
    is_newer_version,
)
from app.updater import UpdateInstallError, download_update, start_update_installer
from app.version import APP_NAME, APP_VERSION, GITHUB_RELEASES_URL, GITHUB_REPOSITORY

from .community_branding import AppLogoLabel, CommunityLogoLabel
from .themes import (
    available_text_sizes,
    available_themes,
    get_current_text_size_key,
    get_current_text_size_label,
    get_current_theme,
    get_current_theme_key,
    set_current_text_size,
    set_current_theme,
)
from .workers import BackgroundTaskMixin


class SettingsTab(BackgroundTaskMixin, QWidget):
    def __init__(self, update_status_callback=None, update_error_callback=None, theme_changed_callback=None):
        super().__init__()

        self.update_status_callback = update_status_callback
        self.update_error_callback = update_error_callback
        self.theme_changed_callback = theme_changed_callback
        self.update_check_running = False
        self.update_install_running = False
        self.latest_release_url = GITHUB_RELEASES_URL
        self.latest_update_info = None
        self.loading_theme_combo = False
        self.loading_text_size_combo = False

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_module_header(
            "Settings",
            "App version, update checks and local data paths.",
        ))
        layout.addWidget(self.build_about_card())
        layout.addWidget(self.build_appearance_card())
        layout.addWidget(self.build_updates_card())
        layout.addWidget(self.build_data_card())
        layout.addStretch(1)

        self.setLayout(layout)

    def build_about_card(self):
        card = self.create_card("ABOUT SC INTEL TOOL")
        layout = card.layout()

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        version = QLabel(f"v{APP_VERSION}")
        version.setObjectName("valueText")
        description = QLabel("Community-made companion app for Star Citizen")
        description.setObjectName("valueText")
        description.setWordWrap(True)
        privacy = QLabel("No telemetry. No analytics. No tracking.")
        privacy.setObjectName("moduleSubtitle")
        privacy.setWordWrap(True)
        legal = QLabel(
            "Unofficial fan-made application. Not affiliated with Cloud Imperium Games. "
            "All trademarks belong to their respective owners."
        )
        legal.setObjectName("moduleSubtitle")
        legal.setWordWrap(True)

        text_layout.addWidget(title)
        text_layout.addWidget(version)
        text_layout.addWidget(description)
        text_layout.addWidget(privacy)
        text_layout.addWidget(legal)

        top_row.addWidget(AppLogoLabel(max_size=108, min_size=78), 0, Qt.AlignLeft | Qt.AlignTop)
        top_row.addLayout(text_layout, 1)
        top_row.addWidget(CommunityLogoLabel(max_size=56, min_size=40), 0, Qt.AlignRight | Qt.AlignTop)
        layout.addLayout(top_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        self.add_fact(grid, 0, "Repository", GITHUB_REPOSITORY)
        self.add_fact(grid, 1, "Runtime", "Packaged build" if is_packaged_app() else "Source / development")
        layout.addLayout(grid)

        diagnostics_row = QHBoxLayout()
        self.copy_diagnostics_button = QPushButton("Copy Diagnostics")
        self.copy_diagnostics_button.clicked.connect(self.copy_diagnostics)
        diagnostics_hint = QLabel("Copies safe local version/path/runtime info for bug reports.")
        diagnostics_hint.setObjectName("moduleSubtitle")
        diagnostics_hint.setWordWrap(True)
        diagnostics_row.addWidget(self.copy_diagnostics_button)
        diagnostics_row.addWidget(diagnostics_hint, 1)
        layout.addLayout(diagnostics_row)
        return card

    def build_appearance_card(self):
        card = self.create_card("APPEARANCE")
        layout = card.layout()

        hint = QLabel(
            "Choose the app theme and text size. Appearance settings apply immediately and are stored locally."
        )
        hint.setObjectName("moduleSubtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        theme_label = QLabel("Theme")
        theme_label.setObjectName("labelText")
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(240)

        self.loading_theme_combo = True
        current_key = get_current_theme_key()
        current_index = 0
        for index, theme in enumerate(available_themes()):
            self.theme_combo.addItem(f"{theme.category} - {theme.name}", theme.key)
            self.theme_combo.setItemData(index, theme.description, Qt.ToolTipRole)
            if theme.key == current_key:
                current_index = index
        self.theme_combo.setCurrentIndex(current_index)
        self.loading_theme_combo = False

        self.theme_combo.currentIndexChanged.connect(self.on_theme_selected)

        text_size_label = QLabel("Text Size")
        text_size_label.setObjectName("labelText")
        self.text_size_combo = QComboBox()
        self.text_size_combo.setMinimumWidth(180)

        self.loading_text_size_combo = True
        current_text_size = get_current_text_size_key()
        current_text_size_index = 0
        for index, (key, label) in enumerate(available_text_sizes()):
            self.text_size_combo.addItem(label, key)
            if key == current_text_size:
                current_text_size_index = index
        self.text_size_combo.setCurrentIndex(current_text_size_index)
        self.loading_text_size_combo = False

        self.text_size_combo.currentIndexChanged.connect(self.on_text_size_selected)
        self.theme_status_label = QLabel("Theme stored locally.")
        self.theme_status_label.setObjectName("moduleSubtitle")
        self.theme_status_label.setWordWrap(True)

        grid.addWidget(theme_label, 0, 0)
        grid.addWidget(self.theme_combo, 0, 1)
        grid.addWidget(text_size_label, 1, 0)
        grid.addWidget(self.text_size_combo, 1, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        layout.addWidget(self.theme_status_label)
        return card

    def build_updates_card(self):
        card = self.create_card("UPDATES")
        layout = card.layout()

        self.update_status_label = QLabel(
            "Check GitHub Releases to see whether a newer build is available."
        )
        self.update_status_label.setObjectName("moduleSubtitle")
        self.update_status_label.setWordWrap(True)
        layout.addWidget(self.update_status_label)

        row = QHBoxLayout()
        self.check_updates_button = QPushButton("Check For Updates")
        self.install_update_button = QPushButton("Install Update")
        self.open_releases_button = QPushButton("Open Releases")
        self.check_updates_button.clicked.connect(self.check_for_updates)
        self.install_update_button.clicked.connect(self.install_update)
        self.open_releases_button.clicked.connect(self.open_releases_page)
        self.install_update_button.setEnabled(False)
        row.addWidget(self.check_updates_button)
        row.addWidget(self.install_update_button)
        row.addWidget(self.open_releases_button)
        row.addStretch(1)
        layout.addLayout(row)
        return card

    def build_sc_trade_tools_card(self):
        card = self.create_card("SC TRADE TOOLS")
        layout = card.layout()

        hint = QLabel(
            "Optional local API token for SC Trade Tools workflows that require authentication. "
            "Leave empty to keep token-backed Trading subtabs disabled."
        )
        hint.setObjectName("moduleSubtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        row = QHBoxLayout()
        self.sc_trade_token_input = QLineEdit()
        self.sc_trade_token_input.setEchoMode(QLineEdit.Password)
        self.sc_trade_token_input.setPlaceholderText("SC Trade Tools API token (optional)")
        self.sc_trade_token_input.setText(get_app_setting(SC_TRADE_TOOLS_TOKEN_SETTING, ""))
        self.save_sc_trade_token_button = QPushButton("Save Token")
        self.test_sc_trade_token_button = QPushButton("Test Connection")
        self.save_sc_trade_token_button.clicked.connect(self.save_sc_trade_token)
        self.test_sc_trade_token_button.clicked.connect(self.test_sc_trade_token)
        row.addWidget(self.sc_trade_token_input, 1)
        row.addWidget(self.save_sc_trade_token_button)
        row.addWidget(self.test_sc_trade_token_button)
        layout.addLayout(row)

        self.sc_trade_token_status_label = QLabel("Not configured")
        self.sc_trade_token_status_label.setObjectName("moduleSubtitle")
        layout.addWidget(self.sc_trade_token_status_label)
        self.update_sc_trade_token_status()
        return card

    def build_data_card(self):
        card = self.create_card("LOCAL DATA")
        layout = card.layout()

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        self.add_fact(grid, 0, "Active Data Folder", str(get_active_data_dir()))
        self.add_fact(grid, 1, "Active Database", str(DB_PATH))
        layout.addLayout(grid)

        hint = QLabel(
            "User data is stored outside the app folder by default so notes and history survive updates."
        )
        hint.setObjectName("moduleSubtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        row = QHBoxLayout()
        self.open_data_folder_button = QPushButton("Open Data Folder")
        self.open_data_folder_button.clicked.connect(self.open_data_folder)
        row.addWidget(self.open_data_folder_button)
        row.addStretch(1)
        layout.addLayout(row)
        return card

    def on_theme_selected(self):
        if self.loading_theme_combo:
            return
        theme_key = self.theme_combo.currentData()
        theme = set_current_theme(theme_key)
        if self.theme_changed_callback:
            self.theme_changed_callback(theme)
        self.theme_status_label.setText(f"Active theme: {theme.name}. Stored locally.")

    def on_text_size_selected(self):
        if self.loading_text_size_combo:
            return
        set_current_text_size(self.text_size_combo.currentData())
        if self.theme_changed_callback:
            self.theme_changed_callback(get_current_theme())
        self.theme_status_label.setText(f"Text size: {get_current_text_size_label()}. Stored locally.")

    def check_for_updates(self):
        if self.update_check_running:
            return

        self.update_check_running = True
        self.latest_update_info = None
        self.check_updates_button.setEnabled(False)
        self.install_update_button.setEnabled(False)
        self.check_updates_button.setText("Checking...")
        self.update_status_label.setText("Checking latest GitHub Release...")

        self.start_background_task(
            fetch_update_info,
            self.on_update_check_finished,
            self.on_update_check_error,
            self.finish_update_check,
        )

    def on_update_check_finished(self, result):
        self.apply_update_check_result(result)

    def apply_update_check_result(self, result, notify=True):
        self.latest_release_url = result.release_url or GITHUB_RELEASES_URL
        if notify and self.update_status_callback:
            self.update_status_callback(result)

        update_available = result.update_available or is_newer_version(
            result.latest_version,
            result.current_version,
        )
        if update_available:
            self.latest_update_info = result
            if result.asset_url:
                self.install_update_button.setEnabled(True)
                self.update_status_label.setText(
                    f"Update available: {result.latest_version}. "
                    f"Current version: {result.current_version}. Click Install Update to download, "
                    "replace this app. When the installer finishes, start SC-Intel-Tool.exe manually."
                )
            else:
                self.update_status_label.setText(
                    f"Update available: {result.latest_version}, but no Windows executable was found. "
                    "Open Releases to download it manually."
                )
            return

        self.latest_update_info = None
        self.install_update_button.setEnabled(False)
        self.update_status_label.setText(
            f"No newer release found. Current version: {result.current_version}; "
            f"latest release: {result.latest_version}."
        )

    def on_update_check_error(self, exc):
        self.apply_update_check_error(exc)

    def apply_update_check_error(self, exc, show_popup=True, notify=True):
        if isinstance(exc, UpdateCheckError):
            message = str(exc)
        else:
            message = f"Update check failed: {exc}"

        self.update_status_label.setText(message)
        if notify and self.update_error_callback:
            self.update_error_callback(exc)
        if show_popup:
            QMessageBox.warning(self, "Update check failed", message)

    def finish_update_check(self):
        self.update_check_running = False
        self.check_updates_button.setEnabled(True)
        self.check_updates_button.setText("Check For Updates")

    def install_update(self):
        if self.update_install_running or not self.latest_update_info:
            return

        if not is_packaged_app():
            QMessageBox.information(
                self,
                "Automatic install unavailable",
                "Automatic install is only available in packaged Windows builds. "
                "For source/development runs, update with git or download from Releases.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Install update",
            f"Download and install {self.latest_update_info.latest_version}? "
            "SC Intel Tool will close so the updater can replace it. "
            "When the installer finishes, start SC-Intel-Tool.exe manually.",
        )
        if answer != QMessageBox.Yes:
            return

        self.update_install_running = True
        self.check_updates_button.setEnabled(False)
        self.install_update_button.setEnabled(False)
        self.open_releases_button.setEnabled(False)
        self.install_update_button.setText("Installing...")
        self.update_status_label.setText("Downloading update...")

        update_info = self.latest_update_info
        self.start_background_task(
            lambda: download_update(update_info),
            self.on_update_downloaded,
            self.on_update_install_error,
            self.finish_update_install,
        )

    def on_update_downloaded(self, downloaded_update):
        try:
            start_update_installer(downloaded_update)
        except UpdateInstallError as exc:
            self.on_update_install_error(exc)
            return

        self.update_status_label.setText(
            "Update downloaded. Closing app so the updater can finish. "
            "Start SC-Intel-Tool.exe manually when the installer completes."
        )
        app = QApplication.instance()
        if app:
            app.quit()

    def on_update_install_error(self, exc):
        message = str(exc) if isinstance(exc, UpdateInstallError) else f"Update install failed: {exc}"
        self.update_status_label.setText(message)
        QMessageBox.warning(self, "Update install failed", message)

    def finish_update_install(self):
        self.update_install_running = False
        self.check_updates_button.setEnabled(True)
        self.open_releases_button.setEnabled(True)
        self.install_update_button.setText("Install Update")
        self.install_update_button.setEnabled(bool(self.latest_update_info and self.latest_update_info.asset_url))

    def save_sc_trade_token(self):
        set_app_setting(SC_TRADE_TOOLS_TOKEN_SETTING, self.sc_trade_token_input.text().strip())
        self.update_sc_trade_token_status()

    def update_sc_trade_token_status(self):
        token = self.sc_trade_token_input.text().strip()
        if not token:
            self.sc_trade_token_status_label.setText("Not configured")
        else:
            self.sc_trade_token_status_label.setText("Token saved locally. Connection not tested.")

    def test_sc_trade_token(self):
        token = self.sc_trade_token_input.text().strip()
        set_app_setting(SC_TRADE_TOOLS_TOKEN_SETTING, token)
        if not token:
            self.sc_trade_token_status_label.setText("Not configured")
            return

        self.test_sc_trade_token_button.setEnabled(False)
        self.test_sc_trade_token_button.setText("Testing...")
        self.sc_trade_token_status_label.setText("Testing SC Trade Tools connection...")
        self.start_background_task(
            lambda: test_token_connection(token),
            self.on_sc_trade_token_tested,
            self.on_sc_trade_token_error,
            self.finish_sc_trade_token_test,
        )

    def on_sc_trade_token_tested(self, connected):
        if connected:
            self.sc_trade_token_status_label.setText("Connected")
        else:
            self.sc_trade_token_status_label.setText("Invalid")

    def on_sc_trade_token_error(self, exc):
        if isinstance(exc, SCTradeToolsError):
            self.sc_trade_token_status_label.setText(f"Invalid: {exc}")
        else:
            self.sc_trade_token_status_label.setText(f"Connection failed: {exc}")

    def finish_sc_trade_token_test(self):
        self.test_sc_trade_token_button.setEnabled(True)
        self.test_sc_trade_token_button.setText("Test Connection")

    def copy_diagnostics(self):
        QApplication.clipboard().setText(safe_diagnostics_text(database_path=DB_PATH))
        QMessageBox.information(
            self,
            "Diagnostics copied",
            "Safe diagnostics were copied to the clipboard. They include version, runtime, paths and asset status only.",
        )

    def open_releases_page(self):
        QDesktopServices.openUrl(QUrl(self.latest_release_url or GITHUB_RELEASES_URL))

    def open_data_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(get_active_data_dir())))

    def create_module_header(self, title, subtitle):
        card = QFrame()
        card.setObjectName("playerCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("moduleHeading")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("moduleSubtitle")
        subtitle_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        card.setLayout(layout)
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

    def add_fact(self, layout, row, label, value):
        label_widget = QLabel(label.upper())
        label_widget.setObjectName("labelText")
        value_widget = QLabel(str(value))
        value_widget.setObjectName("valueText")
        value_widget.setWordWrap(True)
        value_widget.setTextInteractionFlags(value_widget.textInteractionFlags() | Qt.TextSelectableByMouse)

        layout.addWidget(label_widget, row, 0)
        layout.addWidget(value_widget, row, 1)
