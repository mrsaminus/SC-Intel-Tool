from conftest import isolated_database, reload_module


def test_missing_theme_setting_uses_release_default(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    theme_manager = reload_module("app.gui.themes.theme_manager")

    assert theme_manager.get_current_theme_key() == theme_manager.DEFAULT_THEME_KEY


def test_hidden_or_invalid_theme_setting_falls_back_safely(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)
    database.set_app_setting("appearance.theme", "drake_theme")
    theme_manager = reload_module("app.gui.themes.theme_manager")

    assert theme_manager.get_current_theme_key() == theme_manager.DEFAULT_THEME_KEY

    database.set_app_setting("appearance.theme", "not-a-real-theme")
    assert theme_manager.get_current_theme_key() == theme_manager.DEFAULT_THEME_KEY


def test_missing_text_size_setting_uses_default(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    theme_manager = reload_module("app.gui.themes.theme_manager")

    assert theme_manager.get_current_text_size_key() == theme_manager.DEFAULT_TEXT_SIZE_KEY


def test_invalid_text_size_setting_falls_back_safely(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)
    database.set_app_setting("appearance.text_size", "huge")
    theme_manager = reload_module("app.gui.themes.theme_manager")

    assert theme_manager.get_current_text_size_key() == theme_manager.DEFAULT_TEXT_SIZE_KEY


def test_text_size_setting_persists_and_scales_stylesheet(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    theme_manager = reload_module("app.gui.themes.theme_manager")

    theme_manager.set_current_text_size("large")
    stylesheet = theme_manager.stylesheet_for_theme(theme_manager.get_current_theme())

    assert theme_manager.get_current_text_size_key() == "large"
    assert "font-size: 11pt;" in stylesheet
    assert "font-size: 19.8pt;" in stylesheet
