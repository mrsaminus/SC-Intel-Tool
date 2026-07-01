from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app import notes_storage
from app.paths import bundled_path

from .sortable_table_item import ROW_ROLE, SORT_ROLE, SortableTableWidgetItem
from .table_utils import configure_readable_table_columns


class NotesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.current_note_id = None
        self.notes = []
        self.loading_editor = False

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_module_header(
            "Notes",
            "Local knowledge base for intel, trading, crafting, mining and planning notes.",
        ))
        layout.addWidget(self.build_notes_workspace(), 1)
        layout.addWidget(self.build_changelog_card())
        self.setLayout(layout)

        self.reload_categories()
        self.reload_notes()

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

    def build_notes_workspace(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.build_note_list_card())
        splitter.addWidget(self.build_editor_card())
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([420, 680])
        return splitter

    def build_note_list_card(self):
        card = self.create_card("KNOWLEDGE BASE")

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search title, tags, category or body...")
        self.category_filter = QComboBox()
        self.category_filter.addItem("All categories", "All")
        controls.addWidget(self.search_input, 1)
        controls.addWidget(self.category_filter)
        card.layout().addLayout(controls)

        self.notes_table = QTableWidget(0, 4)
        self.notes_table.setHorizontalHeaderLabels(["Pin", "Title", "Category", "Modified"])
        self.notes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.notes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.notes_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.notes_table.setAlternatingRowColors(True)
        self.notes_table.setSortingEnabled(True)
        self.notes_table.itemSelectionChanged.connect(self.on_note_selected)
        configure_readable_table_columns(self.notes_table, min_width=90, max_width=420, stretch_last=True)
        card.layout().addWidget(self.notes_table, 1)

        self.empty_label = QLabel("No notes yet. Create a note to start building your local knowledge base.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        card.layout().addWidget(self.empty_label)

        button_row = QHBoxLayout()
        self.new_button = QPushButton("New Note")
        self.duplicate_button = QPushButton("Duplicate")
        self.delete_button = QPushButton("Delete")
        self.new_button.clicked.connect(self.new_note)
        self.duplicate_button.clicked.connect(self.duplicate_current_note)
        self.delete_button.clicked.connect(self.delete_current_note)
        button_row.addWidget(self.new_button)
        button_row.addWidget(self.duplicate_button)
        button_row.addWidget(self.delete_button)
        button_row.addStretch(1)
        card.layout().addLayout(button_row)

        self.search_input.textChanged.connect(self.reload_notes)
        self.category_filter.currentIndexChanged.connect(self.reload_notes)
        return card

    def build_editor_card(self):
        card = self.create_card("NOTE DETAILS")

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Title")
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("comma-separated tags")
        self.pin_checkbox = QCheckBox("Pin note")
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText("Write local plain-text notes here...")
        self.body_input.setMinimumHeight(180)

        self.linked_type_input = QLineEdit()
        self.linked_type_input.setPlaceholderText("optional future link type")
        self.linked_key_input = QLineEdit()
        self.linked_key_input.setPlaceholderText("optional future link key")

        self.created_label = QLabel("Created: -")
        self.modified_label = QLabel("Modified: -")
        for label in (self.created_label, self.modified_label):
            label.setObjectName("moduleSubtitle")
            label.setWordWrap(True)

        card.layout().addWidget(QLabel("Title"))
        card.layout().addWidget(self.title_input)
        card.layout().addWidget(QLabel("Category"))
        card.layout().addWidget(self.category_input)
        card.layout().addWidget(QLabel("Tags"))
        card.layout().addWidget(self.tags_input)
        card.layout().addWidget(self.pin_checkbox)

        link_row = QHBoxLayout()
        link_row.setSpacing(8)
        link_row.addWidget(self.linked_type_input)
        link_row.addWidget(self.linked_key_input)
        card.layout().addLayout(link_row)

        card.layout().addWidget(self.body_input, 1)
        card.layout().addWidget(self.created_label)
        card.layout().addWidget(self.modified_label)

        button_row = QHBoxLayout()
        self.save_button = QPushButton("Save Note")
        self.clear_button = QPushButton("Clear Editor")
        self.save_button.clicked.connect(self.save_current_note)
        self.clear_button.clicked.connect(self.new_note)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.clear_button)
        button_row.addStretch(1)
        card.layout().addLayout(button_row)

        self.status_label = QLabel("Notes are stored locally only.")
        self.status_label.setObjectName("moduleSubtitle")
        self.status_label.setWordWrap(True)
        card.layout().addWidget(self.status_label)
        return card

    def build_changelog_card(self):
        card = self.create_card("CHANGELOG")
        subtitle = QLabel("Release notes loaded from the bundled CHANGELOG.md file.")
        subtitle.setObjectName("moduleSubtitle")
        card.layout().addWidget(subtitle)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setMinimumHeight(90)
        text.setMaximumHeight(180)
        text.setPlainText(load_changelog_text())
        card.layout().addWidget(text)
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

    def reload_categories(self):
        categories = notes_storage.note_categories()
        current_filter = self.category_filter.currentData() if hasattr(self, "category_filter") else "All"
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All categories", "All")
        for category in categories:
            self.category_filter.addItem(category, category)
        index = self.category_filter.findData(current_filter)
        self.category_filter.setCurrentIndex(index if index >= 0 else 0)
        self.category_filter.blockSignals(False)

        current_editor = self.category_input.currentText() if hasattr(self, "category_input") else "General"
        self.category_input.clear()
        self.category_input.addItems(categories)
        if current_editor:
            index = self.category_input.findText(current_editor)
            if index >= 0:
                self.category_input.setCurrentIndex(index)
            else:
                self.category_input.setEditText(current_editor)

    def reload_notes(self, *_args, select_id=None):
        query = self.search_input.text().strip()
        category = self.category_filter.currentData() or "All"
        self.notes = notes_storage.list_notes(query=query, category=category)

        sorting_enabled = self.notes_table.isSortingEnabled()
        self.notes_table.setSortingEnabled(False)
        self.notes_table.setRowCount(len(self.notes))
        for row, note in enumerate(self.notes):
            values = [
                "Yes" if note.is_pinned else "",
                note.title,
                note.category,
                note.modified_at,
            ]
            sort_values = [
                1 if note.is_pinned else 0,
                note.title.lower(),
                note.category.lower(),
                note.modified_at,
            ]
            for col, value in enumerate(values):
                item = SortableTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(SORT_ROLE, sort_values[col])
                item.setData(ROW_ROLE, row)
                item.setToolTip(str(value))
                self.notes_table.setItem(row, col, item)

        self.notes_table.setSortingEnabled(sorting_enabled)
        configure_readable_table_columns(self.notes_table, min_width=90, max_width=420, stretch_last=True)
        self.empty_label.setVisible(not self.notes)

        target_id = select_id or self.current_note_id
        if target_id:
            self.select_note(target_id)
        elif self.notes:
            self.notes_table.selectRow(0)
        else:
            self.new_note(update_status=False)

    def select_note(self, note_id):
        for row in range(self.notes_table.rowCount()):
            item = self.notes_table.item(row, 0)
            if not item:
                continue
            index = item.data(ROW_ROLE)
            if index is not None and index < len(self.notes) and self.notes[index].id == note_id:
                self.notes_table.selectRow(row)
                return

    def on_note_selected(self):
        row = self.notes_table.currentRow()
        if row < 0:
            return
        item = self.notes_table.item(row, 0)
        if not item:
            return
        index = item.data(ROW_ROLE)
        if index is None or index >= len(self.notes):
            return
        self.load_note(self.notes[index])

    def load_note(self, note):
        self.loading_editor = True
        self.current_note_id = note.id
        self.title_input.setText(note.title)
        self.category_input.setEditText(note.category)
        self.tags_input.setText(note.tags)
        self.pin_checkbox.setChecked(note.is_pinned)
        self.linked_type_input.setText(note.linked_type)
        self.linked_key_input.setText(note.linked_key)
        self.body_input.setPlainText(note.body)
        self.created_label.setText(f"Created: {note.created_at or '-'}")
        self.modified_label.setText(f"Modified: {note.modified_at or '-'}")
        self.delete_button.setEnabled(True)
        self.duplicate_button.setEnabled(True)
        self.loading_editor = False

    def new_note(self, update_status=True):
        self.current_note_id = None
        self.title_input.clear()
        self.category_input.setEditText("General")
        self.tags_input.clear()
        self.pin_checkbox.setChecked(False)
        self.linked_type_input.clear()
        self.linked_key_input.clear()
        self.body_input.clear()
        self.created_label.setText("Created: -")
        self.modified_label.setText("Modified: -")
        self.delete_button.setEnabled(False)
        self.duplicate_button.setEnabled(False)
        if update_status:
            self.status_label.setText("New note ready. Save when you are done.")

    def save_current_note(self):
        note = notes_storage.KnowledgeNote(
            id=self.current_note_id,
            title=self.title_input.text(),
            category=self.category_input.currentText(),
            tags=self.tags_input.text(),
            body=self.body_input.toPlainText(),
            linked_type=self.linked_type_input.text(),
            linked_key=self.linked_key_input.text(),
            is_pinned=self.pin_checkbox.isChecked(),
        )
        saved = notes_storage.save_note(note)
        self.current_note_id = saved.id
        self.reload_categories()
        self.reload_notes(select_id=saved.id)
        self.status_label.setText("Note saved locally.")

    def delete_current_note(self):
        if not self.current_note_id:
            return
        response = QMessageBox.question(
            self,
            "Delete Note",
            "Delete this local note?\n\nThis cannot be undone.",
            QMessageBox.Cancel | QMessageBox.Yes,
            QMessageBox.Cancel,
        )
        if response != QMessageBox.Yes:
            return
        deleted = notes_storage.delete_note(self.current_note_id)
        self.current_note_id = None
        self.reload_categories()
        self.reload_notes()
        self.status_label.setText(f"Deleted {deleted} note(s).")

    def duplicate_current_note(self):
        if not self.current_note_id:
            return
        duplicate = notes_storage.duplicate_note(self.current_note_id)
        self.reload_categories()
        self.reload_notes(select_id=duplicate.id)
        self.status_label.setText("Note duplicated locally.")


def load_changelog_text():
    changelog_path = bundled_path("CHANGELOG.md")
    if not changelog_path.exists():
        return "No bundled changelog was found for this build."

    return changelog_path.read_text(encoding="utf-8").strip()
