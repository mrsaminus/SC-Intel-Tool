from conftest import isolated_database


def test_app_settings_persist_in_isolated_database(monkeypatch, tmp_path):
    database, db_path = isolated_database(monkeypatch, tmp_path)

    database.set_app_setting("theme", "Windows XP Luna")

    assert db_path.exists()
    assert database.get_app_setting("theme") == "Windows XP Luna"
    assert database.get_app_setting("missing", "fallback") == "fallback"


def test_wikelo_checklist_state_can_be_set_and_reset(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)

    database.set_wikelo_checklist_state("reward", "option", "material", True)
    assert database.get_wikelo_checklist_state("reward") == {("option", "material"): True}

    database.set_wikelo_checklist_state("reward", "option", "material", False)
    assert database.get_wikelo_checklist_state("reward") == {("option", "material"): False}

    assert database.reset_wikelo_checklist_reward("reward") == 1
    assert database.get_wikelo_checklist_state("reward") == {}


def test_lookup_history_dedupes_case_insensitive_handles(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)

    database.save_lookup("Saminus", "Saminus", "NOVA", "https://example.test/one")
    database.save_lookup("saminus", "Saminus", "NOVA", "https://example.test/two")

    rows = database.get_lookup_history()
    assert len([row for row in rows if row["handle"].lower() == "saminus"]) == 1
