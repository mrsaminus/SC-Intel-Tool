import logging

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database import get_app_setting
from app.event_center.service import record_event
from app.hauling import (
    CONTRACT_STATE_DELIVERED,
    CONTRACT_STATE_LOADED,
    CONTRACT_STATE_PLANNED,
    SESSION_STATUS_ARCHIVED,
    SESSION_STATUS_COMPLETED,
    HaulingContractParser,
    archive_session,
    build_manifest,
    capacity_status_text,
    group_by_destination,
    group_by_pickup,
    group_by_route,
    group_summary,
    list_sessions,
    load_session,
    save_session,
    toggle_delivered_state,
    toggle_loaded_state,
)
from app.ocr import (
    HAULING_CONTRACTS_PROFILE_KEY,
    REWARD_SCANNER_PROFILE_KEY,
    HaulingContractsOCRParser,
    OCRProfileManager,
    OCRRegion,
    OCRService,
)
from app.ocr.workers import create_ocr_worker

from .sortable_table_item import SORT_ROLE, SortableTableWidgetItem
from .responsive import ResponsiveStack, install_scroll_area, stabilize_card, stabilize_table
from .table_utils import configure_readable_table_columns
from .trading.ship_selection import configure_ship_combo, selected_ship_name
from .workers import BackgroundTaskMixin


logger = logging.getLogger(__name__)

HAULING_REGION_NAME = "Hauling Contracts"
REWARD_SCANNER_REGION_NAME = "Reward Scanner"
LEGACY_REWARD_REGION_SETTING_KEY = "bp_reward_scanner_region"
CONTRACT_ID_ROLE = Qt.UserRole + 25
SESSION_ID_ROLE = Qt.UserRole + 26


class HaulingTab(BackgroundTaskMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.parser = HaulingContractParser()
        self.parse_result = None
        self.contracts = ()
        self.manifest = build_manifest(())
        self.ocr_profile_manager = OCRProfileManager()
        self.ocr_service = OCRService(settings=self.current_ocr_profile().to_settings())
        self.ocr_capture_running = False
        self.ocr_capture_request_id = 0
        self.manifest_started_logged = False
        self.manifest_completed_logged = False
        self.current_session_id = None
        self.current_session_status = "unsaved"

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self.create_header())
        layout.addWidget(self.create_status_line())
        layout.addWidget(self.create_session_card())

        self.intake_stack = ResponsiveStack(breakpoint_width=1080, spacing=12)
        self.intake_stack.addWidget(self.create_manual_input_card(), 3)
        self.intake_stack.addWidget(self.create_capacity_card(), 2)
        layout.addWidget(self.intake_stack)

        layout.addWidget(self.create_operations_dashboard())
        layout.addWidget(self.create_manifest_preview(), 1)
        self.hauling_scroll_area = install_scroll_area(self, content)

        self.update_manifest()
        self.refresh_session_history()

    def create_header(self):
        header = QFrame()
        header.setObjectName("playerCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title = QLabel("Hauling Operations Center")
        title.setObjectName("moduleHeading")
        subtitle = QLabel("Plan hauling contracts, cargo capacity and delivery manifests.")
        subtitle.setObjectName("moduleSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        header.setLayout(layout)
        return header

    def create_status_line(self):
        self.status_label = QLabel("Paste hauling contract text, then parse it into a local manifest.")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        return self.status_label

    def create_session_card(self):
        card = self.create_card("MANIFEST SESSION")
        layout = card.layout()

        controls = QHBoxLayout()
        controls.setSpacing(8)
        name_label = QLabel("Session Name")
        name_label.setObjectName("labelText")
        self.session_name_input = QLineEdit()
        self.session_name_input.setPlaceholderText("Hauling Session")
        self.session_status_label = QLabel("Current session: Unsaved")
        self.session_status_label.setObjectName("moduleSubtitle")
        self.session_status_label.setWordWrap(True)
        controls.addWidget(name_label)
        controls.addWidget(self.session_name_input, 2)
        controls.addWidget(self.session_status_label, 1)
        layout.addLayout(controls)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.new_session_button = QPushButton("New Session")
        self.save_session_button = QPushButton("Save Session")
        self.load_session_button = QPushButton("Load Session")
        self.archive_session_button = QPushButton("Archive Session")
        self.new_session_button.clicked.connect(lambda _checked=False: self.new_session())
        self.save_session_button.clicked.connect(lambda _checked=False: self.save_current_session())
        self.load_session_button.clicked.connect(lambda _checked=False: self.load_selected_session())
        self.archive_session_button.clicked.connect(lambda _checked=False: self.archive_selected_session())
        buttons.addWidget(self.new_session_button)
        buttons.addWidget(self.save_session_button)
        buttons.addWidget(self.load_session_button)
        buttons.addWidget(self.archive_session_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.session_history_table = self.create_table([
            "Status",
            "Session",
            "Ship",
            "Total SCU",
            "Progress",
            "Updated",
        ])
        self.session_history_table.setMinimumHeight(150)
        layout.addWidget(self.session_history_table)
        return card

    def create_manual_input_card(self):
        card = self.create_card("MANUAL CONTRACT TEXT")
        layout = card.layout()

        self.contract_text = QTextEdit()
        self.contract_text.setPlaceholderText(
            "Paste hauling contract or OCR text here.\n\n"
            "Example:\n"
            "Pick up: Checkmate\n"
            "Deliver to: Teasa Spaceport\n"
            "Commodity: Construction Materials\n"
            "Quantity: 32 SCU"
        )
        self.contract_text.setMinimumHeight(170)
        layout.addWidget(self.contract_text, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.parse_button = QPushButton("Parse Contracts")
        self.capture_ocr_button = QPushButton("Capture Contracts (OCR)")
        self.clear_button = QPushButton("Clear Input")
        self.copy_manifest_button = QPushButton("Copy Manifest")
        self.parse_button.clicked.connect(self.parse_contracts)
        self.capture_ocr_button.clicked.connect(self.capture_contracts_ocr)
        self.clear_button.clicked.connect(self.clear_input)
        self.copy_manifest_button.clicked.connect(self.copy_manifest)
        button_row.addWidget(self.parse_button)
        button_row.addWidget(self.capture_ocr_button)
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.copy_manifest_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        return card

    def create_capacity_card(self):
        card = self.create_card("SHIP & CAPACITY")
        layout = card.layout()

        self.ship_combo = QComboBox()
        configure_ship_combo(self.ship_combo)
        self.ship_combo.currentTextChanged.connect(self.on_ship_changed)
        layout.addWidget(self.ship_combo)

        self.capacity_label = QLabel()
        self.capacity_label.setObjectName("valueText")
        self.capacity_label.setWordWrap(True)
        self.total_scu_label = QLabel()
        self.total_scu_label.setObjectName("valueText")
        self.total_scu_label.setWordWrap(True)
        self.remaining_scu_label = QLabel()
        self.remaining_scu_label.setObjectName("valueText")
        self.remaining_scu_label.setWordWrap(True)
        self.capacity_warning_label = QLabel()
        self.capacity_warning_label.setObjectName("moduleSubtitle")
        self.capacity_warning_label.setWordWrap(True)

        layout.addWidget(self.capacity_label)
        layout.addWidget(self.total_scu_label)
        layout.addWidget(self.remaining_scu_label)
        layout.addWidget(self.capacity_warning_label)
        layout.addStretch(1)
        return card

    def create_operations_dashboard(self):
        card = self.create_card("CARGO OPERATIONS")
        card.setMinimumHeight(180)
        layout = card.layout()

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)

        self.dashboard_labels = {}
        rows = [
            ("selected_ship", "Selected Ship"),
            ("ship_capacity", "Ship Capacity"),
            ("loaded_scu", "Current Loaded SCU"),
            ("remaining_capacity", "Remaining Capacity"),
            ("total_contracts", "Total Contracts"),
            ("planned_contracts", "Planned"),
            ("loaded_contracts", "Loaded"),
            ("delivered_contracts", "Delivered"),
            ("capacity_status", "Capacity Status"),
        ]
        for index, (key, label) in enumerate(rows):
            row = index // 3
            column = (index % 3) * 2
            label_widget = QLabel(label)
            label_widget.setObjectName("labelText")
            label_widget.setWordWrap(True)
            value_widget = QLabel("N/A")
            value_widget.setObjectName("valueText")
            value_widget.setWordWrap(True)
            grid.addWidget(label_widget, row, column)
            grid.addWidget(value_widget, row, column + 1)
            self.dashboard_labels[key] = value_widget

        layout.addLayout(grid)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)
        progress_label = QLabel("Progress")
        progress_label.setObjectName("labelText")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_detail_label = QLabel("0% complete")
        self.progress_detail_label.setObjectName("moduleSubtitle")
        self.progress_detail_label.setWordWrap(True)
        progress_row.addWidget(progress_label)
        progress_row.addWidget(self.progress_bar, 1)
        progress_row.addWidget(self.progress_detail_label)
        layout.addLayout(progress_row)
        return card

    def create_manifest_preview(self):
        card = self.create_card("MANIFEST PREVIEW")
        layout = card.layout()

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.toggle_loaded_button = QPushButton("Load Cargo")
        self.toggle_delivered_button = QPushButton("Mark Delivered")
        self.toggle_loaded_button.clicked.connect(self.toggle_selected_loaded)
        self.toggle_delivered_button.clicked.connect(self.toggle_selected_delivered)
        action_hint = QLabel("Select a contract row, then update its cargo state.")
        action_hint.setObjectName("moduleSubtitle")
        action_hint.setWordWrap(True)
        action_row.addWidget(self.toggle_loaded_button)
        action_row.addWidget(self.toggle_delivered_button)
        action_row.addWidget(action_hint, 1)
        layout.addLayout(action_row)

        self.preview_tabs = QTabWidget()
        self.contracts_table = self.create_table([
            "Status",
            "Pickup",
            "Delivery",
            "Commodity",
            "SCU",
            "Reward",
            "Confidence",
            "Warnings",
        ])
        self.contracts_table.itemSelectionChanged.connect(self.update_contract_action_state)
        self.pickup_table = self.create_table([
            "Pickup",
            "Total SCU",
            "Remaining SCU",
            "Delivered SCU",
            "Remaining",
            "Delivered",
            "Commodities",
        ])
        self.destination_table = self.create_table([
            "Destination",
            "Total SCU",
            "Remaining SCU",
            "Delivered SCU",
            "Remaining",
            "Delivered",
            "Commodities",
        ])
        self.route_table = self.create_table([
            "Route",
            "Total SCU",
            "Remaining SCU",
            "Delivered SCU",
            "Remaining",
            "Delivered",
            "Commodities",
        ])
        self.warnings_text = QTextEdit()
        self.warnings_text.setReadOnly(True)
        self.warnings_text.setMinimumHeight(180)
        self.warnings_text.setPlaceholderText("Warnings and parser notes will appear here.")

        self.preview_tabs.addTab(self.contracts_table, "Contracts")
        self.preview_tabs.addTab(self.pickup_table, "By Pickup")
        self.preview_tabs.addTab(self.destination_table, "By Destination")
        self.preview_tabs.addTab(self.route_table, "By Route")
        self.preview_tabs.addTab(self.warnings_text, "Warnings")
        self.preview_tabs.setMinimumHeight(320)
        layout.addWidget(self.preview_tabs, 1)
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
        return stabilize_card(card)

    def create_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        configure_readable_table_columns(table, min_width=110, max_width=360, stretch_last=True)
        return stabilize_table(table, minimum_height=190)

    def parse_contracts(self):
        text = self.contract_text.toPlainText()
        self.apply_parse_result(self.parser.parse(text))
        if self.contracts:
            self.status_label.setText(
                f"Parsed {len(self.contracts)} contract candidate"
                f"{'s' if len(self.contracts) != 1 else ''} into the manifest."
            )
        else:
            self.status_label.setText("No hauling contracts parsed. Check the pasted text and try again.")

    def apply_parse_result(self, parse_result):
        self.parse_result = parse_result
        self.contracts = self.parse_result.contracts
        self.manifest_started_logged = False
        self.manifest_completed_logged = False
        self.update_manifest()
        self.record_manifest_started()

    def clear_input(self):
        self.contract_text.clear()
        self.parse_result = None
        self.contracts = ()
        self.manifest_started_logged = False
        self.manifest_completed_logged = False
        self.update_manifest()
        self.status_label.setText("Input cleared. Paste hauling contract text to build a manifest.")

    def new_session(self):
        self.current_session_id = None
        self.current_session_status = "unsaved"
        self.session_name_input.clear()
        self.contract_text.clear()
        self.parse_result = None
        self.contracts = ()
        self.manifest_started_logged = False
        self.manifest_completed_logged = False
        self.update_manifest()
        self.update_session_status_label()
        self.status_label.setText("New hauling session started. Parse or capture contracts to begin.")

    def save_current_session(self):
        if not self.contracts:
            self.status_label.setText("No hauling contracts to save. Parse or capture contracts first.")
            return
        previous_status = self.current_session_status
        session = save_session(
            self.session_name_input.text(),
            self.manifest,
            session_id=self.current_session_id,
            notes="",
        )
        self.current_session_id = session.id
        self.current_session_status = session.status
        self.session_name_input.setText(session.name)
        self.update_session_status_label()
        self.refresh_session_history(select_session_id=session.id)
        self.record_session_event("hauling_session_saved", "Hauling session saved.", session)
        if session.status == SESSION_STATUS_COMPLETED and previous_status != SESSION_STATUS_COMPLETED:
            self.record_session_event("hauling_session_completed", "Hauling session completed.", session)
        self.status_label.setText(f"Session saved locally: {session.name}.")

    def load_selected_session(self):
        session_id = self.selected_session_id()
        if not session_id:
            self.status_label.setText("Select a saved session to load.")
            return
        session = load_session(session_id)
        if not session:
            self.status_label.setText("Selected session could not be loaded.")
            self.refresh_session_history()
            return
        self.apply_session(session)
        self.record_session_event("hauling_session_loaded", "Hauling session loaded.", session)
        self.status_label.setText(f"Loaded hauling session: {session.name}.")

    def archive_selected_session(self, confirm=True):
        session_id = self.selected_session_id() or self.current_session_id
        if not session_id:
            self.status_label.setText("Select a saved session to archive.")
            return
        session = load_session(session_id)
        if not session:
            self.status_label.setText("Selected session could not be archived.")
            self.refresh_session_history()
            return
        if confirm:
            response = QMessageBox.question(
                self,
                "Archive Hauling Session",
                f"Archive the hauling session '{session.name}'? It will remain local and can still be loaded.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if response != QMessageBox.Yes:
                return
        archive_session(session_id)
        archived = load_session(session_id) or session
        self.record_session_event("hauling_session_archived", "Hauling session archived.", archived)
        if self.current_session_id == session_id:
            self.current_session_status = SESSION_STATUS_ARCHIVED
            self.update_session_status_label()
        self.refresh_session_history(select_session_id=session_id)
        self.status_label.setText(f"Session archived locally: {session.name}.")

    def apply_session(self, session):
        self.current_session_id = session.id
        self.current_session_status = session.status
        self.session_name_input.setText(session.name)
        if session.selected_ship:
            self.ship_combo.setCurrentText(session.selected_ship)
        self.contract_text.clear()
        self.parse_result = None
        self.contracts = session.manifest.contracts
        self.manifest_started_logged = bool(self.contracts)
        self.manifest_completed_logged = bool(
            self.contracts and session.manifest.delivered_contracts == len(session.manifest.contracts)
        )
        self.update_manifest()
        self.update_session_status_label()
        self.refresh_session_history(select_session_id=session.id)

    def selected_session_id(self):
        row = self.session_history_table.currentRow()
        if row < 0:
            return None
        item = self.session_history_table.item(row, 0)
        if not item:
            return None
        return item.data(SESSION_ID_ROLE)

    def refresh_session_history(self, select_session_id=None):
        sessions = list_sessions(include_archived=True)
        table = self.session_history_table
        table.setSortingEnabled(False)
        table.setRowCount(len(sessions))
        selected_row = -1
        for row, session in enumerate(sessions):
            values = [
                session.status.title(),
                session.name,
                session.selected_ship or "N/A",
                format_number(session.total_scu),
                f"{format_number(session.completion_percentage)}%",
                session.updated_at,
            ]
            sort_values = [
                session.status,
                session.name,
                session.selected_ship,
                session.total_scu,
                session.completion_percentage,
                session.updated_at,
            ]
            for column, value in enumerate(values):
                item = table_item(value, sort_values[column])
                item.setData(SESSION_ID_ROLE, session.id)
                table.setItem(row, column, item)
            if select_session_id and session.id == select_session_id:
                selected_row = row
        table.setSortingEnabled(True)
        configure_readable_table_columns(table, min_width=100, max_width=300, stretch_last=True)
        if selected_row >= 0:
            table.setCurrentCell(selected_row, 0)

    def update_session_status_label(self):
        if self.current_session_id:
            self.session_status_label.setText(
                f"Current session: #{self.current_session_id} / {str(self.current_session_status).title()}"
            )
        else:
            self.session_status_label.setText("Current session: Unsaved")

    def on_ship_changed(self):
        self.update_manifest()

    def current_ocr_profile(self):
        return self.ocr_profile_manager.get_profile(HAULING_CONTRACTS_PROFILE_KEY)

    def ocr_region(self):
        region = self.ocr_profile_manager.get_region(HAULING_CONTRACTS_PROFILE_KEY, HAULING_REGION_NAME)
        if region and region.is_valid():
            return region

        fallback = self.ocr_profile_manager.get_region(REWARD_SCANNER_PROFILE_KEY, REWARD_SCANNER_REGION_NAME)
        if fallback and fallback.is_valid():
            return OCRRegion.from_tuple(
                fallback.to_tuple(),
                name=HAULING_REGION_NAME,
                profile=HAULING_CONTRACTS_PROFILE_KEY,
                monitor=fallback.monitor,
                resolution=fallback.resolution,
                description="Hauling contract OCR capture region copied from the saved Reward Scanner region.",
            )

        legacy_region = legacy_reward_region()
        if legacy_region:
            return OCRRegion.from_tuple(
                legacy_region,
                name=HAULING_REGION_NAME,
                profile=HAULING_CONTRACTS_PROFILE_KEY,
                description="Hauling contract OCR capture region copied from legacy Reward Scanner coordinates.",
            )
        return None

    def capture_contracts_ocr(self):
        if self.ocr_capture_running:
            self.status_label.setText("OCR capture already running. Wait for the current scan to finish.")
            return

        region = self.ocr_region()
        if not region:
            self.status_label.setText(
                "No OCR capture region saved. Save a local OCR region first, or paste contract text manually."
            )
            return

        self.ocr_capture_running = True
        self.ocr_capture_request_id += 1
        request_id = self.ocr_capture_request_id
        profile = self.current_ocr_profile()
        parser = HaulingContractsOCRParser(self.parser)
        worker = create_ocr_worker(
            self.ocr_service,
            region,
            parser=parser,
            profile=profile,
        )

        self.capture_ocr_button.setEnabled(False)
        self.capture_ocr_button.setText("Capturing...")
        self.status_label.setText("Capturing selected region and running local OCR for hauling contracts...")
        self.start_ocr_worker(
            worker,
            lambda result, current_request=request_id: self.on_ocr_capture_result(current_request, result),
            lambda exc, current_request=request_id: self.on_ocr_capture_error(current_request, exc),
            lambda current_request=request_id: self.finish_ocr_capture(current_request),
        )

    def start_ocr_worker(self, worker, on_result=None, on_error=None, on_finished=None):
        if not hasattr(self, "_background_workers"):
            self._background_workers = set()
        self._background_workers.add(worker)
        if on_result:
            worker.signals.result.connect(on_result)
        if on_error:
            worker.signals.error.connect(on_error)
        if on_finished:
            worker.signals.finished.connect(on_finished)
        worker.signals.finished.connect(lambda completed=worker: self._background_workers.discard(completed))
        QThreadPool.globalInstance().start(worker)
        return worker

    def on_ocr_capture_result(self, request_id, result):
        if request_id != self.ocr_capture_request_id:
            return

        status = getattr(result, "status", "")
        if status == "capture_error":
            self.status_label.setText(f"OCR capture failed locally: {getattr(result, 'message', '')}")
            return
        if status == "missing_ocr":
            self.status_label.setText(
                "No local OCR engine is available. Paste hauling contract text manually and click Parse Contracts."
            )
            return
        if status == "ocr_error":
            self.status_label.setText(f"OCR failed locally: {getattr(result, 'message', '')}")
            return
        if status == "parse_error":
            self.status_label.setText(f"OCR text parsing failed locally: {getattr(result, 'message', '')}")
            return

        ocr_result = getattr(result, "ocr_result", None)
        text = getattr(ocr_result, "text", "") if ocr_result else ""
        self.contract_text.setPlainText(text)

        parsed_result = getattr(result, "parsed_result", None)
        parse_result = getattr(parsed_result, "data", None)
        if parse_result is None:
            parse_result = self.parser.parse(text)
        self.apply_parse_result(parse_result)
        self.record_ocr_scan_event(status or "ok")

        if not str(text or "").strip():
            self.status_label.setText("OCR completed, but no text was detected in the selected region.")
        elif self.contracts:
            self.status_label.setText(
                f"OCR captured and parsed {len(self.contracts)} contract candidate"
                f"{'s' if len(self.contracts) != 1 else ''} into the manifest."
            )
        else:
            self.status_label.setText("OCR captured text, but no hauling contracts were parsed.")

    def on_ocr_capture_error(self, request_id, exc):
        if request_id != self.ocr_capture_request_id:
            return
        self.status_label.setText(f"OCR capture failed locally: {exc}")

    def finish_ocr_capture(self, request_id):
        if request_id != self.ocr_capture_request_id:
            return
        self.ocr_capture_running = False
        self.capture_ocr_button.setEnabled(True)
        self.capture_ocr_button.setText("Capture Contracts (OCR)")

    def record_ocr_scan_event(self, status):
        try:
            record_event(
                category="Hauling",
                source="Hauling Operations Center",
                entity_name="Hauling OCR Scan",
                event_type="hauling_ocr_scan",
                message=f"Hauling OCR scan parsed {len(self.contracts)} contract candidate"
                f"{'s' if len(self.contracts) != 1 else ''}.",
                metadata={
                    "status": status,
                    "contract_count": len(self.contracts),
                    "total_scu": self.manifest.total_scu,
                    "selected_ship": self.manifest.selected_ship or "",
                },
                severity="Info",
                dedupe=False,
            )
        except Exception as exc:
            logger.warning("Failed to record Hauling OCR scan event: %s", exc)

    def selected_ship(self):
        return selected_ship_name(self.ship_combo)

    def update_manifest(self):
        ship = self.selected_ship()
        self.manifest = build_manifest(self.contracts, selected_ship=ship)
        self.populate_contracts()
        self.populate_grouped_tables()
        self.update_capacity_summary()
        self.update_dashboard()
        self.update_warnings()
        self.update_contract_action_state()
        self.record_manifest_completed_if_needed()

    def selected_contract_id(self):
        row = self.contracts_table.currentRow()
        if row < 0:
            return ""
        item = self.contracts_table.item(row, 0)
        if not item:
            return ""
        return item.data(CONTRACT_ID_ROLE) or ""

    def selected_contract(self):
        contract_id = self.selected_contract_id()
        for contract in self.contracts:
            if contract.id == contract_id:
                return contract
        return None

    def toggle_selected_loaded(self):
        contract = self.selected_contract()
        if not contract:
            self.status_label.setText("Select a contract row before toggling loaded state.")
            return
        updated, changed = toggle_loaded_state(self.contracts, contract.id)
        if changed is None:
            self.status_label.setText("Could not update selected contract.")
            return
        if changed.state == CONTRACT_STATE_DELIVERED:
            self.status_label.setText("Delivered contracts remain loaded. Use Undo Delivered first if needed.")
            return
        self.contracts = updated
        self.update_manifest()
        self.record_contract_state_event(changed, "loaded" if changed.state == CONTRACT_STATE_LOADED else "planned")
        self.status_label.setText(f"Contract marked {state_label(changed.state)}.")

    def toggle_selected_delivered(self):
        contract = self.selected_contract()
        if not contract:
            self.status_label.setText("Select a contract row before toggling delivered state.")
            return
        updated, changed = toggle_delivered_state(self.contracts, contract.id)
        if changed is None:
            self.status_label.setText("Could not update selected contract.")
            return
        self.contracts = updated
        self.update_manifest()
        self.record_contract_state_event(
            changed,
            "delivered" if changed.state == CONTRACT_STATE_DELIVERED else "loaded",
        )
        self.status_label.setText(f"Contract marked {state_label(changed.state)}.")

    def update_contract_action_state(self):
        contract = self.selected_contract()
        has_selection = contract is not None
        state = contract.state if contract else CONTRACT_STATE_PLANNED

        if state == CONTRACT_STATE_DELIVERED:
            self.toggle_loaded_button.setText("Cargo Delivered")
            self.toggle_loaded_button.setEnabled(False)
            self.toggle_delivered_button.setText("Undo Delivered")
            self.toggle_delivered_button.setEnabled(True)
            return

        if state == CONTRACT_STATE_LOADED:
            self.toggle_loaded_button.setText("Unload Cargo")
            self.toggle_delivered_button.setText("Mark Delivered")
        else:
            self.toggle_loaded_button.setText("Load Cargo")
            self.toggle_delivered_button.setText("Mark Delivered")

        self.toggle_loaded_button.setEnabled(has_selection)
        self.toggle_delivered_button.setEnabled(has_selection)

    def populate_contracts(self):
        table = self.contracts_table
        table.setSortingEnabled(False)
        table.setRowCount(len(self.manifest.contracts))
        for row, contract in enumerate(self.manifest.contracts):
            values = [
                state_label(contract.state),
                contract.pickup or "Missing",
                contract.delivery or "Missing",
                contract.commodity or "Missing",
                format_number(contract.scu),
                format_money(contract.reward),
                f"{contract.confidence:.0%}",
                "; ".join(contract.warnings),
            ]
            sort_values = [
                state_sort_value(contract.state),
                contract.pickup,
                contract.delivery,
                contract.commodity,
                contract.scu,
                contract.reward if contract.reward is not None else -1,
                contract.confidence,
                "; ".join(contract.warnings),
            ]
            for column, value in enumerate(values):
                item = table_item(value, sort_values[column])
                item.setData(CONTRACT_ID_ROLE, contract.id)
                table.setItem(row, column, item)
        table.setSortingEnabled(True)
        configure_readable_table_columns(table, min_width=110, max_width=380, stretch_last=True)

    def populate_grouped_tables(self):
        self.populate_location_table(self.pickup_table, group_by_pickup(self.manifest.contracts))
        self.populate_location_table(
            self.destination_table,
            group_by_destination(self.manifest.contracts),
        )
        self.populate_route_table(group_by_route(self.manifest.contracts))

    def populate_location_table(self, table, groups):
        table.setSortingEnabled(False)
        table.setRowCount(len(groups))
        for row, (location, contracts) in enumerate(groups.items()):
            summary = group_summary(contracts)
            commodities = commodity_summary(contracts)
            table.setItem(row, 0, table_item(location, location))
            table.setItem(row, 1, table_item(format_number(summary["total_scu"]), summary["total_scu"]))
            table.setItem(row, 2, table_item(format_number(summary["remaining_scu"]), summary["remaining_scu"]))
            table.setItem(row, 3, table_item(format_number(summary["delivered_scu"]), summary["delivered_scu"]))
            table.setItem(row, 4, table_item(str(summary["remaining_contracts"]), summary["remaining_contracts"]))
            table.setItem(row, 5, table_item(str(summary["completed_contracts"]), summary["completed_contracts"]))
            table.setItem(row, 6, table_item(commodities, commodities))
        table.setSortingEnabled(True)
        configure_readable_table_columns(table, min_width=110, max_width=380, stretch_last=True)

    def populate_route_table(self, groups):
        self.route_table.setSortingEnabled(False)
        self.route_table.setRowCount(len(groups))
        for row, ((pickup, delivery), contracts) in enumerate(groups.items()):
            summary = group_summary(contracts)
            route = f"{pickup or 'Missing'} -> {delivery or 'Missing'}"
            commodities = commodity_summary(contracts)
            self.route_table.setItem(row, 0, table_item(route, route))
            self.route_table.setItem(row, 1, table_item(format_number(summary["total_scu"]), summary["total_scu"]))
            self.route_table.setItem(row, 2, table_item(format_number(summary["remaining_scu"]), summary["remaining_scu"]))
            self.route_table.setItem(row, 3, table_item(format_number(summary["delivered_scu"]), summary["delivered_scu"]))
            self.route_table.setItem(row, 4, table_item(str(summary["remaining_contracts"]), summary["remaining_contracts"]))
            self.route_table.setItem(row, 5, table_item(str(summary["completed_contracts"]), summary["completed_contracts"]))
            self.route_table.setItem(row, 6, table_item(commodities, commodities))
        self.route_table.setSortingEnabled(True)
        configure_readable_table_columns(self.route_table, min_width=110, max_width=420, stretch_last=True)

    def update_capacity_summary(self):
        if self.manifest.selected_ship:
            capacity = self.manifest.ship_capacity_scu
            self.capacity_label.setText(
                f"Ship Capacity: {format_number(capacity)} SCU"
                if capacity is not None
                else "Ship Capacity: Unknown"
            )
        else:
            self.capacity_label.setText("Ship Capacity: Select a ship")

        self.total_scu_label.setText(f"Total Parsed SCU: {format_number(self.manifest.total_scu)}")
        if self.manifest.remaining_scu is None:
            self.remaining_scu_label.setText("Remaining SCU: Select a ship")
        else:
            self.remaining_scu_label.setText(f"Remaining SCU: {format_number(self.manifest.remaining_scu)}")

        self.capacity_warning_label.setText(
            capacity_status_text(self.manifest.contracts, self.manifest.ship_capacity_scu)
        )

    def update_dashboard(self):
        values = {
            "selected_ship": self.manifest.selected_ship or "Select a ship",
            "ship_capacity": f"{format_number(self.manifest.ship_capacity_scu)} SCU",
            "loaded_scu": f"{format_number(self.manifest.loaded_scu)} SCU",
            "remaining_capacity": (
                f"{format_number(self.manifest.remaining_scu)} SCU"
                if self.manifest.remaining_scu is not None
                else "Select a ship"
            ),
            "total_contracts": str(self.manifest.total_contracts),
            "planned_contracts": str(self.manifest.planned_contracts),
            "loaded_contracts": str(self.manifest.loaded_contracts),
            "delivered_contracts": str(self.manifest.delivered_contracts),
            "capacity_status": capacity_status_text(self.manifest.contracts, self.manifest.ship_capacity_scu).replace(
                "Capacity status: ",
                "",
            ),
        }
        for key, value in values.items():
            self.dashboard_labels[key].setText(value)

        progress = int(round(self.manifest.completion_percentage))
        self.progress_bar.setValue(progress)
        self.progress_detail_label.setText(
            f"{format_number(self.manifest.delivered_scu)} / {format_number(self.manifest.total_scu)} SCU delivered "
            f"({format_number(self.manifest.completion_percentage)}%)"
        )

    def update_warnings(self):
        warnings = self.all_warnings()
        self.warnings_text.setPlainText("\n".join(f"- {warning}" for warning in warnings))
        if not warnings:
            self.warnings_text.setPlainText("- No manifest warnings.")

    def all_warnings(self):
        warnings = []
        if self.parse_result:
            warnings.extend(self.parse_result.warnings)
        if not self.contracts:
            warnings.append("No contracts parsed.")
        for contract in self.contracts:
            for warning in contract.warnings:
                label = contract.commodity or contract.contract_name or contract.id or "Contract"
                warnings.append(f"{label}: {warning}")
        warnings.extend(self.manifest.warnings)
        return tuple(dict.fromkeys(warnings))

    def record_manifest_started(self):
        if self.manifest_started_logged or not self.contracts:
            return
        self.manifest_started_logged = True
        self.record_hauling_event(
            event_type="hauling_manifest_started",
            message=f"Hauling manifest started with {len(self.contracts)} contract candidate"
            f"{'s' if len(self.contracts) != 1 else ''}.",
        )

    def record_contract_state_event(self, contract, state_name):
        if state_name == "loaded":
            event_type = "hauling_contract_loaded"
            message = "Hauling contract marked loaded."
        elif state_name == "delivered":
            event_type = "hauling_contract_delivered"
            message = "Hauling contract marked delivered."
        else:
            event_type = "hauling_contract_planned"
            message = "Hauling contract returned to planned."
        self.record_hauling_event(
            event_type=event_type,
            message=message,
            extra_metadata={
                "contract_id": contract.id,
                "contract_scu": contract.scu,
                "contract_state": contract.state,
            },
        )

    def record_manifest_completed_if_needed(self):
        if self.manifest_completed_logged or not self.contracts:
            return
        if self.manifest.delivered_contracts != len(self.contracts):
            return
        self.manifest_completed_logged = True
        self.record_hauling_event(
            event_type="hauling_manifest_completed",
            message="Hauling manifest completed.",
        )

    def record_session_event(self, event_type, message, session):
        try:
            record_event(
                category="Hauling",
                source="Hauling Operations Center",
                entity_name=session.name or "Hauling Session",
                event_type=event_type,
                message=message,
                metadata={
                    "session_id": session.id,
                    "session_name": session.name,
                    "selected_ship": session.selected_ship or "",
                    "contract_count": len(session.manifest.contracts),
                    "total_scu": session.manifest.total_scu,
                    "progress": session.manifest.completion_percentage,
                },
                severity="Info",
                dedupe=False,
            )
        except Exception as exc:
            logger.warning("Failed to record Hauling session event: %s", exc)

    def record_hauling_event(self, event_type, message, extra_metadata=None):
        try:
            metadata = {
                "ship": self.manifest.selected_ship or "",
                "contract_count": len(self.contracts),
                "loaded_scu": self.manifest.loaded_scu,
                "delivered_scu": self.manifest.delivered_scu,
            }
            metadata.update(extra_metadata or {})
            record_event(
                category="Hauling",
                source="Hauling Operations Center",
                entity_name="Hauling Manifest",
                event_type=event_type,
                message=message,
                metadata=metadata,
                severity="Info",
                dedupe=False,
            )
        except Exception as exc:
            logger.warning("Failed to record Hauling event: %s", exc)

    def copy_manifest(self):
        QApplication.clipboard().setText(self.manifest_text())
        self.status_label.setText("Manifest copied to clipboard.")

    def manifest_text(self):
        lines = [
            "Hauling Manifest",
            f"Ship: {self.manifest.selected_ship or 'Not selected'}",
            f"Capacity: {format_number(self.manifest.ship_capacity_scu)} SCU",
            f"Total SCU: {format_number(self.manifest.total_scu)}",
            f"Loaded SCU: {format_number(self.manifest.loaded_scu)}",
            f"Delivered SCU: {format_number(self.manifest.delivered_scu)}",
            f"Remaining SCU: {format_number(self.manifest.remaining_scu)}",
            f"Progress: {format_number(self.manifest.completion_percentage)}%",
            "",
            "Contracts:",
        ]
        if not self.manifest.contracts:
            lines.append("- None parsed")
        for contract in self.manifest.contracts:
            lines.append(
                f"- [{state_label(contract.state)}] {contract.commodity or 'Missing commodity'}: "
                f"{contract.pickup or 'Missing pickup'} -> {contract.delivery or 'Missing delivery'} "
                f"({format_number(contract.scu)} SCU)"
            )
        warnings = self.all_warnings()
        if warnings:
            lines.append("")
            lines.append("Warnings:")
            lines.extend(f"- {warning}" for warning in warnings)
        return "\n".join(lines)


def table_item(text, sort_value=None):
    item = SortableTableWidgetItem(str(text or ""))
    item.setData(SORT_ROLE, sort_value if sort_value is not None else str(text or ""))
    return item


def format_number(value):
    if value is None:
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")


def format_money(value):
    if value is None:
        return "N/A"
    return f"{format_number(value)} aUEC"


def state_label(state):
    state = str(state or "").lower()
    labels = {
        CONTRACT_STATE_PLANNED: "Planned",
        CONTRACT_STATE_LOADED: "Loaded",
        CONTRACT_STATE_DELIVERED: "Delivered",
    }
    return labels.get(state, state.replace("_", " ").title() or "Planned")


def state_sort_value(state):
    state = str(state or "").lower()
    order = {
        CONTRACT_STATE_PLANNED: 0,
        CONTRACT_STATE_LOADED: 1,
        CONTRACT_STATE_DELIVERED: 2,
    }
    return order.get(state, 99)


def commodity_summary(contracts):
    commodities = []
    for contract in contracts:
        name = contract.commodity or "Missing commodity"
        if name not in commodities:
            commodities.append(name)
    return ", ".join(commodities)


def legacy_reward_region():
    value = get_app_setting(LEGACY_REWARD_REGION_SETTING_KEY, "")
    if not value:
        return None
    parts = value.split(",")
    if len(parts) != 4:
        return None
    try:
        region = tuple(int(part.strip()) for part in parts)
    except ValueError:
        return None
    if region[2] <= 0 or region[3] <= 0:
        return None
    return region
