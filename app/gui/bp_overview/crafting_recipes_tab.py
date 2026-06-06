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
            "shows confirmed crafting fields: ingredients, quantities, quality scaling, "
            "craft time and mission drops when available."
        )
        text.setObjectName("valueText")
        text.setWordWrap(True)
        card.layout().addWidget(text)

        limitations = QLabel(
            "Reward Scanner alpha is available as an optional, local-only confirmation workflow. "
            "Full OCR engine packaging, account sync and deeper in-game inventory import remain deferred. "
            "Owned blueprint and material state remains local SQLite data only."
        )
        limitations.setObjectName("moduleSubtitle")
        limitations.setWordWrap(True)
        card.layout().addWidget(limitations)

        layout.addWidget(card)
        layout.addStretch(1)
        self.setLayout(layout)
