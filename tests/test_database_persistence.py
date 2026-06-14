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


def test_wikelo_reset_reward_does_not_touch_other_rewards(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)

    database.set_wikelo_checklist_state("reward-a", "option", "material", True)
    database.set_wikelo_checklist_state("reward-b", "option", "material", True)

    assert database.reset_wikelo_checklist_reward("reward-a") == 1
    assert database.get_wikelo_checklist_state("reward-a") == {}
    assert database.get_wikelo_checklist_state("reward-b") == {("option", "material"): True}

    assert database.reset_all_wikelo_checklist_state() == 1
    assert database.get_wikelo_checklist_state("reward-b") == {}


def test_lookup_history_dedupes_case_insensitive_handles(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)

    database.save_lookup("Saminus", "Saminus", "NOVA", "https://example.test/one")
    database.save_lookup("saminus", "Saminus", "NOVA", "https://example.test/two")

    rows = database.get_lookup_history()
    assert len([row for row in rows if row["handle"].lower() == "saminus"]) == 1


def test_database_initialization_creates_core_tables(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)

    with database.get_connection() as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }

    assert "player_notes" in tables
    assert "lookup_history" in tables
    assert "app_settings" in tables
    assert "wikelo_checklist_state" in tables
