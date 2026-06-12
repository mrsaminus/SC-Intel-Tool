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
        name="Windows XP",
        category="Retro",
        description="Luna-inspired blue chrome with soft panels and rounded plastic controls.",
        colors={
            "background": "#17407f",
            "surface": "#e8f2ff",
            "surface_alt": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:0.45 #dcecff, stop:1 #8fb8f4)",
            "surface_hover": "#f6fbff",
            "panel_border": "#6f9ee6",
            "panel_border_active": "#1f58bd",
            "text_primary": "#102044",
            "text_base": "#102044",
            "text_heading": "#07183d",
            "text_secondary": "#334f83",
            "text_muted": "#667da4",
            "accent": "#1f58bd",
            "accent_bright": "#0d3f9b",
            "accent_soft": "#c6dcff",
            "button_bg": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:0.45 #dcecff, stop:1 #8fb8f4)",
            "button_hover": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:0.45 #eaf4ff, stop:1 #a7c8fb)",
            "button_border": "#3d6bc7",
            "button_border_hover": "#1f58bd",
            "checkbox_checked_bg": "#45a049",
            "home_card_border": "#6f9ee6",
            "home_card_hover_border": "#1f58bd",
            "status_chip_bg": "#d9e9ff",
            "input_bg": "#ffffff",
            "input_border": "#6c8fc8",
            "selection_bg": "#316ac5",
            "selection_text": "#ffffff",
            "danger": "#d0342c",
            "success": "#45a049",
            "table_header_bg": "#cfe2ff",
            "table_grid": "#b4c8e8",
        },
        metrics={"radius": "7px", "card_radius": "8px"},
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
            "background": "#12161A",
            "surface": "#19201f",
            "surface_alt": "#2A3A2B",
            "surface_hover": "#314832",
            "panel_border": "#3A444C",
            "panel_border_active": "#FF9900",
            "text_primary": "#f3eadb",
            "text_base": "#d9cdb8",
            "text_heading": "#fff3de",
            "text_secondary": "#b7c6a5",
            "text_muted": "#87917d",
            "accent": "#FF9900",
            "accent_bright": "#4EFE50",
            "accent_soft": "#2b2a18",
            "button_bg": "#20272a",
            "button_hover": "#2f392f",
            "button_disabled": "#171b1f",
            "button_border": "#5f5b32",
            "button_border_hover": "#FF9900",
            "checkbox_checked_bg": "#2A3A2B",
            "home_card_border": "#3A444C",
            "home_card_hover_border": "#FF9900",
            "status_chip_bg": "#20291f",
            "input_bg": "#14191d",
            "input_border": "#3A444C",
            "selection_bg": "#233f2a",
            "selection_text": "#f8fff0",
            "warning": "#ffb165",
            "danger": "#AC0000",
            "success": "#4EFE50",
            "table_header_bg": "#222b28",
            "table_grid": "#303a3f",
            "avatar_bg": "#101417",
            "avatar_border": "#FF9900",
            "avatar_text": "#4EFE50",
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
    tokens["BUTTON_BORDER"] = colors.get("button_border", colors["panel_border"])
    tokens["BUTTON_BORDER_HOVER"] = colors.get("button_border_hover", colors["accent_bright"])
    tokens["BUTTON_BORDER_TOP"] = colors.get("button_border_top", tokens["BUTTON_BORDER"])
    tokens["BUTTON_BORDER_LEFT"] = colors.get("button_border_left", tokens["BUTTON_BORDER"])
    tokens["BUTTON_BORDER_RIGHT"] = colors.get("button_border_right", tokens["BUTTON_BORDER"])
    tokens["BUTTON_BORDER_BOTTOM"] = colors.get("button_border_bottom", tokens["BUTTON_BORDER"])
    tokens["CHECKBOX_CHECKED_BG"] = colors.get("checkbox_checked_bg", colors["accent_soft"])
    tokens["HOME_CARD_BORDER"] = colors.get("home_card_border", colors["panel_border"])
    tokens["HOME_CARD_HOVER_BORDER"] = colors.get("home_card_hover_border", colors["accent_bright"])
    tokens["STATUS_CHIP_BG"] = colors.get("status_chip_bg", colors["surface_alt"])
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
    border: 1px solid %(HOME_CARD_BORDER)s;
    border-radius: %(CARD_RADIUS)s;
}

QFrame#homeNavCard:hover {
    background: %(SURFACE_HOVER)s;
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
    background: %(STATUS_CHIP_BG)s;
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
