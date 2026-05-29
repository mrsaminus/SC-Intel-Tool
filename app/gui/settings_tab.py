from PySide6.QtWidgets import (
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Settings will be here.\n\n"
            "Planned:\n"
            "- Theme\n"
            "- Default scan region\n"
            "- RSI lookup timeout\n"
            "- Local data folders\n"
            "- Export/import"
        )

        layout.addWidget(text)
        self.setLayout(layout)
