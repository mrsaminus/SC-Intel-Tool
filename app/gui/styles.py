from .themes.theme_manager import DEFAULT_THEME_KEY, get_current_theme, get_theme, stylesheet_for_theme


def current_app_style():
    return stylesheet_for_theme(get_current_theme())


APP_STYLE = stylesheet_for_theme(get_theme(DEFAULT_THEME_KEY))
