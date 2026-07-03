from PySide6.QtWidgets import QComboBox


class SafeComboBox(QComboBox):
    """Combo box that leaves mouse-wheel scrolling to parent scroll areas."""

    def wheelEvent(self, event):
        view = self.view()
        if view and view.isVisible():
            super().wheelEvent(event)
            return
        event.ignore()
