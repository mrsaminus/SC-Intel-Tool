from .shared import *
from app.local_cache import (
    ITEM_FINDER_CACHE_KEY,
    cache_is_fresh,
    get_cache_metadata,
    load_item_finder_cache,
    mark_cache_error,
    save_item_finder_cache,
)


class ItemFinderDataMixin:
    def ensure_finder_data_then_search(self):
        self.item_filter_timer.stop()
        if self.finder_data_is_stale():
            if self.finder_items:
                self.update_finder_cache_status_label()
                self.populate_item_results()
                return
            if self.load_finder_cache_if_available():
                self.populate_item_results()
                return
            self.refresh_finder_items()
            return

        self.populate_item_results()


    def finder_data_is_stale(self):
        if not self.finder_items or not self.finder_last_refresh:
            return True
        metadata = get_cache_metadata(ITEM_FINDER_CACHE_KEY)
        if metadata:
            return not cache_is_fresh(ITEM_FINDER_CACHE_KEY)

        return datetime.now() - self.finder_last_refresh >= self.finder_refresh_interval


    def load_finder_cache_if_available(self):
        items, cstone_locations, metadata = load_item_finder_cache()
        if not items:
            return False

        self.finder_items = items
        self.cstone_location_names = cstone_locations
        self.location_search_cache.clear()
        self.item_location_cache.clear()
        self.finder_last_refresh = datetime.now()
        if not self.finder_refresh_timer.isActive():
            self.finder_refresh_timer.start()
        self.update_finder_cache_status_label(metadata)
        return True


    def update_finder_cache_status_label(self, metadata=None):
        metadata = metadata or get_cache_metadata(ITEM_FINDER_CACHE_KEY)
        if metadata and cache_is_fresh(ITEM_FINDER_CACHE_KEY):
            self.finder_status_label.setText(
                f"Loaded {len(self.finder_items)} cached item rows. Cache is fresh for up to 6 hours."
            )
        else:
            self.finder_status_label.setText(
                f"Loaded {len(self.finder_items)} cached item rows. Refresh live data when you want the latest sources."
            )


    def refresh_finder_items(self, silent=False):
        if self.finder_refresh_running:
            return

        self.finder_refresh_running = True
        self.refresh_finder_items_button.setEnabled(False)
        self.refresh_finder_items_button.setText("Refreshing...")

        def load_items():
            loaded_items = []
            failed = []
            cstone_locations = []
            try:
                loaded_items.extend(fetch_cstone_items())
            except (CStoneError, requests.RequestException, ValueError) as exc:
                failed.append(f"Cornerstone: {exc}")

            try:
                cstone_locations = fetch_cstone_location_names()
            except (CStoneError, requests.RequestException, ValueError) as exc:
                failed.append(f"Cornerstone locations: {exc}")

            try:
                loaded_items.extend(fetch_scfocus_ship_items())
            except (requests.RequestException, ValueError) as exc:
                failed.append(f"SC Focus: {exc}")

            return {
                "loaded_items": loaded_items,
                "cstone_locations": cstone_locations,
                "failed": failed,
                "silent": silent,
            }

        self.start_background_task(
            load_items,
            self.on_finder_items_refreshed,
            self.on_finder_items_refresh_error,
            self.finish_finder_items_refresh,
        )


    def on_finder_items_refreshed(self, result):
        loaded_items = result["loaded_items"]
        cstone_locations = result["cstone_locations"]
        failed = result["failed"]
        silent = result["silent"]

        if loaded_items:
            self.finder_items = loaded_items
            self.cstone_location_names = cstone_locations
            self.location_search_cache.clear()
            self.item_location_cache.clear()
            self.finder_last_refresh = datetime.now()
            save_item_finder_cache(loaded_items, cstone_locations, failed)
            if not self.finder_refresh_timer.isActive():
                self.finder_refresh_timer.start()
        elif failed:
            mark_cache_error(
                ITEM_FINDER_CACHE_KEY,
                "Cornerstone + SC Focus",
                "1",
                "; ".join(failed),
            )

        if failed:
            self.finder_status_label.setText(
                f"Loaded {len(self.finder_items)} rows with {len(failed)} source warning(s). "
                "Cached data remains available locally."
            )
            if not silent:
                QMessageBox.warning(self, "Live refresh warning", "\n".join(failed))
        else:
            self.finder_status_label.setText(
                f"Loaded {len(self.finder_items)} live rows and {len(self.cstone_location_names)} Cornerstone locations. "
                "Cached locally for faster reuse."
            )

        self.populate_item_results()


    def on_finder_items_refresh_error(self, exc):
        mark_cache_error(ITEM_FINDER_CACHE_KEY, "Cornerstone + SC Focus", "1", str(exc))
        self.finder_status_label.setText(f"Live data refresh failed: {exc}")
        QMessageBox.critical(self, "Live refresh failed", str(exc))


    def finish_finder_items_refresh(self):
        self.finder_refresh_running = False
        self.refresh_finder_items_button.setEnabled(True)
        self.refresh_finder_items_button.setText("Refresh Live Data")

