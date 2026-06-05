from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .shared import create_card


class CraftingRecipesTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        card = create_card("CRAFTING RECIPES")
        text = QLabel(
            "Recipe and material details are shown in the Blueprint Browser details panel. "
            "This alpha keeps the recipe workflow tied to the selected blueprint so the app only "
            "shows fields that SC Craft Tools exposes publicly: ingredients, quantities, "
            "quality/effect hints, craft time and mission drops when available."
        )
        text.setObjectName("valueText")
        text.setWordWrap(True)
        card.layout().addWidget(text)

        limitations = QLabel(
            "Deferred: OCR/screen-reader capture, account sync and deeper in-game inventory import. "
            "Owned blueprint state remains local SQLite data only."
        )
        limitations.setObjectName("moduleSubtitle")
        limitations.setWordWrap(True)
        card.layout().addWidget(limitations)

        layout.addWidget(card)
        layout.addStretch(1)
        self.setLayout(layout)
