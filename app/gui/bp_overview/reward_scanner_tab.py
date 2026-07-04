import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.blueprints_client import load_blueprints
from app.blueprints_storage import get_owned_blueprint_keys, set_blueprint_owned
from app.database import get_app_setting, set_app_setting
from app.event_center.service import record_event
from app.ocr import OCRProfileManager, OCRRegion, OCRService, REWARD_SCANNER_PROFILE_KEY
from app.ocr.blueprint_reward_workflow import (
    BlueprintRewardWorkflow,
    detect_blueprint_reward_trigger,
    title_region_from_reward_region,
)
from app.ocr.debug_capture import is_ocr_debug_enabled, start_ocr_debug_session
from app.ocr.reward_scanner import RewardScannerParser, reward_scan_result_from_pipeline

from ..responsive import install_scroll_area
from ..workers import BackgroundTaskMixin
from .reward_scanner_matching import (
    CONFIRM_THRESHOLD,
    STRONG_MATCH_THRESHOLD,
    capture_region_image,
    match_blueprint_text,
    pixmap_from_image,
)
from .reward_scanner_overlay import RegionSelectionOverlay
from .shared import ROW_ROLE, create_card, create_table, table_item


REGION_SETTING_KEY = "bp_reward_scanner_region"
REGION_NAME = "Reward Scanner"
NONMATCH_DEBUG_SAMPLE_SECONDS = 30


class RewardScannerTab(BackgroundTaskMixin, QWidget):
    def __init__(self, ownership_changed_callback=None):
        super().__init__()
        self.blueprints = []
        self.matches = []
        self.selected_match = None
        self.ownership_changed_callback = ownership_changed_callback
        self.scan_running = False
        self.scan_once_running = False
        self.trigger_check_running = False
        self.scan_once_request_id = 0
        self.trigger_request_id = 0
        self.last_nonmatch_debug_saved_at = 0.0
        self.full_scan_debug_sessions = {}
        self.region_overlay = None
        self.ocr_profile_manager = OCRProfileManager()
        self.ocr_service = OCRService(settings=self.current_ocr_profile().to_settings())
        self.reward_workflow = BlueprintRewardWorkflow()
        self.trigger_timer = QTimer(self)
        self.trigger_timer.setInterval(2500)
        self.trigger_timer.timeout.connect(self.check_reward_trigger)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.build_privacy_card())
        layout.addWidget(self.build_scanner_card(), 1)
        self.reward_scanner_scroll_area = install_scroll_area(self, content_widget)

        self.load_region()
        self.update_match_state(None)

    def build_privacy_card(self):
        card = create_card("REWARD SCANNER ALPHA")
        text = QLabel(
            "Optional and off by default. When enabled, the scanner watches the selected region for the "
            "\"Received Blueprint\" title first, then runs full local OCR only when the reward window is visible. "
            "No screenshots or OCR text are uploaded. Confirm Add is required before ownership changes."
        )
        text.setObjectName("moduleSubtitle")
        text.setWordWrap(True)
        card.layout().addWidget(text)
        return card

    def build_scanner_card(self):
        card = create_card("SCAN / MATCH BLUEPRINT REWARD")
        layout = card.layout()

        top_controls = QHBoxLayout()
        top_controls.setSpacing(8)
        self.enabled_checkbox = QCheckBox("Enable scanner")
        self.enabled_checkbox.toggled.connect(self.on_scanner_enabled_changed)
        self.load_blueprints_button = QPushButton("Load Blueprint Names")
        self.load_blueprints_button.clicked.connect(self.refresh_blueprints)
        top_controls.addWidget(self.enabled_checkbox)
        top_controls.addStretch(1)
        top_controls.addWidget(self.load_blueprints_button)
        layout.addLayout(top_controls)

        region_grid = QGridLayout()
        region_grid.setHorizontalSpacing(8)
        region_grid.setVerticalSpacing(6)
        self.x_input = QLineEdit()
        self.y_input = QLineEdit()
        self.width_input = QLineEdit()
        self.height_input = QLineEdit()
        for field, placeholder in (
            (self.x_input, "X"),
            (self.y_input, "Y"),
            (self.width_input, "Width"),
            (self.height_input, "Height"),
        ):
            field.setPlaceholderText(placeholder)
        region_grid.addWidget(QLabel("Region"), 0, 0)
        region_grid.addWidget(self.x_input, 0, 1)
        region_grid.addWidget(self.y_input, 0, 2)
        region_grid.addWidget(self.width_input, 0, 3)
        region_grid.addWidget(self.height_input, 0, 4)
        self.remember_region_checkbox = QCheckBox("Remember region locally")
        self.save_region_button = QPushButton("Save Region")
        self.select_region_button = QPushButton("Select Screen Region")
        self.save_region_button.clicked.connect(self.save_region)
        self.select_region_button.clicked.connect(self.select_screen_region)
        region_grid.addWidget(self.remember_region_checkbox, 1, 1, 1, 2)
        region_grid.addWidget(self.select_region_button, 1, 3)
        region_grid.addWidget(self.save_region_button, 1, 4)
        layout.addLayout(region_grid)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.scan_once_button = QPushButton("Check Now")
        self.preview_region_button = QPushButton("Preview Region")
        self.parse_text_button = QPushButton("Parse Text")
        self.copy_text_button = QPushButton("Copy OCR Text")
        self.ignore_button = QPushButton("Ignore")
        self.confirm_button = QPushButton("Confirm Add")
        self.scan_once_button.clicked.connect(self.scan_once)
        self.preview_region_button.clicked.connect(self.preview_region)
        self.parse_text_button.clicked.connect(self.parse_text)
        self.copy_text_button.clicked.connect(self.copy_ocr_text)
        self.ignore_button.clicked.connect(self.ignore_match)
        self.confirm_button.clicked.connect(self.confirm_add)
        buttons.addWidget(self.scan_once_button)
        buttons.addWidget(self.preview_region_button)
        buttons.addWidget(self.parse_text_button)
        buttons.addWidget(self.copy_text_button)
        buttons.addWidget(self.ignore_button)
        buttons.addWidget(self.confirm_button)
        layout.addLayout(buttons)

        self.status_label = QLabel("Scanner is off. Enable it to watch for the Received Blueprint trigger.")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.debug_status_label = QLabel(self.default_debug_status_text())
        self.debug_status_label.setObjectName("moduleSubtitle")
        self.debug_status_label.setWordWrap(True)
        layout.addWidget(self.debug_status_label)

        self.ocr_text = QTextEdit()
        self.ocr_text.setPlaceholderText("Paste OCR text here, or use Check Now to run the local OCR scanner...")
        self.ocr_text.setMinimumHeight(150)
        layout.addWidget(self.ocr_text)

        self.result_label = QLabel("Detected Blueprint: None")
        self.result_label.setObjectName("valueText")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        self.matches_table = create_table([
            "Blueprint",
            "Confidence",
            "Match",
            "Owned",
        ])
        self.matches_table.itemSelectionChanged.connect(self.on_candidate_selected)
        layout.addWidget(self.matches_table, 1)
        return card

    def set_blueprints(self, blueprints):
        self.blueprints = list(blueprints or [])
        self.status_label.setText(f"Loaded {len(self.blueprints)} blueprint names for local reward matching.")
        if self.ocr_text.toPlainText().strip():
            self.parse_text()

    def refresh_blueprints(self):
        if self.scan_running:
            return
        self.scan_running = True
        self.load_blueprints_button.setEnabled(False)
        self.load_blueprints_button.setText("Loading...")
        self.status_label.setText("Loading blueprint names...")
        self.start_background_task(
            lambda: load_blueprints(raise_on_missing=False),
            self.on_blueprints_loaded,
            self.on_blueprints_error,
            self.finish_blueprint_refresh,
        )

    def on_blueprints_loaded(self, snapshot):
        blueprints = snapshot.blueprints if hasattr(snapshot, "blueprints") else snapshot
        self.set_blueprints([blueprint for blueprint in blueprints if blueprint.ownable])
        if hasattr(snapshot, "source_error") and snapshot.source_error and not blueprints:
            self.status_label.setText(f"Blueprint name load failed: {snapshot.source_error}")

    def on_blueprints_error(self, exc):
        self.status_label.setText(f"Blueprint name load failed: {exc}")

    def finish_blueprint_refresh(self):
        self.scan_running = False
        self.load_blueprints_button.setEnabled(True)
        self.load_blueprints_button.setText("Load Blueprint Names")

    def scan_once(self):
        if not self.enabled_checkbox.isChecked():
            QMessageBox.information(
                self,
                "Scanner Disabled",
                "Enable the scanner before checking for a Received Blueprint window. It remains off by default.",
            )
            return
        self.check_reward_trigger(force=True)

    def on_scanner_enabled_changed(self, enabled):
        if enabled:
            self.status_label.setText("Scanner enabled. Watching for the Received Blueprint trigger.")
            self.trigger_timer.start()
            self.check_reward_trigger(force=True)
            return
        self.trigger_timer.stop()
        self.reward_workflow.reset()
        self.trigger_check_running = False
        self.scan_once_running = False
        self.scan_once_button.setEnabled(True)
        self.scan_once_button.setText("Check Now")
        self.status_label.setText("Scanner is off. Enable it to watch for the Received Blueprint trigger.")

    def check_reward_trigger(self, force=False):
        if not self.enabled_checkbox.isChecked():
            return
        if self.trigger_check_running or self.scan_once_running:
            if force:
                self.status_label.setText("Scanner is already checking this region.")
            return
        region = self.region()
        if not region:
            if force:
                QMessageBox.warning(self, "Region Required", "Enter X, Y, Width and Height before checking.")
            else:
                self.status_label.setText("Scanner enabled. Select a Received Blueprint region to begin.")
            return
        if self.remember_region_checkbox.isChecked():
            self.save_region()

        profile = self.current_ocr_profile()
        ocr_region = OCRRegion.from_tuple(
            region,
            name=REGION_NAME,
            profile=profile.key,
            description="BP Overview reward scanner capture region.",
        )
        trigger_region = title_region_from_reward_region(ocr_region)
        self.trigger_check_running = True
        self.trigger_request_id += 1
        request_id = self.trigger_request_id
        self.scan_once_button.setEnabled(False)
        self.scan_once_button.setText("Checking...")
        if self.reward_workflow.waiting_for_window_close:
            self.status_label.setText("Waiting for the current Received Blueprint window to close.")
        else:
            self.status_label.setText("Checking for Received Blueprint trigger...")

        self.start_background_task(
            lambda: self.ocr_service.scan_profile_region(profile, trigger_region, parser=None),
            lambda result, current_request=request_id: self.on_trigger_check_result(current_request, result),
            lambda exc, current_request=request_id: self.on_trigger_check_error(current_request, exc),
            lambda current_request=request_id: self.finish_trigger_check(current_request),
        )

    def on_trigger_check_result(self, request_id, pipeline):
        if request_id != self.trigger_request_id:
            return

        status = pipeline.status
        text = pipeline.ocr_result.text if pipeline.ocr_result else ""
        state_before = self.reward_workflow.state
        trigger_match = detect_blueprint_reward_trigger(text)
        debug_session = self.save_trigger_debug_result(
            pipeline=pipeline,
            text=text,
            trigger_match=trigger_match,
            state_before=state_before,
            state_after=self.reward_workflow.state,
        )
        if status == "capture_error":
            self.status_label.setText(f"Trigger capture failed locally: {pipeline.message}")
            return
        if status == "missing_ocr":
            self.status_label.setText(
                f"Local OCR engine unavailable: {pipeline.message}. Manual paste is available. "
                "Debug captures are stored locally when capture runs."
            )
            return
        if status in {"ocr_error", "parse_error"}:
            self.status_label.setText(f"Trigger check failed locally: {pipeline.message}")
            return

        should_scan = self.reward_workflow.trigger_seen(text)
        if debug_session:
            debug_session.update_metadata({"scanner_state_after": self.reward_workflow.state})
        if self.reward_workflow.waiting_for_window_close:
            self.status_label.setText("Received Blueprint already processed. Waiting for the reward window to close.")
            return
        if not trigger_match:
            self.status_label.setText("Watching for Received Blueprint trigger.")
            return
        if should_scan:
            self.status_label.setText("Received Blueprint trigger detected. Running full local OCR.")
            self.start_full_reward_scan(debug_session=debug_session)

    def on_trigger_check_error(self, request_id, exc):
        if request_id != self.trigger_request_id:
            return
        self.status_label.setText(f"Trigger check failed locally: {exc}")

    def finish_trigger_check(self, request_id):
        if request_id != self.trigger_request_id:
            return
        self.trigger_check_running = False
        if not self.scan_once_running:
            self.scan_once_button.setEnabled(True)
            self.scan_once_button.setText("Check Now")

    def start_full_reward_scan(self, debug_session=None):
        if self.scan_once_running:
            return
        region = self.region()
        if not region:
            self.status_label.setText("Region disappeared before full scan could run.")
            return
        self.reward_workflow.start_scanning()
        self.scan_once_running = True
        self.scan_once_request_id += 1
        request_id = self.scan_once_request_id
        blueprints = tuple(self.blueprints)
        profile = self.current_ocr_profile()
        ocr_region = OCRRegion.from_tuple(
            region,
            name=REGION_NAME,
            profile=profile.key,
            description="BP Overview reward scanner capture region.",
        )
        parser = RewardScannerParser(blueprints)
        self.scan_once_button.setEnabled(False)
        self.scan_once_button.setText("Scanning...")
        self.status_label.setText("Capturing full reward region and running local OCR...")
        if debug_session:
            self.full_scan_debug_sessions[request_id] = debug_session

        self.start_background_task(
            lambda: self.ocr_service.scan_profile_region(profile, ocr_region, parser=parser),
            lambda result, current_request=request_id, count=len(blueprints): self.on_scan_once_result(
                current_request,
                reward_scan_result_from_pipeline(result, count),
            ),
            lambda exc, current_request=request_id: self.on_scan_once_error(current_request, exc),
            lambda current_request=request_id: self.finish_scan_once(current_request),
        )

    def on_scan_once_result(self, request_id, result):
        if request_id != self.scan_once_request_id:
            return

        self.save_full_debug_result(request_id, result)
        status = result.get("status")
        if status == "capture_error":
            self.status_label.setText(f"Region capture failed locally: {result.get('message', '')}")
            self.reward_workflow.wait_for_window_close()
            return
        if status == "missing_ocr":
            self.status_label.setText(
                f"Local OCR engine unavailable: {pipeline.message}. Manual paste is available. "
                "Debug captures are stored locally when capture runs."
            )
            self.reward_workflow.wait_for_window_close()
            return
        if status == "ocr_error":
            self.status_label.setText(f"Scan failed locally: {result.get('message', '')}")
            self.reward_workflow.wait_for_window_close()
            return

        text = result.get("text", "")
        self.ocr_text.setPlainText(text)
        if not result.get("blueprint_count"):
            self.status_label.setText("Load blueprint names before parsing reward text.")
            self.populate_matches([])
            self.update_match_state(None)
            self.reward_workflow.wait_for_window_close()
            return
        self.apply_matches(text, result.get("matches", []))
        self.reward_workflow.mark_matched()
        self.reward_workflow.wait_for_window_close()

    def on_scan_once_error(self, request_id, exc):
        if request_id != self.scan_once_request_id:
            return
        self.status_label.setText(f"Scan failed locally: {exc}")

    def finish_scan_once(self, request_id):
        if request_id != self.scan_once_request_id:
            return
        self.full_scan_debug_sessions.pop(request_id, None)
        self.scan_once_running = False
        self.scan_once_button.setEnabled(True)
        self.scan_once_button.setText("Check Now")

    def save_trigger_debug_result(self, pipeline, text, trigger_match, state_before, state_after):
        if not is_ocr_debug_enabled():
            self.debug_status_label.setText(self.default_debug_status_text())
            return None
        if not trigger_match and not self.should_save_nonmatch_debug_sample():
            return None

        region = self.region()
        trigger_region = None
        if region:
            profile = self.current_ocr_profile()
            trigger_region = title_region_from_reward_region(
                OCRRegion.from_tuple(region, name=REGION_NAME, profile=profile.key)
            )
        session = start_ocr_debug_session(
            "blueprint_reward",
            metadata={
                "workflow_name": "Blueprint Reward Scanner",
                "phase": "trigger",
                "scanner_state_before": state_before,
                "scanner_state_after": state_after,
                "trigger_match": trigger_match,
                "status": getattr(pipeline, "status", ""),
                "message": getattr(pipeline, "message", ""),
                "region": trigger_region.to_dict() if trigger_region else None,
                "warnings": getattr(pipeline, "warnings", ()),
                "errors": getattr(pipeline, "errors", ()),
                "sample_policy": "trigger_match" if trigger_match else "throttled_nonmatch",
            },
        )
        if not session:
            self.debug_status_label.setText(self.default_debug_status_text())
            return None
        session.save_image("trigger.png", getattr(pipeline, "captured_image", None))
        session.save_text("trigger_ocr.txt", text)
        self.debug_status_label.setText(f"Last debug capture saved: {session.path}")
        if not trigger_match:
            self.last_nonmatch_debug_saved_at = time.monotonic()
        return session

    def save_full_debug_result(self, request_id, result):
        session = self.full_scan_debug_sessions.get(request_id)
        if not session:
            return
        region = self.region()
        profile = self.current_ocr_profile()
        ocr_region = OCRRegion.from_tuple(region, name=REGION_NAME, profile=profile.key) if region else None
        session.save_image("full_region.png", result.get("captured_image"))
        session.save_text("full_ocr.txt", result.get("text", ""))
        session.update_metadata({
            "phase": "full_scan",
            "scanner_state": self.reward_workflow.state,
            "full_scan_status": result.get("status", ""),
            "full_scan_message": result.get("message", ""),
            "full_region": ocr_region.to_dict() if ocr_region else None,
            "blueprint_count": result.get("blueprint_count", 0),
            "match_count": len(result.get("matches") or []),
            "warnings": result.get("warnings", ()),
            "errors": result.get("errors", ()),
            "parser_warnings": result.get("parser_warnings", ()),
            "parser_errors": result.get("parser_errors", ()),
        })
        self.debug_status_label.setText(f"Last debug capture saved: {session.path}")

    def should_save_nonmatch_debug_sample(self):
        return (time.monotonic() - self.last_nonmatch_debug_saved_at) >= NONMATCH_DEBUG_SAMPLE_SECONDS

    def default_debug_status_text(self):
        if is_ocr_debug_enabled():
            return "OCR debug: no capture saved yet."
        return "OCR debug disabled in Settings."

    def parse_text(self):
        text = self.ocr_text.toPlainText().strip()
        if not text:
            self.status_label.setText("No OCR text to parse.")
            self.populate_matches([])
            self.update_match_state(None)
            return
        if not self.blueprints:
            self.status_label.setText("Load blueprint names before parsing reward text.")
            self.populate_matches([])
            self.update_match_state(None)
            return
        matches = match_blueprint_text(text, self.blueprints)
        self.apply_matches(text, matches)

    def apply_matches(self, text, matches):
        if not str(text or "").strip():
            self.status_label.setText("No OCR text to parse.")
            self.populate_matches([])
            self.update_match_state(None)
            return
        self.populate_matches(matches)
        self.update_match_state(matches[0] if matches else None)
        if matches:
            self.status_label.setText(f"Found {len(matches)} possible blueprint match{'es' if len(matches) != 1 else ''}.")
        else:
            self.status_label.setText("No confident blueprint match found.")

    def populate_matches(self, matches):
        self.matches = matches
        owned_keys = get_owned_blueprint_keys()
        self.matches_table.setSortingEnabled(False)
        self.matches_table.setRowCount(len(matches))
        for row, match in enumerate(matches):
            blueprint = match["blueprint"]
            values = [
                blueprint.blueprint_name,
                f"{match['confidence']:.0%}",
                match["match_type"].title(),
                "Yes" if blueprint.key in owned_keys else "No",
            ]
            sort_values = [
                values[0],
                match["confidence"],
                values[2],
                1 if blueprint.key in owned_keys else 0,
            ]
            for column, value in enumerate(values):
                item = table_item(value, sort_values[column])
                item.setData(ROW_ROLE, row)
                self.matches_table.setItem(row, column, item)
        self.matches_table.setSortingEnabled(True)
        if matches:
            self.matches_table.setCurrentCell(0, 0)

    def on_candidate_selected(self):
        row = self.matches_table.currentRow()
        if row < 0:
            return
        item = self.matches_table.item(row, 0)
        if not item:
            return
        source_row = item.data(ROW_ROLE)
        if source_row is None or source_row >= len(self.matches):
            return
        self.update_match_state(self.matches[source_row])

    def update_match_state(self, match):
        self.selected_match = match
        if not match:
            self.result_label.setText("Detected Blueprint: None")
            self.confirm_button.setEnabled(False)
            return
        blueprint = match["blueprint"]
        confidence = match["confidence"]
        self.result_label.setText(
            f"Detected Blueprint: {blueprint.blueprint_name}\n"
            f"Confidence: {confidence:.0%}\n"
            f"Match: {match['match_type'].title()}"
        )
        self.confirm_button.setEnabled(confidence >= CONFIRM_THRESHOLD)

    def confirm_add(self):
        if not self.selected_match:
            return
        blueprint = self.selected_match["blueprint"]
        confidence = self.selected_match["confidence"]
        if confidence < STRONG_MATCH_THRESHOLD:
            response = QMessageBox.warning(
                self,
                "Low Confidence Match",
                "This match is not high confidence. Confirm only if the blueprint name is correct.",
                QMessageBox.Cancel | QMessageBox.Ok,
                QMessageBox.Cancel,
            )
            if response != QMessageBox.Ok:
                return

        owned_keys = get_owned_blueprint_keys()
        if blueprint.key in owned_keys:
            QMessageBox.information(self, "Already Owned", "This blueprint is already marked owned.")
            return

        set_blueprint_owned(blueprint.key, blueprint.blueprint_name, "Reward Scanner", True)
        record_event(
            category="Item",
            source="BP Overview",
            entity_name=blueprint.blueprint_name,
            event_type="blueprint_owned_reward_scanner",
            message=f"Blueprint marked owned from Reward Scanner: {blueprint.blueprint_name}",
            metadata={
                "blueprint_key": blueprint.key,
                "confidence": confidence,
                "match_type": self.selected_match["match_type"],
            },
            severity="Info",
        )
        QMessageBox.information(self, "Blueprint Added", "Blueprint ownership was updated locally.")
        if self.ownership_changed_callback:
            self.ownership_changed_callback()
        self.parse_text()

    def ignore_match(self):
        self.update_match_state(None)
        self.matches_table.clearSelection()
        self.status_label.setText("Detected match ignored. No ownership changes were made.")

    def copy_ocr_text(self):
        QApplication.clipboard().setText(self.ocr_text.toPlainText())

    def select_screen_region(self):
        screen = QApplication.primaryScreen()
        if not screen:
            QMessageBox.warning(self, "No Screen Found", "Could not find a primary screen for region selection.")
            return
        self.status_label.setText("Select a region on the primary screen. Press ESC to cancel.")
        self.region_overlay = RegionSelectionOverlay(screen)
        self.region_overlay.region_selected.connect(self.on_region_selected)
        self.region_overlay.region_cancelled.connect(self.on_region_cancelled)
        self.region_overlay.show()
        self.region_overlay.raise_()
        self.region_overlay.activateWindow()

    def on_region_selected(self, region):
        x, y, width, height = region
        self.x_input.setText(str(x))
        self.y_input.setText(str(y))
        self.width_input.setText(str(width))
        self.height_input.setText(str(height))
        if self.remember_region_checkbox.isChecked():
            self.save_region_values(region)
        self.status_label.setText(
            f"Selected region {width}x{height} at X{x}, Y{y}. Preview or Scan Once when ready."
        )
        self.region_overlay = None

    def on_region_cancelled(self):
        self.status_label.setText("Region selection cancelled. Manual coordinates are still available.")
        self.region_overlay = None

    def preview_region(self):
        region = self.region()
        if not region:
            QMessageBox.warning(self, "Region Required", "Enter or select X, Y, Width and Height before Preview Region.")
            return
        try:
            image = capture_region_image(region, settings=self.current_ocr_profile().to_settings())
            pixmap = pixmap_from_image(image)
        except Exception as exc:
            self.status_label.setText(f"Preview capture failed locally: {exc}")
            QMessageBox.warning(self, "Preview Failed", f"Could not capture the selected region:\n\n{exc}")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Reward Scanner Region Preview")
        layout = QVBoxLayout(dialog)
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        label.setPixmap(pixmap.scaled(720, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        info = QLabel("Captured once locally. No OCR was run and nothing was uploaded.")
        info.setObjectName("moduleSubtitle")
        info.setWordWrap(True)
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(label)
        layout.addWidget(info)
        layout.addWidget(close_button)
        dialog.resize(760, 520)
        dialog.exec()

    def region(self):
        try:
            x = int(self.x_input.text().strip())
            y = int(self.y_input.text().strip())
            width = int(self.width_input.text().strip())
            height = int(self.height_input.text().strip())
        except ValueError:
            return None
        if width <= 0 or height <= 0:
            return None
        return x, y, width, height

    def load_region(self):
        profile_region = self.ocr_profile_manager.get_region(REWARD_SCANNER_PROFILE_KEY, REGION_NAME)
        if profile_region and profile_region.is_valid():
            self.apply_region(profile_region.to_tuple())
            self.remember_region_checkbox.setChecked(True)
            return

        value = get_app_setting(REGION_SETTING_KEY, "")
        if not value:
            return
        parts = value.split(",")
        if len(parts) != 4:
            return
        try:
            region = tuple(int(part.strip()) for part in parts)
        except ValueError:
            return
        self.apply_region(region)
        self.remember_region_checkbox.setChecked(True)
        self.save_region_values(region)

    def save_region(self):
        region = self.region()
        if not region:
            QMessageBox.warning(self, "Invalid Region", "Enter valid X, Y, Width and Height values.")
            return
        self.save_region_values(region)
        self.status_label.setText("Reward scanner region saved locally.")

    def current_ocr_profile(self):
        return self.ocr_profile_manager.get_profile(REWARD_SCANNER_PROFILE_KEY)

    def apply_region(self, region):
        for field, part in zip((self.x_input, self.y_input, self.width_input, self.height_input), region):
            field.setText(str(part).strip())

    def save_region_values(self, region):
        set_app_setting(REGION_SETTING_KEY, ",".join(str(value) for value in region))
        self.ocr_profile_manager.save_region(
            OCRRegion.from_tuple(
                region,
                name=REGION_NAME,
                profile=REWARD_SCANNER_PROFILE_KEY,
                description="BP Overview reward scanner capture region.",
            )
        )
