import sys
from dataclasses import replace
from datetime import datetime, timedelta
from itertools import combinations

import requests
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database import (
    clear_lookup_history,
    delete_lookup_history,
    get_lookup_history,
    get_note,
    init_db,
    save_lookup,
    save_note,
)
from app.cstone_client import (
    CSTONE_HOME_URL,
    CStoneError,
    cstone_category_labels,
    cstone_category_url,
    fetch_cstone_item_locations,
    fetch_cstone_items,
)
from app.mining_data import load_mining_data
from app.rsi_lookup import RSILookupError, lookup_player
from app.scfocus_client import SCFOCUS_SHIPS_URL, fetch_scfocus_ship_items
from app.uex_client import UEXError, fetch_commodity_sell_prices


APP_STYLE = """
QMainWindow, QWidget {
    background: #071118;
    color: #d8f7ff;
    font-family: Segoe UI;
    font-size: 10pt;
}

QTabWidget::pane {
    border: 1px solid #1d3442;
    background: #071118;
}

QTabBar::tab {
    background: #121a22;
    color: #d8f7ff;
    border: 1px solid #243746;
    border-bottom: 0;
    padding: 8px 14px;
}

QTabBar::tab:selected {
    background: #0d2530;
    color: #44e6ff;
}

QLineEdit, QTextEdit, QComboBox {
    background: #0b1820;
    border: 1px solid #264858;
    border-radius: 4px;
    color: #f2fdff;
    selection-background-color: #00a8cc;
    padding: 6px;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #24d8ff;
}

QPushButton {
    background: #132733;
    border: 1px solid #2b5b6e;
    border-radius: 4px;
    color: #e6fbff;
    padding: 7px 12px;
}

QPushButton:hover {
    background: #173849;
    border-color: #34d8f5;
}

QPushButton:disabled {
    background: #111820;
    border-color: #24313b;
    color: #5f7780;
}

QScrollArea {
    border: 0;
    background: transparent;
}

QTableWidget {
    background: #071118;
    border: 1px solid #1e5060;
    border-radius: 4px;
    color: #effcff;
    gridline-color: #153441;
    selection-background-color: #123a49;
    selection-color: #ffffff;
}

QHeaderView::section {
    background: #0d2530;
    border: 0;
    border-right: 1px solid #1e5060;
    color: #33dfff;
    font-weight: 700;
    padding: 7px;
}

QFrame#playerCard, QFrame#sectionCard, QFrame#orgCard, QFrame#affiliationCard {
    background: #0b1820;
    border: 1px solid #1e5060;
    border-radius: 6px;
}

QFrame#playerCard {
    border-color: #28788d;
}

QLabel {
    background: transparent;
}

QLabel#avatarBox {
    background: #061017;
    border: 1px solid #2b7386;
    border-radius: 4px;
    color: #466978;
}

QLabel#sectionTitle {
    color: #33dfff;
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#heroHandle {
    color: #f5fdff;
    font-size: 22pt;
    font-weight: 700;
}

QLabel#heroSubtitle {
    color: #6ddff0;
    font-size: 11pt;
}

QLabel#labelText {
    color: #6f9ead;
    font-size: 8pt;
    text-transform: uppercase;
}

QLabel#valueText {
    color: #effcff;
    font-size: 10pt;
}

QLabel#orgName {
    color: #32e8ff;
    font-size: 15pt;
    font-weight: 700;
}

QLabel#orgSid {
    color: #8ff4ff;
    font-size: 10pt;
}

QLabel#emptyState {
    color: #6a8894;
    padding: 18px;
}

QLabel#moduleHeading {
    color: #f5fdff;
    font-size: 18pt;
    font-weight: 700;
}

QLabel#moduleSubtitle {
    color: #7bb9c8;
    font-size: 10pt;
}
"""


TAG_COLORS = {
    "Unmarked": ("#5e737c", "#13202a"),
    "Friendly": ("#58e6a6", "#0f2a22"),
    "Neutral": ("#d1d9df", "#1c252d"),
    "Hostile": ("#ff6b6b", "#331718"),
    "Pirate": ("#ff9f43", "#321f0d"),
    "Scammer": ("#ff5fd2", "#321329"),
    "NOVA": ("#33dfff", "#092936"),
    "Defence": ("#5aa8ff", "#10243a"),
    "Relief": ("#58e6e6", "#0c2a2d"),
    "Skyline": ("#b58cff", "#241737"),
    "Frontiers": ("#5ee37d", "#102a18"),
    "Core": ("#c7ff6b", "#24320e"),
    "B.A.L.D.E.R.": ("#ffd166", "#32270b"),
}

IMAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 SC-Intel-Tool",
}

SHIP_ORE_MATERIALS = [
    ("QUAN", "Quantainium"),
    ("STIL", "Stileron"),
    ("SAVR", "Savrilium"),
    ("RICC", "Riccite"),
    ("LIND", "Lindinium"),
    ("GOLD", "Gold"),
    ("BORS", "Borase"),
    ("BEX", "Bexalite"),
    ("TARA", "Taranite"),
    ("BERL", "Beryl"),
    ("AGRI", "Agricium"),
    ("TUNG", "Tungsten"),
    ("TITA", "Titanium"),
    ("LARA", "Laranite"),
    ("TORI", "Torite"),
    ("DIAM", "Diamond"),
    ("ICE", "Ice"),
    ("QUAR", "Quartz"),
    ("HEPH", "Hephaestanite"),
    ("ALUM", "Aluminum"),
    ("TIN", "Tin"),
    ("COPP", "Copper"),
    ("CORU", "Corundum"),
    ("IRON", "Iron"),
    ("SILI", "Silicon"),
    ("INER", "Inert Materials"),
]

SALVAGE_REFINERY_MATERIALS = [
    ("RUBL", "Construction Rubble"),
    ("PIEC", "Construction Pieces"),
    ("CSAL", "Construction Salvage"),
]

GEM_SELLING_MATERIALS = [
    ("JANA", "Janalite"),
    ("HADA", "Hadanite"),
    ("FEYN", "Feynmaline"),
    ("BERA", "Beradom"),
    ("DOLV", "Dolivine"),
    ("GLAC", "Glacosite"),
    ("APHO", "Aphorite"),
    ("CARI", "Caranite"),
    ("JACL", "Jaclium"),
    ("SALD", "Saldynium"),
]

SHIP_REFINERY_MATERIALS = SHIP_ORE_MATERIALS + SALVAGE_REFINERY_MATERIALS + GEM_SELLING_MATERIALS

SALVAGE_REFINERY_DETAILS = {
    "Construction Rubble": {
        "density": "Highest density",
        "yield": "Lowest yield",
        "time": "Fastest refinery processing time",
        "yield_multiplier": 0.7,
    },
    "Construction Pieces": {
        "density": "Medium density",
        "yield": "Medium yield",
        "time": "Medium refinery processing time",
        "yield_multiplier": 1.0,
    },
    "Construction Salvage": {
        "density": "Lowest density",
        "yield": "Highest yield",
        "time": "Longest refinery processing time",
        "yield_multiplier": 1.3,
    },
}

REFINERY_STATIONS = [
    "Any refinery",
    "No Refinery (Sell Raw Ore)",
    "Arc-L1: Wide Forest Station",
    "Arc-L2: Lively Pathway Station",
    "Arc-L4: Faint Glen Station",
    "CRU-L1: Ambitious Dream Station",
    "HUR-L1: Green Glade Station",
    "HUR-L2: Faithful Dream Station",
    "ST-MAG: Magnus Gateway",
    "MIC-L1: Shallow Frontier Station",
    "MIC-L2: Long Forest Station",
    "MIC-L5: Modern Icarus Station",
    "ST-PYR: Pyro Gateway",
    "ST-TER: Terra Gateway",
    "Checkmate Station",
    "Orbituary Station",
    "Ruin Station",
    "PYR-ST: Stanton Gateway",
    "Levski Station",
    "NYX-ST: Stanton Gateway",
]

REFINERY_METHODS = [
    "Dinyx Solventation",
    "Cormack Method",
    "Electrostarolysis",
    "Ferron Exchange",
    "Gaskin Process",
    "Kazen Winnowing",
    "Pyrometric Chromalysis",
    "Thermonatic Deposition",
    "XCR Reaction",
]

REFINERY_METHOD_YIELD_FALLBACKS = {
    "Dinyx Solventation": 0.45,
    "Ferron Exchange": 0.45,
    "Pyrometric Chromalysis": 0.45,
    "Thermonatic Deposition": 0.382,
    "Electrostarolysis": 0.382,
    "Gaskin Process": 0.382,
    "Kazen Winnowing": 0.315,
    "Cormack Method": 0.315,
    "XCR Reaction": 0.315,
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SC Intel Tool")
        self.setMinimumSize(1120, 780)
        self.setStyleSheet(APP_STYLE)

        self.tabs = QTabWidget()

        self.history_tab = SearchHistoryTab()
        self.player_tab = PlayerLookupTab(on_lookup_saved=self.history_tab.refresh_history)
        self.mining_tab = MiningTab()
        self.trading_tab = TradingTab()
        self.item_finder_tab = ItemFinderTab()
        self.notes_tab = NotesTab()
        self.settings_tab = SettingsTab()

        self.tabs.addTab(self.player_tab, "Player Lookup")
        self.tabs.addTab(self.history_tab, "Search History")
        self.tabs.addTab(self.mining_tab, "Mining & Salvage")
        self.tabs.addTab(self.trading_tab, "Trading")
        self.tabs.addTab(self.item_finder_tab, "Item Finder")
        self.tabs.addTab(self.notes_tab, "Notes")
        self.tabs.addTab(self.settings_tab, "Settings")

        self.setCentralWidget(self.tabs)


class PlayerLookupTab(QWidget):
    def __init__(self, on_lookup_saved=None):
        super().__init__()

        self.on_lookup_saved = on_lookup_saved
        self.current_handle = None
        self.current_profile_url = None
        self.current_organizations_url = None
        self.current_main_org_url = None

        self.player_facts = {}
        self.main_org_facts = {}

        self.build_ui()
        self.connect_signals()
        self.set_actions_enabled(False)
        self.update_tag_badge(self.tag_box.currentText())

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        search_row = QHBoxLayout()
        self.handle_input = QLineEdit()
        self.handle_input.setPlaceholderText("Enter RSI handle...")
        self.search_button = QPushButton("Lookup")
        self.copy_handle_button = QPushButton("Copy Handle")
        self.copy_handle_button.setEnabled(False)

        search_row.addWidget(self.handle_input, 1)
        search_row.addWidget(self.search_button)
        search_row.addWidget(self.copy_handle_button)
        layout.addLayout(search_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        scroll_content.setLayout(self.content_layout)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        self.build_player_card()
        self.build_main_org_card()
        self.build_affiliations_section()
        self.build_notes_section()

        self.setLayout(layout)

    def build_player_card(self):
        card = QFrame()
        card.setObjectName("playerCard")
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self.avatar_label = QLabel("NO\nIMAGE")
        self.avatar_label.setObjectName("avatarBox")
        self.avatar_label.setFixedSize(146, 146)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.avatar_label)

        info_column = QVBoxLayout()
        self.handle_title = QLabel("No Player Loaded")
        self.handle_title.setObjectName("heroHandle")
        self.handle_title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.display_subtitle = QLabel("Search an RSI handle to load citizen intel.")
        self.display_subtitle.setObjectName("heroSubtitle")
        self.display_subtitle.setTextInteractionFlags(Qt.TextSelectableByMouse)

        info_column.addWidget(self.handle_title)
        info_column.addWidget(self.display_subtitle)

        facts_grid = QGridLayout()
        facts_grid.setHorizontalSpacing(18)
        facts_grid.setVerticalSpacing(6)
        fields = [
            ("citizen_record", "Citizen Record"),
            ("enlisted", "Enlisted"),
            ("location", "Location"),
            ("fluency", "Fluency"),
        ]
        for row, (key, label) in enumerate(fields):
            self.add_fact_row(facts_grid, row, label, self.player_facts, key)

        info_column.addLayout(facts_grid)
        info_column.addStretch(1)
        layout.addLayout(info_column, 2)

        action_column = QVBoxLayout()
        action_column.setSpacing(8)

        self.tag_badge = QLabel("Unmarked")
        self.tag_badge.setAlignment(Qt.AlignCenter)
        action_column.addWidget(self.tag_badge)

        tag_label = QLabel("Local Tag")
        tag_label.setObjectName("labelText")
        self.tag_box = QComboBox()
        self.tag_box.addItems([
            "Unmarked",
            "Friendly",
            "Neutral",
            "Hostile",
            "Pirate",
            "Scammer",
            "NOVA",
            "Defence",
            "Relief",
            "Skyline",
            "Frontiers",
            "Core",
            "B.A.L.D.E.R.",
        ])

        self.open_profile_button = QPushButton("Open Profile")
        self.open_orgs_button = QPushButton("Open Organizations")
        self.open_main_org_button = QPushButton("Open Main Org")

        action_column.addWidget(tag_label)
        action_column.addWidget(self.tag_box)
        action_column.addSpacing(8)
        action_column.addWidget(self.open_profile_button)
        action_column.addWidget(self.open_orgs_button)
        action_column.addWidget(self.open_main_org_button)
        action_column.addStretch(1)

        layout.addLayout(action_column, 1)
        card.setLayout(layout)
        self.content_layout.addWidget(card)

    def build_main_org_card(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        title = QLabel("MAIN ORGANIZATION")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        body = QHBoxLayout()
        body.setSpacing(14)
        self.main_org_logo_label = self.create_image_label("ORG\nLOGO", 112)
        body.addWidget(self.main_org_logo_label)

        details_column = QVBoxLayout()
        details_column.setSpacing(12)

        header = QHBoxLayout()
        org_identity = QVBoxLayout()
        self.main_org_name = QLabel("No main organization loaded")
        self.main_org_name.setObjectName("orgName")
        self.main_org_sid = QLabel("SID: N/A")
        self.main_org_sid.setObjectName("orgSid")
        org_identity.addWidget(self.main_org_name)
        org_identity.addWidget(self.main_org_sid)
        header.addLayout(org_identity, 1)

        self.main_org_piracy = QLabel("Piracy: N/A")
        self.main_org_piracy.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.main_org_piracy)
        details_column.addLayout(header)

        facts_grid = QGridLayout()
        facts_grid.setHorizontalSpacing(24)
        facts_grid.setVerticalSpacing(8)
        fields = [
            ("rank", "Rank"),
            ("member_count", "Members"),
            ("type", "Type"),
            ("commitment", "Commitment"),
            ("exclusivity", "Exclusivity"),
        ]
        for index, (key, label) in enumerate(fields):
            row = index // 3
            col = (index % 3) * 2
            self.add_fact_pair(facts_grid, row, col, label, self.main_org_facts, key)

        details_column.addLayout(facts_grid)
        body.addLayout(details_column, 1)
        layout.addLayout(body)
        card.setLayout(layout)
        self.content_layout.addWidget(card)

    def build_affiliations_section(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("AFFILIATIONS")
        title.setObjectName("sectionTitle")
        self.affiliation_count_label = QLabel("0 linked orgs")
        self.affiliation_count_label.setObjectName("labelText")
        self.affiliation_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(title)
        header.addWidget(self.affiliation_count_label, 1)
        layout.addLayout(header)

        self.affiliations_grid = QGridLayout()
        self.affiliations_grid.setHorizontalSpacing(12)
        self.affiliations_grid.setVerticalSpacing(12)
        layout.addLayout(self.affiliations_grid)

        self.affiliations_empty = QLabel("No affiliations loaded.")
        self.affiliations_empty.setObjectName("emptyState")
        self.affiliations_empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.affiliations_empty)

        card.setLayout(layout)
        self.content_layout.addWidget(card)

    def build_notes_section(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        title = QLabel("LOCAL INTEL NOTES")
        title.setObjectName("sectionTitle")
        self.notes_box = QTextEdit()
        self.notes_box.setPlaceholderText("Local notes about this player...")
        self.notes_box.setMinimumHeight(130)
        self.save_note_button = QPushButton("Save Note")

        layout.addWidget(title)
        layout.addWidget(self.notes_box)
        layout.addWidget(self.save_note_button)
        card.setLayout(layout)
        self.content_layout.addWidget(card)

    def connect_signals(self):
        self.search_button.clicked.connect(self.search_player)
        self.handle_input.returnPressed.connect(self.search_player)
        self.save_note_button.clicked.connect(self.save_current_note)
        self.copy_handle_button.clicked.connect(self.copy_current_handle)
        self.open_profile_button.clicked.connect(self.open_current_profile)
        self.open_orgs_button.clicked.connect(self.open_current_organizations)
        self.open_main_org_button.clicked.connect(self.open_current_main_org)
        self.tag_box.currentTextChanged.connect(self.update_tag_badge)

    def add_fact_row(self, layout, row, label, registry, key):
        self.add_fact_pair(layout, row, 0, label, registry, key)

    def add_fact_pair(self, layout, row, col, label, registry, key):
        label_widget = QLabel(label.upper())
        label_widget.setObjectName("labelText")
        value_widget = QLabel("N/A")
        value_widget.setObjectName("valueText")
        value_widget.setWordWrap(True)
        value_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
        registry[key] = value_widget

        layout.addWidget(label_widget, row, col)
        layout.addWidget(value_widget, row, col + 1)

    def search_player(self):
        handle = self.handle_input.text().strip()

        try:
            self.search_button.setEnabled(False)
            self.search_button.setText("Looking up...")

            data = lookup_player(handle)
            self.display_player(data)
            self.load_saved_note(data["handle"])

            save_lookup(
                data["handle"],
                data["display_name"],
                data["main_org"],
                data["profile_url"],
                org_sid=data["org_sid"],
                org_piracy=data["org_piracy"],
                any_org_piracy=data["any_org_piracy"],
            )
            if self.on_lookup_saved:
                self.on_lookup_saved()

        except RSILookupError as e:
            self.set_actions_enabled(False)
            QMessageBox.warning(self, "Lookup failed", str(e))
        except Exception as e:
            self.set_actions_enabled(False)
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self.search_button.setEnabled(True)
            self.search_button.setText("Lookup")

    def display_player(self, data):
        self.current_handle = data["handle"]
        self.current_profile_url = data["profile_url"]
        self.current_organizations_url = data["organizations_url"]
        self.current_main_org_url = data["org_url"]

        self.handle_title.setText(data["handle"])
        self.display_subtitle.setText(data["display_name"])
        self.set_fact_values(self.player_facts, {
            "citizen_record": data["citizen_record"],
            "enlisted": data["enlisted"],
            "location": data["location"],
            "fluency": data["fluency"],
        })

        self.main_org_name.setText(data["main_org"])
        self.main_org_sid.setText(f"SID: {data['org_sid']}")
        self.set_fact_values(self.main_org_facts, {
            "rank": data["org_rank"],
            "member_count": data["org_member_count"],
            "type": data["org_type"],
            "commitment": data["org_commitment"],
            "exclusivity": data["org_exclusivity"],
        })
        self.set_piracy_badge(self.main_org_piracy, data["org_piracy"])

        self.load_avatar(data["avatar"])
        self.load_image_into_label(
            self.main_org_logo_label,
            data.get("org_logo"),
            "ORG\nLOGO",
        )
        self.render_affiliations(data["affiliations"])
        self.set_actions_enabled(True)

    def set_fact_values(self, registry, values):
        for key, value in values.items():
            registry[key].setText(str(value or "N/A"))

    def render_affiliations(self, affiliations):
        self.clear_layout(self.affiliations_grid)

        if not affiliations:
            self.affiliation_count_label.setText("0 linked orgs")
            self.affiliations_empty.show()
            return

        self.affiliations_empty.hide()
        self.affiliation_count_label.setText(f"{len(affiliations)} linked orgs")

        for index, org in enumerate(affiliations):
            row = index // 2
            col = index % 2
            self.affiliations_grid.addWidget(self.create_affiliation_card(org), row, col)

    def create_affiliation_card(self, org):
        card = QFrame()
        card.setObjectName("affiliationCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        logo = self.create_image_label("ORG\nLOGO", 78)
        self.load_image_into_label(logo, org.get("logo_url"), "ORG\nLOGO")
        layout.addWidget(logo)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)

        name = QLabel(org["name"])
        name.setObjectName("orgName")
        name.setWordWrap(True)
        sid = QLabel(f"SID: {org['sid']}")
        sid.setObjectName("orgSid")
        details = QLabel(
            f"Rank: {org['rank']}  |  Members: {org['member_count']}  |  "
            f"{org['type']} / {org['commitment']} / {org['exclusivity']}"
        )
        details.setObjectName("valueText")
        details.setWordWrap(True)
        piracy = QLabel()
        self.set_piracy_badge(piracy, org["piracy"])

        text_layout.addWidget(name)
        text_layout.addWidget(sid)
        text_layout.addWidget(details)
        text_layout.addWidget(piracy)
        layout.addLayout(text_layout, 1)
        card.setLayout(layout)
        return card

    def load_saved_note(self, handle):
        saved_note = get_note(handle)
        if saved_note:
            tag, notes = saved_note
            self.tag_box.setCurrentText(tag or "Unmarked")
            self.notes_box.setPlainText(notes or "")
        else:
            self.tag_box.setCurrentText("Unmarked")
            self.notes_box.clear()

    def load_avatar(self, avatar_url):
        self.load_image_into_label(self.avatar_label, avatar_url, "NO\nIMAGE")

    def create_image_label(self, placeholder, size):
        label = QLabel(placeholder)
        label.setObjectName("avatarBox")
        label.setFixedSize(size, size)
        label.setAlignment(Qt.AlignCenter)
        return label

    def load_image_into_label(self, label, image_url, placeholder):
        label.setPixmap(QPixmap())
        label.setText(placeholder)

        if not image_url:
            return

        try:
            response = requests.get(image_url, headers=IMAGE_HEADERS, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            return

        pixmap = QPixmap()
        if not pixmap.loadFromData(response.content):
            return

        scaled = pixmap.scaled(
            label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        label.setText("")
        label.setPixmap(scaled)

    def update_tag_badge(self, tag):
        foreground, background = TAG_COLORS.get(tag, TAG_COLORS["Unmarked"])
        self.tag_badge.setText(tag.upper())
        self.tag_badge.setStyleSheet(
            f"""
            QLabel {{
                color: {foreground};
                background: {background};
                border: 1px solid {foreground};
                border-radius: 4px;
                padding: 7px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            """
        )

    def set_piracy_badge(self, label, has_piracy):
        if has_piracy:
            label.setText("Piracy: YES")
            label.setStyleSheet("color: #ff8a65; font-weight: 700;")
        else:
            label.setText("Piracy: No")
            label.setStyleSheet("color: #68e6a5; font-weight: 700;")

    def set_actions_enabled(self, enabled):
        self.copy_handle_button.setEnabled(enabled)
        self.open_profile_button.setEnabled(enabled)
        self.open_orgs_button.setEnabled(enabled)
        self.open_main_org_button.setEnabled(enabled and bool(self.current_main_org_url))

    def open_current_profile(self):
        self.open_url(self.current_profile_url, "No profile", "Lookup a player first.")

    def open_current_organizations(self):
        self.open_url(
            self.current_organizations_url,
            "No organizations",
            "Lookup a player first.",
        )

    def open_current_main_org(self):
        self.open_url(
            self.current_main_org_url,
            "No main org",
            "No main organization URL is available for this player.",
        )

    def open_url(self, url, title, message):
        if not url:
            QMessageBox.warning(self, title, message)
            return

        QDesktopServices.openUrl(QUrl(url))

    def copy_current_handle(self):
        if not self.current_handle:
            QMessageBox.warning(self, "No player", "Lookup a player first.")
            return

        QApplication.clipboard().setText(self.current_handle)

    def save_current_note(self):
        if not self.current_handle:
            QMessageBox.warning(self, "No player", "Lookup a player first.")
            return

        save_note(
            self.current_handle,
            self.tag_box.currentText(),
            self.notes_box.toPlainText(),
        )

        QMessageBox.information(self, "Saved", "Note saved.")

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())


class SearchHistoryTab(QWidget):
    def __init__(self):
        super().__init__()

        self.history_rows = []
        self.current_profile_url = None
        self.current_organizations_url = None
        self.current_main_org_url = None
        self.detail_player_facts = {}
        self.detail_org_facts = {}
        self.history_sort_column = None
        self.history_sort_order = Qt.AscendingOrder

        self.build_ui()
        self.reset_detail_panel()
        self.refresh_history()

    def build_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        list_card = QFrame()
        list_card.setObjectName("sectionCard")
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(16, 14, 16, 16)
        list_layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("SEARCH HISTORY")
        title.setObjectName("sectionTitle")
        self.refresh_button = QPushButton("Refresh")
        self.remove_selected_button = QPushButton("Remove Selected")
        self.clear_history_button = QPushButton("Clear History")
        header.addWidget(title, 1)
        header.addWidget(self.refresh_button)
        list_layout.addLayout(header)

        history_actions = QHBoxLayout()
        history_actions.addWidget(self.remove_selected_button)
        history_actions.addWidget(self.clear_history_button)
        list_layout.addLayout(history_actions)

        filter_row = QHBoxLayout()
        self.history_filter_input = QLineEdit()
        self.history_filter_input.setPlaceholderText("Filter name/org/SID...")
        self.piracy_filter_box = QComboBox()
        self.piracy_filter_box.addItems(["All", "Piracy YES", "Piracy NO"])
        filter_row.addWidget(self.history_filter_input, 1)
        filter_row.addWidget(self.piracy_filter_box)
        list_layout.addLayout(filter_row)

        filter_meta_row = QHBoxLayout()
        self.history_count_label = QLabel("0 shown")
        self.history_count_label.setObjectName("labelText")
        self.clear_filters_button = QPushButton("Clear Filters")
        filter_meta_row.addWidget(self.history_count_label, 1)
        filter_meta_row.addWidget(self.clear_filters_button)
        list_layout.addLayout(filter_meta_row)

        self.history_table = QTableWidget(0, 3)
        self.history_table.setHorizontalHeaderLabels(["Name", "Org", "Piracy"])
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionsClickable(True)
        self.history_table.horizontalHeader().setSortIndicatorShown(False)
        list_layout.addWidget(self.history_table)

        list_card.setLayout(list_layout)
        layout.addWidget(list_card, 2)

        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_content = QWidget()
        self.detail_layout = QVBoxLayout()
        self.detail_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_layout.setSpacing(12)
        detail_content.setLayout(self.detail_layout)
        detail_scroll.setWidget(detail_content)

        self.build_history_player_card()
        self.build_history_main_org_card()
        self.build_history_affiliations_card()
        self.detail_layout.addStretch(1)

        layout.addWidget(detail_scroll, 3)
        self.setLayout(layout)

        self.refresh_button.clicked.connect(lambda: self.refresh_history())
        self.remove_selected_button.clicked.connect(self.remove_selected_history)
        self.clear_history_button.clicked.connect(self.clear_all_history)
        self.history_filter_input.textChanged.connect(lambda: self.apply_history_filters())
        self.piracy_filter_box.currentTextChanged.connect(lambda: self.apply_history_filters())
        self.clear_filters_button.clicked.connect(self.clear_history_filters)
        self.history_table.horizontalHeader().sectionClicked.connect(self.sort_history_by_column)
        self.history_table.cellClicked.connect(self.open_history_row)
        self.detail_open_profile_button.clicked.connect(
            lambda: self.open_url(self.current_profile_url, "No profile URL available.")
        )
        self.detail_open_orgs_button.clicked.connect(
            lambda: self.open_url(self.current_organizations_url, "No organizations URL available.")
        )
        self.detail_open_main_org_button.clicked.connect(
            lambda: self.open_url(self.current_main_org_url, "No main org URL available.")
        )

    def reset_detail_panel(self):
        self.current_profile_url = None
        self.current_organizations_url = None
        self.current_main_org_url = None

        self.detail_handle.setText("No history row selected")
        self.detail_display_name.setText("Click a lookup row to open a dossier here.")
        self.set_fact_values(self.detail_player_facts, {
            "citizen_record": "N/A",
            "enlisted": "N/A",
            "location": "N/A",
            "fluency": "N/A",
        })

        self.detail_main_org_name.setText("No main organization loaded")
        self.detail_main_org_sid.setText("SID: N/A")
        self.set_fact_values(self.detail_org_facts, {
            "rank": "N/A",
            "member_count": "N/A",
            "type": "N/A",
            "commitment": "N/A",
            "exclusivity": "N/A",
        })
        self.detail_main_org_piracy.setText("Piracy: N/A")
        self.detail_main_org_piracy.setStyleSheet("color: #6a8894; font-weight: 700;")

        self.load_image_into_label(self.detail_avatar, None, "NO\nIMAGE")
        self.load_image_into_label(self.detail_main_org_logo, None, "ORG\nLOGO")
        self.clear_layout(self.detail_affiliations_grid)
        self.detail_affiliation_count_label.setText("0 linked orgs")
        self.detail_affiliations_empty.setText("No profile selected.")
        self.detail_affiliations_empty.show()
        self.set_detail_actions_enabled(False)

    def build_history_player_card(self):
        card = QFrame()
        card.setObjectName("playerCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self.detail_avatar = self.create_image_label("NO\nIMAGE", 112)
        layout.addWidget(self.detail_avatar)

        info_column = QVBoxLayout()
        self.detail_handle = QLabel("No history row selected")
        self.detail_handle.setObjectName("heroHandle")
        self.detail_handle.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.detail_display_name = QLabel("Click a lookup row to open a dossier here.")
        self.detail_display_name.setObjectName("heroSubtitle")
        self.detail_display_name.setTextInteractionFlags(Qt.TextSelectableByMouse)

        info_column.addWidget(self.detail_handle)
        info_column.addWidget(self.detail_display_name)

        facts_grid = QGridLayout()
        facts_grid.setHorizontalSpacing(18)
        facts_grid.setVerticalSpacing(7)
        fields = [
            ("citizen_record", "Citizen Record"),
            ("enlisted", "Enlisted"),
            ("location", "Location"),
            ("fluency", "Fluency"),
        ]
        for row, (key, label) in enumerate(fields):
            self.add_fact_pair(facts_grid, row, 0, label, self.detail_player_facts, key)

        info_column.addLayout(facts_grid)
        layout.addLayout(info_column, 1)

        action_column = QVBoxLayout()
        self.detail_open_profile_button = QPushButton("Open Profile")
        self.detail_open_orgs_button = QPushButton("Open Organizations")
        self.detail_open_main_org_button = QPushButton("Open Main Org")
        action_column.addWidget(self.detail_open_profile_button)
        action_column.addWidget(self.detail_open_orgs_button)
        action_column.addWidget(self.detail_open_main_org_button)
        layout.addLayout(action_column)

        card.setLayout(layout)
        self.detail_layout.addWidget(card)

    def build_history_main_org_card(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        title = QLabel("MAIN ORGANIZATION")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        body = QHBoxLayout()
        body.setSpacing(14)
        self.detail_main_org_logo = self.create_image_label("ORG\nLOGO", 104)
        body.addWidget(self.detail_main_org_logo)

        details_column = QVBoxLayout()
        details_column.setSpacing(12)

        header = QHBoxLayout()
        org_identity = QVBoxLayout()
        self.detail_main_org_name = QLabel("No main organization loaded")
        self.detail_main_org_name.setObjectName("orgName")
        self.detail_main_org_sid = QLabel("SID: N/A")
        self.detail_main_org_sid.setObjectName("orgSid")
        org_identity.addWidget(self.detail_main_org_name)
        org_identity.addWidget(self.detail_main_org_sid)
        header.addLayout(org_identity, 1)

        self.detail_main_org_piracy = QLabel("Piracy: N/A")
        self.detail_main_org_piracy.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.detail_main_org_piracy)
        details_column.addLayout(header)

        facts_grid = QGridLayout()
        facts_grid.setHorizontalSpacing(18)
        facts_grid.setVerticalSpacing(7)
        fields = [
            ("rank", "Rank"),
            ("member_count", "Members"),
            ("type", "Type"),
            ("commitment", "Commitment"),
            ("exclusivity", "Exclusivity"),
        ]
        for index, (key, label) in enumerate(fields):
            row = index // 3
            col = (index % 3) * 2
            self.add_fact_pair(facts_grid, row, col, label, self.detail_org_facts, key)

        details_column.addLayout(facts_grid)
        body.addLayout(details_column, 1)
        layout.addLayout(body)

        card.setLayout(layout)
        self.detail_layout.addWidget(card)

    def build_history_affiliations_card(self):
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("AFFILIATIONS")
        title.setObjectName("sectionTitle")
        self.detail_affiliation_count_label = QLabel("0 linked orgs")
        self.detail_affiliation_count_label.setObjectName("labelText")
        self.detail_affiliation_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(title)
        header.addWidget(self.detail_affiliation_count_label, 1)
        layout.addLayout(header)

        self.detail_affiliations_grid = QGridLayout()
        self.detail_affiliations_grid.setHorizontalSpacing(12)
        self.detail_affiliations_grid.setVerticalSpacing(12)
        layout.addLayout(self.detail_affiliations_grid)

        self.detail_affiliations_empty = QLabel("No profile selected.")
        self.detail_affiliations_empty.setObjectName("emptyState")
        self.detail_affiliations_empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.detail_affiliations_empty)

        card.setLayout(layout)
        self.detail_layout.addWidget(card)

    def refresh_history(self, selected_handle=None):
        if selected_handle is None:
            selected = self.selected_history_row()
            if selected:
                selected_handle = selected["handle"]

        self.history_rows = get_lookup_history()
        self.apply_history_filters(selected_handle=selected_handle)

    def apply_history_filters(self, selected_handle=None):
        if selected_handle is None:
            selected = self.selected_history_row()
            if selected:
                selected_handle = selected["handle"]

        query = self.history_filter_input.text().strip().lower()
        piracy_filter = self.piracy_filter_box.currentText()
        filtered_rows = [
            (row_index, row)
            for row_index, row in enumerate(self.history_rows)
            if self.history_row_matches_filter(row, query, piracy_filter)
        ]

        if self.history_sort_column is not None:
            reverse = self.history_sort_order == Qt.DescendingOrder
            filtered_rows.sort(
                key=lambda item: self.history_sort_key(item[1], self.history_sort_column),
                reverse=reverse,
            )

        self.history_table.setUpdatesEnabled(False)
        self.history_table.clearSelection()
        self.history_table.setRowCount(len(filtered_rows))

        for table_row, (row_index, row) in enumerate(filtered_rows):
            name = row.get("display_name") or row["handle"]
            org = row.get("main_org") or "N/A"
            has_piracy = self.history_row_has_piracy(row)
            piracy = "YES" if has_piracy else "NO"

            for col, value in enumerate((name, org, piracy)):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, row_index)
                if col == 2:
                    item.setForeground(QColor("#ff8a65" if has_piracy else "#68e6a5"))
                self.history_table.setItem(table_row, col, item)

        self.history_table.setUpdatesEnabled(True)
        self.history_count_label.setText(f"{len(filtered_rows)} / {len(self.history_rows)} shown")

        if self.history_sort_column is None:
            self.history_table.horizontalHeader().setSortIndicatorShown(False)
        else:
            self.history_table.horizontalHeader().setSortIndicatorShown(True)
            self.history_table.horizontalHeader().setSortIndicator(
                self.history_sort_column,
                self.history_sort_order,
            )

        if selected_handle:
            self.select_history_handle(selected_handle)

    def history_row_matches_filter(self, row, query, piracy_filter):
        has_piracy = self.history_row_has_piracy(row)
        if piracy_filter == "Piracy YES" and not has_piracy:
            return False
        if piracy_filter == "Piracy NO" and has_piracy:
            return False

        if not query:
            return True

        searchable = " ".join(
            str(row.get(field) or "")
            for field in ("handle", "display_name", "main_org", "org_sid")
        ).lower()
        return query in searchable

    def history_sort_key(self, row, column):
        if column == 0:
            return (row.get("display_name") or row["handle"]).lower()
        if column == 1:
            return (row.get("main_org") or "").lower()
        if column == 2:
            return 1 if self.history_row_has_piracy(row) else 0

        return ""

    def sort_history_by_column(self, column):
        if self.history_sort_column == column:
            self.history_sort_order = (
                Qt.DescendingOrder
                if self.history_sort_order == Qt.AscendingOrder
                else Qt.AscendingOrder
            )
        else:
            self.history_sort_column = column
            self.history_sort_order = Qt.DescendingOrder if column == 2 else Qt.AscendingOrder

        self.apply_history_filters()

    def clear_history_filters(self):
        self.history_filter_input.blockSignals(True)
        self.piracy_filter_box.blockSignals(True)
        self.history_filter_input.clear()
        self.piracy_filter_box.setCurrentIndex(0)
        self.history_filter_input.blockSignals(False)
        self.piracy_filter_box.blockSignals(False)
        self.apply_history_filters()

    def select_history_handle(self, handle):
        handle_key = handle.lower()
        for table_row in range(self.history_table.rowCount()):
            row = self.history_row_from_table_row(table_row)
            if row and row["handle"].lower() == handle_key:
                self.history_table.selectRow(table_row)
                return

    def history_row_has_piracy(self, row):
        if row.get("any_org_piracy") is not None:
            return bool(row.get("any_org_piracy"))

        return bool(row.get("org_piracy"))

    def history_row_from_table_row(self, table_row):
        if table_row < 0 or table_row >= self.history_table.rowCount():
            return None

        item = self.history_table.item(table_row, 0)
        if not item:
            return None

        row_index = item.data(Qt.UserRole)
        if row_index is None or row_index < 0 or row_index >= len(self.history_rows):
            return None

        return self.history_rows[row_index]

    def selected_history_row(self):
        selection = self.history_table.selectionModel()
        if not selection:
            return None

        selected_rows = selection.selectedRows()
        if not selected_rows:
            return None

        table_row = selected_rows[0].row()
        return self.history_row_from_table_row(table_row)

    def remove_selected_history(self):
        row = self.selected_history_row()
        if not row:
            QMessageBox.information(
                self,
                "No selection",
                "Select a history row to remove.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Remove history entry",
            f"Remove {row['handle']} from search history?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        delete_lookup_history(row["handle"])
        self.refresh_history()
        self.reset_detail_panel()

    def clear_all_history(self):
        if not self.history_rows:
            QMessageBox.information(
                self,
                "History empty",
                "Search history is already empty.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Clear search history",
            "Remove all search history entries? Notes and tags will be kept.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        clear_lookup_history()
        self.refresh_history()
        self.reset_detail_panel()

    def open_history_row(self, row_index, _column):
        row = self.history_row_from_table_row(row_index)
        if not row:
            return

        self.detail_handle.setText(row["handle"])
        self.detail_display_name.setText("Loading fresh profile intel...")
        self.clear_layout(self.detail_affiliations_grid)
        self.detail_affiliations_empty.setText("Loading affiliations...")
        self.detail_affiliations_empty.show()
        QApplication.processEvents()

        try:
            data = lookup_player(row["handle"])
            self.display_lookup_detail(data)
            self.update_stored_history_detail(data)
        except RSILookupError as e:
            self.display_stored_detail(row)
            QMessageBox.warning(self, "Lookup failed", str(e))
        except Exception as e:
            self.display_stored_detail(row)
            QMessageBox.critical(self, "Error", str(e))

    def display_lookup_detail(self, data):
        self.current_profile_url = data["profile_url"]
        self.current_organizations_url = data["organizations_url"]
        self.current_main_org_url = data["org_url"]

        self.detail_handle.setText(data["handle"])
        self.detail_display_name.setText(data["display_name"])
        self.set_fact_values(self.detail_player_facts, {
            "citizen_record": data["citizen_record"],
            "enlisted": data["enlisted"],
            "location": data["location"],
            "fluency": data["fluency"],
        })
        self.detail_main_org_name.setText(data["main_org"])
        self.detail_main_org_sid.setText(f"SID: {data['org_sid']}")
        self.set_fact_values(self.detail_org_facts, {
            "rank": data["org_rank"],
            "member_count": data["org_member_count"],
            "type": data["org_type"],
            "commitment": data["org_commitment"],
            "exclusivity": data["org_exclusivity"],
        })
        self.set_piracy_badge(self.detail_main_org_piracy, data["org_piracy"])
        self.load_image_into_label(self.detail_avatar, data.get("avatar"), "NO\nIMAGE")
        self.load_image_into_label(
            self.detail_main_org_logo,
            data.get("org_logo"),
            "ORG\nLOGO",
        )
        self.render_detail_affiliations(data["affiliations"])
        self.set_detail_actions_enabled(True)

    def update_stored_history_detail(self, data):
        save_lookup(
            data["handle"],
            data["display_name"],
            data["main_org"],
            data["profile_url"],
            org_sid=data["org_sid"],
            org_piracy=data["org_piracy"],
            any_org_piracy=data["any_org_piracy"],
            refresh_timestamp=False,
        )
        self.refresh_history(selected_handle=data["handle"])

    def display_stored_detail(self, row):
        self.current_profile_url = row.get("profile_url")
        self.current_organizations_url = None
        self.current_main_org_url = None

        self.detail_handle.setText(row["handle"])
        self.detail_display_name.setText(row.get("display_name") or row["handle"])
        self.set_fact_values(self.detail_player_facts, {
            "citizen_record": "N/A",
            "enlisted": "N/A",
            "location": "N/A",
            "fluency": "N/A",
        })
        self.detail_main_org_name.setText(row.get("main_org") or "N/A")
        self.detail_main_org_sid.setText(f"SID: {row.get('org_sid') or 'N/A'}")
        self.set_fact_values(self.detail_org_facts, {
            "rank": "N/A",
            "member_count": "N/A",
            "type": "N/A",
            "commitment": "N/A",
            "exclusivity": "N/A",
        })
        self.set_piracy_badge(self.detail_main_org_piracy, bool(row.get("org_piracy")))
        self.clear_layout(self.detail_affiliations_grid)
        self.detail_affiliation_count_label.setText("0 linked orgs")
        self.detail_affiliations_empty.setText("Live lookup failed; showing stored history only.")
        self.detail_affiliations_empty.show()
        self.load_image_into_label(self.detail_avatar, None, "NO\nIMAGE")
        self.load_image_into_label(self.detail_main_org_logo, None, "ORG\nLOGO")
        self.set_detail_actions_enabled(True)

    def add_fact_pair(self, layout, row, col, label, registry, key):
        label_widget = QLabel(label.upper())
        label_widget.setObjectName("labelText")
        value_widget = QLabel("N/A")
        value_widget.setObjectName("valueText")
        value_widget.setWordWrap(True)
        value_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
        registry[key] = value_widget

        layout.addWidget(label_widget, row, col)
        layout.addWidget(value_widget, row, col + 1)

    def set_fact_values(self, registry, values):
        for key, value in values.items():
            registry[key].setText(str(value or "N/A"))

    def render_detail_affiliations(self, affiliations):
        self.clear_layout(self.detail_affiliations_grid)

        if not affiliations:
            self.detail_affiliation_count_label.setText("0 linked orgs")
            self.detail_affiliations_empty.setText("No affiliations loaded.")
            self.detail_affiliations_empty.show()
            return

        self.detail_affiliations_empty.hide()
        self.detail_affiliation_count_label.setText(f"{len(affiliations)} linked orgs")

        for index, org in enumerate(affiliations):
            row = index // 2
            col = index % 2
            self.detail_affiliations_grid.addWidget(
                self.create_detail_affiliation_card(org),
                row,
                col,
            )

    def create_detail_affiliation_card(self, org):
        card = QFrame()
        card.setObjectName("affiliationCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        logo = self.create_image_label("ORG\nLOGO", 72)
        self.load_image_into_label(logo, org.get("logo_url"), "ORG\nLOGO")
        layout.addWidget(logo)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        name = QLabel(org["name"])
        name.setObjectName("orgName")
        name.setWordWrap(True)
        sid = QLabel(f"SID: {org['sid']}")
        sid.setObjectName("orgSid")
        details = QLabel(
            f"Rank: {org['rank']}  |  Members: {org['member_count']}  |  "
            f"{org['type']} / {org['commitment']} / {org['exclusivity']}"
        )
        details.setObjectName("valueText")
        details.setWordWrap(True)
        piracy = QLabel()
        self.set_piracy_badge(piracy, org["piracy"])

        text_layout.addWidget(name)
        text_layout.addWidget(sid)
        text_layout.addWidget(details)
        text_layout.addWidget(piracy)
        layout.addLayout(text_layout, 1)
        card.setLayout(layout)
        return card

    def create_image_label(self, placeholder, size):
        label = QLabel(placeholder)
        label.setObjectName("avatarBox")
        label.setFixedSize(size, size)
        label.setAlignment(Qt.AlignCenter)
        return label

    def load_image_into_label(self, label, image_url, placeholder):
        label.setPixmap(QPixmap())
        label.setText(placeholder)

        if not image_url:
            return

        try:
            response = requests.get(image_url, headers=IMAGE_HEADERS, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            return

        pixmap = QPixmap()
        if not pixmap.loadFromData(response.content):
            return

        scaled = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setText("")
        label.setPixmap(scaled)

    def set_piracy_badge(self, label, has_piracy):
        if has_piracy:
            label.setText("Piracy: YES")
            label.setStyleSheet("color: #ff8a65; font-weight: 700;")
        else:
            label.setText("Piracy: No")
            label.setStyleSheet("color: #68e6a5; font-weight: 700;")

    def set_detail_actions_enabled(self, enabled):
        self.detail_open_profile_button.setEnabled(enabled and bool(self.current_profile_url))
        self.detail_open_orgs_button.setEnabled(enabled and bool(self.current_organizations_url))
        self.detail_open_main_org_button.setEnabled(enabled and bool(self.current_main_org_url))

    def open_url(self, url, message):
        if not url:
            QMessageBox.warning(self, "No link", message)
            return

        QDesktopServices.openUrl(QUrl(url))

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())


class MiningTab(QWidget):
    def __init__(self):
        super().__init__()
        self.mining_data = load_mining_data()
        self.refinery_station_lookup = {
            self.refinery_option_key(station.display_name): station
            for station in self.mining_data.refinery_stations
        }
        self.refinery_method_lookup = {
            self.refinery_option_key(method.name): method
            for method in self.mining_data.refinery_methods
        }
        self.uex_prices = {}
        self.uex_price_lists = {}
        self.refinery_sessions = {}
        self.refinery_completed_sessions = []
        self.refinery_tab_session_ids = []
        self.loading_refinery_tabs = False
        self.refinery_session_counter = 0
        self.current_refinery_session = None
        self.loading_refinery_table = False
        self.refinery_timer_remaining_seconds = 0
        self.refinery_timer = QTimer(self)
        self.refinery_timer.setInterval(1000)
        self.refinery_timer.timeout.connect(self.tick_refinery_timer)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = self.create_module_header(
            "Mining & Salvage Intelligence",
            "Ore search, salvage resources, refining, rock breaking, equipment and profit tools.",
        )
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_overview_tab(), "Overview")
        self.tabs.addTab(self.build_ore_finder_tab(), "Ore Finder")
        self.tabs.addTab(self.build_locations_tab(), "Locations")
        self.tabs.addTab(self.build_scan_identifier_tab(), "Scan ID")
        self.tabs.addTab(self.build_quality_bands_tab(), "Quality Bands")
        self.tabs.addTab(self.build_refinery_tab(), "Refinery")
        self.tabs.addTab(self.build_rock_breaker_tab(), "Rock Breaker")
        self.tabs.addTab(self.build_equipment_tab(), "Equipment")
        layout.addWidget(self.tabs, 1)

        self.setLayout(layout)
        self.connect_signals()
        self.populate_mining_tables()

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

    def unique_options(self, values):
        options = []
        seen = set()
        for value in values:
            key = self.refinery_option_key(value)
            if not value or key in seen:
                continue
            seen.add(key)
            options.append(value)
        return options

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
        self.ore_results_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.ore_results_table, 1)
        self.ore_empty_label = self.create_empty_state("No ore results match the current filters.")
        layout.addWidget(self.ore_empty_label)
        widget.setLayout(layout)
        return widget

    def build_locations_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("LOCATION FILTERS")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.location_system_filter = self.create_combo(["All systems", "Stanton", "Pyro", "Nyx", "Unknown"])
        self.location_search_input = QLineEdit()
        self.location_search_input.setPlaceholderText("Filter body/mineral...")
        self.location_focus_filter = self.create_combo(["All mining types", "Surface", "Asteroid", "General"])
        row.addWidget(self.location_system_filter)
        row.addWidget(self.location_search_input, 1)
        row.addWidget(self.location_focus_filter)
        filter_layout.addLayout(row)
        layout.addWidget(filter_card)

        self.location_table = self.create_table([
            "System",
            "Body / Area",
            "Deposit",
            "Minerals",
            "Count",
            "Notes",
        ])
        layout.addWidget(self.location_table, 1)
        self.location_empty_label = self.create_empty_state("No locations match the current filters.")
        layout.addWidget(self.location_empty_label)
        widget.setLayout(layout)
        return widget

    def build_scan_identifier_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("SCAN SIGNATURE IDENTIFIER")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.scan_value_input = QLineEdit()
        self.scan_value_input.setPlaceholderText("Exact value, ~value for +/-10%, or min-max...")
        self.scan_category_filter = self.create_combo([
            "All categories",
            "Legendary",
            "Epic",
            "Rare",
            "Uncommon",
            "Common",
            "ROC Mineables",
            "FPS Mineables",
            "Salvage",
        ])
        row.addWidget(self.scan_value_input, 1)
        row.addWidget(self.scan_category_filter)
        filter_layout.addLayout(row)

        hint = QLabel("Examples: 8600 | ~5000 | 8000-9000 | comma-separated values")
        hint.setObjectName("moduleSubtitle")
        filter_layout.addWidget(hint)
        layout.addWidget(filter_card)

        self.scan_signature_table = self.create_table([
            "Resource",
            "Category",
            "Max",
            "Matches",
            "All Signatures",
        ])
        layout.addWidget(self.scan_signature_table, 1)
        self.scan_empty_label = self.create_empty_state("No scan signatures match the current input.")
        layout.addWidget(self.scan_empty_label)
        widget.setLayout(layout)
        return widget

    def build_quality_bands_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("RESOURCE QUALITY BANDS")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.quality_search_input = QLineEdit()
        self.quality_search_input.setPlaceholderText("Filter resource...")
        self.quality_score_input = QLineEdit()
        self.quality_score_input.setPlaceholderText("Quality score...")
        row.addWidget(self.quality_search_input, 1)
        row.addWidget(self.quality_score_input)
        filter_layout.addLayout(row)

        hint = QLabel("Quality score columns show the mapped resource value for each score band.")
        hint.setObjectName("moduleSubtitle")
        filter_layout.addWidget(hint)
        layout.addWidget(filter_card)

        self.quality_bands_table = self.create_table([
            "Resource",
            "Matched Band",
            *self.mining_data.quality_band_labels,
        ])
        layout.addWidget(self.quality_bands_table, 1)
        self.quality_empty_label = self.create_empty_state("No quality bands match the current filters.")
        layout.addWidget(self.quality_empty_label)
        widget.setLayout(layout)
        return widget

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
        work_layout = QVBoxLayout()
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(12)

        content = QHBoxLayout()
        content.setSpacing(12)

        input_card = self.create_filter_card("SHIP ORES / REFINING")
        input_layout = input_card.layout()

        session_row = QHBoxLayout()
        self.refinery_session_name_input = QLineEdit()
        self.refinery_session_name_input.setPlaceholderText("Session name...")
        self.refinery_new_session_button = QPushButton("New Session")
        self.refinery_save_session_button = QPushButton("Save To History")
        self.refinery_close_session_button = QPushButton("Close Session")
        session_row.addWidget(self.refinery_session_name_input, 1)
        session_row.addWidget(self.refinery_new_session_button)
        session_row.addWidget(self.refinery_save_session_button)
        session_row.addWidget(self.refinery_close_session_button)
        input_layout.addLayout(session_row)

        setup_row = QHBoxLayout()
        self.refinery_station_filter = self.create_combo(self.refinery_station_options())
        self.refinery_method_filter = self.create_combo(self.refinery_method_options())
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
        self.refinery_table.horizontalHeader().setStretchLastSection(True)
        self.refinery_table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.EditKeyPressed
        )
        input_layout.addWidget(self.refinery_table, 1)
        self.refinery_empty_label = self.create_empty_state("No material selected for this refining session.")
        input_layout.addWidget(self.refinery_empty_label)

        summary_card = self.create_filter_card("SELLING / PROFIT SUMMARY")
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
        timer_row.addWidget(self.refinery_timer_start_button)
        timer_row.addWidget(self.refinery_timer_reset_button)
        summary_layout.addLayout(timer_row)

        sell_locations_label = QLabel("SELL LOCATION OPTIONS")
        sell_locations_label.setObjectName("sectionTitle")
        summary_layout.addWidget(sell_locations_label)
        self.refinery_sell_locations_table = self.create_table([
            "Location",
            "Sell Value",
            "Materials",
        ])
        self.refinery_sell_locations_table.setSortingEnabled(False)
        self.refinery_sell_locations_table.setMinimumHeight(150)
        self.refinery_sell_locations_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.refinery_sell_locations_table.horizontalHeader().setStretchLastSection(False)
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

        content.addWidget(input_card, 2)
        content.addWidget(summary_card, 1)
        work_layout.addLayout(content, 1)
        work_widget.setLayout(work_layout)

        self.refinery_history_widget = self.build_refinery_history_widget()
        self.refinery_stack.addWidget(work_widget)
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
        self.refinery_history_table.horizontalHeader().setStretchLastSection(True)
        history_layout.addWidget(self.refinery_history_table, 1)
        self.refinery_history_empty_label = self.create_empty_state("No saved refinery sessions yet.")
        history_layout.addWidget(self.refinery_history_empty_label)
        layout.addWidget(history_card, 1)
        widget.setLayout(layout)
        return widget

    def build_rock_breaker_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        input_card = self.create_filter_card("ROCK PROFILE")
        input_layout = input_card.layout()
        row = QHBoxLayout()
        self.rock_mass_input = QLineEdit()
        self.rock_mass_input.setPlaceholderText("Mass...")
        self.rock_resistance_input = QLineEdit()
        self.rock_resistance_input.setPlaceholderText("Resistance...")
        self.rock_instability_input = QLineEdit()
        self.rock_instability_input.setPlaceholderText("Instability...")
        self.rock_laser_filter = self.create_combo(["Any laser", "Ship mining", "Vehicle mining", "Hand mining"])
        self.rock_calculate_button = QPushButton("Analyze")
        row.addWidget(self.rock_mass_input)
        row.addWidget(self.rock_resistance_input)
        row.addWidget(self.rock_instability_input)
        row.addWidget(self.rock_laser_filter)
        row.addWidget(self.rock_calculate_button)
        input_layout.addLayout(row)
        layout.addWidget(input_card)

        self.rock_table = self.create_table([
            "Setup",
            "Laser",
            "Modules",
            "Power Window",
            "Risk",
            "Notes",
        ])
        self.rock_table.setSortingEnabled(False)
        self.rock_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.rock_table, 1)
        self.rock_empty_label = self.create_empty_state("No rock-breaking setups match the current filters.")
        layout.addWidget(self.rock_empty_label)
        widget.setLayout(layout)
        return widget

    def build_equipment_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_card = self.create_filter_card("EQUIPMENT FILTERS")
        filter_layout = filter_card.layout()
        row = QHBoxLayout()
        self.equipment_search_input = QLineEdit()
        self.equipment_search_input.setPlaceholderText("Search equipment...")
        self.equipment_type_filter = self.create_combo(["All equipment", "Laser", "Module", "Gadget", "Salvage"])
        self.equipment_size_filter = self.create_combo(["Any size", "FPS", "S0", "S1", "S2", "S3", "N/A"])
        row.addWidget(self.equipment_search_input, 1)
        row.addWidget(self.equipment_type_filter)
        row.addWidget(self.equipment_size_filter)
        filter_layout.addLayout(row)
        layout.addWidget(filter_card)

        self.equipment_table = self.create_table([
            "Item",
            "Type",
            "Size",
            "Price",
            "Shops",
            "Best Shop",
            "Best Location",
            "Effect",
            "Notes",
        ])
        layout.addWidget(self.equipment_table, 1)
        self.equipment_empty_label = self.create_empty_state("No equipment matches the current filters.")
        layout.addWidget(self.equipment_empty_label)
        widget.setLayout(layout)
        return widget

    def connect_signals(self):
        self.ore_search_input.textChanged.connect(lambda: self.populate_ore_results())
        self.ore_system_filter.currentTextChanged.connect(lambda: self.populate_ore_results())
        self.ore_type_filter.currentTextChanged.connect(lambda: self.populate_ore_results())
        self.refresh_uex_prices_button.clicked.connect(self.refresh_visible_uex_prices)

        self.location_search_input.textChanged.connect(lambda: self.populate_location_results())
        self.location_system_filter.currentTextChanged.connect(lambda: self.populate_location_results())
        self.location_focus_filter.currentTextChanged.connect(lambda: self.populate_location_results())

        self.scan_value_input.textChanged.connect(lambda: self.populate_scan_identifier())
        self.scan_category_filter.currentTextChanged.connect(lambda: self.populate_scan_identifier())

        self.quality_search_input.textChanged.connect(lambda: self.populate_quality_bands())
        self.quality_score_input.textChanged.connect(lambda: self.populate_quality_bands())

        self.refinery_session_tabs.currentChanged.connect(self.on_refinery_session_tab_changed)
        self.refinery_session_name_input.editingFinished.connect(self.rename_current_refinery_session)
        self.refinery_new_session_button.clicked.connect(self.create_refinery_session)
        self.refinery_save_session_button.clicked.connect(self.save_refinery_session_to_history)
        self.refinery_close_session_button.clicked.connect(self.close_refinery_session)
        self.refinery_history_remove_button.clicked.connect(self.remove_selected_refinery_history)
        self.refinery_history_clear_button.clicked.connect(self.clear_refinery_history)
        self.refinery_remove_material_button.clicked.connect(self.remove_selected_refinery_material)
        self.refinery_refresh_uex_button.clicked.connect(self.refresh_refinery_uex_prices)
        self.refinery_fee_input.textChanged.connect(self.on_refinery_fee_changed)
        self.refinery_time_input.textChanged.connect(self.on_refinery_time_changed)
        self.refinery_station_filter.currentTextChanged.connect(self.on_refinery_setup_changed)
        self.refinery_method_filter.currentTextChanged.connect(self.on_refinery_setup_changed)
        self.refinery_timer_start_button.clicked.connect(self.toggle_refinery_timer)
        self.refinery_timer_reset_button.clicked.connect(self.reset_refinery_timer)
        self.refinery_table.itemChanged.connect(self.on_refinery_item_changed)

        self.equipment_search_input.textChanged.connect(lambda: self.populate_equipment_results())
        self.equipment_type_filter.currentTextChanged.connect(lambda: self.populate_equipment_results())
        self.equipment_size_filter.currentTextChanged.connect(lambda: self.populate_equipment_results())
        self.rock_mass_input.textChanged.connect(lambda: self.populate_rock_breaker_results())
        self.rock_resistance_input.textChanged.connect(lambda: self.populate_rock_breaker_results())
        self.rock_instability_input.textChanged.connect(lambda: self.populate_rock_breaker_results())
        self.rock_laser_filter.currentTextChanged.connect(lambda: self.populate_rock_breaker_results())
        self.rock_calculate_button.clicked.connect(self.populate_rock_breaker_results)

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
        self.mining_status_label.setText(
            f"Loaded {len(data.minerals)} minerals, "
            f"{len(data.locations)} location rows, "
            f"{len(data.equipment)} equipment items. "
            f"Also loaded {len(data.quality_bands)} quality-band rows and "
            f"{len(data.scan_signatures)} scan signatures, "
            f"{len(data.refinery_stations)} refineries and "
            f"{len(data.refinery_methods)} refinery methods. "
            "Market prices are fetched live from UEX and are not stored locally."
        )

        if data.errors:
            self.mining_source_label.setText("Data warnings: " + " | ".join(data.errors))
        else:
            self.mining_source_label.setText(
                "Static mining reference data is loaded from the app/reference bundle. "
                "Live market prices use UEX on demand."
            )

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
        self.ore_empty_label.setVisible(not rows)

    def refresh_visible_uex_prices(self):
        minerals = self.visible_ore_minerals()
        if not minerals:
            QMessageBox.information(
                self,
                "No visible ores",
                "No visible ore rows to refresh.",
            )
            return

        self.refresh_uex_prices_button.setEnabled(False)
        self.refresh_uex_prices_button.setText("Refreshing UEX...")
        QApplication.processEvents()

        refreshed = 0
        failed = []
        for mineral in minerals:
            try:
                prices = fetch_commodity_sell_prices(mineral)
            except (UEXError, requests.RequestException, ValueError) as exc:
                failed.append(f"{mineral}: {exc}")
                continue

            self.uex_prices[mineral.lower()] = prices[0] if prices else None
            refreshed += 1

        self.refresh_uex_prices_button.setEnabled(True)
        self.refresh_uex_prices_button.setText("Refresh Visible UEX Prices")
        self.populate_ore_results()

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

    def populate_rock_breaker_results(self):
        lasers = [
            laser
            for laser in self.mining_data.rock_lasers
            if self.rock_laser_matches_filter(laser)
        ]
        mass = self.parse_float(self.rock_mass_input.text())
        resistance = self.parse_float(self.rock_resistance_input.text())
        instability = self.parse_float(self.rock_instability_input.text())
        has_power_stats = mass > 0 and resistance > 0

        if not has_power_stats:
            rows = [
                [
                    "Baseline",
                    f"{laser.name} S{laser.size}",
                    f"{laser.module_slots} slots",
                    f"{self.format_number(laser.min_power)}-{self.format_number(laser.max_power)}",
                    "Enter rock stats",
                    (
                        f"Price {self.format_auec_amount(laser.price or 0)} | "
                        f"Res x{laser.resistance_factor:g} | Instab x{laser.instability_factor:g} | "
                        f"Window x{laser.optimal_charge_window:g}"
                    ),
                ]
                for laser in sorted(lasers, key=lambda item: (item.size, item.name.lower()))
            ]
            self.set_table_rows(self.rock_table, rows)
            self.color_rock_risk_cells()
            self.rock_empty_label.setVisible(not rows)
            return

        module_candidates = self.rock_module_candidates()
        gadgets = [None, *self.mining_data.rock_gadgets]
        setups = []
        for laser in lasers:
            for modules in self.rock_module_combinations(module_candidates, laser.module_slots):
                for gadget in gadgets:
                    setups.append(self.evaluate_rock_setup(laser, modules, gadget, mass, resistance, instability))

        setups.sort(key=lambda item: item["score"])
        rows = []
        for rank, setup in enumerate(setups[:120], start=1):
            rows.append([
                f"#{rank} {setup['setup']}",
                setup["laser"],
                setup["modules"],
                setup["power_window"],
                setup["risk"],
                setup["notes"],
            ])

        self.set_table_rows(self.rock_table, rows)
        self.color_rock_risk_cells()
        self.rock_empty_label.setVisible(not rows)

    def rock_laser_matches_filter(self, laser):
        selected = self.rock_laser_filter.currentText()
        if selected == "Ship mining":
            return laser.size >= 1
        if selected in {"Vehicle mining", "Hand mining"}:
            return laser.size == 0
        return True

    def rock_module_candidates(self):
        return [
            module
            for module in self.mining_data.rock_modules
            if any(
                abs(value - 1) > 0.001
                for value in (
                    module.mining_laser_power,
                    module.resistance_factor,
                    module.instability_factor,
                    module.optimal_charge_rate,
                    module.optimal_charge_window,
                )
            )
        ]

    def rock_module_combinations(self, modules, slots):
        if slots <= 0:
            return [()]

        combos = [()]
        for size in range(1, min(slots, 3) + 1):
            combos.extend(combinations(modules, size))
        return combos

    def evaluate_rock_setup(self, laser, modules, gadget, mass, resistance, instability):
        power_factor = self.multiply_factors([module.mining_laser_power for module in modules])
        resistance_factor = laser.resistance_factor * self.multiply_factors(
            [module.resistance_factor for module in modules]
        )
        instability_factor = laser.instability_factor * self.multiply_factors(
            [module.instability_factor for module in modules]
        )
        charge_rate = laser.optimal_charge_rate * self.multiply_factors(
            [module.optimal_charge_rate for module in modules]
        )
        charge_window = laser.optimal_charge_window * self.multiply_factors(
            [module.optimal_charge_window for module in modules]
        )

        if gadget:
            resistance_factor *= gadget.resistance_factor
            instability_factor *= gadget.instability_factor
            charge_window *= gadget.optimal_charge_window
            charge_rate *= gadget.optimal_charge_rate

        min_power = laser.min_power * power_factor
        max_power = laser.max_power * power_factor
        required_power = mass * resistance * resistance_factor
        rock_instability = instability if instability > 0 else 1
        effective_instability = rock_instability * instability_factor
        risk_score = effective_instability / max(charge_window, 0.1)

        if required_power > max_power:
            risk = "Too weak"
            score = 100000 + ((required_power / max(max_power, 1)) * 1000) + risk_score
            setup = "Needs more power"
        elif required_power < min_power:
            risk = "Overpowered"
            score = 50000 + ((min_power / max(required_power, 1)) * 250) + risk_score
            setup = "Throttle carefully"
        else:
            if risk_score >= 1.35 or effective_instability >= 1.5 or charge_window < 0.7:
                risk = "High"
            elif risk_score >= 0.85 or effective_instability >= 1.1 or charge_window < 1:
                risk = "Medium"
            else:
                risk = "Low"

            score = (
                risk_score * 100
                - min(max_power - required_power, max_power) / max(max_power, 1) * 20
                + len(modules) * 4
                + (6 if gadget else 0)
            )
            setup = "Recommended" if risk == "Low" else "Workable"

        module_text = ", ".join(module.name for module in modules) or "None"
        if gadget:
            module_text = f"{module_text} + {gadget.name} gadget"

        notes = (
            f"S{laser.size} | Slots {laser.module_slots} | "
            f"Res x{resistance_factor:.2f} | Instab x{effective_instability:.2f} | "
            f"Window x{charge_window:.2f} | Rate x{charge_rate:.2f}"
        )
        if required_power > max_power:
            notes += f" | Needs {required_power / max(max_power, 1):.1f}x max power"

        return {
            "score": score,
            "setup": setup,
            "laser": f"{laser.name} S{laser.size}",
            "modules": module_text,
            "power_window": (
                f"Need {self.format_number(required_power)} / "
                f"{self.format_number(min_power)}-{self.format_number(max_power)}"
            ),
            "risk": risk,
            "notes": notes,
        }

    def multiply_factors(self, values):
        result = 1.0
        for value in values:
            result *= value
        return result

    def color_rock_risk_cells(self):
        colors = {
            "Low": QColor("#5cffbd"),
            "Medium": QColor("#ffd166"),
            "High": QColor("#ff8f66"),
            "Too weak": QColor("#ff5c5c"),
            "Overpowered": QColor("#ffb86b"),
        }
        for row in range(self.rock_table.rowCount()):
            item = self.rock_table.item(row, 4)
            if item and item.text() in colors:
                item.setForeground(colors[item.text()])

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
        grouped_locations = {}
        has_sell_quantity = False
        has_price_rows = False
        for material, entry in session.get("materials", {}).items():
            sell_quantity = self.refinery_sell_quantity_cscu(material, entry, session)
            if sell_quantity <= 0:
                continue

            has_sell_quantity = True
            prices = self.uex_price_lists.get(material.lower(), [])
            has_price_rows = has_price_rows or bool(prices)
            for price in prices:
                if not price.price_sell:
                    continue

                key = (
                    price.star_system_name,
                    price.location_name,
                    price.terminal_name,
                )
                location = grouped_locations.setdefault(key, {
                    "label": self.format_uex_terminal(price),
                    "materials": [],
                    "value": 0.0,
                })
                value = self.refinery_material_value_from_price(sell_quantity, price.price_sell)
                location["value"] += value
                location["materials"].append(f"{material} ({self.format_auec_amount(value)})")

        rows = sorted(
            grouped_locations.values(),
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
            else:
                empty_text = "No matching UEX sell locations found for the selected materials."
            self.refinery_sell_locations_empty_label.setText(empty_text)

        self.refinery_sell_locations_empty_label.setVisible(not rows)
        self.refinery_sell_locations_table.setVisible(bool(rows))
        if rows:
            self.resize_refinery_sell_location_columns()

    def resize_refinery_sell_location_columns(self):
        header = self.refinery_sell_locations_table.horizontalHeader()
        for column in range(self.refinery_sell_locations_table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)

        self.refinery_sell_locations_table.resizeColumnsToContents()
        padding = 18
        for column in range(self.refinery_sell_locations_table.columnCount()):
            width = self.refinery_sell_locations_table.columnWidth(column) + padding
            self.refinery_sell_locations_table.setColumnWidth(column, width)
            header.setSectionResizeMode(column, QHeaderView.Interactive)

    def refresh_refinery_uex_prices(self):
        materials = sorted(self.refinery_session()["materials"])
        if not materials:
            QMessageBox.information(
                self,
                "No ores selected",
                "Add one or more refinery materials before refreshing UEX prices.",
            )
            return

        self.refinery_refresh_uex_button.setEnabled(False)
        self.refinery_refresh_uex_button.setText("Refreshing UEX...")
        QApplication.processEvents()

        refreshed = 0
        failed = []
        for material in materials:
            try:
                prices = fetch_commodity_sell_prices(material)
            except (UEXError, requests.RequestException, ValueError) as exc:
                failed.append(f"{material}: {exc}")
                continue

            self.uex_price_lists[material.lower()] = prices
            self.uex_prices[material.lower()] = prices[0] if prices else None
            refreshed += 1

        self.refinery_refresh_uex_button.setEnabled(True)
        self.refinery_refresh_uex_button.setText("Refresh UEX For Session")
        self.populate_refinery_table()

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

        method = self.selected_refinery_method()
        method_yield = method.yield_factor if method else REFINERY_METHOD_YIELD_FALLBACKS.get(
            self.refinery_method_filter.currentText(),
            0.0,
        )
        if method_yield <= 0:
            return 0.0

        station = self.selected_refinery_station()
        bonus = station.bonuses.get(self.canonical_refinery_material(material), 0.0) if station else 0.0
        salvage_multiplier = SALVAGE_REFINERY_DETAILS.get(material, {}).get("yield_multiplier", 1.0)
        return max(0.0, float(round(qty * method_yield * (1 + bonus) * salvage_multiplier)))

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

    def populate_location_results(self):
        query = self.location_search_input.text().strip().lower()
        system_filter = self.location_system_filter.currentText()
        deposit_filter = self.location_focus_filter.currentText()
        grouped = {}

        for location in self.mining_data.locations:
            if system_filter != "All systems" and location.system != system_filter:
                continue
            if deposit_filter != "All mining types" and location.deposit_type != deposit_filter:
                continue
            if query and query not in self.location_search_text(location):
                continue

            key = (location.system, location.body, location.deposit_type)
            group = grouped.setdefault(key, {"minerals": set(), "notes": set()})
            group["minerals"].add(location.mineral)
            if location.notes:
                group["notes"].add(location.notes)

        rows = []
        for (system, body, deposit_type), group in grouped.items():
            minerals = sorted(group["minerals"])
            rows.append([
                system,
                body,
                deposit_type,
                ", ".join(minerals),
                str(len(minerals)),
                ", ".join(sorted(group["notes"])),
            ])

        rows.sort(key=lambda row: (row[0], row[1].lower(), row[2]))
        self.set_table_rows(self.location_table, rows)
        self.location_empty_label.setVisible(not rows)

    def populate_scan_identifier(self):
        tokens = self.parse_scan_tokens(self.scan_value_input.text())
        category_filter = self.scan_category_filter.currentText()
        rows = []

        for signature in self.mining_data.scan_signatures:
            if category_filter != "All categories" and signature.category != category_filter:
                continue

            matches = self.match_scan_values(signature.values, tokens)
            if tokens and not matches:
                continue

            rows.append([
                signature.resource,
                signature.category,
                f"{signature.max_multiplier}x",
                self.format_signature_values(matches) if matches else "",
                self.format_signature_values(signature.values),
            ])

        rows.sort(key=lambda row: (self.scan_category_rank(row[1]), row[0].lower()))
        self.set_table_rows(self.scan_signature_table, rows)
        self.scan_empty_label.setVisible(not rows)

    def populate_quality_bands(self):
        query = self.quality_search_input.text().strip().lower()
        score = self.parse_int(self.quality_score_input.text())
        rows = []

        for row in self.mining_data.quality_bands:
            if query and query not in row.resource.lower():
                continue

            matched_band = self.quality_match_text(row, score)
            rows.append([
                row.resource,
                matched_band,
                *[
                    self.format_quality_value(value)
                    for value in row.values
                ],
            ])

        rows.sort(key=lambda values: values[0].lower())
        self.set_table_rows(self.quality_bands_table, rows)
        self.quality_empty_label.setVisible(not rows)

    def populate_equipment_results(self):
        query = self.equipment_search_input.text().strip().lower()
        type_filter = self.equipment_type_filter.currentText()
        size_filter = self.equipment_size_filter.currentText()
        rows = []

        for item in self.mining_data.equipment:
            if type_filter != "All equipment" and item.equipment_type != type_filter:
                continue
            if size_filter != "Any size" and item.size != size_filter:
                continue
            searchable = " ".join((
                item.name,
                item.equipment_type,
                item.size,
                str(item.shop_count),
                item.best_shop,
                item.best_location,
                item.effect,
                item.notes,
            )).lower()
            if query and query not in searchable:
                continue

            rows.append([
                item.name,
                item.equipment_type,
                item.size,
                self.format_price(item.price),
                f"{item.shop_count} locations" if item.shop_count else "No known shops",
                item.best_shop,
                item.best_location,
                item.effect,
                item.notes,
            ])

        rows.sort(key=lambda row: (row[1], row[2], row[0].lower()))
        self.set_table_rows(self.equipment_table, rows)
        self.equipment_empty_label.setVisible(not rows)

    def location_search_text(self, location):
        return " ".join((
            location.mineral,
            location.system,
            location.body,
            location.deposit_type,
            location.notes,
        )).lower()

    def set_table_rows(self, table, rows):
        sorting_enabled = table.isSortingEnabled()
        table.setSortingEnabled(False)
        table.setRowCount(len(rows))

        for row_index, row_values in enumerate(rows):
            for col_index, value in enumerate(row_values):
                item = QTableWidgetItem(str(value))
                table.setItem(row_index, col_index, item)

        table.setSortingEnabled(sorting_enabled)

    def parse_scan_tokens(self, text):
        tokens = []
        for raw_token in text.split(","):
            token = raw_token.strip().replace(" ", "")
            if not token:
                continue

            if token.startswith("~"):
                center = self.parse_int(token[1:])
                if center is None:
                    continue
                tokens.append((int(center * 0.9), int(center * 1.1)))
                continue

            if "-" in token:
                left, right = token.split("-", 1)
                low = self.parse_int(left)
                high = self.parse_int(right)
                if low is None or high is None:
                    continue
                tokens.append((min(low, high), max(low, high)))
                continue

            value = self.parse_int(token)
            if value is not None:
                tokens.append((value, value))

        return tokens

    def match_scan_values(self, values, tokens):
        if not tokens:
            return []

        matches = []
        for value in values:
            for low, high in tokens:
                if low <= value <= high:
                    matches.append(value)
                    break

        return matches

    def scan_category_rank(self, category):
        order = {
            "Legendary": 0,
            "Epic": 1,
            "Rare": 2,
            "Uncommon": 3,
            "Common": 4,
            "ROC Mineables": 5,
            "FPS Mineables": 6,
            "Salvage": 7,
        }
        return order.get(category, 99)

    def quality_match_text(self, row, score):
        if score is None:
            return ""

        for label, value in zip(self.mining_data.quality_band_labels, row.values):
            bounds = label.rstrip("Q").split("-", 1)
            if len(bounds) != 2:
                continue
            low = self.parse_int(bounds[0])
            high = self.parse_int(bounds[1])
            if low is None or high is None:
                continue
            if low <= score <= high:
                return f"{label}: {self.format_quality_value(value)}"

        return "Out of range"

    def parse_int(self, value):
        cleaned = "".join(char for char in str(value) if char.isdigit())
        if not cleaned:
            return None

        try:
            return int(cleaned)
        except ValueError:
            return None

    def parse_float(self, value):
        text = str(value or "").strip().replace(" ", "")
        if not text:
            return 0.0

        if "," in text and "." not in text:
            parts = text.split(",")
            if len(parts[-1]) == 3 and all(part.isdigit() for part in parts):
                text = "".join(parts)
            else:
                text = text.replace(",", ".")
        else:
            text = text.replace(",", "")

        cleaned = "".join(char for char in text if char.isdigit() or char in ".-")
        if cleaned in ("", "-", ".", "-."):
            return 0.0

        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def format_signature_values(self, values):
        return " | ".join(f"{value:,}" for value in values)

    def format_quality_value(self, value):
        if value is None:
            return "-"

        return str(value)

    def format_price(self, value):
        if value in (None, "", 0):
            return "N/A"

        try:
            return f"{float(value):,.0f} aUEC"
        except (TypeError, ValueError):
            return str(value)

    def format_number(self, value):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)

        if abs(numeric - round(numeric)) < 0.001:
            return f"{numeric:,.0f}"

        return f"{numeric:,.2f}"

    def format_auec_amount(self, value):
        return f"{self.format_number(value)} aUEC"

    def create_filter_card(self, title):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)
        card.setLayout(layout)
        return card

    def create_combo(self, items):
        combo = QComboBox()
        combo.addItems(items)
        return combo

    def create_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSortingEnabled(True)
        table.setWordWrap(False)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        for index in range(len(headers)):
            table.horizontalHeader().setSectionResizeMode(index, QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(False)
        return table

    def create_empty_state(self, text):
        label = QLabel(text)
        label.setObjectName("emptyState")
        label.setAlignment(Qt.AlignCenter)
        return label


class TradingTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("playerCard")
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(4)
        title = QLabel("Trading")
        title.setObjectName("moduleHeading")
        subtitle = QLabel("Market routes, commodity prices and hauling tools will live here later.")
        subtitle.setObjectName("moduleSubtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header.setLayout(header_layout)
        layout.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.addWidget(self.create_trading_card(
            "MARKET WATCH",
            "Track commodity prices, demand and supply.",
        ), 0, 0)
        grid.addWidget(self.create_trading_card(
            "ROUTE PLANNER",
            "Compare buy/sell locations and cargo margins.",
        ), 0, 1)
        grid.addWidget(self.create_trading_card(
            "CARGO NOTES",
            "Keep local notes for hauling runs and risky terminals.",
        ), 1, 0)
        grid.addWidget(self.create_trading_card(
            "MINING LINK",
            "Use refined ore value as input for later profit planning.",
        ), 1, 1)
        grid.setRowStretch(2, 1)
        layout.addLayout(grid, 1)

        self.setLayout(layout)

    def create_trading_card(self, title, summary):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        summary_label = QLabel(summary)
        summary_label.setObjectName("valueText")
        summary_label.setWordWrap(True)
        status = QLabel("Planned")
        status.setObjectName("moduleSubtitle")
        layout.addWidget(title_label)
        layout.addWidget(summary_label)
        layout.addWidget(status)
        layout.addStretch(1)
        card.setLayout(layout)
        return card


class ItemFinderTab(QWidget):
    def __init__(self):
        super().__init__()
        self.finder_items = []
        self.visible_finder_items = []
        self.finder_locations = []
        self.current_finder_item_id = None
        self.finder_last_refresh = None
        self.finder_refresh_interval = timedelta(hours=4)
        self.availability_counts = {}
        self.auto_availability_limit = 25
        self.availability_auto_load_scheduled = False
        self.auto_loading_availability = False
        self.finder_refresh_timer = QTimer(self)
        self.finder_refresh_timer.setInterval(int(self.finder_refresh_interval.total_seconds() * 1000))
        self.finder_refresh_timer.timeout.connect(lambda: self.refresh_finder_items(silent=True))

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_module_header(
            "Item Finder",
            "Live lookup for equipment, ship sale/rental locations and other SC shopping intel. No source data is stored locally.",
        ))

        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self.build_item_search_panel(), 3)
        content.addWidget(self.build_item_detail_panel(), 2)
        layout.addLayout(content, 1)

        self.setLayout(layout)
        self.connect_signals()
        self.populate_item_results()
        self.update_selected_item_panel()

    def build_item_search_panel(self):
        card = self.create_filter_card("LIVE ITEM SEARCH")
        layout = card.layout()

        row = QHBoxLayout()
        self.item_search_input = QLineEdit()
        self.item_search_input.setPlaceholderText("Search gear, ship, location or effect...")
        self.item_category_filter = self.create_combo([
            "All categories",
            "Ships for Sale",
            "Ships for Rent",
            "Ships for Earning",
            *cstone_category_labels(),
        ])
        row.addWidget(self.item_search_input, 1)
        row.addWidget(self.item_category_filter)
        layout.addLayout(row)

        button_row = QHBoxLayout()
        self.refresh_finder_items_button = QPushButton("Refresh Live Data")
        self.open_source_home_button = QPushButton("Open Source")
        self.open_source_category_button = QPushButton("Open Category")
        button_row.addWidget(self.refresh_finder_items_button)
        button_row.addWidget(self.open_source_home_button)
        button_row.addWidget(self.open_source_category_button)
        layout.addLayout(button_row)

        self.finder_status_label = QLabel(
            "Press Enter to load live data. First load can take a while and the app may look frozen briefly; Not Sold Cornerstone items are skipped."
        )
        self.finder_status_label.setObjectName("moduleSubtitle")
        self.finder_status_label.setWordWrap(True)
        layout.addWidget(self.finder_status_label)

        self.item_results_table = self.create_table([
            "Item",
            "Category",
            "Type",
            "Availability",
            "Summary",
        ])
        layout.addWidget(self.item_results_table, 1)
        self.item_empty_label = self.create_empty_state("No live item data loaded yet.")
        layout.addWidget(self.item_empty_label)
        return card

    def build_item_detail_panel(self):
        card = self.create_filter_card("BUY LOCATIONS")
        layout = card.layout()

        self.selected_item_name_label = QLabel("No item selected")
        self.selected_item_name_label.setObjectName("orgName")
        self.selected_item_category_label = QLabel("")
        self.selected_item_category_label.setObjectName("moduleSubtitle")
        self.selected_item_effect_label = QLabel("")
        self.selected_item_effect_label.setObjectName("valueText")
        self.selected_item_effect_label.setWordWrap(True)
        layout.addWidget(self.selected_item_name_label)
        layout.addWidget(self.selected_item_category_label)
        layout.addWidget(self.selected_item_effect_label)

        button_row = QHBoxLayout()
        self.load_item_locations_button = QPushButton("Reload Locations")
        self.open_selected_item_button = QPushButton("Open Item")
        self.open_selected_location_button = QPushButton("Open Location")
        button_row.addWidget(self.load_item_locations_button)
        button_row.addWidget(self.open_selected_item_button)
        button_row.addWidget(self.open_selected_location_button)
        layout.addLayout(button_row)

        self.item_locations_table = self.create_table([
            "Location",
            "Base Price",
            "Verified",
        ])
        layout.addWidget(self.item_locations_table, 1)
        self.item_location_empty_label = self.create_empty_state(
            "Select an item and load buy locations."
        )
        layout.addWidget(self.item_location_empty_label)
        return card

    def connect_signals(self):
        self.item_search_input.textChanged.connect(self.populate_item_results)
        self.item_search_input.returnPressed.connect(self.ensure_finder_data_then_search)
        self.item_category_filter.currentTextChanged.connect(self.populate_item_results)
        self.refresh_finder_items_button.clicked.connect(self.refresh_finder_items)
        self.open_source_home_button.clicked.connect(self.open_source_home)
        self.open_source_category_button.clicked.connect(self.open_selected_category)
        self.item_results_table.itemSelectionChanged.connect(self.on_selected_item_changed)
        self.item_results_table.cellDoubleClicked.connect(lambda row, column: self.load_selected_item_locations())
        self.item_locations_table.itemSelectionChanged.connect(self.update_location_action_state)
        self.load_item_locations_button.clicked.connect(self.load_selected_item_locations)
        self.open_selected_item_button.clicked.connect(self.open_selected_item)
        self.open_selected_location_button.clicked.connect(self.open_selected_location)

    def ensure_finder_data_then_search(self):
        if self.finder_data_is_stale():
            self.refresh_finder_items()
            return

        self.populate_item_results()

    def finder_data_is_stale(self):
        if not self.finder_items or not self.finder_last_refresh:
            return True

        return datetime.now() - self.finder_last_refresh >= self.finder_refresh_interval

    def refresh_finder_items(self, silent=False):
        self.refresh_finder_items_button.setEnabled(False)
        self.refresh_finder_items_button.setText("Refreshing...")
        QApplication.processEvents()

        loaded_items = []
        failed = []
        try:
            loaded_items.extend(fetch_cstone_items())
        except (CStoneError, requests.RequestException, ValueError) as exc:
            failed.append(f"Cornerstone: {exc}")

        try:
            loaded_items.extend(fetch_scfocus_ship_items())
        except (requests.RequestException, ValueError) as exc:
            failed.append(f"SC Focus: {exc}")

        if loaded_items:
            self.finder_items = loaded_items
            self.finder_last_refresh = datetime.now()
            if not self.finder_refresh_timer.isActive():
                self.finder_refresh_timer.start()

        if failed:
            self.finder_status_label.setText(
                f"Loaded {len(self.finder_items)} rows with {len(failed)} source warning(s). "
                "Data is in-memory only."
            )
            if not silent:
                QMessageBox.warning(self, "Live refresh warning", "\n".join(failed))
        else:
            self.finder_status_label.setText(
                f"Loaded {len(self.finder_items)} live rows from Cornerstone and SC Focus. "
                "Data is in-memory only and will refresh every 4 hours."
            )

        self.refresh_finder_items_button.setEnabled(True)
        self.refresh_finder_items_button.setText("Refresh Live Data")
        self.populate_item_results()

    def populate_item_results(self):
        query = self.item_search_input.text().strip().lower()
        category_filter = self.item_category_filter.currentText()
        self.visible_finder_items = []

        for item in self.finder_items:
            if category_filter != "All categories" and item.category != category_filter:
                continue
            searchable = " ".join((
                item.name,
                item.source,
                item.category,
                item.item_type,
                item.availability,
                item.effect,
            )).lower()
            if query and query not in searchable:
                continue
            self.visible_finder_items.append(item)

        self.item_results_table.setSortingEnabled(False)
        self.item_results_table.clearSelection()
        self.item_results_table.setRowCount(len(self.visible_finder_items))
        for row_index, item in enumerate(self.visible_finder_items):
            values = [
                item.name,
                item.category,
                item.item_type,
                self.display_item_availability(item),
                item.effect,
            ]
            for col_index, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                table_item.setData(Qt.UserRole, row_index)
                if col_index == 3:
                    table_item.setForeground(QColor("#68e6a5" if item.sold else "#7bb9c8"))
                self.item_results_table.setItem(row_index, col_index, table_item)

        self.item_results_table.setSortingEnabled(True)
        self.item_empty_label.setVisible(not self.visible_finder_items)
        if not self.finder_items:
            self.item_empty_label.setText("No live item data loaded yet.")
        else:
            self.item_empty_label.setText("No items match the current filters.")
        self.update_selected_item_panel()
        self.schedule_availability_autoload()

    def on_selected_item_changed(self):
        previous_item_id = self.current_finder_item_id
        item = self.selected_item()
        self.update_selected_item_panel()
        if item and item.item_id != previous_item_id:
            self.load_selected_item_locations()

    def display_item_availability(self, item):
        if item.source != "Cornerstone":
            return item.availability

        key = self.finder_item_key(item)
        if key in self.availability_counts:
            return self.location_count_text(self.availability_counts[key])

        pending = self.pending_visible_cornerstone_items()
        if len(pending) <= self.auto_availability_limit:
            return "Checking..."

        return "Narrow search"

    def schedule_availability_autoload(self):
        if self.auto_loading_availability or self.availability_auto_load_scheduled:
            return

        pending = self.pending_visible_cornerstone_items()
        if not pending:
            return

        if len(pending) > self.auto_availability_limit:
            self.finder_status_label.setText(
                f"{len(pending)} visible Cornerstone rows need location counts. "
                f"Narrow the search to {self.auto_availability_limit} or fewer and they load automatically."
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
        QApplication.processEvents()

        for item in pending:
            try:
                locations = fetch_cstone_item_locations(item.detail_url)
            except (CStoneError, requests.RequestException, ValueError):
                self.set_item_availability_count(item, 0)
                continue

            self.set_item_availability_count(item, len(locations))
            if self.selected_item() and self.finder_item_key(self.selected_item()) == self.finder_item_key(item):
                self.finder_locations = locations
                self.populate_location_rows()
            QApplication.processEvents()

        self.auto_loading_availability = False
        self.finder_status_label.setText("Availability loaded for visible rows.")

    def pending_visible_cornerstone_items(self):
        pending = []
        seen = set()
        for item in self.visible_finder_items:
            key = self.finder_item_key(item)
            if item.source == "Cornerstone" and key not in self.availability_counts and key not in seen:
                pending.append(item)
                seen.add(key)

        return pending

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
        self.selected_item_effect_label.setText(item.effect)
        self.update_location_action_state()

    def load_selected_item_locations(self):
        item = self.selected_item()
        if not item:
            return

        self.load_item_locations_button.setEnabled(False)
        self.load_item_locations_button.setText("Loading...")
        QApplication.processEvents()

        if item.source == "SC Focus":
            self.finder_locations = list(item.locations)
        else:
            try:
                self.finder_locations = fetch_cstone_item_locations(item.detail_url)
            except (CStoneError, requests.RequestException, ValueError) as exc:
                QMessageBox.warning(self, "Location lookup failed", str(exc))
                self.finder_locations = []

            self.set_item_availability_count(item, len(self.finder_locations))

        self.load_item_locations_button.setEnabled(True)
        self.load_item_locations_button.setText("Reload Locations")
        self.populate_location_rows()

    def set_item_availability_count(self, item, location_count):
        if not item or item.source != "Cornerstone":
            return

        key = self.finder_item_key(item)
        availability = self.location_count_text(location_count)
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
                f"{updated_item.category} | {updated_item.item_type} | {updated_item.availability} | Source: {updated_item.source}"
            )

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

    def finder_item_key(self, item):
        return (item.source, item.item_id)

    def location_count_text(self, location_count):
        return f"{location_count} location{'s' if location_count != 1 else ''}"

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
                if col_index == 1:
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.item_locations_table.setItem(row_index, col_index, table_item)

        self.item_locations_table.setSortingEnabled(True)
        self.item_location_empty_label.setVisible(not self.finder_locations)
        if self.finder_locations:
            self.item_locations_table.selectRow(0)
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

    def open_source_home(self):
        item = self.selected_item()
        if item and item.source == "SC Focus":
            QDesktopServices.openUrl(QUrl(SCFOCUS_SHIPS_URL))
            return

        if not item and self.item_category_filter.currentText().startswith("Ships for "):
            QDesktopServices.openUrl(QUrl(SCFOCUS_SHIPS_URL))
            return

        QDesktopServices.openUrl(QUrl(CSTONE_HOME_URL))

    def open_selected_category(self):
        item = self.selected_item()
        if item:
            QDesktopServices.openUrl(QUrl(item.category_url))
            return

        category = self.item_category_filter.currentText()
        if category.startswith("Ships for "):
            QDesktopServices.openUrl(QUrl(SCFOCUS_SHIPS_URL))
            return

        QDesktopServices.openUrl(QUrl(cstone_category_url(category)))

    def open_selected_item(self):
        item = self.selected_item()
        if item:
            QDesktopServices.openUrl(QUrl(item.detail_url))

    def open_selected_location(self):
        url = self.selected_location_url()
        if url:
            QDesktopServices.openUrl(QUrl(url))

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

    def create_filter_card(self, title):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)
        card.setLayout(layout)
        return card

    def create_combo(self, items):
        combo = QComboBox()
        combo.addItems(items)
        return combo

    def create_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSortingEnabled(True)
        table.setWordWrap(False)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        for index in range(len(headers)):
            table.horizontalHeader().setSectionResizeMode(index, QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def create_empty_state(self, text):
        label = QLabel(text)
        label.setObjectName("emptyState")
        label.setAlignment(Qt.AlignCenter)
        return label


class NotesTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Global notes/watchlist kommer her.\n\n"
            "Dette blir brukt til:\n"
            "- Watchlist\n"
            "- Hostile list\n"
            "- Friendly list\n"
            "- NOVA/Defence/Relief/Skyline/Frontiers/Core/BALDER tagging"
        )

        layout.addWidget(text)
        self.setLayout(layout)


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Settings will be here.\n\n"
            "Planned:\n"
            "- Theme\n"
            "- Default scan region\n"
            "- RSI lookup timeout\n"
            "- Local data folders\n"
            "- Export/import"
        )

        layout.addWidget(text)
        self.setLayout(layout)


def run_app():
    init_db()

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
