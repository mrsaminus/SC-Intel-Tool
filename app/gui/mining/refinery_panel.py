from .shared import *


class MiningRefineryMixin:
    def refinery_station_options(self):
        return self.unique_options(
            ["Any refinery", "No Refinery (Sell Raw Ore)"]
            + [station.display_name for station in self.mining_data.refinery_stations]
            + REFINERY_STATIONS
        )


    def refinery_method_options(self):
        return self.unique_options(
            [method.name for method in self.mining_data.refinery_methods]
            + REFINERY_METHODS
        )


    def build_refinery_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.refinery_session_tabs = QTabWidget()
        self.refinery_session_tabs.setMaximumHeight(44)
        layout.addWidget(self.refinery_session_tabs)

        self.refinery_stack = QStackedWidget()

        work_widget = QWidget()
        work_widget.setMinimumSize(980, 700)
        work_layout = QVBoxLayout()
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(12)

        content = QHBoxLayout()
        content.setSpacing(12)

        input_card = self.create_filter_card("SHIP ORES / REFINING")
        input_card.setMinimumWidth(600)
        input_layout = input_card.layout()

        session_row = QHBoxLayout()
        self.refinery_session_name_input = QLineEdit()
        self.refinery_session_name_input.setPlaceholderText("Session name...")
        self.refinery_new_session_button = QPushButton("New Session")
        self.refinery_save_session_button = QPushButton("Save To History")
        self.refinery_close_session_button = QPushButton("Close Session")
        self.refinery_session_name_input.setMinimumWidth(170)
        for button in (
            self.refinery_new_session_button,
            self.refinery_save_session_button,
            self.refinery_close_session_button,
        ):
            button.setMinimumWidth(110)
        session_row.addWidget(self.refinery_session_name_input, 1)
        session_row.addWidget(self.refinery_new_session_button)
        session_row.addWidget(self.refinery_save_session_button)
        session_row.addWidget(self.refinery_close_session_button)
        input_layout.addLayout(session_row)

        setup_row = QHBoxLayout()
        self.refinery_station_filter = self.create_combo(self.refinery_station_options())
        self.refinery_method_filter = self.create_combo(self.refinery_method_options())
        self.refinery_station_filter.setMinimumWidth(280)
        self.refinery_method_filter.setMinimumWidth(220)
        setup_row.addWidget(self.refinery_station_filter, 1)
        setup_row.addWidget(self.refinery_method_filter, 1)
        input_layout.addLayout(setup_row)

        self.add_refinery_material_section(input_layout, "ORE CHOOSER", SHIP_ORE_MATERIALS, columns=6)
        self.add_refinery_material_section(input_layout, "SALVAGE", SALVAGE_REFINERY_MATERIALS, columns=3)
        self.add_refinery_material_section(
            input_layout,
            "GEM SELLING (NO REFINING)",
            GEM_SELLING_MATERIALS,
            columns=5,
        )

        material_actions = QHBoxLayout()
        all_button = QPushButton("ALL")
        all_button.clicked.connect(self.add_all_refinery_materials)
        none_button = QPushButton("NONE")
        none_button.clicked.connect(self.clear_refinery_session)
        material_actions.addWidget(all_button)
        material_actions.addWidget(none_button)
        material_actions.addStretch(1)
        input_layout.addLayout(material_actions)

        table_actions = QHBoxLayout()
        self.refinery_remove_material_button = QPushButton("Remove Selected Material")
        self.refinery_refresh_uex_button = QPushButton("Refresh UEX For Session")
        self.refinery_remove_material_button.setMinimumWidth(180)
        self.refinery_refresh_uex_button.setMinimumWidth(180)
        table_actions.addWidget(self.refinery_remove_material_button)
        table_actions.addWidget(self.refinery_refresh_uex_button)
        input_layout.addLayout(table_actions)

        self.refinery_table = self.create_table([
            "Material",
            "QTY (cSCU)",
            "QTY (SCU)",
            "Yield (cSCU)",
            "Yield (SCU)",
            "UEX Sell",
            "Sell Value",
        ])
        self.refinery_table.setSortingEnabled(False)
        self.refinery_table.setMinimumHeight(240)
        configure_readable_table_columns(self.refinery_table, min_width=96, max_width=180, stretch_last=True)
        self.refinery_table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.AnyKeyPressed
            | QAbstractItemView.EditKeyPressed
        )
        input_layout.addWidget(self.refinery_table, 1)
        self.refinery_empty_label = self.create_empty_state("No material selected for this refining session.")
        input_layout.addWidget(self.refinery_empty_label)

        summary_card = self.create_filter_card("SELLING / PROFIT SUMMARY")
        summary_card.setMinimumWidth(400)
        summary_layout = summary_card.layout()
        self.refinery_price_status_label = QLabel(
            "UEX prices are fetched live for this session and are not stored locally."
        )
        self.refinery_price_status_label.setObjectName("moduleSubtitle")
        self.refinery_price_status_label.setWordWrap(True)
        summary_layout.addWidget(self.refinery_price_status_label)

        totals_grid = QGridLayout()
        totals_grid.setHorizontalSpacing(12)
        totals_grid.setVerticalSpacing(8)
        self.refinery_total_qty_label = QLabel("0 cSCU / 0 SCU")
        self.refinery_total_yield_label = QLabel("0 cSCU / 0 SCU")
        self.refinery_gross_value_label = QLabel("0 aUEC")
        self.refinery_net_value_label = QLabel("0 aUEC")
        self.refinery_time_left_label = QLabel("00:00:00")
        for value_label in (
            self.refinery_total_qty_label,
            self.refinery_total_yield_label,
            self.refinery_gross_value_label,
            self.refinery_net_value_label,
            self.refinery_time_left_label,
        ):
            value_label.setObjectName("valueText")

        self.refinery_fee_input = QLineEdit("0")
        self.refinery_fee_input.setPlaceholderText("Refinery fee...")
        self.refinery_time_input = QLineEdit()
        self.refinery_time_input.setPlaceholderText("HH:MM:SS or minutes...")
        totals = [
            ("TOTAL QTY", self.refinery_total_qty_label),
            ("TOTAL YIELD", self.refinery_total_yield_label),
            ("SELL VALUE", self.refinery_gross_value_label),
            ("REFINERY FEE", self.refinery_fee_input),
            ("NET VALUE", self.refinery_net_value_label),
            ("REFINERY TIME", self.refinery_time_input),
            ("TIME LEFT", self.refinery_time_left_label),
        ]
        for row_index, (label_text, widget_item) in enumerate(totals):
            label = QLabel(label_text)
            label.setObjectName("labelText")
            totals_grid.addWidget(label, row_index, 0)
            totals_grid.addWidget(widget_item, row_index, 1)

        summary_layout.addLayout(totals_grid)
        timer_row = QHBoxLayout()
        self.refinery_timer_start_button = QPushButton("Start")
        self.refinery_timer_reset_button = QPushButton("Reset")
        self.refinery_timer_start_button.setMinimumWidth(110)
        self.refinery_timer_reset_button.setMinimumWidth(110)
        timer_row.addWidget(self.refinery_timer_start_button)
        timer_row.addWidget(self.refinery_timer_reset_button)
        summary_layout.addLayout(timer_row)

        sell_locations_label = QLabel("BEST SHARED SELL LOCATIONS")
        sell_locations_label.setObjectName("sectionTitle")
        summary_layout.addWidget(sell_locations_label)
        self.refinery_sell_locations_table = self.create_table([
            "Location",
            "Sell Value",
            "Materials",
        ])
        self.refinery_sell_locations_table.setSortingEnabled(False)
        self.refinery_sell_locations_table.setMinimumHeight(210)
        self.refinery_sell_locations_table.setMinimumWidth(380)
        self.refinery_sell_locations_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        configure_readable_table_columns(self.refinery_sell_locations_table, min_width=120, max_width=520)
        summary_layout.addWidget(self.refinery_sell_locations_table, 1)
        self.refinery_sell_locations_empty_label = self.create_empty_state(
            "Refresh UEX For Session to see matching sell locations."
        )
        summary_layout.addWidget(self.refinery_sell_locations_empty_label)

        hint = QLabel(
            "Enter ore QTY in either cSCU or SCU. Yield is auto-estimated from refinery station and method; "
            "you can still edit Yield if the in-game quote differs. Gems use QTY directly because they are sold, not refined. "
            "Sell value uses the best live UEX sell price in memory."
        )
        hint.setObjectName("moduleSubtitle")
        hint.setWordWrap(True)
        summary_layout.addWidget(hint)

        content.addWidget(input_card, 5)
        content.addWidget(summary_card, 4)
        work_layout.addLayout(content, 1)
        work_widget.setLayout(work_layout)

        self.refinery_history_widget = self.build_refinery_history_widget()
        work_scroll = QScrollArea()
        work_scroll.setWidgetResizable(True)
        work_scroll.setFrameShape(QFrame.NoFrame)
        work_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        work_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        work_scroll.setWidget(work_widget)

        self.refinery_stack.addWidget(work_scroll)
        self.refinery_stack.addWidget(self.refinery_history_widget)
        layout.addWidget(self.refinery_stack, 1)
        widget.setLayout(layout)
        return widget


    def add_refinery_material_section(self, parent_layout, title, materials, columns=6):
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        parent_layout.addWidget(label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        for index, (code, material) in enumerate(materials):
            button = QPushButton(code)
            button.setToolTip(self.refinery_material_tooltip(material))
            button.setMinimumWidth(96)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(lambda checked=False, selected=material: self.add_refinery_material(selected))
            grid.addWidget(button, index // columns, index % columns)

        parent_layout.addLayout(grid)


    def build_refinery_history_widget(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        history_card = self.create_filter_card("REFINERY SESSION HISTORY")
        history_layout = history_card.layout()
        actions = QHBoxLayout()
        self.refinery_history_remove_button = QPushButton("Remove Selected")
        self.refinery_history_clear_button = QPushButton("Clear History")
        actions.addStretch(1)
        actions.addWidget(self.refinery_history_remove_button)
        actions.addWidget(self.refinery_history_clear_button)
        history_layout.addLayout(actions)
        self.refinery_history_table = self.create_table([
            "Name",
            "Station",
            "Method",
            "QTY",
            "Yield",
            "Sell Value",
            "Net",
            "Saved",
        ])
        configure_readable_table_columns(self.refinery_history_table, min_width=110, max_width=260, stretch_last=True)
        history_layout.addWidget(self.refinery_history_table, 1)
        self.refinery_history_empty_label = self.create_empty_state("No saved refinery sessions yet.")
        history_layout.addWidget(self.refinery_history_empty_label)
        layout.addWidget(history_card, 1)
        widget.setLayout(layout)
        return widget


    def ensure_refinery_session(self):
        if not self.current_refinery_session:
            self.create_refinery_session()


    def create_refinery_session(self):
        self.refinery_session_counter += 1
        session_id = f"session-{self.refinery_session_counter}"
        session_name = f"Session {self.refinery_session_counter}"
        session_name = self.unique_refinery_session_name(session_name)
        self.refinery_sessions[session_id] = {
            "name": session_name,
            "materials": {},
            "fee": 0.0,
            "station": self.refinery_station_filter.currentText() if hasattr(self, "refinery_station_filter") else "",
            "method": self.refinery_method_filter.currentText() if hasattr(self, "refinery_method_filter") else "",
            "time_text": "",
            "time_remaining": 0,
            "timer_running": False,
        }
        self.current_refinery_session = session_id

        self.load_refinery_session_fields()
        self.refresh_refinery_session_tabs()
        self.populate_refinery_table()


    def on_refinery_session_tab_changed(self, index):
        if self.loading_refinery_tabs or index < 0:
            return

        if index >= len(self.refinery_tab_session_ids):
            self.refinery_stack.setCurrentWidget(self.refinery_history_widget)
            self.populate_refinery_history_table()
            return

        session_id = self.refinery_tab_session_ids[index]
        if session_id not in self.refinery_sessions:
            return

        self.current_refinery_session = session_id
        self.refinery_stack.setCurrentIndex(0)
        self.load_refinery_session_fields()
        self.populate_refinery_table()


    def load_refinery_session_fields(self):
        session = self.refinery_session()

        self.refinery_session_name_input.blockSignals(True)
        self.refinery_session_name_input.setText(session.get("name", ""))
        self.refinery_session_name_input.blockSignals(False)
        self.refinery_station_filter.blockSignals(True)
        self.refinery_station_filter.setCurrentText(session.get("station", "Any refinery"))
        self.refinery_station_filter.blockSignals(False)
        self.refinery_method_filter.blockSignals(True)
        self.refinery_method_filter.setCurrentText(session.get("method", REFINERY_METHODS[0]))
        self.refinery_method_filter.blockSignals(False)
        self.refinery_fee_input.blockSignals(True)
        self.refinery_fee_input.setText(self.format_number(session.get("fee", 0)))
        self.refinery_fee_input.blockSignals(False)
        self.load_refinery_timer_fields()


    def refresh_refinery_session_tabs(self):
        if not hasattr(self, "refinery_session_tabs"):
            return

        self.loading_refinery_tabs = True
        self.refinery_session_tabs.clear()
        self.refinery_tab_session_ids = list(self.refinery_sessions.keys())
        for session_id in self.refinery_tab_session_ids:
            session = self.refinery_sessions[session_id]
            self.refinery_session_tabs.addTab(QWidget(), self.refinery_tab_label(session))

        self.refinery_session_tabs.addTab(QWidget(), "History")

        if self.current_refinery_session in self.refinery_tab_session_ids:
            self.refinery_session_tabs.setCurrentIndex(self.refinery_tab_session_ids.index(self.current_refinery_session))
            self.refinery_stack.setCurrentIndex(0)
        else:
            self.refinery_session_tabs.setCurrentIndex(len(self.refinery_tab_session_ids))
            self.refinery_stack.setCurrentWidget(self.refinery_history_widget)
            self.populate_refinery_history_table()

        self.loading_refinery_tabs = False


    def refinery_tab_label(self, session):
        label = session.get("name", "Session")
        if session.get("timer_running"):
            label = f"{label} ({self.format_duration(session.get('time_remaining', 0))})"
        return label


    def unique_refinery_session_name(self, name):
        base_name = name.strip() or f"Session {self.refinery_session_counter}"
        existing = {
            session.get("name", "").lower()
            for session in self.refinery_sessions.values()
        }
        if base_name.lower() not in existing:
            return base_name

        suffix = 2
        while f"{base_name} {suffix}".lower() in existing:
            suffix += 1
        return f"{base_name} {suffix}"


    def rename_current_refinery_session(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        session = self.refinery_sessions[self.current_refinery_session]
        new_name = self.refinery_session_name_input.text().strip()
        if not new_name or new_name == session.get("name"):
            self.refinery_session_name_input.setText(session.get("name", ""))
            return

        existing = {
            other.get("name", "").lower()
            for session_id, other in self.refinery_sessions.items()
            if session_id != self.current_refinery_session
        }
        if new_name.lower() in existing:
            new_name = self.unique_refinery_session_name(new_name)

        session["name"] = new_name
        self.refinery_session_name_input.setText(new_name)
        self.refresh_refinery_session_tabs()


    def refinery_session(self):
        self.ensure_refinery_session()
        return self.refinery_sessions[self.current_refinery_session]


    def add_refinery_material(self, material):
        session = self.refinery_session()
        materials = session["materials"]
        if material not in materials:
            materials[material] = {
                "code": self.refinery_material_code(material),
                "qty_cscu": 0.0,
                "yield_cscu": 0.0,
            }
            self.populate_refinery_table()

        self.select_refinery_material(material)


    def add_all_refinery_materials(self):
        session = self.refinery_session()
        for code, material in SHIP_REFINERY_MATERIALS:
            session["materials"].setdefault(material, {
                "code": code,
                "qty_cscu": 0.0,
                "yield_cscu": 0.0,
            })

        self.populate_refinery_table()


    def clear_refinery_session(self):
        session = self.refinery_session()
        session["materials"].clear()
        session["fee"] = 0.0
        session["time_text"] = ""
        session["time_remaining"] = 0
        session["timer_running"] = False
        self.refinery_fee_input.blockSignals(True)
        self.refinery_fee_input.setText("0")
        self.refinery_fee_input.blockSignals(False)
        self.refinery_timer_start_button.setText("Start")
        self.load_refinery_timer_fields()
        self.refresh_refinery_session_tabs()
        self.update_refinery_timer_activity()
        self.populate_refinery_table()


    def close_refinery_session(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        closing_id = self.current_refinery_session
        session_ids = list(self.refinery_sessions.keys())
        closing_index = session_ids.index(closing_id)
        self.refinery_sessions.pop(closing_id, None)

        if self.refinery_sessions:
            remaining_ids = list(self.refinery_sessions.keys())
            self.current_refinery_session = remaining_ids[min(closing_index, len(remaining_ids) - 1)]
            self.load_refinery_session_fields()
            self.populate_refinery_table()
        else:
            self.current_refinery_session = None
            self.create_refinery_session()

        self.refresh_refinery_session_tabs()
        self.update_refinery_timer_activity()


    def save_refinery_session_to_history(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        session_id = self.current_refinery_session
        session = self.refinery_sessions[session_id]
        self.refinery_completed_sessions.append(self.refinery_history_snapshot(session))
        self.close_refinery_session()
        self.populate_refinery_history_table()
        if hasattr(self, "refinery_session_tabs"):
            self.refinery_session_tabs.setCurrentIndex(len(self.refinery_tab_session_ids))


    def refinery_history_snapshot(self, session):
        total_qty, total_yield, gross_value, net_value = self.refinery_session_totals(session)
        return {
            "name": session.get("name", "Session"),
            "station": session.get("station", ""),
            "method": session.get("method", ""),
            "total_qty": total_qty,
            "total_yield": total_yield,
            "gross_value": gross_value,
            "net_value": net_value,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }


    def populate_refinery_history_table(self):
        if not hasattr(self, "refinery_history_table"):
            return

        sorting_enabled = self.refinery_history_table.isSortingEnabled()
        self.refinery_history_table.setSortingEnabled(False)
        self.refinery_history_table.setRowCount(len(self.refinery_completed_sessions))

        for row_index, (history_index, session) in enumerate(reversed(list(enumerate(self.refinery_completed_sessions)))):
            row_values = [
                session.get("name", "Session"),
                session.get("station", ""),
                session.get("method", ""),
                self.format_cscu_and_scu(session.get("total_qty", 0)),
                self.format_cscu_and_scu(session.get("total_yield", 0)),
                self.format_auec_amount(session.get("gross_value", 0)),
                self.format_auec_amount(session.get("net_value", 0)),
                session.get("saved_at", ""),
            ]
            for column_index, value in enumerate(row_values):
                item = QTableWidgetItem(str(value))
                if column_index == 0:
                    item.setData(Qt.UserRole, history_index)
                self.refinery_history_table.setItem(row_index, column_index, item)

        self.refinery_history_table.setSortingEnabled(sorting_enabled)
        self.refinery_history_empty_label.setVisible(not self.refinery_completed_sessions)
        configure_readable_table_columns(self.refinery_history_table, min_width=110, max_width=260, stretch_last=True)


    def remove_selected_refinery_history(self):
        row = self.refinery_history_table.currentRow()
        if row < 0:
            return

        item = self.refinery_history_table.item(row, 0)
        if not item:
            return

        history_index = item.data(Qt.UserRole)
        if not isinstance(history_index, int):
            return

        if 0 <= history_index < len(self.refinery_completed_sessions):
            self.refinery_completed_sessions.pop(history_index)
            self.populate_refinery_history_table()


    def clear_refinery_history(self):
        self.refinery_completed_sessions.clear()
        self.populate_refinery_history_table()


    def remove_selected_refinery_material(self):
        row = self.refinery_table.currentRow()
        if row < 0:
            return

        material_item = self.refinery_table.item(row, 0)
        if not material_item:
            return

        material = material_item.data(Qt.UserRole) or material_item.text()
        session = self.refinery_session()
        session["materials"].pop(material, None)
        self.populate_refinery_table()


    def on_refinery_fee_changed(self):
        session = self.refinery_session()
        session["fee"] = self.parse_float(self.refinery_fee_input.text())
        self.update_refinery_summary()


    def on_refinery_setup_changed(self):
        session = self.refinery_session()
        session["station"] = self.refinery_station_filter.currentText()
        session["method"] = self.refinery_method_filter.currentText()
        self.recalculate_refinery_yields()


    def on_refinery_item_changed(self, item):
        if self.loading_refinery_table or item.column() not in (1, 2, 3, 4):
            return

        material_item = self.refinery_table.item(item.row(), 0)
        if not material_item:
            return

        material = material_item.data(Qt.UserRole) or material_item.text()
        session = self.refinery_session()
        if material not in session["materials"]:
            return

        if item.column() in (1, 2):
            field_name = "qty_cscu"
        else:
            field_name = "yield_cscu"

        value = self.parse_float(item.text())
        if item.column() in (2, 4):
            value = round(value * 100, 4)

        session["materials"][material][field_name] = value
        if field_name == "qty_cscu":
            session["materials"][material]["yield_cscu"] = self.calculate_refinery_yield(material, value)
        else:
            session["materials"][material]["yield_manual"] = True

        self.update_refinery_row_value(item.row(), material)
        self.update_refinery_summary()


    def recalculate_refinery_yields(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        session = self.refinery_session()
        for material, entry in session["materials"].items():
            entry["yield_cscu"] = self.calculate_refinery_yield(material, entry.get("qty_cscu", 0))
            entry["yield_manual"] = False

        self.populate_refinery_table()


    def populate_refinery_table(self):
        session = self.refinery_session()
        materials = session["materials"]
        self.loading_refinery_table = True
        self.refinery_table.setRowCount(len(materials))

        for row_index, material in enumerate(sorted(materials)):
            entry = materials[material]
            price = self.uex_prices.get(material.lower())
            sell_only = self.is_sell_only_refinery_material(material, session)
            sell_value = self.refinery_material_value(
                material,
                self.refinery_sell_quantity_cscu(material, entry, session),
            )
            yield_cscu_item = self.read_only_item("N/A") if sell_only else self.editable_number_item(
                entry.get("yield_cscu", 0)
            )
            yield_scu_item = self.read_only_item("N/A") if sell_only else self.editable_number_item(
                self.format_scu_from_cscu(entry.get("yield_cscu", 0))
            )
            row_items = [
                self.read_only_item(material, material),
                self.editable_number_item(entry.get("qty_cscu", 0)),
                self.editable_number_item(self.format_scu_from_cscu(entry.get("qty_cscu", 0))),
                yield_cscu_item,
                yield_scu_item,
                self.read_only_item(self.format_price(price.price_sell if price else None)),
                self.read_only_item(self.format_auec_amount(sell_value)),
            ]
            row_items[0].setToolTip(entry.get("code", material))
            for col_index, table_item in enumerate(row_items):
                if col_index in (1, 2, 3, 4, 5, 6):
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.refinery_table.setItem(row_index, col_index, table_item)

        self.loading_refinery_table = False
        self.refinery_empty_label.setVisible(not materials)
        configure_readable_table_columns(self.refinery_table, min_width=96, max_width=180, stretch_last=True)
        self.update_refinery_summary()


    def update_refinery_row_value(self, row, material):
        session = self.refinery_session()
        entry = session["materials"].get(material, {})
        sell_only = self.is_sell_only_refinery_material(material, session)
        sell_value = self.refinery_material_value(
            material,
            self.refinery_sell_quantity_cscu(material, entry, session),
        )
        qty_cscu_item = self.refinery_table.item(row, 1)
        qty_scu_item = self.refinery_table.item(row, 2)
        yield_cscu_item = self.refinery_table.item(row, 3)
        yield_scu_item = self.refinery_table.item(row, 4)
        gross_item = self.refinery_table.item(row, 6)
        if not gross_item:
            return

        self.loading_refinery_table = True
        if qty_cscu_item:
            qty_cscu_item.setText(self.format_number(entry.get("qty_cscu", 0)))
        if qty_scu_item:
            qty_scu_item.setText(self.format_scu_from_cscu(entry.get("qty_cscu", 0)))
        if yield_cscu_item:
            yield_cscu_item.setText("N/A" if sell_only else self.format_number(entry.get("yield_cscu", 0)))
        if yield_scu_item:
            yield_scu_item.setText("N/A" if sell_only else self.format_scu_from_cscu(entry.get("yield_cscu", 0)))
        gross_item.setText(self.format_auec_amount(sell_value))
        self.loading_refinery_table = False


    def update_refinery_summary(self):
        session = self.refinery_session()
        materials = session["materials"]
        total_qty, total_yield, gross_value, net_value = self.refinery_session_totals(session)

        self.refinery_total_qty_label.setText(self.format_cscu_and_scu(total_qty))
        self.refinery_total_yield_label.setText(self.format_cscu_and_scu(total_yield))
        self.refinery_gross_value_label.setText(self.format_auec_amount(gross_value))
        self.refinery_net_value_label.setText(self.format_auec_amount(net_value))
        self.refinery_timer_start_button.setText("Pause" if session.get("timer_running") else "Start")

        missing_prices = [
            material
            for material in materials
            if not self.uex_prices.get(material.lower())
        ]
        if not materials:
            self.refinery_price_status_label.setText(
                "Create a session, click ore buttons, then enter QTY and Yield. "
                "Nothing here is saved locally."
            )
        elif missing_prices:
            self.refinery_price_status_label.setText(
                f"{len(missing_prices)} selected materials need a live UEX refresh. "
                "Prices stay in memory only."
            )
        else:
            self.refinery_price_status_label.setText(
                "All selected materials have live UEX prices in memory only."
            )
        self.populate_refinery_sell_locations(session)


    def refinery_session_totals(self, session):
        materials = session.get("materials", {})
        total_qty = sum(entry.get("qty_cscu", 0) for entry in materials.values())
        total_yield = sum(
            0 if self.is_sell_only_refinery_material(material, session) else entry.get("yield_cscu", 0)
            for material, entry in materials.items()
        )
        gross_value = sum(
            self.refinery_material_value(
                material,
                self.refinery_sell_quantity_cscu(material, entry, session),
            )
            for material, entry in materials.items()
        )
        fee = session.get("fee", 0)
        return total_qty, total_yield, gross_value, gross_value - fee


    def populate_refinery_sell_locations(self, session=None):
        if not hasattr(self, "refinery_sell_locations_table"):
            return

        session = session or self.refinery_session()
        locations_by_material = {}
        required_materials = []
        has_sell_quantity = False
        has_price_rows = False
        for material, entry in session.get("materials", {}).items():
            sell_quantity = self.refinery_sell_quantity_cscu(material, entry, session)
            if sell_quantity <= 0:
                continue

            has_sell_quantity = True
            required_materials.append(material)
            prices = self.deduped_refinery_sell_prices(self.uex_price_lists.get(material.lower(), []))
            has_price_rows = has_price_rows or bool(prices)
            material_locations = {}
            for price in prices:
                if not price.price_sell:
                    continue

                key = self.refinery_sell_location_key(price)
                value = self.refinery_material_value_from_price(sell_quantity, price.price_sell)
                material_locations[key] = {
                    "label": self.format_uex_terminal(price),
                    "material": material,
                    "value": value,
                }
            locations_by_material[material] = material_locations

        grouped_locations = []
        if required_materials:
            shared_keys = set(locations_by_material.get(required_materials[0], {}))
            for material in required_materials[1:]:
                shared_keys &= set(locations_by_material.get(material, {}))

            for key in shared_keys:
                material_rows = [
                    locations_by_material[material][key]
                    for material in required_materials
                ]
                grouped_locations.append({
                    "label": material_rows[0]["label"],
                    "materials": [
                        f"{row['material']} ({self.format_auec_amount(row['value'])})"
                        for row in material_rows
                    ],
                    "value": sum(row["value"] for row in material_rows),
                })

        rows = sorted(
            grouped_locations,
            key=lambda location: location["value"],
            reverse=True,
        )[:12]

        self.refinery_sell_locations_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            row_values = [
                row["label"],
                self.format_auec_amount(row["value"]),
                ", ".join(row["materials"]),
            ]
            for column_index, value in enumerate(row_values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column_index == 1:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.refinery_sell_locations_table.setItem(row_index, column_index, item)

        if not rows:
            if not session.get("materials"):
                empty_text = "Add materials to see sell location options."
            elif not has_sell_quantity:
                empty_text = "Enter QTY to calculate sell location values."
            elif not has_price_rows:
                empty_text = "Refresh UEX For Session to see matching sell locations."
            elif len(required_materials) > 1:
                empty_text = "No shared UEX sell locations can buy every selected material."
            else:
                empty_text = "No matching UEX sell locations found for the selected materials."
            self.refinery_sell_locations_empty_label.setText(empty_text)

        self.refinery_sell_locations_empty_label.setVisible(not rows)
        self.refinery_sell_locations_table.setVisible(bool(rows))
        if rows:
            self.resize_refinery_sell_location_columns()


    def deduped_refinery_sell_prices(self, prices):
        best_by_location = {}
        for price in prices:
            if not price.price_sell:
                continue

            key = self.refinery_sell_location_key(price)
            current = best_by_location.get(key)
            if current is None or (price.price_sell or 0) > (current.price_sell or 0):
                best_by_location[key] = price

        return sorted(
            best_by_location.values(),
            key=lambda price: (-(price.price_sell or 0), self.format_uex_terminal(price).lower()),
        )


    def refinery_sell_location_key(self, price):
        system = " ".join(str(price.star_system_name or "").lower().split())
        location = str(price.location_name or "").strip()
        if not location or location == "N/A":
            location = str(price.terminal_name or "").strip()
        location = " ".join(location.lower().replace("'", "").split())
        return system, location


    def resize_refinery_sell_location_columns(self):
        configure_readable_table_columns(self.refinery_sell_locations_table, min_width=120, max_width=520)


    def refresh_refinery_uex_prices(self):
        if self.refinery_uex_refresh_running:
            return

        materials = sorted(self.refinery_session()["materials"])
        if not materials:
            QMessageBox.information(
                self,
                "No ores selected",
                "Add one or more refinery materials before refreshing UEX prices.",
            )
            return

        self.refinery_uex_refresh_running = True
        self.refinery_refresh_uex_button.setEnabled(False)
        self.refinery_refresh_uex_button.setText("Refreshing UEX...")

        def load_prices():
            refreshed = 0
            failed = []
            prices_by_material = {}
            price_lists_by_material = {}
            for material in materials:
                try:
                    prices = fetch_commodity_sell_prices(material)
                except (UEXError, requests.RequestException, ValueError) as exc:
                    failed.append(f"{material}: {exc}")
                    continue

                key = material.lower()
                price_lists_by_material[key] = prices
                prices_by_material[key] = prices[0] if prices else None
                refreshed += 1

            return {
                "materials": materials,
                "prices": prices_by_material,
                "price_lists": price_lists_by_material,
                "refreshed": refreshed,
                "failed": failed,
            }

        self.start_background_task(
            load_prices,
            self.on_refinery_uex_prices_refreshed,
            self.on_refinery_uex_prices_error,
            self.finish_refinery_uex_prices_refresh,
        )


    def on_refinery_uex_prices_refreshed(self, result):
        self.uex_prices.update(result["prices"])
        self.uex_price_lists.update(result["price_lists"])
        self.populate_refinery_table()
        failed = result["failed"]
        materials = result["materials"]
        refreshed = result["refreshed"]
        if failed:
            self.refinery_price_status_label.setText(
                f"UEX refreshed {refreshed}/{len(materials)} materials; "
                f"{len(failed)} failed. Prices were not stored locally."
            )
            QMessageBox.warning(
                self,
                "UEX refresh incomplete",
                "\n".join(failed[:5]),
            )
        else:
            self.refinery_price_status_label.setText(
                f"UEX refreshed {refreshed} session materials. Prices were not stored locally."
            )


    def on_refinery_uex_prices_error(self, exc):
        self.refinery_price_status_label.setText(f"UEX refresh failed: {exc}")
        QMessageBox.critical(self, "UEX refresh failed", str(exc))


    def finish_refinery_uex_prices_refresh(self):
        self.refinery_uex_refresh_running = False
        self.refinery_refresh_uex_button.setEnabled(True)
        self.refinery_refresh_uex_button.setText("Refresh UEX For Session")


    def on_refinery_time_changed(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        session = self.refinery_session()
        if session.get("timer_running"):
            return

        remaining_seconds = self.parse_duration_seconds(self.refinery_time_input.text())
        session["time_text"] = self.refinery_time_input.text()
        session["time_remaining"] = remaining_seconds
        self.refinery_timer_remaining_seconds = remaining_seconds
        self.refinery_time_left_label.setText(self.format_duration(remaining_seconds))
        self.update_refinery_session_tab_labels()


    def toggle_refinery_timer(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        session = self.refinery_session()
        if session.get("timer_running"):
            session["timer_running"] = False
            self.refinery_timer_start_button.setText("Start")
            self.update_refinery_timer_activity()
            self.update_refinery_session_tab_labels()
            return

        remaining_seconds = session.get("time_remaining", 0)
        if remaining_seconds <= 0:
            remaining_seconds = self.parse_duration_seconds(self.refinery_time_input.text())

        if remaining_seconds <= 0:
            QMessageBox.information(
                self,
                "No refinery time",
                "Enter a refinery time first. Use HH:MM:SS, MM:SS, or minutes.",
            )
            return

        session["time_text"] = self.refinery_time_input.text()
        session["time_remaining"] = remaining_seconds
        session["timer_running"] = True
        self.refinery_timer_remaining_seconds = remaining_seconds
        self.refinery_time_left_label.setText(self.format_duration(remaining_seconds))
        self.refinery_timer_start_button.setText("Pause")
        self.update_refinery_timer_activity()
        self.update_refinery_session_tab_labels()


    def reset_refinery_timer(self):
        if not self.current_refinery_session or self.current_refinery_session not in self.refinery_sessions:
            return

        session = self.refinery_session()
        remaining_seconds = self.parse_duration_seconds(self.refinery_time_input.text())
        session["time_text"] = self.refinery_time_input.text()
        session["time_remaining"] = remaining_seconds
        session["timer_running"] = False
        self.refinery_timer_remaining_seconds = remaining_seconds
        self.refinery_timer_start_button.setText("Start")
        self.refinery_time_left_label.setText(self.format_duration(remaining_seconds))
        self.update_refinery_timer_activity()
        self.update_refinery_session_tab_labels()


    def tick_refinery_timer(self):
        any_running = False
        for session in self.refinery_sessions.values():
            if not session.get("timer_running"):
                continue

            remaining_seconds = max(0, int(session.get("time_remaining", 0)) - 1)
            session["time_remaining"] = remaining_seconds
            if remaining_seconds <= 0:
                session["timer_running"] = False
            else:
                any_running = True

        if self.current_refinery_session in self.refinery_sessions:
            current = self.refinery_sessions[self.current_refinery_session]
            self.refinery_timer_remaining_seconds = current.get("time_remaining", 0)
            self.refinery_time_left_label.setText(self.format_duration(self.refinery_timer_remaining_seconds))
            self.refinery_timer_start_button.setText("Pause" if current.get("timer_running") else "Start")

        self.update_refinery_session_tab_labels()
        if not any_running:
            self.refinery_timer.stop()


    def update_refinery_timer_activity(self):
        if any(session.get("timer_running") for session in self.refinery_sessions.values()):
            if not self.refinery_timer.isActive():
                self.refinery_timer.start()
            return

        if self.refinery_timer.isActive():
            self.refinery_timer.stop()


    def update_refinery_session_tab_labels(self):
        if not hasattr(self, "refinery_session_tabs"):
            return

        for index, session_id in enumerate(self.refinery_tab_session_ids):
            session = self.refinery_sessions.get(session_id)
            if session:
                self.refinery_session_tabs.setTabText(index, self.refinery_tab_label(session))


    def load_refinery_timer_fields(self):
        session = self.refinery_session()
        self.refinery_time_input.blockSignals(True)
        self.refinery_time_input.setText(session.get("time_text", ""))
        self.refinery_time_input.blockSignals(False)
        self.refinery_timer_remaining_seconds = session.get("time_remaining", 0)
        self.refinery_time_left_label.setText(self.format_duration(self.refinery_timer_remaining_seconds))
        self.refinery_timer_start_button.setText("Pause" if session.get("timer_running") else "Start")


    def parse_duration_seconds(self, value):
        text = str(value or "").strip()
        if not text:
            return 0

        if ":" in text:
            parts = [part.strip() for part in text.split(":")]
            if len(parts) not in (2, 3):
                return 0
            try:
                numbers = [int(part) for part in parts]
            except ValueError:
                return 0

            if len(numbers) == 2:
                minutes, seconds = numbers
                return max(0, minutes * 60 + seconds)

            hours, minutes, seconds = numbers
            return max(0, hours * 3600 + minutes * 60 + seconds)

        return max(0, int(self.parse_float(text) * 60))


    def format_duration(self, seconds):
        seconds = max(0, int(seconds or 0))
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


    def refinery_material_code(self, material):
        for code, candidate in SHIP_REFINERY_MATERIALS:
            if candidate == material:
                return code

        return material[:4].upper()


    def refinery_material_tooltip(self, material):
        if self.is_gem_selling_material(material):
            return f"{material}\nGem selling only. Cannot be refined; value uses QTY."

        details = SALVAGE_REFINERY_DETAILS.get(material)
        if not details:
            return material

        return (
            f"{material}\n"
            f"{details['density']} | {details['yield']} | {details['time']}"
        )


    def select_refinery_material(self, material):
        for row in range(self.refinery_table.rowCount()):
            item = self.refinery_table.item(row, 0)
            if item and item.data(Qt.UserRole) == material:
                self.refinery_table.selectRow(row)
                return


    def is_gem_selling_material(self, material):
        return any(candidate == material for _, candidate in GEM_SELLING_MATERIALS)


    def is_salvage_refinery_material(self, material):
        return material in SALVAGE_REFINERY_DETAILS


    def is_no_refinery_session(self, session=None):
        if session is not None:
            station_text = session.get("station", "")
        elif hasattr(self, "refinery_station_filter"):
            station_text = self.refinery_station_filter.currentText()
        else:
            station_text = ""

        return str(station_text).startswith("No Refinery")


    def is_sell_only_refinery_material(self, material, session=None):
        return self.is_gem_selling_material(material) or self.is_no_refinery_session(session)


    def refinery_sell_quantity_cscu(self, material, entry, session=None):
        if self.is_sell_only_refinery_material(material, session):
            return self.parse_float(entry.get("qty_cscu", 0))

        return self.parse_float(entry.get("yield_cscu", 0))


    def refinery_material_value(self, material, yield_cscu):
        price = self.uex_prices.get(material.lower())
        if not price or not price.price_sell:
            return 0.0

        return self.refinery_material_value_from_price(yield_cscu, price.price_sell)


    def refinery_material_value_from_price(self, quantity_cscu, price_sell):
        return (self.parse_float(quantity_cscu) / 100) * self.parse_float(price_sell)


    def calculate_refinery_yield(self, material, qty_cscu):
        qty = self.parse_float(qty_cscu)
        if qty <= 0 or self.is_sell_only_refinery_material(material):
            return 0.0

        method_yield = self.refinery_method_yield_for_material(material)
        if method_yield <= 0:
            return 0.0

        station = self.selected_refinery_station()
        bonus = station.bonuses.get(self.canonical_refinery_material(material), 0.0) if station else 0.0
        salvage_multiplier = SALVAGE_REFINERY_DETAILS.get(material, {}).get("yield_multiplier", 1.0)
        return max(0.0, float(round(qty * method_yield * (1 + bonus) * salvage_multiplier)))


    def refinery_method_yield_for_material(self, material):
        if self.is_salvage_refinery_material(material):
            method_key = self.refinery_option_key(self.refinery_method_filter.currentText())
            for method_name, yield_factor in SALVAGE_REFINERY_METHOD_YIELD_FALLBACKS.items():
                if self.refinery_option_key(method_name) == method_key:
                    return yield_factor
            return 0.0

        method = self.selected_refinery_method()
        if method:
            return method.yield_factor

        return REFINERY_METHOD_YIELD_FALLBACKS.get(
            self.refinery_method_filter.currentText(),
            0.0,
        )


    def selected_refinery_station(self):
        return self.refinery_station_lookup.get(
            self.refinery_option_key(self.refinery_station_filter.currentText())
        )


    def selected_refinery_method(self):
        return self.refinery_method_lookup.get(
            self.refinery_option_key(self.refinery_method_filter.currentText())
        )


    def canonical_refinery_material(self, material):
        aliases = {
            "Quantanium": "Quantainium",
        }
        return aliases.get(material, material)


    def refinery_option_key(self, value):
        return " ".join(str(value or "").lower().replace(":", " ").replace("-", " ").split())


    def format_scu_from_cscu(self, cscu):
        return self.format_number(self.parse_float(cscu) / 100)


    def format_cscu_and_scu(self, cscu):
        return f"{self.format_number(cscu)} cSCU / {self.format_scu_from_cscu(cscu)} SCU"


    def read_only_item(self, value, user_data=None):
        item = QTableWidgetItem(str(value))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        if user_data is not None:
            item.setData(Qt.UserRole, user_data)
        return item


    def editable_number_item(self, value):
        item = QTableWidgetItem(self.format_number(value))
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

