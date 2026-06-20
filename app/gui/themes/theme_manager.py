from app.database import get_app_setting, set_app_setting

from .theme_models import Theme


THEME_SETTING_KEY = "appearance.theme"
DEFAULT_THEME_KEY = "sc_intel_dark"
TEXT_SIZE_SETTING_KEY = "appearance.text_size"
DEFAULT_TEXT_SIZE_KEY = "normal"
RELEASE_THEME_KEYS = (
    "sc_intel_dark",
    "white_mode",
    "windows_xp",
    "windows_95",
)
TEXT_SIZE_OPTIONS = {
    "normal": {"label": "Normal", "scale": 1.0},
    "large": {"label": "Large", "scale": 1.1},
    "extra_large": {"label": "Extra Large", "scale": 1.25},
}


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
    "tab_padding": "8px 14px",
    "tab_min_height": "18px",
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
            "tab_min_height": "16px",
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
        name="Windows 95 Classic",
        category="Retro",
        description="Classic Win9x grey controls, navy active chrome and hard bevels.",
        colors={
            "background": "#008080",
            "surface": "#C0C0C0",
            "surface_alt": "#000080",
            "surface_hover": "#DFDFDF",
            "panel_border": "#404040",
            "panel_border_active": "#000080",
            "text_primary": "#000000",
            "text_base": "#000000",
            "text_heading": "#000000",
            "text_secondary": "#202020",
            "text_muted": "#404040",
            "accent": "#000080",
            "accent_bright": "#FFFFFF",
            "accent_soft": "#DFDFDF",
            "button_bg": "#C0C0C0",
            "button_hover": "#DFDFDF",
            "button_disabled": "#C0C0C0",
            "button_border": "#808080",
            "button_border_top": "#FFFFFF",
            "button_border_left": "#FFFFFF",
            "button_border_right": "#404040",
            "button_border_bottom": "#404040",
            "button_border_hover": "#000080",
            "checkbox_checked_bg": "#000080",
            "home_card_border": "#404040",
            "home_card_hover_border": "#000080",
            "status_chip_bg": "#000080",
            "input_bg": "#ffffff",
            "input_border": "#404040",
            "selection_bg": "#000080",
            "selection_text": "#ffffff",
            "table_header_bg": "#C0C0C0",
            "table_grid": "#808080",
            "avatar_bg": "#DFDFDF",
            "avatar_border": "#404040",
            "avatar_text": "#404040",
        },
        metrics={"radius": "0px", "card_radius": "0px", "button_padding": "5px 10px", "input_padding": "4px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="windows_xp",
        name="Windows XP Luna",
        category="Retro",
        description="Luna-inspired blue chrome with soft panels and rounded plastic controls.",
        colors={
            "background": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7FB2FF, stop:0.11 #3C7FF0, stop:0.52 #245EDB, stop:1 #1B4FAE)",
            "surface": "#DCE8F6",
            "surface_alt": "#EEF4FD",
            "surface_hover": "#FFFFFF",
            "top_bar_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B8D6FF, stop:0.08 #7FB2FF, stop:0.34 #3A7BEB, stop:0.74 #245EDB, stop:1 #1B4FAE)",
            "top_bar_border": "#2C5FD5",
            "pane_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7FB2FF, stop:0.10 #3A7BEB, stop:0.62 #245EDB, stop:1 #1B4FAE)",
            "card_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:0.05 #FFFFFF, stop:0.16 #F8FBFF, stop:0.48 #EEF4FD, stop:0.78 #DCE8F6, stop:1 #C4DAF4)",
            "card_hover_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:0.20 #FFFFFF, stop:0.58 #F1F7FF, stop:1 #D7E8FA)",
            "panel_border": "#7EA9F2",
            "panel_border_active": "#1D4FBA",
            "card_border_top": "#FFFFFF",
            "card_border_left": "#FFFFFF",
            "card_border_right": "#7EA9F2",
            "card_border_bottom": "#4E89F5",
            "text_primary": "#102044",
            "text_base": "#102044",
            "text_heading": "#0b1d4a",
            "text_secondary": "#31507e",
            "text_muted": "#667da4",
            "accent": "#245EDB",
            "accent_bright": "#1D4FBA",
            "accent_soft": "#AFCBFF",
            "button_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:0.16 #FFFFFF, stop:0.50 #E8F1FF, stop:1 #BDD7FF)",
            "button_hover": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:0.24 #FFFFFF, stop:0.54 #F0F7FF, stop:1 #CCE2FF)",
            "button_pressed": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7BAAF7, stop:0.18 #5A8AEF, stop:0.56 #2F69DD, stop:1 #1B4FAE)",
            "button_disabled": "#D6E6FA",
            "button_border": "#5A8AEF",
            "button_border_top": "#FFFFFF",
            "button_border_left": "#FFFFFF",
            "button_border_right": "#5A8AEF",
            "button_border_bottom": "#2C5FD5",
            "button_border_hover": "#245EDB",
            "checkbox_checked_bg": "#45a049",
            "home_card_border": "#7EA9F2",
            "home_card_hover_border": "#4E89F5",
            "status_chip_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #CFE2FF)",
            "input_bg": "#ffffff",
            "input_border": "#7EA9F2",
            "input_border_top": "#6A87B8",
            "input_border_left": "#6A87B8",
            "input_border_right": "#FFFFFF",
            "input_border_bottom": "#FFFFFF",
            "selection_bg": "#316ac5",
            "selection_text": "#ffffff",
            "tab_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F0F6FF, stop:0.17 #E8F2FF, stop:0.58 #BCD6FF, stop:1 #7DAAF7)",
            "tab_border": "#4E89F5",
            "tab_border_top": "#FFFFFF",
            "tab_border_left": "#FFFFFF",
            "tab_border_right": "#2C5FD5",
            "tab_border_bottom": "#1B4FAE",
            "tab_hover_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:0.20 #FFFFFF, stop:0.56 #D8E9FF, stop:1 #8EBBFF)",
            "tab_hover_text": "#1D4FBA",
            "tab_selected_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F7FBFF, stop:0.15 #FFFFFF, stop:0.52 #D8E9FF, stop:1 #A9CBFF)",
            "tab_selected_border": "#4E89F5",
            "tab_selected_border_top": "#FFFFFF",
            "tab_selected_border_left": "#FFFFFF",
            "tab_selected_border_right": "#4E89F5",
            "tab_selected_border_bottom": "#7FB2FF",
            "tab_selected_text": "#0b1d4a",
            "home_tab_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B6FF9A, stop:0.16 #6FD643, stop:0.54 #43B72A, stop:1 #2B8F1B)",
            "home_tab_hover_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #D2FFBF, stop:0.20 #82E65A, stop:0.58 #4EC83A, stop:1 #2F9A20)",
            "home_tab_border": "#1F7D18",
            "home_tab_border_top": "#B6FF9A",
            "home_tab_border_left": "#B6FF9A",
            "home_tab_border_right": "#1F7D18",
            "home_tab_border_bottom": "#1F7D18",
            "home_tab_text": "#FFFFFF",
            "home_tab_font_weight": "700",
            "danger": "#e35b2f",
            "success": "#45a049",
            "table_bg": "#FFFFFF",
            "table_header_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:0.36 #ECF3FB, stop:1 #CFE2FF)",
            "table_grid": "#b4c8e8",
        },
        metrics={
            "font_family": "Tahoma",
            "radius": "9px",
            "card_radius": "10px",
            "tab_radius": "9px",
            "tab_padding": "8px 15px",
            "tab_min_height": "20px",
            "top_bar_padding": "4px 5px 0 5px",
            "tab_margin_right": "2px",
            "tab_margin_top": "4px",
            "tab_selected_margin_top": "0px",
            "tab_selected_margin_bottom": "-2px",
            "button_padding": "7px 14px",
        },
    ),
    SC_INTEL_DARK.with_updates(
        key="rsi_theme",
        name="RSI",
        category="Manufacturer",
        description="Official ship terminal feel with steel-blue panels and cyan HUD accents.",
        colors={
            "background": "#111F29",
            "surface": "#142735",
            "surface_alt": "#1C4D6E",
            "surface_hover": "#215d83",
            "panel_border": "#456f82",
            "panel_border_active": "#35B6EC",
            "text_primary": "#EBEBEB",
            "text_base": "#d8e8ef",
            "text_heading": "#f7fbff",
            "text_secondary": "#9BC3D1",
            "text_muted": "#7895a1",
            "accent": "#35B6EC",
            "accent_bright": "#9BC3D1",
            "accent_soft": "#173a50",
            "button_bg": "#132b3a",
            "button_hover": "#174461",
            "button_disabled": "#101820",
            "button_border": "#1C4D6E",
            "button_border_hover": "#35B6EC",
            "checkbox_checked_bg": "#1C4D6E",
            "home_card_border": "#2d5b74",
            "home_card_hover_border": "#35B6EC",
            "status_chip_bg": "#142f42",
            "input_bg": "#0d1a24",
            "input_border": "#3b708a",
            "selection_bg": "#1C4D6E",
            "selection_text": "#EBEBEB",
            "table_header_bg": "#162f40",
            "table_grid": "#274858",
            "avatar_bg": "#0d1821",
            "avatar_border": "#35B6EC",
            "avatar_text": "#9BC3D1",
        },
        metrics={"radius": "2px", "card_radius": "3px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="drake_theme",
        name="Drake",
        category="Manufacturer",
        description="Rugged cockpit software with industrial steel, olive panels and warning accents.",
        colors={
            "background": "#0E1012",
            "surface": "#171C1D",
            "surface_alt": "#1B2224",
            "surface_hover": "#2A2E31",
            "card_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1B2224, stop:0.08 #202728, stop:1 #121719)",
            "card_hover_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #252d2f, stop:0.12 #2A2E31, stop:1 #171C1D)",
            "panel_border": "#32373B",
            "panel_border_active": "#FF8A1C",
            "text_primary": "#f3e7d5",
            "text_base": "#d4c1a6",
            "text_heading": "#fff0d8",
            "text_secondary": "#c79555",
            "text_muted": "#8a7760",
            "accent": "#FF8A1C",
            "accent_bright": "#FFB347",
            "accent_soft": "#3a2210",
            "button_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2A2E31, stop:0.16 #202728, stop:0.82 #141819, stop:1 #0B0D0E)",
            "button_hover": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3a3d3c, stop:0.18 #2A2E31, stop:0.66 #2b241c, stop:1 #211409)",
            "button_disabled": "#181b1d",
            "button_border": "#4A433A",
            "button_border_hover": "#FF8A1C",
            "checkbox_checked_bg": "#D87816",
            "home_card_border": "#4A433A",
            "home_card_hover_border": "#FF8A1C",
            "status_chip_bg": "#24170d",
            "input_bg": "#111516",
            "input_border": "#4A433A",
            "selection_bg": "#5a3413",
            "selection_text": "#fff1dd",
            "tab_hover_bg": "#2A2E31",
            "tab_hover_text": "#FF8A1C",
            "tab_selected_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2A2E31, stop:0.55 #1B2224, stop:1 #24170d)",
            "tab_selected_border": "#FF8A1C",
            "tab_selected_text": "#FFB347",
            "warning": "#FFB347",
            "danger": "#AC0000",
            "success": "#7EA048",
            "table_header_bg": "#1B2224",
            "table_grid": "#2f3437",
            "avatar_bg": "#0B0D0E",
            "avatar_border": "#FF8A1C",
            "avatar_text": "#D87816",
        },
        metrics={"radius": "2px", "card_radius": "3px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="origin_theme",
        name="Origin",
        category="Manufacturer",
        description="Luxury bridge terminal with dark contrast, premium gold and restrained cyan.",
        colors={
            "background": "#151C25",
            "surface": "#1c2531",
            "surface_alt": "#262a2f",
            "surface_hover": "#31313a",
            "panel_border": "#A18262",
            "panel_border_active": "#D4AF37",
            "text_primary": "#F9F9FB",
            "text_base": "#eee8dc",
            "text_heading": "#ffffff",
            "text_secondary": "#d8c49a",
            "text_muted": "#a89882",
            "accent": "#D4AF37",
            "accent_bright": "#00D2FF",
            "accent_soft": "#3c3321",
            "button_bg": "#202934",
            "button_hover": "#2b3340",
            "button_disabled": "#181d24",
            "button_border": "#A18262",
            "button_border_hover": "#D4AF37",
            "checkbox_checked_bg": "#3c3321",
            "home_card_border": "#7f6f57",
            "home_card_hover_border": "#D4AF37",
            "status_chip_bg": "#252a2f",
            "input_bg": "#121922",
            "input_border": "#A18262",
            "selection_bg": "#4e3f21",
            "selection_text": "#F9F9FB",
            "warning": "#D4AF37",
            "success": "#00D2FF",
            "table_header_bg": "#222832",
            "table_grid": "#373538",
            "avatar_bg": "#111821",
            "avatar_border": "#D4AF37",
            "avatar_text": "#A18262",
        },
        metrics={"radius": "7px", "card_radius": "9px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="aegis_theme",
        name="Aegis",
        category="Manufacturer",
        description="Heavy military weapons terminal with matte armor grey and tactical amber.",
        colors={
            "background": "#14181b",
            "surface": "#1D2226",
            "surface_alt": "#2b3237",
            "surface_hover": "#333d43",
            "panel_border": "#3A444A",
            "panel_border_active": "#E1A11A",
            "text_primary": "#f2f0e6",
            "text_base": "#d8d2c0",
            "text_heading": "#fff6df",
            "text_secondary": "#c7b98d",
            "text_muted": "#8d897c",
            "accent": "#E1A11A",
            "accent_bright": "#ffd166",
            "accent_soft": "#3c2f12",
            "button_bg": "#242b30",
            "button_hover": "#323a40",
            "button_disabled": "#181d20",
            "button_border": "#3A444A",
            "button_border_hover": "#E1A11A",
            "checkbox_checked_bg": "#3c2f12",
            "home_card_border": "#3A444A",
            "home_card_hover_border": "#E1A11A",
            "status_chip_bg": "#242318",
            "input_bg": "#151a1e",
            "input_border": "#465158",
            "selection_bg": "#4c3710",
            "selection_text": "#fff7e2",
            "warning": "#E1A11A",
            "success": "#b9d08f",
            "table_header_bg": "#262d32",
            "table_grid": "#353f45",
            "avatar_bg": "#111518",
            "avatar_border": "#E1A11A",
            "avatar_text": "#a8a18f",
        },
        metrics={"radius": "2px", "card_radius": "3px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="anvil_theme",
        name="Anvil",
        category="Manufacturer",
        description="Modern UEE tactical field computer with armored green and scanner cyan.",
        colors={
            "background": "#111815",
            "surface": "#1b2520",
            "surface_alt": "#3E4B43",
            "surface_hover": "#47574d",
            "panel_border": "#4d655b",
            "panel_border_active": "#00FFCC",
            "text_primary": "#ecfff9",
            "text_base": "#d3eee5",
            "text_heading": "#f6fffc",
            "text_secondary": "#9ccabb",
            "text_muted": "#829b92",
            "accent": "#00FFCC",
            "accent_bright": "#9effec",
            "accent_soft": "#143a34",
            "button_bg": "#243129",
            "button_hover": "#304237",
            "button_disabled": "#18211d",
            "button_border": "#4d655b",
            "button_border_hover": "#D16A1E",
            "checkbox_checked_bg": "#174d42",
            "home_card_border": "#4d655b",
            "home_card_hover_border": "#00FFCC",
            "status_chip_bg": "#20332e",
            "input_bg": "#121c18",
            "input_border": "#4d655b",
            "selection_bg": "#15584d",
            "selection_text": "#f6fffc",
            "warning": "#D16A1E",
            "success": "#00FFCC",
            "table_header_bg": "#25342d",
            "table_grid": "#32473f",
            "avatar_bg": "#101714",
            "avatar_border": "#00FFCC",
            "avatar_text": "#7bdac7",
        },
        metrics={"radius": "3px", "card_radius": "4px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="crusader_theme",
        name="Crusader",
        category="Manufacturer",
        description="Commercial aerospace interface with clean navy, sky white and atmospheric blue.",
        colors={
            "background": "#1A2B4C",
            "surface": "#e6edf5",
            "surface_alt": "#c9d9e9",
            "surface_hover": "#f6fbff",
            "panel_border": "#61A5C2",
            "panel_border_active": "#1A2B4C",
            "text_primary": "#10223f",
            "text_base": "#132947",
            "text_heading": "#07162a",
            "text_secondary": "#315b78",
            "text_muted": "#68849a",
            "accent": "#1A2B4C",
            "accent_bright": "#61A5C2",
            "accent_soft": "#d8e8f3",
            "button_bg": "#EAF0F6",
            "button_hover": "#d9e8f3",
            "button_disabled": "#dfe6ec",
            "button_border": "#61A5C2",
            "button_border_hover": "#1A2B4C",
            "checkbox_checked_bg": "#61A5C2",
            "home_card_border": "#61A5C2",
            "home_card_hover_border": "#1A2B4C",
            "status_chip_bg": "#d7e8f2",
            "input_bg": "#ffffff",
            "input_border": "#61A5C2",
            "selection_bg": "#61A5C2",
            "selection_text": "#07162a",
            "table_header_bg": "#d7e5f1",
            "table_grid": "#abc3d4",
            "avatar_bg": "#dce8f1",
            "avatar_border": "#61A5C2",
            "avatar_text": "#446b84",
        },
        metrics={"radius": "6px", "card_radius": "8px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="misc_theme",
        name="MISC",
        category="Manufacturer",
        description="Industrial retro-future cargo and science UI with aluminum and orange accents.",
        colors={
            "background": "#171b1d",
            "surface": "#24292c",
            "surface_alt": "#3a4044",
            "surface_hover": "#444c50",
            "panel_border": "#7D8489",
            "panel_border_active": "#D9411E",
            "text_primary": "#EAEAEA",
            "text_base": "#d9dddd",
            "text_heading": "#ffffff",
            "text_secondary": "#b6bdbf",
            "text_muted": "#8d969a",
            "accent": "#D9411E",
            "accent_bright": "#ff7a4d",
            "accent_soft": "#3a2119",
            "button_bg": "#30363a",
            "button_hover": "#3e464a",
            "button_disabled": "#202528",
            "button_border": "#7D8489",
            "button_border_hover": "#D9411E",
            "checkbox_checked_bg": "#3a2119",
            "home_card_border": "#7D8489",
            "home_card_hover_border": "#D9411E",
            "status_chip_bg": "#30363a",
            "input_bg": "#1c2124",
            "input_border": "#7D8489",
            "selection_bg": "#6d2d1d",
            "selection_text": "#ffffff",
            "warning": "#D9411E",
            "success": "#EAEAEA",
            "table_header_bg": "#333a3e",
            "table_grid": "#444c50",
            "avatar_bg": "#171b1d",
            "avatar_border": "#D9411E",
            "avatar_text": "#a9b0b4",
        },
        metrics={"radius": "4px", "card_radius": "5px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="consolidated_outland_theme",
        name="Consolidated Outland",
        category="Manufacturer",
        description="Sharp experimental startup-space-tech with blue-grey, bronze and active red accents.",
        colors={
            "background": "#101821",
            "surface": "#202E3D",
            "surface_alt": "#27394b",
            "surface_hover": "#30475e",
            "panel_border": "#526b80",
            "panel_border_active": "#C5A059",
            "text_primary": "#f2f4f5",
            "text_base": "#dce4e8",
            "text_heading": "#ffffff",
            "text_secondary": "#b8c3c9",
            "text_muted": "#89969e",
            "accent": "#C5A059",
            "accent_bright": "#FF3B30",
            "accent_soft": "#3d3020",
            "button_bg": "#243448",
            "button_hover": "#304862",
            "button_disabled": "#182330",
            "button_border": "#526b80",
            "button_border_hover": "#C5A059",
            "checkbox_checked_bg": "#3d3020",
            "home_card_border": "#526b80",
            "home_card_hover_border": "#FF3B30",
            "status_chip_bg": "#27394b",
            "input_bg": "#15212e",
            "input_border": "#526b80",
            "selection_bg": "#5a4020",
            "selection_text": "#ffffff",
            "warning": "#C5A059",
            "danger": "#FF3B30",
            "success": "#8cc8d9",
            "table_header_bg": "#253447",
            "table_grid": "#34475b",
            "avatar_bg": "#101821",
            "avatar_border": "#C5A059",
            "avatar_text": "#a7bbc7",
        },
        metrics={"radius": "2px", "card_radius": "3px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="argo_theme",
        name="ARGO",
        category="Manufacturer",
        description="Industrial construction terminal with soot iron, orange and restrained hazard yellow.",
        colors={
            "background": "#101112",
            "surface": "#1b1d1f",
            "surface_alt": "#2B2D2F",
            "surface_hover": "#36393c",
            "panel_border": "#5a4a32",
            "panel_border_active": "#D97D00",
            "text_primary": "#f6eee0",
            "text_base": "#e1d5c1",
            "text_heading": "#fff8ea",
            "text_secondary": "#d8b36d",
            "text_muted": "#9c8d77",
            "accent": "#D97D00",
            "accent_bright": "#F4D03F",
            "accent_soft": "#3b2a10",
            "button_bg": "#26282a",
            "button_hover": "#35302a",
            "button_disabled": "#181a1b",
            "button_border": "#5a4a32",
            "button_border_hover": "#D97D00",
            "checkbox_checked_bg": "#4a310d",
            "home_card_border": "#5a4a32",
            "home_card_hover_border": "#F4D03F",
            "status_chip_bg": "#2a261d",
            "input_bg": "#141618",
            "input_border": "#5a4a32",
            "selection_bg": "#5a3706",
            "selection_text": "#fff8ea",
            "warning": "#F4D03F",
            "success": "#d2c77a",
            "table_header_bg": "#26282a",
            "table_grid": "#3a3730",
            "avatar_bg": "#101112",
            "avatar_border": "#D97D00",
            "avatar_text": "#d8b36d",
        },
        metrics={"radius": "3px", "card_radius": "4px"},
    ),
    SC_INTEL_DARK.with_updates(
        key="pride_theme",
        name="Rainbow",
        category="Community",
        description="Dark professional base with readable rainbow accents.",
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
            "button_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #18183d, stop:0.30 #172b50, stop:0.58 #163c46, stop:0.78 #332f35, stop:1 #421e35)",
            "button_hover": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #26205c, stop:0.26 #203b72, stop:0.52 #185b68, stop:0.76 #4b4420, stop:1 #63233b)",
            "button_border": "#ff82d7",
            "button_border_hover": "#80f4ff",
            "input_bg": "#0d1224",
            "input_border": "#7482f0",
            "selection_bg": "#593884",
            "checkbox_checked_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #a74ee8, stop:0.35 #2b70ff, stop:0.70 #13a66b, stop:1 #ff6b8b)",
            "home_card_border": "#6c70e8",
            "home_card_hover_border": "#ff82d7",
            "status_chip_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2b225c, stop:0.30 #183d70, stop:0.60 #14533f, stop:1 #5a2437)",
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
    return [THEMES_BY_KEY[key] for key in RELEASE_THEME_KEYS if key in THEMES_BY_KEY]


def available_text_sizes():
    return [(key, value["label"]) for key, value in TEXT_SIZE_OPTIONS.items()]


def get_theme(key):
    return THEMES_BY_KEY.get(key) or THEMES_BY_KEY[DEFAULT_THEME_KEY]


def get_current_theme_key():
    key = get_app_setting(THEME_SETTING_KEY, DEFAULT_THEME_KEY)
    if key not in THEMES_BY_KEY or key not in RELEASE_THEME_KEYS:
        return DEFAULT_THEME_KEY
    return key


def get_current_theme():
    return get_theme(get_current_theme_key())


def set_current_theme(key):
    if key not in RELEASE_THEME_KEYS:
        key = DEFAULT_THEME_KEY
    theme = get_theme(key)
    set_app_setting(THEME_SETTING_KEY, theme.key)
    return theme


def get_current_text_size_key():
    key = get_app_setting(TEXT_SIZE_SETTING_KEY, DEFAULT_TEXT_SIZE_KEY)
    if key not in TEXT_SIZE_OPTIONS:
        return DEFAULT_TEXT_SIZE_KEY
    return key


def get_current_text_size_label():
    return TEXT_SIZE_OPTIONS[get_current_text_size_key()]["label"]


def set_current_text_size(key):
    if key not in TEXT_SIZE_OPTIONS:
        key = DEFAULT_TEXT_SIZE_KEY
    set_app_setting(TEXT_SIZE_SETTING_KEY, key)
    return key


def _format_scaled_point_size(size):
    if float(size).is_integer():
        return f"{int(size)}pt"
    return f"{size:.2f}".rstrip("0").rstrip(".") + "pt"


def _scale_point_size(value, scale):
    text = str(value or "").strip()
    if not text.lower().endswith("pt"):
        return text
    try:
        size = float(text[:-2].strip())
    except ValueError:
        return text
    return _format_scaled_point_size(size * scale)


def stylesheet_for_theme(theme):
    colors = theme.colors
    metrics = theme.metrics
    text_size = TEXT_SIZE_OPTIONS[get_current_text_size_key()]
    font_scale = float(text_size["scale"])
    tokens = {}
    tokens.update({key.upper(): value for key, value in colors.items()})
    tokens.update({key.upper(): value for key, value in metrics.items()})
    tokens["FONT_FAMILY"] = metrics.get("font_family", "Segoe UI")
    tokens["FONT_SIZE"] = _scale_point_size(metrics.get("font_size", "10pt"), font_scale)
    fixed_font_sizes = {
        "SECTION_TITLE_FONT_SIZE": "9pt",
        "HOME_CARD_TITLE_FONT_SIZE": "13pt",
        "APP_TITLE_FONT_SIZE": "13pt",
        "STATUS_CHIP_FONT_SIZE": "8pt",
        "HERO_HANDLE_FONT_SIZE": "22pt",
        "HERO_SUBTITLE_FONT_SIZE": "11pt",
        "LABEL_TEXT_FONT_SIZE": "8pt",
        "VALUE_TEXT_FONT_SIZE": "10pt",
        "ORG_NAME_FONT_SIZE": "15pt",
        "ORG_SID_FONT_SIZE": "10pt",
        "MODULE_HEADING_FONT_SIZE": "18pt",
        "MODULE_SUBTITLE_FONT_SIZE": "10pt",
    }
    for token, value in fixed_font_sizes.items():
        tokens[token] = _scale_point_size(value, font_scale)
    tokens["BUTTON_BORDER"] = colors.get("button_border", colors["panel_border"])
    tokens["BUTTON_BORDER_HOVER"] = colors.get("button_border_hover", colors["accent_bright"])
    tokens["BUTTON_BORDER_TOP"] = colors.get("button_border_top", tokens["BUTTON_BORDER"])
    tokens["BUTTON_BORDER_LEFT"] = colors.get("button_border_left", tokens["BUTTON_BORDER"])
    tokens["BUTTON_BORDER_RIGHT"] = colors.get("button_border_right", tokens["BUTTON_BORDER"])
    tokens["BUTTON_BORDER_BOTTOM"] = colors.get("button_border_bottom", tokens["BUTTON_BORDER"])
    tokens["BUTTON_PRESSED"] = colors.get("button_pressed", colors["accent_soft"])
    tokens["CARD_BG"] = colors.get("card_bg", colors["surface"])
    tokens["CARD_HOVER_BG"] = colors.get("card_hover_bg", colors["surface_hover"])
    tokens["CARD_BORDER_TOP"] = colors.get("card_border_top", colors["panel_border"])
    tokens["CARD_BORDER_LEFT"] = colors.get("card_border_left", colors["panel_border"])
    tokens["CARD_BORDER_RIGHT"] = colors.get("card_border_right", colors["panel_border"])
    tokens["CARD_BORDER_BOTTOM"] = colors.get("card_border_bottom", colors["panel_border"])
    tokens["CHECKBOX_CHECKED_BG"] = colors.get("checkbox_checked_bg", colors["accent_soft"])
    tokens["HOME_CARD_BORDER"] = colors.get("home_card_border", colors["panel_border"])
    tokens["HOME_CARD_HOVER_BORDER"] = colors.get("home_card_hover_border", colors["accent_bright"])
    tokens["INPUT_BORDER_TOP"] = colors.get("input_border_top", colors["input_border"])
    tokens["INPUT_BORDER_LEFT"] = colors.get("input_border_left", colors["input_border"])
    tokens["INPUT_BORDER_RIGHT"] = colors.get("input_border_right", colors["input_border"])
    tokens["INPUT_BORDER_BOTTOM"] = colors.get("input_border_bottom", colors["input_border"])
    tokens["PANE_BG"] = colors.get("pane_bg", colors["background"])
    tokens["PANE_BORDER"] = colors.get("pane_border", colors["panel_border"])
    tokens["STATUS_CHIP_BG"] = colors.get("status_chip_bg", colors["surface_alt"])
    tokens["TOP_BAR_BG"] = colors.get("top_bar_bg", colors["background"])
    tokens["TOP_BAR_BORDER"] = colors.get("top_bar_border", colors["panel_border"])
    tokens["TOP_BAR_PADDING"] = metrics.get("top_bar_padding", "0px")
    tokens["TAB_BG"] = colors.get("tab_bg", colors["button_bg"])
    tokens["TAB_BORDER"] = colors.get("tab_border", colors["panel_border"])
    tokens["TAB_BORDER_TOP"] = colors.get("tab_border_top", tokens["TAB_BORDER"])
    tokens["TAB_BORDER_LEFT"] = colors.get("tab_border_left", tokens["TAB_BORDER"])
    tokens["TAB_BORDER_RIGHT"] = colors.get("tab_border_right", tokens["TAB_BORDER"])
    tokens["TAB_BORDER_BOTTOM"] = colors.get("tab_border_bottom", tokens["TAB_BORDER"])
    tokens["TAB_HOVER_BG"] = colors.get("tab_hover_bg", colors["button_hover"])
    tokens["TAB_HOVER_TEXT"] = colors.get("tab_hover_text", colors["accent_bright"])
    tokens["TAB_SELECTED_BG"] = colors.get("tab_selected_bg", colors["surface_alt"])
    tokens["TAB_SELECTED_BORDER"] = colors.get("tab_selected_border", colors["panel_border_active"])
    tokens["TAB_SELECTED_BORDER_TOP"] = colors.get("tab_selected_border_top", tokens["TAB_SELECTED_BORDER"])
    tokens["TAB_SELECTED_BORDER_LEFT"] = colors.get("tab_selected_border_left", tokens["TAB_SELECTED_BORDER"])
    tokens["TAB_SELECTED_BORDER_RIGHT"] = colors.get("tab_selected_border_right", tokens["TAB_SELECTED_BORDER"])
    tokens["TAB_SELECTED_BORDER_BOTTOM"] = colors.get("tab_selected_border_bottom", tokens["TAB_SELECTED_BORDER"])
    tokens["TAB_SELECTED_TEXT"] = colors.get("tab_selected_text", colors["accent_bright"])
    tokens["HOME_TAB_BG"] = colors.get("home_tab_bg", tokens["TAB_BG"])
    tokens["HOME_TAB_HOVER_BG"] = colors.get("home_tab_hover_bg", tokens["TAB_HOVER_BG"])
    tokens["HOME_TAB_BORDER"] = colors.get("home_tab_border", tokens["TAB_BORDER"])
    tokens["HOME_TAB_BORDER_TOP"] = colors.get("home_tab_border_top", tokens["TAB_BORDER_TOP"])
    tokens["HOME_TAB_BORDER_LEFT"] = colors.get("home_tab_border_left", tokens["TAB_BORDER_LEFT"])
    tokens["HOME_TAB_BORDER_RIGHT"] = colors.get("home_tab_border_right", tokens["TAB_BORDER_RIGHT"])
    tokens["HOME_TAB_BORDER_BOTTOM"] = colors.get("home_tab_border_bottom", tokens["TAB_BORDER_BOTTOM"])
    tokens["HOME_TAB_TEXT"] = colors.get("home_tab_text", colors["text_base"])
    tokens["HOME_TAB_FONT_WEIGHT"] = colors.get("home_tab_font_weight", "400")
    tokens["TAB_RADIUS"] = metrics.get("tab_radius", metrics["radius"])
    tokens["TAB_MIN_HEIGHT"] = metrics.get("tab_min_height", "18px")
    tokens["TAB_MARGIN_RIGHT"] = metrics.get("tab_margin_right", "0px")
    tokens["TAB_MARGIN_TOP"] = metrics.get("tab_margin_top", "0px")
    tokens["TAB_SELECTED_MARGIN_TOP"] = metrics.get("tab_selected_margin_top", "0px")
    tokens["TAB_SELECTED_MARGIN_BOTTOM"] = metrics.get("tab_selected_margin_bottom", "0px")
    tokens["TABLE_BG"] = colors.get("table_bg", colors["background"])
    tokens["TABLE_HEADER_BG"] = colors.get("table_header_bg", colors["surface_alt"])
    return _STYLE_TEMPLATE % tokens


_STYLE_TEMPLATE = """
QMainWindow, QWidget {
    background: %(BACKGROUND)s;
    color: %(TEXT_BASE)s;
    font-family: %(FONT_FAMILY)s;
    font-size: %(FONT_SIZE)s;
}

QTabWidget::pane {
    border: 1px solid %(PANE_BORDER)s;
    background: %(PANE_BG)s;
    border-radius: %(RADIUS)s;
}

QTabBar {
    background: %(TOP_BAR_BG)s;
    border: 1px solid %(TOP_BAR_BORDER)s;
    border-top-color: %(ACCENT_BRIGHT)s;
    border-bottom-color: %(TAB_SELECTED_BORDER_BOTTOM)s;
    padding: %(TOP_BAR_PADDING)s;
}

QTabBar::tab {
    background: %(TAB_BG)s;
    color: %(TEXT_BASE)s;
    border: 1px solid %(TAB_BORDER)s;
    border-top-color: %(TAB_BORDER_TOP)s;
    border-left-color: %(TAB_BORDER_LEFT)s;
    border-right-color: %(TAB_BORDER_RIGHT)s;
    border-bottom-color: %(TAB_BORDER_BOTTOM)s;
    border-top-left-radius: %(TAB_RADIUS)s;
    border-top-right-radius: %(TAB_RADIUS)s;
    margin-right: %(TAB_MARGIN_RIGHT)s;
    margin-top: %(TAB_MARGIN_TOP)s;
    padding: %(TAB_PADDING)s;
    min-height: %(TAB_MIN_HEIGHT)s;
}

QTabBar::tab:first {
    background: %(HOME_TAB_BG)s;
    color: %(HOME_TAB_TEXT)s;
    border-color: %(HOME_TAB_BORDER)s;
    border-top-color: %(HOME_TAB_BORDER_TOP)s;
    border-left-color: %(HOME_TAB_BORDER_LEFT)s;
    border-right-color: %(HOME_TAB_BORDER_RIGHT)s;
    border-bottom-color: %(HOME_TAB_BORDER_BOTTOM)s;
    font-weight: %(HOME_TAB_FONT_WEIGHT)s;
}

QTabBar::tab:first:!selected {
    background: %(HOME_TAB_BG)s;
    color: %(HOME_TAB_TEXT)s;
    border-color: %(HOME_TAB_BORDER)s;
    border-top-color: %(HOME_TAB_BORDER_TOP)s;
    border-left-color: %(HOME_TAB_BORDER_LEFT)s;
    border-right-color: %(HOME_TAB_BORDER_RIGHT)s;
    border-bottom-color: %(HOME_TAB_BORDER_BOTTOM)s;
    font-weight: %(HOME_TAB_FONT_WEIGHT)s;
}

QTabBar::tab:hover {
    background: %(TAB_HOVER_BG)s;
    color: %(TAB_HOVER_TEXT)s;
}

QTabBar::tab:first:hover {
    background: %(HOME_TAB_HOVER_BG)s;
    color: %(HOME_TAB_TEXT)s;
}

QTabBar::tab:first:hover:!selected {
    background: %(HOME_TAB_HOVER_BG)s;
    color: %(HOME_TAB_TEXT)s;
}

QTabBar::tab:selected {
    background: %(TAB_SELECTED_BG)s;
    color: %(TAB_SELECTED_TEXT)s;
    border-color: %(TAB_SELECTED_BORDER)s;
    border-top-color: %(TAB_SELECTED_BORDER_TOP)s;
    border-left-color: %(TAB_SELECTED_BORDER_LEFT)s;
    border-right-color: %(TAB_SELECTED_BORDER_RIGHT)s;
    border-bottom-color: %(TAB_SELECTED_BORDER_BOTTOM)s;
    margin-top: %(TAB_SELECTED_MARGIN_TOP)s;
    margin-bottom: %(TAB_SELECTED_MARGIN_BOTTOM)s;
}

QTabBar::tab:first:selected {
    background: %(TAB_SELECTED_BG)s;
    color: %(TAB_SELECTED_TEXT)s;
    border-color: %(TAB_SELECTED_BORDER)s;
    border-top-color: %(TAB_SELECTED_BORDER_TOP)s;
    border-left-color: %(TAB_SELECTED_BORDER_LEFT)s;
    border-right-color: %(TAB_SELECTED_BORDER_RIGHT)s;
    border-bottom-color: %(TAB_SELECTED_BORDER_BOTTOM)s;
}

QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: %(INPUT_BG)s;
    border: 1px solid %(INPUT_BORDER)s;
    border-top-color: %(INPUT_BORDER_TOP)s;
    border-left-color: %(INPUT_BORDER_LEFT)s;
    border-right-color: %(INPUT_BORDER_RIGHT)s;
    border-bottom-color: %(INPUT_BORDER_BOTTOM)s;
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
    border: 1px solid %(BUTTON_BORDER)s;
    border-top-color: %(BUTTON_BORDER_TOP)s;
    border-left-color: %(BUTTON_BORDER_LEFT)s;
    border-right-color: %(BUTTON_BORDER_RIGHT)s;
    border-bottom-color: %(BUTTON_BORDER_BOTTOM)s;
    border-radius: %(RADIUS)s;
    color: %(TEXT_PRIMARY)s;
    padding: %(BUTTON_PADDING)s;
}

QPushButton:hover {
    background: %(BUTTON_HOVER)s;
    border-color: %(BUTTON_BORDER_HOVER)s;
}

QPushButton:pressed {
    background: %(BUTTON_PRESSED)s;
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
    background: %(CHECKBOX_CHECKED_BG)s;
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
    background: %(TABLE_BG)s;
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
    background: %(CARD_BG)s;
    border: 1px solid %(PANEL_BORDER)s;
    border-top-color: %(CARD_BORDER_TOP)s;
    border-left-color: %(CARD_BORDER_LEFT)s;
    border-right-color: %(CARD_BORDER_RIGHT)s;
    border-bottom-color: %(CARD_BORDER_BOTTOM)s;
    border-radius: %(CARD_RADIUS)s;
}

QFrame#playerCard {
    border-color: %(PANEL_BORDER_ACTIVE)s;
}

QFrame#homeNavCard {
    background: %(CARD_BG)s;
    border: 1px solid %(HOME_CARD_BORDER)s;
    border-top-color: %(CARD_BORDER_TOP)s;
    border-left-color: %(CARD_BORDER_LEFT)s;
    border-right-color: %(CARD_BORDER_RIGHT)s;
    border-bottom-color: %(CARD_BORDER_BOTTOM)s;
    border-radius: %(CARD_RADIUS)s;
}

QFrame#homeNavCard:hover {
    background: %(CARD_HOVER_BG)s;
    border-color: %(HOME_CARD_HOVER_BORDER)s;
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
    font-size: %(SECTION_TITLE_FONT_SIZE)s;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#homeCardTitle {
    color: %(TEXT_HEADING)s;
    font-size: %(HOME_CARD_TITLE_FONT_SIZE)s;
    font-weight: 700;
}

QLabel#appTitle {
    color: %(TEXT_HEADING)s;
    font-size: %(APP_TITLE_FONT_SIZE)s;
    font-weight: 700;
}

QLabel#statusChip {
    background: %(STATUS_CHIP_BG)s;
    border: 1px solid %(PANEL_BORDER_ACTIVE)s;
    border-radius: 10px;
    color: %(ACCENT_BRIGHT)s;
    font-size: %(STATUS_CHIP_FONT_SIZE)s;
    font-weight: 700;
    padding: 3px 8px;
}

QLabel#heroHandle {
    color: %(TEXT_HEADING)s;
    font-size: %(HERO_HANDLE_FONT_SIZE)s;
    font-weight: 700;
}

QLabel#heroSubtitle {
    color: %(ACCENT_BRIGHT)s;
    font-size: %(HERO_SUBTITLE_FONT_SIZE)s;
}

QLabel#labelText {
    color: %(TEXT_MUTED)s;
    font-size: %(LABEL_TEXT_FONT_SIZE)s;
    text-transform: uppercase;
}

QLabel#valueText {
    color: %(TEXT_PRIMARY)s;
    font-size: %(VALUE_TEXT_FONT_SIZE)s;
}

QLabel#orgName {
    color: %(ACCENT_BRIGHT)s;
    font-size: %(ORG_NAME_FONT_SIZE)s;
    font-weight: 700;
}

QLabel#orgSid {
    color: %(ACCENT_BRIGHT)s;
    font-size: %(ORG_SID_FONT_SIZE)s;
}

QLabel#emptyState {
    color: %(TEXT_MUTED)s;
    padding: 18px;
}

QLabel#moduleHeading {
    color: %(TEXT_HEADING)s;
    font-size: %(MODULE_HEADING_FONT_SIZE)s;
    font-weight: 700;
}

QLabel#moduleSubtitle {
    color: %(TEXT_SECONDARY)s;
    font-size: %(MODULE_SUBTITLE_FONT_SIZE)s;
}
"""
