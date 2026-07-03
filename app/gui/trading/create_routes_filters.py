from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QWidget

from ..safe_combobox import SafeComboBox as QComboBox


class MultiSelectFilter(QWidget):
    changed = Signal()

    def __init__(self, title, options, default_checked=None, parent=None):
        super().__init__(parent)
        self.title = title
        self.options = list(options)
        self.checked = set(default_checked or [])
        self._rebuilding = False

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText(f"Filter {title.lower()}...")
        self.filter_input.setMaximumWidth(160)

        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.lineEdit().setReadOnly(True)
        self.combo.view().setMinimumWidth(280)
        self.model = QStandardItemModel(self.combo)
        self.combo.setModel(self.model)

        layout.addWidget(self.filter_input)
        layout.addWidget(self.combo, 1)
        self.setLayout(layout)

        self.filter_input.textChanged.connect(self.rebuild_model)
        self.combo.view().pressed.connect(self.toggle_index)
        self.rebuild_model()

    def rebuild_model(self):
        self._rebuilding = True
        query = self.filter_input.text().strip().lower()
        self.model.clear()

        for option in self.options:
            if query and query not in option.lower():
                continue
            item = QStandardItem(option)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setData(option, Qt.UserRole)
            item.setCheckState(Qt.Checked if option in self.checked else Qt.Unchecked)
            self.model.appendRow(item)

        self._rebuilding = False
        self.update_display_text()

    def toggle_index(self, index):
        item = self.model.itemFromIndex(index)
        if not item:
            return

        option = item.data(Qt.UserRole)
        if option in self.checked:
            self.checked.remove(option)
            item.setCheckState(Qt.Unchecked)
        else:
            self.checked.add(option)
            item.setCheckState(Qt.Checked)

        self.update_display_text()
        self.changed.emit()

    def update_display_text(self):
        if not self.checked:
            text = f"No {self.title.lower()} selected"
        elif len(self.checked) == len(self.options):
            text = f"All {self.title.lower()}"
        elif len(self.checked) <= 2:
            text = ", ".join(option for option in self.options if option in self.checked)
        else:
            text = f"{len(self.checked)} {self.title.lower()} selected"

        self.combo.lineEdit().setText(text)

    def checked_values(self):
        return tuple(option for option in self.options if option in self.checked)

    def set_checked_values(self, values):
        self.checked = {value for value in values if value in self.options}
        self.rebuild_model()
        self.changed.emit()

    def select_all(self):
        self.checked = set(self.options)
        self.rebuild_model()
        self.changed.emit()

    def deselect_all(self):
        self.checked.clear()
        self.rebuild_model()
        self.changed.emit()
