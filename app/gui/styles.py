BACKGROUND = "#071118"
PANEL_BG = "#0b1820"
PANEL_BG_HOVER = "#102735"
PANEL_BORDER = "#1e5060"
PANEL_BORDER_ACTIVE = "#28788d"
TEXT_PRIMARY = "#effcff"
TEXT_HEADING = "#f5fdff"
TEXT_SECONDARY = "#7bb9c8"
TEXT_MUTED = "#6a8894"
ACCENT = "#33dfff"
ACCENT_BRIGHT = "#44e6ff"
BUTTON_BG = "#132733"
BUTTON_BG_HOVER = "#173849"
INPUT_BG = "#0b1820"
INPUT_BORDER = "#264858"
SELECTION_BG = "#123a49"


APP_STYLE = """
QMainWindow, QWidget {
    background: %(BACKGROUND)s;
    color: #d8f7ff;
    font-family: Segoe UI;
    font-size: 10pt;
}

QTabWidget::pane {
    border: 1px solid #1d3442;
    background: %(BACKGROUND)s;
}

QTabBar::tab {
    background: #121a22;
    color: #d8f7ff;
    border: 1px solid #243746;
    border-bottom: 0;
    padding: 7px 12px;
}

QTabBar::tab:selected {
    background: #0d2530;
    color: %(ACCENT_BRIGHT)s;
}

QLineEdit, QTextEdit, QComboBox {
    background: %(INPUT_BG)s;
    border: 1px solid %(INPUT_BORDER)s;
    border-radius: 4px;
    color: #f2fdff;
    selection-background-color: #00a8cc;
    padding: 6px;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #24d8ff;
}

QPushButton {
    background: %(BUTTON_BG)s;
    border: 1px solid #2b5b6e;
    border-radius: 4px;
    color: #e6fbff;
    padding: 7px 12px;
}

QPushButton:hover {
    background: %(BUTTON_BG_HOVER)s;
    border-color: #34d8f5;
}

QPushButton:disabled {
    background: #111820;
    border-color: #24313b;
    color: #5f7780;
}

QCheckBox {
    background: transparent;
    border: none;
    color: %(TEXT_PRIMARY)s;
    spacing: 7px;
    padding: 3px 4px;
}

QCheckBox:hover {
    color: %(ACCENT_BRIGHT)s;
}

QCheckBox:disabled {
    color: #5f7780;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #2b5b6e;
    border-radius: 3px;
    background: #081820;
}

QCheckBox::indicator:hover {
    border-color: #34d8f5;
}

QCheckBox::indicator:checked {
    background: #0d5362;
    border-color: %(ACCENT)s;
}

QCheckBox::indicator:checked:disabled {
    background: #24313b;
    border-color: #5f7780;
}

QScrollArea {
    border: 0;
    background: transparent;
}

QTableWidget {
    background: %(BACKGROUND)s;
    border: 1px solid %(PANEL_BORDER)s;
    border-radius: 4px;
    color: %(TEXT_PRIMARY)s;
    gridline-color: #153441;
    selection-background-color: %(SELECTION_BG)s;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding-left: 6px;
    padding-right: 6px;
}

QHeaderView::section {
    background: #0d2530;
    border: 0;
    border-right: 1px solid %(PANEL_BORDER)s;
    color: %(ACCENT)s;
    font-weight: 700;
    padding: 7px;
}

QFrame#playerCard, QFrame#sectionCard, QFrame#orgCard, QFrame#affiliationCard {
    background: %(PANEL_BG)s;
    border: 1px solid %(PANEL_BORDER)s;
    border-radius: 6px;
}

QFrame#playerCard {
    border-color: %(PANEL_BORDER_ACTIVE)s;
}

QWidget#transparentPanel, QWidget#statusInfoPanel,
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
    color: %(ACCENT)s;
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#heroHandle {
    color: %(TEXT_HEADING)s;
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
    color: %(TEXT_MUTED)s;
    padding: 18px;
}

QLabel#moduleHeading {
    color: %(TEXT_HEADING)s;
    font-size: 18pt;
    font-weight: 700;
}

QLabel#moduleSubtitle {
    color: %(TEXT_SECONDARY)s;
    font-size: 10pt;
}
""" % {
    "BACKGROUND": BACKGROUND,
    "PANEL_BG": PANEL_BG,
    "PANEL_BORDER": PANEL_BORDER,
    "PANEL_BORDER_ACTIVE": PANEL_BORDER_ACTIVE,
    "TEXT_PRIMARY": TEXT_PRIMARY,
    "TEXT_HEADING": TEXT_HEADING,
    "TEXT_SECONDARY": TEXT_SECONDARY,
    "TEXT_MUTED": TEXT_MUTED,
    "ACCENT": ACCENT,
    "ACCENT_BRIGHT": ACCENT_BRIGHT,
    "BUTTON_BG": BUTTON_BG,
    "BUTTON_BG_HOVER": BUTTON_BG_HOVER,
    "INPUT_BG": INPUT_BG,
    "INPUT_BORDER": INPUT_BORDER,
    "SELECTION_BG": SELECTION_BG,
}
