from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.blueprints_storage import list_owned_blueprints

from .shared import ROW_ROLE, create_card, create_table, table_item


class OwnedBlueprintsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.owned_rows = []

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        card = create_card("OWNED BLUEPRINTS")
        card_layout = card.layout()

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_owned)
        self.status_label = QLabel("")
        self.status_label.setObjectName("moduleSubtitle")
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.status_label, 1)
        card_layout.addLayout(controls)

        self.owned_table = create_table([
            "Blueprint",
            "Source",
            "Acquired",
            "Updated",
            "Notes",
        ])
        card_layout.addWidget(self.owned_table, 1)

        self.empty_label = QLabel("No owned blueprints marked yet.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.empty_label)

        layout.addWidget(card, 1)
        self.setLayout(layout)
        self.refresh_owned()

    def refresh_owned(self, *_):
        self.owned_rows = list_owned_blueprints()
        self.owned_table.setSortingEnabled(False)
        self.owned_table.setRowCount(len(self.owned_rows))
        for row, owned in enumerate(self.owned_rows):
            values = [
                owned.get("blueprint_name") or owned.get("blueprint_key") or "",
                owned.get("source") or "",
                owned.get("acquired_at") or "",
                owned.get("updated_at") or "",
                owned.get("notes") or "",
            ]
            for column, value in enumerate(values):
                item = table_item(value)
                item.setData(ROW_ROLE, row)
                self.owned_table.setItem(row, column, item)
        self.owned_table.setSortingEnabled(True)
        self.empty_label.setVisible(not self.owned_rows)
        self.status_label.setText(f"{len(self.owned_rows)} owned blueprints tracked locally.")
