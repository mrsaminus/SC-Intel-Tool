from .shared import *


class MiningOreFinderMixin:
    def build_ore_finder_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("ORE SEARCH")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.ore_search_input = QLineEdit()
        self.ore_search_input.setPlaceholderText("Search mineral...")
        self.ore_system_filter = self.create_combo(["All systems", "Stanton", "Pyro", "Nyx", "Unknown"])
        self.ore_type_filter = self.create_combo(["All deposits", "Surface", "Asteroid", "General"])
        row.addWidget(self.ore_search_input, 1)
        row.addWidget(self.ore_system_filter)
        row.addWidget(self.ore_type_filter)
        filter_layout.addLayout(row)

        uex_row = QHBoxLayout()
        self.uex_status_label = QLabel("UEX prices are live/in-memory only. No local price cache is used.")
        self.uex_status_label.setObjectName("moduleSubtitle")
        self.refresh_uex_prices_button = QPushButton("Refresh Visible UEX Prices")
        uex_row.addWidget(self.uex_status_label, 1)
        uex_row.addWidget(self.refresh_uex_prices_button)
        filter_layout.addLayout(uex_row)
        layout.addWidget(filter_card)

        self.ore_results_table = self.create_table([
            "Mineral",
            "System",
            "Body / Area",
            "Deposit",
            "UEX Sell",
            "Best UEX Terminal",
            "Notes",
        ])
        configure_readable_table_columns(self.ore_results_table, stretch_last=True)
        layout.addWidget(self.ore_results_table, 1)
        self.ore_empty_label = self.create_empty_state("No ore results match the current filters.")
        layout.addWidget(self.ore_empty_label)
        widget.setLayout(layout)
        return widget


    def populate_ore_results(self):
        query = self.ore_search_input.text().strip().lower()
        system_filter = self.ore_system_filter.currentText()
        deposit_filter = self.ore_type_filter.currentText()
        rows = []

        for location in self.mining_data.locations:
            if system_filter != "All systems" and location.system != system_filter:
                continue
            if deposit_filter != "All deposits" and location.deposit_type != deposit_filter:
                continue
            if query and query not in self.location_search_text(location):
                continue

            price = self.uex_prices.get(location.mineral.lower())
            rows.append([
                location.mineral,
                location.system,
                location.body,
                location.deposit_type,
                self.format_price(price.price_sell if price else None),
                self.format_uex_terminal(price),
                location.notes or "",
            ])

        rows.sort(key=lambda row: (row[0].lower(), row[1], row[2].lower(), row[3]))
        self.set_table_rows(self.ore_results_table, rows)
        self.ore_results_columns_sized = True
        self.ore_empty_label.setVisible(not rows)


    def refresh_visible_uex_prices(self):
        if self.uex_refresh_running:
            return

        minerals = self.visible_ore_minerals()
        if not minerals:
            QMessageBox.information(
                self,
                "No visible ores",
                "No visible ore rows to refresh.",
            )
            return

        self.uex_refresh_running = True
        self.refresh_uex_prices_button.setEnabled(False)
        self.refresh_uex_prices_button.setText("Refreshing UEX...")

        def load_prices():
            refreshed = 0
            failed = []
            prices_by_mineral = {}
            for mineral in minerals:
                try:
                    prices = fetch_commodity_sell_prices(mineral)
                except (UEXError, requests.RequestException, ValueError) as exc:
                    failed.append(f"{mineral}: {exc}")
                    continue

                prices_by_mineral[mineral.lower()] = prices[0] if prices else None
                refreshed += 1

            return {
                "minerals": minerals,
                "prices": prices_by_mineral,
                "refreshed": refreshed,
                "failed": failed,
            }

        self.start_background_task(
            load_prices,
            self.on_visible_uex_prices_refreshed,
            self.on_visible_uex_prices_error,
            self.finish_visible_uex_prices_refresh,
        )


    def on_visible_uex_prices_refreshed(self, result):
        self.uex_prices.update(result["prices"])
        self.ore_results_columns_sized = False
        self.populate_ore_results()
        failed = result["failed"]
        minerals = result["minerals"]
        refreshed = result["refreshed"]
        if failed:
            self.uex_status_label.setText(
                f"UEX refreshed {refreshed}/{len(minerals)} minerals; "
                f"{len(failed)} failed. Prices are not stored locally."
            )
            QMessageBox.warning(
                self,
                "UEX refresh incomplete",
                "\n".join(failed[:5]),
            )
        else:
            self.uex_status_label.setText(
                f"UEX refreshed {refreshed} visible minerals. Prices are not stored locally."
            )


    def on_visible_uex_prices_error(self, exc):
        self.uex_status_label.setText(f"UEX refresh failed: {exc}")
        QMessageBox.critical(self, "UEX refresh failed", str(exc))


    def finish_visible_uex_prices_refresh(self):
        self.uex_refresh_running = False
        self.refresh_uex_prices_button.setEnabled(True)
        self.refresh_uex_prices_button.setText("Refresh Visible UEX Prices")


    def visible_ore_minerals(self):
        minerals = {
            self.ore_results_table.item(row, 0).text()
            for row in range(self.ore_results_table.rowCount())
            if self.ore_results_table.item(row, 0)
        }
        return sorted(minerals)


    def format_uex_terminal(self, price):
        if not price:
            return "Refresh UEX"

        location = price.location_name if price.location_name != "N/A" else price.star_system_name
        if location and location != "N/A":
            return f"{location} / {price.terminal_name}"

        return price.terminal_name

