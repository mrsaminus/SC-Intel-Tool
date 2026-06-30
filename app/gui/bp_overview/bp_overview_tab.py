from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .blueprint_browser_tab import BlueprintBrowserTab
from .crafting_materials_tab import CraftingMaterialsTab
from .crafting_recipes_tab import CraftingRecipesTab
from .owned_blueprints_tab import OwnedBlueprintsTab
from .reward_scanner_tab import RewardScannerTab
from .source_missions_tab import SourceMissionsTab
from .shared import create_header


class BPOverviewTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(create_header(
            "BP Overview",
            "Blueprint and crafting reference with local ownership tracking.",
        ))

        self.tabs = QTabWidget()
        self.owned_tab = OwnedBlueprintsTab()
        self.scanner_tab = RewardScannerTab()
        self.browser_tab = BlueprintBrowserTab(
            owned_changed_callback=self.owned_tab.refresh_owned,
            blueprints_loaded_callback=self.scanner_tab.set_blueprints,
        )
        self.materials_tab = CraftingMaterialsTab(materials_changed_callback=self.browser_tab.refresh_material_context)
        self.scanner_tab.ownership_changed_callback = self.refresh_owned
        self.tabs.addTab(self.browser_tab, "Blueprint Browser")
        self.tabs.addTab(self.owned_tab, "Owned Blueprints")
        self.tabs.addTab(self.materials_tab, "Crafting Materials")
        self.tabs.addTab(CraftingRecipesTab(), "Crafting Recipes")
        self.tabs.addTab(SourceMissionsTab(), "Mission Context")
        self.tabs.addTab(self.scanner_tab, "Reward Scanner")
        layout.addWidget(self.tabs, 1)

        self.setLayout(layout)

    def refresh_owned(self):
        self.browser_tab.refresh_owned_keys()
        self.owned_tab.refresh_owned()

    def ensure_initial_load(self):
        self.browser_tab.ensure_initial_load()
