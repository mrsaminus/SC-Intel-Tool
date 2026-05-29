from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.database import DB_PATH
from app.paths import get_user_data_dir, is_packaged_app
from app.update_checker import UpdateCheckError, check_for_updates as fetch_update_info
from app.updater import UpdateInstallError, download_update, start_update_installer
from app.version import APP_NAME, APP_VERSION, GITHUB_RELEASES_URL, GITHUB_REPOSITORY

from .workers import BackgroundTaskMixin


class SettingsTab(BackgroundTaskMixin, QWidget):
    def __init__(self):
        super().__init__()

        self.update_check_running = False
        self.update_install_running = False
        self.latest_release_url = GITHUB_RELEASES_URL
        self.latest_update_info = None

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_module_header(
            "Settings",
            "App version, update checks and local data paths.",
        ))
        layout.addWidget(self.build_about_card())
        layout.addWidget(self.build_updates_card())
        layout.addWidget(self.build_data_card())
        layout.addStretch(1)

        self.setLayout(layout)

    def build_about_card(self):
        card = self.create_card("ABOUT")
        layout = card.layout()

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        self.add_fact(grid, 0, "App", APP_NAME)
        self.add_fact(grid, 1, "Version", APP_VERSION)
        self.add_fact(grid, 2, "Repository", GITHUB_REPOSITORY)
        self.add_fact(grid, 3, "Runtime", "Packaged build" if is_packaged_app() else "Source / development")
        layout.addLayout(grid)
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

    def build_data_card(self):
        card = self.create_card("LOCAL DATA")
        layout = card.layout()

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        self.add_fact(grid, 0, "User Data Folder", str(get_user_data_dir()))
        self.add_fact(grid, 1, "Database", str(DB_PATH))
        layout.addLayout(grid)

        hint = QLabel(
            "Packaged builds store user data outside the app folder so notes and history survive updates."
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
        self.latest_release_url = result.release_url or GITHUB_RELEASES_URL
        if result.update_available:
            self.latest_update_info = result
            if result.asset_url:
                self.install_update_button.setEnabled(True)
                self.update_status_label.setText(
                    f"Update available: {result.latest_version}. "
                    f"Current version: {result.current_version}. Click Install Update to download, "
                    "replace this app and restart."
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
        if isinstance(exc, UpdateCheckError):
            message = str(exc)
        else:
            message = f"Update check failed: {exc}"

        self.update_status_label.setText(message)
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
            "SC Intel Tool will close and restart automatically.",
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

        self.update_status_label.setText("Update downloaded. Closing app so the updater can finish...")
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

    def open_releases_page(self):
        QDesktopServices.openUrl(QUrl(self.latest_release_url or GITHUB_RELEASES_URL))

    def open_data_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(get_user_data_dir())))

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
