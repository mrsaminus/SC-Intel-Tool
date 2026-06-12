from app.database import get_app_setting, set_app_setting

from .theme_models import Theme


THEME_SETTING_KEY = "appearance.theme"
DEFAULT_THEME_KEY = "sc_intel_dark"


BASE_COLORS = {
    "background": "#071118",
    "surface": "#0b1820",
    "surface_alt": "#0d2530",
    "surface_hover": "#102735",
    "panel_border": "#1e5060",
    "panel_border_active": "#28788d",
    "text_primary": "#effcff",
    "text_base": "#d8f7ff",
    "text_heading": "#f5fdff",
    "text_secondary": "#7bb9c8",
    "text_muted": "#6a8894",
    "accent": "#33dfff",
    "accent_bright": "#44e6ff",
    "accent_soft": "#0d5362",
    "button_bg": "#132733",
    "button_hover": "#173849",
    "button_disabled": "#111820",
    "input_bg": "#0b1820",
    "input_border": "#264858",
    "selection_bg": "#123a49",
    "selection_text": "#ffffff",
    "danger": "#e48168",
    "warning": "#ffb56a",
    "success": "#70dfaa",
    "table_grid": "#153441",
    "avatar_bg": "#061017",
    "avatar_border": "#2b7386",
    "avatar_text": "#466978",
    "shadow": "#02070b",
}

BASE_METRICS = {
    "font_size": "10pt",
    "tab_padding": "7px 12px",
    "button_padding": "7px 12px",
    "input_padding": "6px",
    "table_header_padding": "7px",
    "table_item_padding": "6px",
    "checkbox_padding": "3px 4px",
    "checkbox_spacing": "7px",
    "checkbox_size": "14px",
    "radius": "5px",
    "card_radius": "6px",
    "card_padding": "16px",
    "home_card_min_height": "102px",
}


def _theme(key, name, category, description, colors=None, metrics=None, notes=""):
    merged_colors = dict(BASE_COLORS)
    if colors:
        merged_colors.update(colors)
    merged_metrics = dict(BASE_METRICS)
    if metrics:
        merged_metrics.update(metrics)
    return Theme(
        key=key,
        name=name,
        category=category,
        description=description,
        colors=merged_colors,
        metrics=merged_metrics,
        notes=notes,
    )


SC_INTEL_DARK = _theme(
    "sc_intel_dark",
    "SC Intel Dark",
    "Core",
    "The default dark cyan operational interface.",
)

THEMES = [
    SC_INTEL_DARK,
    SC_INTEL_DARK.with_updates(
        key="compact_dark",
        name="Compact Dark",
        description="Default look with tighter controls for dense screens.",
        metrics={
            "font_size": "9pt",
            "tab_padding": "5px 9px",
            "button_padding": "5px 9px",
            "input_padding": "4px",
            "table_header_padding": "5px",
            "table_item_padding": "4px",
            "checkbox_padding": "2px 3px",
            "checkbox_spacing": "5px",
            "home_card_min_height": "86px",
        },
    ),
    SC_INTEL_DARK.with_updates(
        key="high_contrast_dark",
        name="High Contrast Dark",
        description="Darker panels, stronger text and clearer focus states.",
        colors={
            "background": "#03080d",
            "surface": "#09141b",
            "surface_alt": "#102f3d",
            "surface_hover": "#143b4c",
            "panel_border": "#35b9d6",
            "panel_border_active": "#72efff",
            "text_primary": "#ffffff",
            "text_base": "#f0fcff",
            "text_secondary": "#b5eff8",
            "text_muted": "#8cb9c4",
            "accent": "#5df1ff",
            "accent_bright": "#b8fbff",
            "selection_bg": "#15566b",
            "table_grid": "#24596b",
        },
    ),
    SC_INTEL_DARK.with_updates(
        key="white_mode",
        name="White Mode",
        description="Soft light mode for brave daylight operators.",
        colors={
            "background": "#eef3f5",
            "surface": "#f8fbfc",
            "surface_alt": "#dde9ee",
            "surface_hover": "#edf7fa",
            "panel_border": "#9fb7c0",
            "panel_border_active": "#4b91a5",
            "text_primary": "#14242b",
            "text_base": "#1a3038",
            "text_heading": "#0b171d",
            "text_secondary": "#48626c",
            "text_muted": "#708791",
            "accent": "#007f9c",
            "accent_bright": "#005f82",
            "accent_soft": "#c9edf4",
            "button_bg": "#e2edf1",
            "button_hover": "#d4e7ee",
            "button_disabled": "#e8edef",
            "input_bg": "#ffffff",
            "input_border": "#9fb7c0",
            "selection_bg": "#b8dfea",
            "selection_text": "#071118",
            "table_grid": "#c4d5db",
            "avatar_bg": "#e6eef1",
            "avatar_border": "#98b2bc",
            "avatar_text": "#657d86",
        },
    ),
    SC_INTEL_DARK.with_updates(
        key="grey_mode",
        name="Grey Mode",
        description="Muted industrial grayscale UI with restrained contrast.",
        colors={
            "background": "#101214",
            "surface": "#181b1e",
            "surface_alt": "#22272b",
            "surface_hover": "#252c31",
            "panel_border": "#515a60",
            "panel_border_active": "#8d969c",
            "text_primary": "#eceff0",
            "text_base": "#d7dcde",
            "text_heading": "#ffffff",
            "text_secondary": "#a9b0b4",
            "text_muted": "#858d91",
            "accent": "#c8d0d4",
            "accent_bright": "#f0f4f5",
            "accent_soft": "#3d454a",
            "button_bg": "#252a2e",
            "button_hover": "#30373c",
            "input_bg": "#15191c",
            "input_border": "#5a646a",
            "selection_bg": "#3f4a51",
            "table_grid": "#333a3f",
            "avatar_bg": "#111416",
            "avatar_border": "#5c666c",
            "avatar_text": "#8d969c",
        },
    ),
    SC_INTEL_DARK.with_updates(
        key="windows_95",
        name="Windows 95",
        category="Retro",
        description="Classic beveled grey desktop nostalgia.",
        colors={
            "background": "#008080",
            "surface": "#c0c0c0",
            "surface_alt": "#d4d0c8",
            "surface_hover": "#dcd8d0",
            "panel_border": "#404040",
            "panel_border_active": "#000080",
            "text_primary": "#000000",
            "text_base": "#000000",
            "text_heading": "#000000",
            "text_secondary": "#202020",
            "text_muted": "#404040",
            "accent": "#000080",
            "accent_bright": "#0000cc",
            "accent_soft": "#e6e6e6",
            "button_bg": "#c0c0c0",
            "button_hover": "#d4d0c8",
            "button_disabled": "#d0d0d0",
            "input_bg": "#ffffff",
            "input_border": "#404040",
            "selection_bg": "#000080",
            "selection_text": "#ffffff",
            "table_grid": "#808080",
            "avatar_bg": "#d4d0c8",
            "avatar_border": "#404040",
            "avatar_text": "#404040",
        },
        metrics={"radius": "0px", "card_radius": "0px", "button_padding": "5px 10px", "input_padding": "4px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="windows_xp",
        name="Windows XP",
        category="Retro",
        description="Soft Luna-inspired blue without the clutter.",
        colors={
            "background": "#1d3557",
            "surface": "#e9f1ff",
            "surface_alt": "#d5e6ff",
            "surface_hover": "#f4f8ff",
            "panel_border": "#6c8fc8",
            "panel_border_active": "#2b5db4",
            "text_primary": "#13233f",
            "text_base": "#13233f",
            "text_heading": "#07162e",
            "text_secondary": "#344b78",
            "text_muted": "#65769b",
            "accent": "#1f58bd",
            "accent_bright": "#0d3f9b",
            "accent_soft": "#c2d8ff",
            "button_bg": "#dfeaff",
            "button_hover": "#c9dcff",
            "input_bg": "#ffffff",
            "input_border": "#6c8fc8",
            "selection_bg": "#316ac5",
            "selection_text": "#ffffff",
            "table_grid": "#b4c8e8",
        },
    ),
    SC_INTEL_DARK.with_updates(
        key="rsi_theme",
        name="RSI",
        category="Manufacturer",
        description="Clean military tech: cool blue, steel and discipline.",
        colors={
            "background": "#050c14",
            "surface": "#0d1a26",
            "surface_alt": "#12324d",
            "surface_hover": "#183d5c",
            "panel_border": "#3d6f91",
            "panel_border_active": "#62b9f2",
            "text_primary": "#f4fbff",
            "text_base": "#d8ecf7",
            "text_heading": "#ffffff",
            "text_secondary": "#a9cada",
            "text_muted": "#7897a8",
            "accent": "#43aeea",
            "accent_bright": "#8ed7ff",
            "accent_soft": "#143a57",
            "button_bg": "#10263a",
            "button_hover": "#173957",
            "button_disabled": "#0d1721",
            "input_bg": "#091522",
            "input_border": "#416f8d",
            "selection_bg": "#174b70",
            "table_grid": "#1f4058",
            "avatar_bg": "#07111d",
            "avatar_border": "#4f8bb0",
            "avatar_text": "#6f9fb8",
        },
        metrics={"radius": "3px", "card_radius": "4px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="drake_theme",
        name="Drake",
        category="Manufacturer",
        description="Rugged industrial metal with restrained rust accents.",
        colors={
            "background": "#0d0b08",
            "surface": "#18140f",
            "surface_alt": "#2b2016",
            "surface_hover": "#372719",
            "panel_border": "#704821",
            "panel_border_active": "#d07428",
            "text_primary": "#fff2e4",
            "text_base": "#ead2bb",
            "text_heading": "#fff8ee",
            "text_secondary": "#d3aa82",
            "text_muted": "#9a7b60",
            "accent": "#ff8833",
            "accent_bright": "#ffb165",
            "accent_soft": "#4b2816",
            "button_bg": "#261b13",
            "button_hover": "#3a2618",
            "button_disabled": "#18120d",
            "input_bg": "#120f0b",
            "input_border": "#80512a",
            "selection_bg": "#643317",
            "warning": "#ffb165",
            "danger": "#ff775f",
            "success": "#d0c07a",
            "table_grid": "#3d2b1d",
            "avatar_bg": "#0c0907",
            "avatar_border": "#a65d25",
            "avatar_text": "#a47b5b",
        },
        metrics={"radius": "3px", "card_radius": "4px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="origin_theme",
        name="Origin",
        category="Manufacturer",
        description="Executive luxury: clean surfaces, soft gold and high contrast.",
        colors={
            "background": "#08090c",
            "surface": "#11141a",
            "surface_alt": "#1d1b17",
            "surface_hover": "#28241b",
            "panel_border": "#7f6b3e",
            "panel_border_active": "#d1b369",
            "text_primary": "#fff8e8",
            "text_base": "#eee2c9",
            "text_heading": "#fffdf5",
            "text_secondary": "#c7b58b",
            "text_muted": "#8d826e",
            "accent": "#cda85a",
            "accent_bright": "#f0d891",
            "accent_soft": "#342b18",
            "button_bg": "#1c1a16",
            "button_hover": "#2b2518",
            "button_disabled": "#131313",
            "input_bg": "#0d1015",
            "input_border": "#8c7442",
            "selection_bg": "#6e5724",
            "selection_text": "#fff8e8",
            "warning": "#f0d891",
            "success": "#9fd6b6",
            "table_grid": "#332d20",
            "avatar_bg": "#090b0f",
            "avatar_border": "#b8944f",
            "avatar_text": "#9f8d69",
        },
        metrics={"radius": "6px", "card_radius": "8px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="pride_theme",
        name="Pride",
        category="Community",
        description="Dark professional base with respectful rainbow accent touches.",
        colors={
            "background": "#070a13",
            "surface": "#101424",
            "surface_alt": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #402149, stop:0.20 #26306c, stop:0.40 #12445f, stop:0.60 #14513f, stop:0.80 #5a4316, stop:1 #5a1f24)",
            "surface_hover": "#202b52",
            "panel_border": "#5265d9",
            "panel_border_active": "#ff82d7",
            "accent": "#ff82d7",
            "accent_bright": "#80f4ff",
            "accent_soft": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a2458, stop:0.25 #2c3274, stop:0.50 #15506b, stop:0.75 #315d2b, stop:1 #6b2b2f)",
            "text_primary": "#f9f7ff",
            "text_base": "#e5e4ff",
            "text_heading": "#ffffff",
            "text_secondary": "#c9c2ff",
            "text_muted": "#9d98c3",
            "button_bg": "#182142",
            "button_hover": "#283570",
            "input_bg": "#0d1224",
            "input_border": "#7482f0",
            "selection_bg": "#593884",
            "table_header_bg": "#151b34",
            "table_grid": "#26355f",
            "warning": "#ffd166",
            "success": "#76f7a9",
            "danger": "#ff6b6b",
            "avatar_bg": "#0b0f1d",
            "avatar_border": "#ff82d7",
            "avatar_text": "#8edcff",
        },
    ),
]

THEMES_BY_KEY = {theme.key: theme for theme in THEMES}


def available_themes():
    return THEMES


def get_theme(key):
    return THEMES_BY_KEY.get(key) or THEMES_BY_KEY[DEFAULT_THEME_KEY]


def get_current_theme_key():
    key = get_app_setting(THEME_SETTING_KEY, DEFAULT_THEME_KEY)
    if key not in THEMES_BY_KEY:
        return DEFAULT_THEME_KEY
    return key


def get_current_theme():
    return get_theme(get_current_theme_key())


def set_current_theme(key):
    theme = get_theme(key)
    set_app_setting(THEME_SETTING_KEY, theme.key)
    return theme


def stylesheet_for_theme(theme):
    colors = theme.colors
    metrics = theme.metrics
    tokens = {}
    tokens.update({key.upper(): value for key, value in colors.items()})
    tokens.update({key.upper(): value for key, value in metrics.items()})
    tokens["TABLE_HEADER_BG"] = colors.get("table_header_bg", colors["surface_alt"])
    return _STYLE_TEMPLATE % tokens


_STYLE_TEMPLATE = """
QMainWindow, QWidget {
    background: %(BACKGROUND)s;
    color: %(TEXT_BASE)s;
    font-family: Segoe UI;
    font-size: %(FONT_SIZE)s;
}

QTabWidget::pane {
    border: 1px solid %(PANEL_BORDER)s;
    background: %(BACKGROUND)s;
}

QTabBar::tab {
    background: %(BUTTON_BG)s;
    color: %(TEXT_BASE)s;
    border: 1px solid %(PANEL_BORDER)s;
    border-bottom: 0;
    padding: %(TAB_PADDING)s;
}

QTabBar::tab:hover {
    background: %(BUTTON_HOVER)s;
    color: %(ACCENT_BRIGHT)s;
}

QTabBar::tab:selected {
    background: %(SURFACE_ALT)s;
    color: %(ACCENT_BRIGHT)s;
    border-color: %(PANEL_BORDER_ACTIVE)s;
}

QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: %(INPUT_BG)s;
    border: 1px solid %(INPUT_BORDER)s;
    border-radius: %(RADIUS)s;
    color: %(TEXT_PRIMARY)s;
    selection-background-color: %(SELECTION_BG)s;
    selection-color: %(SELECTION_TEXT)s;
    padding: %(INPUT_PADDING)s;
}

QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: %(PANEL_BORDER_ACTIVE)s;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid %(ACCENT_BRIGHT)s;
}

QComboBox QAbstractItemView {
    background: %(SURFACE)s;
    color: %(TEXT_PRIMARY)s;
    border: 1px solid %(PANEL_BORDER_ACTIVE)s;
    selection-background-color: %(SELECTION_BG)s;
    selection-color: %(SELECTION_TEXT)s;
    padding: 3px;
}

QPushButton {
    background: %(BUTTON_BG)s;
    border: 1px solid %(PANEL_BORDER)s;
    border-radius: %(RADIUS)s;
    color: %(TEXT_PRIMARY)s;
    padding: %(BUTTON_PADDING)s;
}

QPushButton:hover {
    background: %(BUTTON_HOVER)s;
    border-color: %(ACCENT_BRIGHT)s;
}

QPushButton:pressed {
    background: %(ACCENT_SOFT)s;
    border-color: %(ACCENT)s;
}

QPushButton:focus {
    border-color: %(ACCENT_BRIGHT)s;
}

QPushButton:disabled {
    background: %(BUTTON_DISABLED)s;
    border-color: %(PANEL_BORDER)s;
    color: %(TEXT_MUTED)s;
}

QCheckBox {
    background: transparent;
    border: none;
    color: %(TEXT_PRIMARY)s;
    spacing: %(CHECKBOX_SPACING)s;
    padding: %(CHECKBOX_PADDING)s;
}

QCheckBox:hover {
    color: %(ACCENT_BRIGHT)s;
}

QCheckBox:disabled {
    color: %(TEXT_MUTED)s;
}

QCheckBox::indicator {
    width: %(CHECKBOX_SIZE)s;
    height: %(CHECKBOX_SIZE)s;
    border: 1px solid %(PANEL_BORDER_ACTIVE)s;
    border-radius: 3px;
    background: %(INPUT_BG)s;
}

QCheckBox::indicator:hover {
    border-color: %(ACCENT_BRIGHT)s;
    background: %(SURFACE_HOVER)s;
}

QCheckBox::indicator:checked {
    background: %(ACCENT_SOFT)s;
    border-color: %(ACCENT_BRIGHT)s;
}

QCheckBox::indicator:checked:disabled {
    background: %(BUTTON_DISABLED)s;
    border-color: %(TEXT_MUTED)s;
}

QScrollArea {
    border: 0;
    background: transparent;
}

QScrollBar:vertical, QScrollBar:horizontal {
    background: %(BACKGROUND)s;
    border: 1px solid %(PANEL_BORDER)s;
    margin: 0;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: %(BUTTON_BG)s;
    border: 1px solid %(PANEL_BORDER_ACTIVE)s;
    border-radius: 3px;
    min-height: 24px;
    min-width: 24px;
}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background: %(BUTTON_HOVER)s;
}

QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
}

QTableWidget, QTableView {
    background: %(BACKGROUND)s;
    border: 1px solid %(PANEL_BORDER)s;
    border-radius: %(RADIUS)s;
    color: %(TEXT_PRIMARY)s;
    gridline-color: %(TABLE_GRID)s;
    selection-background-color: %(SELECTION_BG)s;
    selection-color: %(SELECTION_TEXT)s;
    alternate-background-color: %(SURFACE)s;
}

QTableWidget::item, QTableView::item {
    padding-left: %(TABLE_ITEM_PADDING)s;
    padding-right: %(TABLE_ITEM_PADDING)s;
}

QTableWidget::item:hover, QTableView::item:hover {
    background: %(SURFACE_HOVER)s;
}

QHeaderView::section {
    background: %(TABLE_HEADER_BG)s;
    border: 0;
    border-right: 1px solid %(PANEL_BORDER)s;
    color: %(ACCENT)s;
    font-weight: 700;
    padding: %(TABLE_HEADER_PADDING)s;
}

QFrame#playerCard, QFrame#sectionCard, QFrame#orgCard, QFrame#affiliationCard {
    background: %(SURFACE)s;
    border: 1px solid %(PANEL_BORDER)s;
    border-radius: %(CARD_RADIUS)s;
}

QFrame#playerCard {
    border-color: %(PANEL_BORDER_ACTIVE)s;
}

QFrame#homeNavCard {
    background: %(SURFACE)s;
    border: 1px solid %(PANEL_BORDER)s;
    border-radius: %(CARD_RADIUS)s;
}

QFrame#homeNavCard:hover {
    background: %(SURFACE_HOVER)s;
    border-color: %(ACCENT_BRIGHT)s;
}

QFrame#updateStatusChip {
    border-radius: 9px;
}

QWidget#transparentPanel, QWidget#statusInfoPanel,
QLabel {
    background: transparent;
}

QLabel#avatarBox {
    background: %(AVATAR_BG)s;
    border: 1px solid %(AVATAR_BORDER)s;
    border-radius: %(RADIUS)s;
    color: %(AVATAR_TEXT)s;
}

QLabel#sectionTitle {
    color: %(ACCENT)s;
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#homeCardTitle {
    color: %(TEXT_HEADING)s;
    font-size: 13pt;
    font-weight: 700;
}

QLabel#appTitle {
    color: %(TEXT_HEADING)s;
    font-size: 13pt;
    font-weight: 700;
}

QLabel#statusChip {
    background: %(SURFACE_ALT)s;
    border: 1px solid %(PANEL_BORDER_ACTIVE)s;
    border-radius: 10px;
    color: %(ACCENT_BRIGHT)s;
    font-size: 8pt;
    font-weight: 700;
    padding: 3px 8px;
}

QLabel#heroHandle {
    color: %(TEXT_HEADING)s;
    font-size: 22pt;
    font-weight: 700;
}

QLabel#heroSubtitle {
    color: %(ACCENT_BRIGHT)s;
    font-size: 11pt;
}

QLabel#labelText {
    color: %(TEXT_MUTED)s;
    font-size: 8pt;
    text-transform: uppercase;
}

QLabel#valueText {
    color: %(TEXT_PRIMARY)s;
    font-size: 10pt;
}

QLabel#orgName {
    color: %(ACCENT_BRIGHT)s;
    font-size: 15pt;
    font-weight: 700;
}

QLabel#orgSid {
    color: %(ACCENT_BRIGHT)s;
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
"""
