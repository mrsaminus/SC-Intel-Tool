from .shared import *


class MiningOverviewMixin:
    def create_module_header(self, title, subtitle):
        card = QFrame()
        card.setObjectName("playerCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("moduleHeading")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("moduleSubtitle")
        subtitle_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        card.setLayout(layout)
        return card


    def build_overview_tab(self):
        widget = QWidget()
        layout = QGridLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        layout.addWidget(self.create_data_status_card(), 0, 0, 1, 2)

        cards = [
            (
                "ORE FINDER",
                "Search minerals and see where they can be found.",
                "Static locations with optional live UEX prices on demand.",
                "Ore Finder",
            ),
            (
                "BEST LOCATIONS",
                "Filter by Stanton, Pyro, body, cave, asteroid or surface mining.",
                "Live data: grouped body/location view for planning mining ops.",
                "Locations",
            ),
            (
                "REFINERY",
                "Build refining sessions with ore input, yield and value totals.",
                "Session data and UEX prices stay in memory only.",
                "Refinery",
            ),
            (
                "ROCK BREAKER",
                "Compare mass, resistance, instability, lasers and modules.",
                "Planned data: rock-breaking calculator JSON.",
                "Rock Breaker",
            ),
            (
                "SCAN ID",
                "Identify possible resources from scan signature values.",
                "Live data: resource scan signature values from the provided chart.",
                "Scan ID",
            ),
            (
                "QUALITY BANDS",
                "Compare resource quality thresholds by score band.",
                "Live data: quality quantization JSON matching the uploaded HTML.",
                "Quality Bands",
            ),
            (
                "EQUIPMENT",
                "Find mining lasers, modules, gadgets and shops.",
                "Live data: lasers, modules and gadgets from rock-breaking JSON.",
                "Equipment",
            ),
            (
                "PROFIT",
                "Turn ore, refinery and market data into a quick value readout.",
                "This can later link into the Trading tab.",
                "Refinery",
            ),
        ]

        for index, (title, summary, detail, tab_name) in enumerate(cards):
            layout.addWidget(
                self.create_overview_card(title, summary, detail, tab_name),
                index // 2 + 1,
                index % 2,
            )

        layout.setRowStretch(5, 1)
        widget.setLayout(layout)
        return widget


    def create_data_status_card(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        title = QLabel("DATA STATUS")
        title.setObjectName("sectionTitle")
        self.mining_status_label = QLabel("Loading mining data...")
        self.mining_status_label.setObjectName("valueText")
        self.mining_source_label = QLabel("")
        self.mining_source_label.setObjectName("moduleSubtitle")
        self.mining_source_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.mining_status_label)
        layout.addWidget(self.mining_source_label)
        card.setLayout(layout)
        return card


    def create_overview_card(self, title, summary, detail, tab_name):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setCursor(Qt.PointingHandCursor)
        card.setToolTip(f"Open {tab_name}")
        card.mousePressEvent = lambda event, name=tab_name: self.open_mining_tab(name)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        summary_label = QLabel(summary)
        summary_label.setObjectName("valueText")
        summary_label.setWordWrap(True)
        detail_label = QLabel(detail)
        detail_label.setObjectName("moduleSubtitle")
        detail_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(summary_label)
        layout.addWidget(detail_label)
        layout.addStretch(1)
        card.setLayout(layout)
        return card


    def open_mining_tab(self, tab_name):
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == tab_name:
                self.tabs.setCurrentIndex(index)
                return


    def populate_mining_tables(self):
        self.populate_overview_summary()
        self.populate_ore_results()
        self.populate_location_results()
        self.populate_scan_identifier()
        self.populate_quality_bands()
        self.ensure_refinery_session()
        self.populate_refinery_table()
        self.populate_rock_breaker_results()
        self.populate_equipment_results()


    def populate_overview_summary(self):
        data = self.mining_data
        refinery_count = max(len(self.refinery_station_options()) - 2, 0)
        refinery_method_count = len(self.refinery_method_options())
        self.mining_status_label.setText(
            f"Loaded {len(data.minerals)} minerals, "
            f"{len(data.locations)} location rows, "
            f"{len(data.equipment)} equipment items. "
            f"Also loaded {len(data.quality_bands)} quality-band rows and "
            f"{len(data.scan_signatures)} scan signatures, "
            f"{refinery_count} refinery choices and "
            f"{refinery_method_count} refinery methods. "
            "Market prices are fetched live from UEX and are not stored locally."
        )

        if data.errors:
            self.mining_source_label.setText("Data warnings: " + " | ".join(data.errors))
        else:
            self.mining_source_label.setText(
                "Static mining reference data is loaded from bundled public data and built-in fallback tables. "
                "Live market prices use UEX on demand."
            )

