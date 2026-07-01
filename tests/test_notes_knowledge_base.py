import time

import pytest
from PySide6.QtWidgets import QApplication

from conftest import isolated_database, reload_module


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_notes_crud_search_category_and_tags(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    notes = reload_module("app.notes_storage")

    saved = notes.save_note(notes.KnowledgeNote(
        title="Gold Route",
        category="Trading",
        tags="UEX, profit, UEX",
        body="Area18 to Orison",
        linked_type="trading route",
        linked_key="gold-area18-orison",
        is_pinned=True,
    ))

    assert saved.id is not None
    assert saved.tags == "UEX, profit"
    assert saved.category == "Trading"
    assert notes.list_notes(query="orison")[0].title == "Gold Route"
    assert notes.list_notes(category="Trading")[0].id == saved.id

    time.sleep(0.01)
    edited = notes.save_note(notes.KnowledgeNote(
        id=saved.id,
        title="Gold Route Updated",
        category="Trading",
        tags="profit",
        body="Updated route notes",
    ))

    assert edited.title == "Gold Route Updated"
    assert edited.modified_at >= saved.modified_at
    assert notes.get_note(saved.id).body == "Updated route notes"

    duplicate = notes.duplicate_note(saved.id)
    assert duplicate.id != saved.id
    assert duplicate.title == "Gold Route Updated Copy"

    assert notes.delete_note(saved.id) == 1
    assert notes.get_note(saved.id) is None
    assert notes.get_note(duplicate.id) is not None


def test_notes_migration_preserves_player_notes(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)
    notes = reload_module("app.notes_storage")

    database.save_note("Saminus", "Friendly", "Existing player note")
    saved = notes.save_note(notes.KnowledgeNote(title="General Note", body="Local KB"))

    assert database.get_note("Saminus") == ("Friendly", "Existing player note")
    assert notes.get_note(saved.id).body == "Local KB"


def test_notes_record_safe_activity_log_events(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    notes = reload_module("app.notes_storage")
    event_storage = reload_module("app.event_center.storage")

    saved = notes.save_note(notes.KnowledgeNote(
        title="Sensitive Local Note",
        category="Trading",
        tags="private-tag",
        body="Secret body text should stay out of activity metadata.",
        linked_key="private-linked-key",
    ))
    notes.save_note(notes.KnowledgeNote(
        id=saved.id,
        title="Sensitive Local Note",
        category="Trading",
        body="Updated secret body.",
    ))
    assert notes.delete_note(saved.id) == 1

    events = event_storage.list_notification_events(category="Notes")
    event_types = {event.event_type for event in events}

    assert {"created", "updated", "deleted"}.issubset(event_types)
    for event in events:
        assert event.source == "Notes"
        assert event.severity == "Info"
        assert "Secret body" not in event.message
        assert "Secret body" not in str(event.metadata)
        assert "private-tag" not in str(event.metadata)
        assert "private-linked-key" not in str(event.metadata)


def test_notes_table_migration_adds_missing_columns(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)
    notes = reload_module("app.notes_storage")
    with database.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE knowledge_notes")
        cur.execute("""
        CREATE TABLE knowledge_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT
        )
        """)
        cur.execute("INSERT INTO knowledge_notes (title, body) VALUES (?, ?)", ("Legacy", "Old body"))
        conn.commit()

    notes.ensure_notes_tables()
    loaded = notes.list_notes(query="legacy")

    assert len(loaded) == 1
    assert loaded[0].category == "General"
    assert loaded[0].body == "Old body"


def test_notes_tab_create_and_search_smoke(monkeypatch, tmp_path, qapp):
    isolated_database(monkeypatch, tmp_path)
    notes_tab_module = reload_module("app.gui.notes_tab")

    tab = notes_tab_module.NotesTab()
    tab.title_input.setText("Mining Cheat Sheet")
    tab.category_input.setEditText("Mining")
    tab.tags_input.setText("rocks, quantanium")
    tab.body_input.setPlainText("Keep refinery notes local.")
    tab.save_current_note()
    tab.search_input.setText("quantanium")
    qapp.processEvents()

    assert tab.notes_table.rowCount() == 1
    assert tab.notes[0].title == "Mining Cheat Sheet"
    assert tab.notes[0].category == "Mining"
    tab.close()
