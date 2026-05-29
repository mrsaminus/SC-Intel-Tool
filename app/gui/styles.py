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
