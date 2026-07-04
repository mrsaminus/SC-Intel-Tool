from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget


class RegionSelectionOverlay(QWidget):
    region_selected = Signal(tuple)
    region_cancelled = Signal()

    def __init__(self, screen=None, instruction_text=None):
        super().__init__(None)
        self.screen = screen or QApplication.primaryScreen()
        self.instruction_text = instruction_text or (
            "Drag to select reward popup region. Release to confirm. ESC cancels."
        )
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
            self.instruction_text,
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
