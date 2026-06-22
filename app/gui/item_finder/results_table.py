from .shared import *


class ItemResultsTableMixin:
    def populate_item_results(self):
        query = self.item_search_input.text().strip().lower()
        category_filter = self.item_category_filter.currentText()
        raw_visible_items = []
        visible_keys = set()

        for item in self.finder_items:
            if not self.item_matches_category(item, category_filter):
                continue
            searchable = self.item_search_text(item)
            if query and query not in searchable:
                continue
            raw_visible_items.append(item)
            visible_keys.add(self.finder_item_key(item))

        for item in self.cached_location_search_items(query, category_filter):
            key = self.finder_item_key(item)
            if key in visible_keys:
                continue
            raw_visible_items.append(item)
            visible_keys.add(key)

        self.visible_finder_items = self.deduplicated_visible_items(raw_visible_items, category_filter)
        self.update_item_result_columns(category_filter, self.visible_finder_items)
        self.item_results_table.setUpdatesEnabled(False)
        self.item_results_table.setSortingEnabled(False)
        try:
            self.item_results_table.clearSelection()
            self.item_results_table.setRowCount(len(self.visible_finder_items))
            for row_index, item in enumerate(self.visible_finder_items):
                values = [
                    item.name,
                    item.category,
                    item.item_type,
                    self.display_item_availability(item),
                    self.item_summary_text(item, category_filter),
                ]
                for col_index, value in enumerate(values):
                    table_item = SortableTableWidgetItem(str(value))
                    table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                    table_item.setData(Qt.UserRole, row_index)
                    table_item.setData(SORT_ROLE, self.item_sort_value(item, col_index, value, category_filter))
                    table_item.setToolTip(str(value))
                    if col_index == 3:
                        table_item.setForeground(QColor("#68e6a5" if item.sold else "#7bb9c8"))
                    self.item_results_table.setItem(row_index, col_index, table_item)
            configure_readable_table_columns(self.item_results_table, min_width=110, max_width=360, stretch_last=True)
        finally:
            self.item_results_table.setSortingEnabled(True)
            self.item_results_table.setUpdatesEnabled(True)

        self.item_empty_label.setVisible(not self.visible_finder_items)
        if not self.finder_items:
            self.item_empty_label.setText("No item data loaded yet.")
        else:
            self.item_empty_label.setText("No items match the current filters.")
        self.update_selected_item_panel()
        self.schedule_location_search_if_needed(query, category_filter)
        self.schedule_availability_autoload()


    def update_item_result_columns(self, category_filter, visible_items):
        summary_header = "Lowest Price" if category_filter in {SHIP_SALE_CATEGORY, SHIP_RENT_CATEGORY} else "Summary"
        self.item_results_table.horizontalHeaderItem(4).setText(summary_header)
        self.item_results_table.setColumnHidden(2, self.hide_type_column_for_category(category_filter, visible_items))


    def hide_type_column_for_category(self, category_filter, visible_items):
        if not category_filter.startswith("Armor - ") or not visible_items:
            return False

        expected = self.normalized_armor_type(category_filter)
        return all(
            self.normalized_armor_type(item.item_type) in {expected, category_filter.lower().replace("armor - ", "")}
            for item in visible_items
        )


    def normalized_armor_type(self, value):
        text = str(value or "").lower().replace("armor - ", "").replace("armor", "").strip()
        if text.endswith("s"):
            text = text[:-1]
        if text == "torso":
            return "core"

        return text


    def item_matches_category(self, item, category_filter):
        if category_filter == "All categories":
            return True
        if category_filter == SHIP_SALE_CATEGORY:
            return self.is_ship_sale_item(item)
        if category_filter == SHIP_RENT_CATEGORY:
            return self.is_ship_rent_item(item)

        return item.category == category_filter


    def deduplicated_visible_items(self, items, category_filter):
        groups = {}
        ordered_items = []

        for item in items:
            group_key = self.ship_group_key(item, category_filter)
            if not group_key:
                ordered_items.append(item)
                continue

            if group_key not in groups:
                groups[group_key] = []
                ordered_items.append(group_key)
            groups[group_key].append(item)

        deduplicated = []
        for entry in ordered_items:
            if isinstance(entry, tuple):
                deduplicated.append(self.merged_ship_item(groups[entry], entry[0]))
            else:
                deduplicated.append(entry)

        return deduplicated


    def item_search_text(self, item):
        parts = [
            item.name,
            item.source,
            item.category,
            item.item_type,
            item.availability,
            item.effect,
        ]
        if hasattr(item, "locations"):
            for location in item.locations:
                parts.extend((location.location, location.price, location.verified))

        return " ".join(str(part) for part in parts if part).lower()


    def schedule_item_results_refresh(self):
        self.item_filter_timer.start()

