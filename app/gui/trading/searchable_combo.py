from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter


def configure_searchable_combo(combo, placeholder=None):
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.NoInsert)
    combo.setMaxVisibleItems(18)
    if placeholder:
        combo.setPlaceholderText(placeholder)

    completer = QCompleter(combo.model(), combo)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    combo.setCompleter(completer)
    return combo


def set_combo_items(combo, values, current_text=None):
    if current_text is None:
        current_text = combo.currentText().strip()

    combo.blockSignals(True)
    combo.clear()
    for value in values:
        combo.addItem(str(value))
    if current_text:
        combo.setCurrentText(current_text)
    else:
        combo.setCurrentText("")
    combo.blockSignals(False)

    if combo.completer():
        combo.completer().setModel(combo.model())


def selected_combo_text(combo, allow_free_text=False):
    text = combo.currentText().strip()
    if not text:
        return ""

    for index in range(combo.count()):
        item_text = combo.itemText(index).strip()
        if text.lower() == item_text.lower():
            return item_text

    return text if allow_free_text else ""
