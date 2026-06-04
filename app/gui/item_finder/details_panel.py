from .shared import *


class ItemDetailsPanelMixin:
    def on_selected_item_changed(self):
        previous_item_id = self.current_finder_item_id
        item = self.selected_item()
        self.update_selected_item_panel()
        if item and item.item_id != previous_item_id:
            self.load_selected_item_locations()


    def update_selected_item_panel(self):
        item = self.selected_item()
        has_item = item is not None
        self.load_item_locations_button.setEnabled(has_item)
        self.open_selected_item_button.setEnabled(has_item)
        self.open_selected_location_button.setEnabled(bool(self.selected_location_url()))

        if not item:
            self.current_finder_item_id = None
            self.selected_item_name_label.setText("No item selected")
            self.selected_item_category_label.setText("")
            self.selected_ship_metadata_label.setText("")
            self.selected_ship_metadata_label.setVisible(False)
            self.selected_item_effect_label.setText("")
            self.finder_locations = []
            self.item_locations_table.setRowCount(0)
            self.item_location_empty_label.setVisible(True)
            self.item_location_empty_label.setText("Select an item and load buy locations.")
            return

        if item.item_id != self.current_finder_item_id:
            self.current_finder_item_id = item.item_id
            self.finder_locations = []
            self.item_locations_table.setRowCount(0)
            self.item_location_empty_label.setVisible(True)
            self.item_location_empty_label.setText("Load buy locations for the selected item.")

        self.selected_item_name_label.setText(item.name)
        self.selected_item_category_label.setText(
            f"{item.category} | {item.item_type} | {self.display_item_availability(item)} | Source: {item.source}"
        )
        self.selected_ship_metadata_label.setVisible(self.is_ship_item(item))
        self.selected_ship_metadata_label.setText(self.ship_metadata_text(item) if self.is_ship_item(item) else "")
        self.selected_item_effect_label.setText(item.effect)
        self.update_location_action_state()


    def update_location_action_state(self):
        self.open_selected_location_button.setEnabled(bool(self.selected_location_url()))


    def selected_item(self):
        row = self.item_results_table.currentRow()
        if row < 0:
            return None

        item = self.item_results_table.item(row, 0)
        if not item:
            return None

        index = item.data(Qt.UserRole)
        if index is None or index >= len(self.visible_finder_items):
            return None

        return self.visible_finder_items[index]


    def open_source_home(self):
        item = self.selected_item()
        if item and item.source == "SC Focus":
            QDesktopServices.openUrl(QUrl(SCFOCUS_SHIPS_URL))
            return

        if not item and self.is_scfocus_ship_category(self.item_category_filter.currentText()):
            QDesktopServices.openUrl(QUrl(SCFOCUS_SHIPS_URL))
            return

        QDesktopServices.openUrl(QUrl(CSTONE_HOME_URL))


    def open_selected_category(self):
        item = self.selected_item()
        if item:
            QDesktopServices.openUrl(QUrl(item.category_url))
            return

        category = self.item_category_filter.currentText()
        if self.is_scfocus_ship_category(category):
            QDesktopServices.openUrl(QUrl(SCFOCUS_SHIPS_URL))
            return

        QDesktopServices.openUrl(QUrl(cstone_category_url(category)))


    def is_scfocus_ship_category(self, category):
        return category in {
            "Ships for Sale",
            "Ships for Rent",
            WIKELO_CATEGORY,
            "Special Acquisition Ships",
        }


    def open_selected_item(self):
        item = self.selected_item()
        if item:
            QDesktopServices.openUrl(QUrl(item.detail_url))

