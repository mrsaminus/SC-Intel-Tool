from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.database import DB_PATH
from app.cache_manager import (
    clear_all_cached_data,
    clear_cache_source,
    enumerate_cache_sources,
    recent_cache_operation_summaries,
    refresh_all_cache_sources as refresh_all_cache_sources_data,
    refresh_cache_source as refresh_cache_source_data,
)
from app.diagnostics import safe_diagnostics_text
from app.ocr.debug_capture import (
    clear_ocr_debug_captures,
    format_debug_size,
    get_ocr_debug_root,
    get_ocr_debug_summary,
    is_ocr_debug_enabled,
    set_ocr_debug_enabled,
)
from app.paths import get_active_data_dir, is_packaged_app
from app.update_checker import (
    UpdateCheckError,
    check_for_updates as fetch_update_info,
    is_newer_version,
)
from app.updater import UpdateInstallError, download_update, start_update_installer
from app.version import APP_NAME, APP_VERSION, GITHUB_RELEASES_URL, GITHUB_REPOSITORY

from .community_branding import AppLogoLabel, CommunityLogoLabel
from .safe_combobox import SafeComboBox as QComboBox
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
        self.cache_action_running = False
        self.cache_source_rows = {}
        self.cache_action_buttons = []

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_module_header(
            "Settings",
            "App version, update checks and local data paths.",
        ))
        layout.addWidget(self.build_about_card())
        layout.addWidget(self.build_appearance_card())
        layout.addWidget(self.build_ocr_settings_card())
        layout.addWidget(self.build_ocr_debug_card())
        layout.addWidget(self.build_updates_card())
        layout.addWidget(self.build_data_card())
        layout.addWidget(self.build_local_data_platform_card())
        layout.addStretch(1)

        content.setLayout(layout)
        scroll_area.setWidget(content)
        outer_layout.addWidget(scroll_area)
        self.settings_scroll_area = scroll_area
        self.settings_content = content
        self.setLayout(outer_layout)

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

        for label in (title, version, description, privacy, legal):
            self.configure_wrapping_label(label)

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
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(1, 0)
        self.add_fact(grid, 0, "Repository", GITHUB_REPOSITORY)
        self.add_fact(grid, 1, "Runtime", "Packaged build" if is_packaged_app() else "Source / development")
        layout.addLayout(grid)

        diagnostics_row = QHBoxLayout()
        self.copy_diagnostics_button = QPushButton("Copy Diagnostics")
        self.copy_diagnostics_button.clicked.connect(self.copy_diagnostics)
        diagnostics_hint = QLabel("Copies safe local version/path/runtime info for bug reports.")
        diagnostics_hint.setObjectName("moduleSubtitle")
        diagnostics_hint.setWordWrap(True)
        self.configure_wrapping_label(diagnostics_hint)
        diagnostics_row.addWidget(self.copy_diagnostics_button)
        diagnostics_row.addStretch(1)
        layout.addLayout(diagnostics_row)
        layout.addWidget(diagnostics_hint)
        return card

    def build_appearance_card(self):
        card = self.create_card("APPEARANCE")
        layout = card.layout()

        hint = QLabel(
            "Choose the app theme and text size. Appearance settings apply immediately and are stored locally."
        )
        hint.setObjectName("moduleSubtitle")
        hint.setWordWrap(True)
        self.configure_wrapping_label(hint)
        layout.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        theme_label = QLabel("Theme")
        theme_label.setObjectName("labelText")
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(160)
        self.theme_combo.setMinimumContentsLength(14)
        self.theme_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.theme_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

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
        self.text_size_combo.setMinimumWidth(140)
        self.text_size_combo.setMinimumContentsLength(10)
        self.text_size_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.text_size_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

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
        self.configure_wrapping_label(self.theme_status_label)

        grid.addWidget(theme_label, 0, 0)
        grid.addWidget(self.theme_combo, 0, 1)
        grid.addWidget(text_size_label, 1, 0)
        grid.addWidget(self.text_size_combo, 1, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        layout.addWidget(self.theme_status_label)
        return card

    def build_ocr_settings_card(self):
        card = self.create_card("OCR WORKFLOWS")
        layout = card.layout()

        hint = QLabel(
            "OCR is local-only and workflow-based. Technical OCR tuning is handled internally so normal users only "
            "need to choose regions inside the workflows that use OCR."
        )
        hint.setObjectName("moduleSubtitle")
        hint.setWordWrap(True)
        self.configure_wrapping_label(hint)
        layout.addWidget(hint)

        workflows = [
            (
                "Blueprint Reward Scanner",
                "Enable, select region, preview region and confirm detected rewards from BP Overview.",
            ),
            (
                "Hauling OCR",
                "Capture a selected contract region from the Hauling Operations Center when needed. Hotkey: Ctrl+Shift+H.",
            ),
        ]
        for title, description in workflows:
            title_label = QLabel(title)
            title_label.setObjectName("valueText")
            description_label = QLabel(description)
            description_label.setObjectName("moduleSubtitle")
            description_label.setWordWrap(True)
            self.configure_wrapping_label(description_label)
            layout.addWidget(title_label)
            layout.addWidget(description_label)

        self.ocr_settings_status_label = QLabel(
            "Internal OCR defaults: English text, automatic preprocessing, automatic thresholding and workflow-specific regions."
        )
        self.ocr_settings_status_label.setObjectName("moduleSubtitle")
        self.ocr_settings_status_label.setWordWrap(True)
        self.configure_wrapping_label(self.ocr_settings_status_label)
        layout.addWidget(self.ocr_settings_status_label)
        return card

    def build_ocr_debug_card(self):
        card = self.create_card("OCR DEBUG")
        layout = card.layout()

        warning = QLabel(
            "OCR debug captures are stored locally and may contain screen content from selected OCR regions. "
            "They are never uploaded and are not included in diagnostics unless you explicitly share them."
        )
        warning.setObjectName("moduleSubtitle")
        warning.setWordWrap(True)
        self.configure_wrapping_label(warning)
        layout.addWidget(warning)

        self.ocr_debug_enabled_checkbox = QCheckBox("Save OCR debug captures")
        self.ocr_debug_enabled_checkbox.setChecked(is_ocr_debug_enabled())
        self.ocr_debug_enabled_checkbox.toggled.connect(self.on_ocr_debug_enabled_changed)
        layout.addWidget(self.ocr_debug_enabled_checkbox)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(1, 0)
        self.ocr_debug_path_label = QLabel("")
        self.ocr_debug_path_label.setObjectName("valueText")
        self.ocr_debug_path_label.setWordWrap(True)
        self.ocr_debug_path_label.setTextInteractionFlags(
            self.ocr_debug_path_label.textInteractionFlags() | Qt.TextSelectableByMouse
        )
        self.configure_wrapping_label(self.ocr_debug_path_label)
        self.ocr_debug_count_label = QLabel("")
        self.ocr_debug_count_label.setObjectName("valueText")
        self.configure_wrapping_label(self.ocr_debug_count_label)

        path_title = QLabel("DEBUG FOLDER")
        path_title.setObjectName("labelText")
        count_title = QLabel("CAPTURES / DISK")
        count_title.setObjectName("labelText")
        grid.addWidget(path_title, 0, 0)
        grid.addWidget(self.ocr_debug_path_label, 0, 1)
        grid.addWidget(count_title, 1, 0)
        grid.addWidget(self.ocr_debug_count_label, 1, 1)
        layout.addLayout(grid)

        button_row = QVBoxLayout()
        button_row.setSpacing(8)
        self.open_ocr_debug_folder_button = QPushButton("Open OCR Debug Folder")
        self.clear_ocr_debug_button = QPushButton("Clear OCR Debug Captures")
        self.open_ocr_debug_folder_button.clicked.connect(self.open_ocr_debug_folder)
        self.clear_ocr_debug_button.clicked.connect(self.confirm_clear_ocr_debug_captures)
        for button in (self.open_ocr_debug_folder_button, self.clear_ocr_debug_button):
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button_row.addWidget(self.open_ocr_debug_folder_button)
        button_row.addWidget(self.clear_ocr_debug_button)
        layout.addLayout(button_row)

        self.ocr_debug_status_label = QLabel("")
        self.ocr_debug_status_label.setObjectName("moduleSubtitle")
        self.ocr_debug_status_label.setWordWrap(True)
        self.configure_wrapping_label(self.ocr_debug_status_label)
        layout.addWidget(self.ocr_debug_status_label)

        self.refresh_ocr_debug_status()
        return card

    def build_updates_card(self):
        card = self.create_card("UPDATES")
        layout = card.layout()

        self.update_status_label = QLabel(
            "Check GitHub Releases to see whether a newer build is available."
        )
        self.update_status_label.setObjectName("moduleSubtitle")
        self.update_status_label.setWordWrap(True)
        self.configure_wrapping_label(self.update_status_label)
        layout.addWidget(self.update_status_label)

        row = QVBoxLayout()
        row.setSpacing(8)
        self.check_updates_button = QPushButton("Check For Updates")
        self.install_update_button = QPushButton("Install Update")
        self.open_releases_button = QPushButton("Open Releases")
        for button in (self.check_updates_button, self.install_update_button, self.open_releases_button):
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.check_updates_button.clicked.connect(self.check_for_updates)
        self.install_update_button.clicked.connect(self.install_update)
        self.open_releases_button.clicked.connect(self.open_releases_page)
        self.install_update_button.setEnabled(False)
        row.addWidget(self.check_updates_button)
        row.addWidget(self.install_update_button)
        row.addWidget(self.open_releases_button)
        layout.addLayout(row)
        return card

    def build_data_card(self):
        card = self.create_card("LOCAL DATA")
        layout = card.layout()

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(1, 0)
        self.add_fact(grid, 0, "Active Data Folder", str(get_active_data_dir()))
        self.add_fact(grid, 1, "Active Database", str(DB_PATH))
        layout.addLayout(grid)

        hint = QLabel(
            "User data is stored outside the app folder by default so notes and history survive updates."
        )
        hint.setObjectName("moduleSubtitle")
        hint.setWordWrap(True)
        self.configure_wrapping_label(hint)
        layout.addWidget(hint)

        row = QHBoxLayout()
        self.open_data_folder_button = QPushButton("Open Data Folder")
        self.open_data_folder_button.clicked.connect(self.open_data_folder)
        row.addWidget(self.open_data_folder_button)
        row.addStretch(1)
        layout.addLayout(row)
        return card

    def build_local_data_platform_card(self):
        card = self.create_card("LOCAL DATA PLATFORM")
        layout = card.layout()

        hint = QLabel(
            "Cached external reference data is stored locally for faster reuse and better offline diagnostics."
        )
        hint.setObjectName("moduleSubtitle")
        hint.setWordWrap(True)
        self.configure_wrapping_label(hint)
        layout.addWidget(hint)

        self.cache_platform_status_label = QLabel("Cache metadata inspected locally. No sources refresh on startup.")
        self.cache_platform_status_label.setObjectName("moduleSubtitle")
        self.cache_platform_status_label.setWordWrap(True)
        self.configure_wrapping_label(self.cache_platform_status_label)
        layout.addWidget(self.cache_platform_status_label)

        self.cache_sources_layout = QVBoxLayout()
        self.cache_sources_layout.setSpacing(8)
        layout.addLayout(self.cache_sources_layout)

        action_row = QVBoxLayout()
        action_row.setSpacing(8)
        self.refresh_all_cache_button = QPushButton("Refresh All Sources")
        self.clear_all_cache_button = QPushButton("Clear All Cached Data")
        self.refresh_all_cache_button.clicked.connect(self.refresh_all_cache_sources)
        self.clear_all_cache_button.clicked.connect(self.confirm_clear_all_cached_data)
        for button in (self.refresh_all_cache_button, self.clear_all_cache_button):
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cache_action_buttons.extend((self.refresh_all_cache_button, self.clear_all_cache_button))
        action_row.addWidget(self.refresh_all_cache_button)
        action_row.addWidget(self.clear_all_cache_button)
        layout.addLayout(action_row)

        recent_title = QLabel("Recent Cache Activity")
        recent_title.setObjectName("valueText")
        layout.addWidget(recent_title)

        self.cache_operations_label = QLabel("No cache operations recorded yet.")
        self.cache_operations_label.setObjectName("moduleSubtitle")
        self.cache_operations_label.setWordWrap(True)
        self.configure_wrapping_label(self.cache_operations_label)
        layout.addWidget(self.cache_operations_label)

        self.rebuild_cache_source_rows()
        self.update_cache_recent_operations()
        return card

    def rebuild_cache_source_rows(self):
        while self.cache_sources_layout.count():
            item = self.cache_sources_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.cache_source_rows = {}
        self.cache_action_buttons = [
            self.refresh_all_cache_button,
            self.clear_all_cache_button,
        ]
        for info in enumerate_cache_sources():
            widget = self.create_cache_source_widget(info)
            self.cache_sources_layout.addWidget(widget)

    def create_cache_source_widget(self, info):
        row = QFrame()
        row.setObjectName("transparentPanel")
        row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        title = QLabel(info.name)
        title.setObjectName("valueText")
        description = QLabel(info.description)
        description.setObjectName("moduleSubtitle")
        description.setWordWrap(True)
        self.configure_wrapping_label(description)
        top_row.addWidget(title, 1)

        details = QLabel()
        details.setObjectName("moduleSubtitle")
        details.setWordWrap(True)
        self.configure_wrapping_label(details)

        button_row = QVBoxLayout()
        button_row.setSpacing(6)
        refresh_button = QPushButton("Refresh")
        clear_button = QPushButton("Clear")
        for button in (refresh_button, clear_button):
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        refresh_button.setEnabled(info.refresh_supported)
        clear_button.setEnabled(info.clear_supported)
        refresh_button.clicked.connect(lambda _checked=False, key=info.key: self.refresh_cache_source(key))
        clear_button.clicked.connect(lambda _checked=False, key=info.key: self.confirm_clear_cache_source(key))
        self.cache_action_buttons.extend((refresh_button, clear_button))
        button_row.addWidget(refresh_button)
        button_row.addWidget(clear_button)

        layout.addLayout(top_row)
        layout.addWidget(description)
        layout.addWidget(details)
        layout.addLayout(button_row)
        row.setLayout(layout)

        self.cache_source_rows[info.key] = {
            "details": details,
            "refresh": refresh_button,
            "clear": clear_button,
        }
        self.update_cache_source_row(info)
        return row

    def update_cache_source_rows(self):
        for info in enumerate_cache_sources():
            self.update_cache_source_row(info)

    def update_cache_source_row(self, info):
        row = self.cache_source_rows.get(info.key)
        if not row:
            return

        details = row["details"]
        details.setText(
            f"Status: {info.status} | Last Updated: {info.last_updated} | "
            f"Rows Cached: {info.row_count} | Cache Age: {info.age} | "
            f"Schema: {info.schema_version}\n"
            f"Last Success: {info.last_success} | Last Failure: {info.last_failure} | "
            f"Last Operation: {info.last_operation_status} | Last Refresh: {info.last_refresh_duration}"
        )
        error_text = info.last_error or info.error_message
        if error_text:
            details.setToolTip(error_text)
        else:
            details.setToolTip("")

    def update_cache_recent_operations(self):
        if not hasattr(self, "cache_operations_label"):
            return
        summaries = recent_cache_operation_summaries(limit=6)
        if not summaries:
            self.cache_operations_label.setText("No cache operations recorded yet.")
            return
        self.cache_operations_label.setText("\n".join(f"- {summary}" for summary in summaries))

    def refresh_cache_source(self, cache_key):
        if self.cache_action_running:
            return

        self.cache_action_running = True
        self.set_cache_action_buttons_enabled(False)
        self.cache_platform_status_label.setText("Refreshing cache source...")
        self.start_background_task(
            lambda: refresh_cache_source_data(cache_key),
            self.on_cache_source_refreshed,
            self.on_cache_action_error,
            self.finish_cache_action,
        )

    def refresh_all_cache_sources(self):
        if self.cache_action_running:
            return

        self.cache_action_running = True
        self.set_cache_action_buttons_enabled(False)
        self.cache_platform_status_label.setText("Refreshing all cache sources sequentially...")
        self.start_background_task(
            refresh_all_cache_sources_data,
            self.on_all_cache_sources_refreshed,
            self.on_cache_action_error,
            self.finish_cache_action,
        )

    def on_cache_source_refreshed(self, result):
        self.update_cache_source_rows()
        self.update_cache_recent_operations()
        self.cache_platform_status_label.setText(result.message)

    def on_all_cache_sources_refreshed(self, results):
        self.update_cache_source_rows()
        self.update_cache_recent_operations()
        failed = [result for result in results if not result.success]
        succeeded = len(results) - len(failed)
        self.cache_platform_status_label.setText(
            f"Refresh complete: {succeeded} succeeded, {len(failed)} failed."
        )

    def on_cache_action_error(self, exc):
        self.update_cache_source_rows()
        self.update_cache_recent_operations()
        self.cache_platform_status_label.setText(f"Cache action failed: {exc}")
        QMessageBox.warning(self, "Cache action failed", str(exc))

    def finish_cache_action(self):
        self.cache_action_running = False
        self.set_cache_action_buttons_enabled(True)

    def confirm_clear_cache_source(self, cache_key):
        if self.cache_action_running:
            return

        answer = QMessageBox.question(
            self,
            "Clear Cached Data",
            "Clear this cached external reference source?\n\n"
            "This does not delete notes, history, watchlists or user-created data.",
        )
        if answer != QMessageBox.Yes:
            return

        clear_cache_source(cache_key)
        self.update_cache_source_rows()
        self.update_cache_recent_operations()
        self.cache_platform_status_label.setText("Cached source cleared.")

    def confirm_clear_all_cached_data(self):
        if self.cache_action_running:
            return

        answer = QMessageBox.question(
            self,
            "Clear All Cached Data",
            "Clear all cached external reference data?\n\n"
            "This does not delete notes, history, watchlists or user-created data.",
        )
        if answer != QMessageBox.Yes:
            return

        clear_all_cached_data()
        self.update_cache_source_rows()
        self.update_cache_recent_operations()
        self.cache_platform_status_label.setText("All cached external reference data cleared.")

    def set_cache_action_buttons_enabled(self, enabled):
        for button in self.cache_action_buttons:
            button.setEnabled(enabled)

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

    def refresh_ocr_debug_status(self):
        if not hasattr(self, "ocr_debug_path_label"):
            return
        summary = get_ocr_debug_summary()
        debug_path = summary["path"]
        self.ocr_debug_path_label.setText(self.wrap_fact_value(debug_path))
        self.ocr_debug_path_label.setToolTip(str(debug_path))
        self.ocr_debug_count_label.setText(
            f"{summary['capture_count']} sessions | {format_debug_size(summary['disk_bytes'])}"
        )
        enabled_text = "enabled" if is_ocr_debug_enabled() else "disabled"
        self.ocr_debug_status_label.setText(
            f"OCR debug capture saving is {enabled_text}. Retention keeps the latest 50 sessions per workflow."
        )

    def on_ocr_debug_enabled_changed(self, enabled):
        set_ocr_debug_enabled(enabled)
        self.refresh_ocr_debug_status()

    def open_ocr_debug_folder(self):
        debug_path = get_ocr_debug_root(create=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(debug_path)))
        self.refresh_ocr_debug_status()

    def confirm_clear_ocr_debug_captures(self):
        answer = QMessageBox.question(
            self,
            "Clear OCR Debug Captures",
            "Clear all local OCR debug captures?\n\n"
            "This deletes saved OCR region screenshots and OCR text samples only. "
            "It does not delete notes, history, watchlists or cached reference data.",
        )
        if answer != QMessageBox.Yes:
            return

        removed = clear_ocr_debug_captures()
        self.refresh_ocr_debug_status()
        self.ocr_debug_status_label.setText(f"Cleared {removed} OCR debug capture session{'s' if removed != 1 else ''}.")

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
        self.configure_wrapping_label(title_label)
        self.configure_wrapping_label(subtitle_label)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        card.setLayout(layout)
        return card

    def create_card(self, title):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        self.configure_wrapping_label(title_label)
        layout.addWidget(title_label)
        card.setLayout(layout)
        return card

    def add_fact(self, layout, row, label, value):
        container = QWidget()
        container.setObjectName("transparentPanel")
        container.setMinimumWidth(0)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)

        label_widget = QLabel(label.upper())
        label_widget.setObjectName("labelText")
        label_widget.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        label_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        value_widget = QLabel(self.wrap_fact_value(value))
        value_widget.setObjectName("valueText")
        value_widget.setWordWrap(True)
        value_widget.setToolTip(str(value))
        value_widget.setMinimumWidth(0)
        value_widget.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.configure_wrapping_label(value_widget)
        value_widget.setTextInteractionFlags(value_widget.textInteractionFlags() | Qt.TextSelectableByMouse)

        container_layout.addWidget(label_widget)
        container_layout.addWidget(value_widget)
        container.setLayout(container_layout)
        layout.addWidget(container, row, 0, 1, 2)

    def configure_wrapping_label(self, label):
        label.setMinimumWidth(0)
        label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def wrap_fact_value(self, value):
        text = str(value)
        return (
            text.replace("\\", "\\\u200b")
            .replace("/", "/\u200b")
            .replace(":", ":\u200b")
            .replace("-", "-\u200b")
        )
