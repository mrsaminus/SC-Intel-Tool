from .shared import *


class ItemFinderLocationMixin:
    def cached_location_search_items(self, query, category_filter):
        if category_filter != "All categories" or len(query) < 3:
            return []

        return self.location_search_cache.get(query, [])


    def schedule_location_search_if_needed(self, query, category_filter):
        if category_filter != "All categories" or len(query) < 3:
            return
        if not self.cstone_location_names or self.location_search_running:
            return
        if query in self.location_search_cache:
            return

        matching_locations = self.matching_cstone_locations(query)
        if not matching_locations:
            return

        if len(matching_locations) > self.location_search_limit:
            self.finder_status_label.setText(
                f"{len(matching_locations)} Cornerstone locations match '{query}'. "
                f"Keep filtering to {self.location_search_limit} or fewer locations to load shop items."
            )
            return

        self.location_search_running = True
        self.location_search_request_id += 1
        request_id = self.location_search_request_id
        self.finder_status_label.setText(
            f"Loading shop inventory for {len(matching_locations)} location(s) matching '{query}'..."
        )

        def load_location_inventory():
            results = []
            failures = []
            for location in matching_locations:
                try:
                    results.extend(fetch_cstone_location_inventory(location))
                except (CStoneError, requests.RequestException, ValueError) as exc:
                    failures.append(f"{location}: {exc}")

            return {
                "request_id": request_id,
                "query": query,
                "locations": matching_locations,
                "results": results,
                "failures": failures,
            }

        self.start_background_task(
            load_location_inventory,
            self.on_location_search_loaded,
            self.on_location_search_error,
            lambda requested_id=request_id: self.finish_location_search(requested_id),
        )


    def matching_cstone_locations(self, query):
        return [
            location
            for location in self.cstone_location_names
            if query in location.lower()
        ]


    def on_location_search_loaded(self, result):
        request_id = result["request_id"]
        query = result["query"]
        if request_id != self.location_search_request_id:
            return

        items = []
        for inventory_item in result["results"]:
            item = self.location_inventory_to_item(inventory_item)
            key = self.finder_item_key(item)
            self.availability_counts[key] = 1
            self.item_location_cache[key] = [CStoneLocation(
                location=inventory_item.location,
                price=inventory_item.price,
                verified="Cornerstone",
                url=inventory_item.location_url,
            )]
            items.append(item)

        self.location_search_cache[query] = items
        if result["failures"]:
            self.finder_status_label.setText(
                f"Loaded {len(items)} shop rows from {len(result['locations'])} matching location(s), "
                f"with {len(result['failures'])} warning(s)."
            )
        else:
            self.finder_status_label.setText(
                f"Loaded {len(items)} shop rows from {len(result['locations'])} matching location(s)."
            )

        if self.item_search_input.text().strip().lower() == query:
            self.populate_item_results()


    def on_location_search_error(self, exc):
        self.finder_status_label.setText(f"Location inventory lookup failed: {exc}")


    def finish_location_search(self, request_id):
        if request_id != self.location_search_request_id:
            return

        self.location_search_running = False
        query = self.item_search_input.text().strip().lower()
        category_filter = self.item_category_filter.currentText()
        if query and query not in self.location_search_cache:
            self.schedule_location_search_if_needed(query, category_filter)


    def location_inventory_to_item(self, inventory_item):
        return CStoneItem(
            item_id=f"location:{inventory_item.item_id}:{inventory_item.location}",
            name=inventory_item.name,
            category="Location Search",
            size=inventory_item.size,
            sold=True,
            detail_url=inventory_item.detail_url,
            category_url=inventory_item.location_url,
            effect=f"{inventory_item.location} | {inventory_item.price}",
            source="Cornerstone",
            item_type=inventory_item.item_type,
            availability="1 location",
        )


    def display_item_availability(self, item):
        locations = self.known_item_locations(item)
        if locations is not None:
            return self.location_availability_text(locations)

        if item.source != "Cornerstone":
            return item.availability

        key = self.finder_item_key(item)
        if key in self.availability_counts:
            return self.location_count_text(self.availability_counts[key])

        pending = self.pending_visible_cornerstone_items()
        if len(pending) <= self.auto_availability_limit:
            return "Checking..."

        return "Filter more"


    def schedule_availability_autoload(self):
        if self.auto_loading_availability or self.availability_auto_load_scheduled:
            return

        pending = self.pending_visible_cornerstone_items()
        if not pending:
            return

        if len(pending) > self.auto_availability_limit:
            self.finder_status_label.setText(
                f"{len(pending)} visible Cornerstone items need location counts. "
                f"Keep filtering to {self.auto_availability_limit} or fewer items to load location counts automatically."
            )
            return

        self.availability_auto_load_scheduled = True
        QTimer.singleShot(0, self.auto_load_visible_availability)


    def auto_load_visible_availability(self):
        self.availability_auto_load_scheduled = False
        pending = self.pending_visible_cornerstone_items()
        if not pending or len(pending) > self.auto_availability_limit:
            return

        self.auto_loading_availability = True
        self.finder_status_label.setText(f"Loading availability for {len(pending)} visible rows...")

        def load_availability():
            results = []
            for item in pending:
                try:
                    locations = fetch_cstone_item_locations(item.detail_url)
                except (CStoneError, requests.RequestException, ValueError):
                    locations = []
                results.append((item, locations))
            return results

        self.start_background_task(
            load_availability,
            self.on_visible_availability_loaded,
            self.on_visible_availability_error,
            self.finish_visible_availability_load,
        )


    def on_visible_availability_loaded(self, results):
        selected = self.selected_item()
        selected_key = self.finder_item_key(selected) if selected else None
        for item, locations in results:
            self.set_item_availability_locations(item, locations)
            if selected_key == self.finder_item_key(item):
                self.finder_locations = locations
                self.populate_location_rows()

        self.finder_status_label.setText("Availability loaded for visible rows.")


    def on_visible_availability_error(self, exc):
        self.finder_status_label.setText(f"Availability lookup failed: {exc}")


    def finish_visible_availability_load(self):
        self.auto_loading_availability = False
        self.schedule_availability_autoload()


    def pending_visible_cornerstone_items(self):
        pending = []
        seen = set()
        for item in self.visible_finder_items:
            key = self.finder_item_key(item)
            if item.source == "Cornerstone" and key not in self.availability_counts and key not in seen:
                pending.append(item)
                seen.add(key)

        return pending


    def load_selected_item_locations(self):
        item = self.selected_item()
        if not item:
            return

        self.item_location_request_id += 1
        request_id = self.item_location_request_id
        self.item_locations_loading = True
        self.load_item_locations_button.setEnabled(False)
        self.load_item_locations_button.setText("Loading...")

        cached_locations = self.item_location_cache.get(self.finder_item_key(item))
        if cached_locations is not None:
            if request_id == self.item_location_request_id:
                self.finder_locations = list(cached_locations)
                self.populate_location_rows()
            self.finish_selected_item_locations_load(request_id)
            return

        if item.source == "SC Focus":
            if request_id == self.item_location_request_id:
                self.finder_locations = list(item.locations)
                self.populate_location_rows()
            self.finish_selected_item_locations_load(request_id)
            return

        def load_locations():
            return fetch_cstone_item_locations(item.detail_url)

        self.start_background_task(
            load_locations,
            lambda locations, requested_item=item, requested_id=request_id: self.on_selected_item_locations_loaded(
                requested_id,
                requested_item,
                locations,
            ),
            lambda exc, requested_item=item, requested_id=request_id: self.on_selected_item_locations_error(
                requested_id,
                requested_item,
                exc,
            ),
            lambda requested_id=request_id: self.finish_selected_item_locations_load(requested_id),
        )


    def on_selected_item_locations_loaded(self, request_id, requested_item, locations):
        if request_id != self.item_location_request_id:
            return

        self.set_item_availability_locations(requested_item, locations)
        selected = self.selected_item()
        if selected and self.finder_item_key(selected) == self.finder_item_key(requested_item):
            self.finder_locations = locations
            self.populate_location_rows()


    def on_selected_item_locations_error(self, request_id, requested_item, exc):
        if request_id != self.item_location_request_id:
            return

        selected = self.selected_item()
        if selected and self.finder_item_key(selected) == self.finder_item_key(requested_item):
            QMessageBox.warning(self, "Location lookup failed", str(exc))
            self.finder_locations = []
            self.populate_location_rows()


    def finish_selected_item_locations_load(self, request_id=None):
        if request_id is not None and request_id != self.item_location_request_id:
            return

        self.item_locations_loading = False
        self.load_item_locations_button.setEnabled(bool(self.selected_item()))
        self.load_item_locations_button.setText("Reload Locations")


    def set_item_availability_count(self, item, location_count):
        if not item or item.source != "Cornerstone":
            return

        key = self.finder_item_key(item)
        locations = self.item_location_cache.get(key)
        availability = (
            self.location_availability_text(locations)
            if locations is not None
            else self.location_count_text(location_count)
        )
        self.availability_counts[key] = location_count
        updated_item = replace(item, availability=availability)

        for item_index, visible_item in enumerate(self.visible_finder_items):
            if self.finder_item_key(visible_item) == key:
                self.visible_finder_items[item_index] = updated_item

        for full_index, full_item in enumerate(self.finder_items):
            if self.finder_item_key(full_item) == key:
                self.finder_items[full_index] = updated_item
                break

        self.update_visible_availability_cells(key, availability)
        selected = self.selected_item()
        if selected and self.finder_item_key(selected) == key:
            self.selected_item_category_label.setText(
                f"{updated_item.category} | {updated_item.item_type} | {availability} | Source: {updated_item.source}"
            )


    def set_item_availability_locations(self, item, locations):
        key = self.finder_item_key(item)
        self.item_location_cache[key] = list(locations)
        self.set_item_availability_count(item, len(locations))


    def update_visible_availability_cells(self, key, availability):
        for row in range(self.item_results_table.rowCount()):
            item = self.item_results_table.item(row, 0)
            if not item:
                continue

            index = item.data(Qt.UserRole)
            if index is None or index >= len(self.visible_finder_items):
                continue

            visible_item = self.visible_finder_items[index]
            if self.finder_item_key(visible_item) == key:
                availability_item = self.item_results_table.item(row, 3)
                if availability_item:
                    availability_item.setText(availability)


    def known_item_locations(self, item):
        if hasattr(item, "locations"):
            return list(item.locations)

        return self.item_location_cache.get(self.finder_item_key(item))


    def location_availability_text(self, locations):
        if len(locations) == 1:
            return locations[0].location

        return self.location_count_text(len(locations))


    def populate_location_rows(self):
        self.item_locations_table.setSortingEnabled(False)
        self.item_locations_table.clearSelection()
        self.item_locations_table.setRowCount(len(self.finder_locations))
        for row_index, location in enumerate(self.finder_locations):
            for col_index, value in enumerate((
                location.location,
                location.price,
                location.verified,
            )):
                table_item = QTableWidgetItem(str(value))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                table_item.setData(Qt.UserRole, row_index)
                table_item.setToolTip(str(value))
                if col_index == 1:
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.item_locations_table.setItem(row_index, col_index, table_item)

        configure_readable_table_columns(self.item_locations_table, min_width=110, max_width=420, stretch_last=True)
        self.item_locations_table.setSortingEnabled(True)
        self.item_location_empty_label.setVisible(not self.finder_locations)
        if self.finder_locations:
            self.item_locations_table.selectRow(0)
        self.update_location_action_state()


    def selected_location_url(self):
        row = self.item_locations_table.currentRow()
        if row < 0:
            return None

        item = self.item_locations_table.item(row, 0)
        if not item:
            return None

        index = item.data(Qt.UserRole)
        if index is None or index >= len(self.finder_locations):
            return None

        return self.finder_locations[index].url


    def open_selected_location(self):
        url = self.selected_location_url()
        if url:
            QDesktopServices.openUrl(QUrl(url))

