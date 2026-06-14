from conftest import isolated_database


def test_watchlist_entry_snapshot_and_event_persist(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)

    from app.watchlists.storage import (
        add_watchlist_event,
        add_watchlist_snapshot,
        get_latest_snapshot,
        get_watchlist_entry,
        list_watchlist_events,
        upsert_watchlist_entry,
    )

    entry_id, created = upsert_watchlist_entry(
        "Player",
        "Saminus",
        "saminus",
        source="Player Lookup",
        metadata={"handle": "Saminus"},
    )

    assert created is True
    assert get_watchlist_entry(entry_id).name == "Saminus"

    add_watchlist_snapshot(entry_id, "Checked", {"org": "NOVA"}, "Smoke test")
    latest = get_latest_snapshot(entry_id)
    assert latest.status == "Checked"
    assert latest.value == {"org": "NOVA"}

    event_id = add_watchlist_event(entry_id, "changed", "Profile changed")
    events = list_watchlist_events(entry_id)
    assert events[0].id == event_id
    assert events[0].message == "Profile changed"
