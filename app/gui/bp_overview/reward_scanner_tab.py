import difflib
import re

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
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

from app.blueprints_client import fetch_blueprints
from app.blueprints_storage import get_owned_blueprint_keys, set_blueprint_owned
from app.database import get_app_setting, set_app_setting
from app.event_center.service import record_event

from ..workers import BackgroundTaskMixin
from .shared import ROW_ROLE, create_card, create_table, table_item


REGION_SETTING_KEY = "bp_reward_scanner_region"
CONFIRM_THRESHOLD = 0.55
STRONG_MATCH_THRESHOLD = 0.75


class RegionSelectionOverlay(QWidget):
    region_selected = Signal(tuple)
    region_cancelled = Signal()

    def __init__(self, screen=None):
        super().__init__(None)
        self.screen = screen or QApplication.primaryScreen()
        self.start_pos = None
        self.current_pos = None
        self.selection_rect = QRect()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        if self.screen:
            self.setGeometry(self.screen.geometry())

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
        painter.setPen(QPen(QColor(0, 220, 255), 2))
        painter.setBrush(QColor(0, 220, 255, 35))
        if not self.selection_rect.isNull():
            painter.drawRect(self.selection_rect.normalized())
        painter.setPen(QColor(210, 245, 255))
        painter.drawText(
            24,
            32,
            "Drag to select reward popup region. Release to confirm. ESC cancels.",
        )

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self.start_pos = event.position().toPoint()
        self.current_pos = self.start_pos
        self.selection_rect = QRect(self.start_pos, self.current_pos)
        self.update()

    def mouseMoveEvent(self, event):
        if self.start_pos is None:
            return
        self.current_pos = event.position().toPoint()
        self.selection_rect = QRect(self.start_pos, self.current_pos).normalized()
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self.start_pos is None:
            return
        self.current_pos = event.position().toPoint()
        rect = QRect(self.start_pos, self.current_pos).normalized()
        self.start_pos = None
        if rect.width() < 8 or rect.height() < 8:
            self.region_cancelled.emit()
            self.close()
            return
        screen_geometry = self.geometry()
        self.region_selected.emit((
            screen_geometry.x() + rect.x(),
            screen_geometry.y() + rect.y(),
            rect.width(),
            rect.height(),
        ))
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.region_cancelled.emit()
            self.close()
            return
        super().keyPressEvent(event)


class RewardScannerTab(BackgroundTaskMixin, QWidget):
    def __init__(self, ownership_changed_callback=None):
        super().__init__()
        self.blueprints = []
        self.matches = []
        self.selected_match = None
        self.ownership_changed_callback = ownership_changed_callback
        self.scan_running = False
        self.region_overlay = None

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.build_privacy_card())
        layout.addWidget(self.build_scanner_card(), 1)
        self.setLayout(layout)

        self.load_region()
        self.update_match_state(None)

    def build_privacy_card(self):
        card = create_card("REWARD SCANNER ALPHA")
        text = QLabel(
            "Optional and off by default. Reads only the selected region when you click Scan Once. "
            "No screenshots or OCR text are uploaded. No telemetry. Confirm Add is required before ownership changes."
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
        self.scan_once_button = QPushButton("Scan Once")
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

        self.status_label = QLabel("Scanner is off. Enable it manually before Scan Once.")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.ocr_text = QTextEdit()
        self.ocr_text.setPlaceholderText("Paste OCR text here, or use Scan Once when a local OCR engine is available...")
        self.ocr_text.setMinimumHeight(110)
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
            fetch_blueprints,
            self.on_blueprints_loaded,
            self.on_blueprints_error,
            self.finish_blueprint_refresh,
        )

    def on_blueprints_loaded(self, blueprints):
        self.set_blueprints([blueprint for blueprint in blueprints if blueprint.ownable])

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
                "Enable the scanner manually before scanning. It remains off by default.",
            )
            return
        region = self.region()
        if not region:
            QMessageBox.warning(self, "Region Required", "Enter X, Y, Width and Height before Scan Once.")
            return
        if self.remember_region_checkbox.isChecked():
            self.save_region()

        try:
            image = capture_region_image(region)
        except Exception as exc:
            self.status_label.setText(f"Region capture failed locally: {exc}")
            return

        try:
            import pytesseract
        except ImportError:
            self.status_label.setText(
                "Region captured once. No local OCR engine is available in this build; paste OCR text manually and click Parse Text."
            )
            return

        try:
            text = pytesseract.image_to_string(image)
        except Exception as exc:
            self.status_label.setText(f"Scan failed locally: {exc}")
            return

        self.ocr_text.setPlainText(text)
        self.parse_text()

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
            set_app_setting(REGION_SETTING_KEY, ",".join(str(value) for value in region))
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
            image = capture_region_image(region)
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
        value = get_app_setting(REGION_SETTING_KEY, "")
        if not value:
            return
        parts = value.split(",")
        if len(parts) != 4:
            return
        for field, part in zip((self.x_input, self.y_input, self.width_input, self.height_input), parts):
            field.setText(part.strip())
        self.remember_region_checkbox.setChecked(True)

    def save_region(self):
        region = self.region()
        if not region:
            QMessageBox.warning(self, "Invalid Region", "Enter valid X, Y, Width and Height values.")
            return
        set_app_setting(REGION_SETTING_KEY, ",".join(str(value) for value in region))
        self.status_label.setText("Reward scanner region saved locally.")


def match_blueprint_text(text, blueprints, limit=8):
    normalized_text = normalize_match_text(text)
    lines = [
        normalize_match_text(line)
        for line in text.splitlines()
        if normalize_match_text(line)
    ]
    matches = []
    for blueprint in blueprints:
        name = blueprint.blueprint_name
        normalized_name = normalize_match_text(name)
        if not normalized_name:
            continue
        if normalized_name in normalized_text:
            confidence = 1.0
            match_type = "exact"
        else:
            line_score = max(
                (difflib.SequenceMatcher(None, normalized_name, line).ratio() for line in lines),
                default=0,
            )
            whole_score = difflib.SequenceMatcher(None, normalized_name, normalized_text).ratio()
            token_score = token_overlap_score(normalized_name, normalized_text)
            confidence = max(line_score, whole_score, token_score)
            match_type = "partial" if confidence >= CONFIRM_THRESHOLD else "none"
        if confidence >= 0.35:
            matches.append({
                "blueprint": blueprint,
                "confidence": confidence,
                "match_type": match_type,
                "name_length": len(normalized_name),
            })

    matches.sort(key=lambda item: (
        -item["confidence"],
        -item["name_length"],
        item["blueprint"].blueprint_name.lower(),
    ))
    return matches[:limit]


def normalize_match_text(text):
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def token_overlap_score(name, text):
    name_tokens = set(name.split())
    text_tokens = set(text.split())
    if not name_tokens:
        return 0
    overlap = len(name_tokens & text_tokens) / len(name_tokens)
    if overlap < 0.5:
        return overlap * 0.5
    return min(0.85, overlap)


def capture_region_image(region):
    from PIL import ImageGrab

    x, y, width, height = region
    return ImageGrab.grab(bbox=(x, y, x + width, y + height))


def pixmap_from_image(image):
    from PIL.ImageQt import ImageQt

    qimage = ImageQt(image.convert("RGBA"))
    return QPixmap.fromImage(qimage)
