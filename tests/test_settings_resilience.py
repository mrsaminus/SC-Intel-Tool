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
