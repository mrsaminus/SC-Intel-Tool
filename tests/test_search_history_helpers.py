from app.gui.search_history_helpers import (
    history_flags_text,
    history_row_has_piracy,
    history_row_matches_filter,
    history_sort_key,
)


def test_history_filter_matches_text_and_piracy_state():
    row = {
        "handle": "Saminus",
        "display_name": "Saminus",
        "main_org": "NOVA",
        "org_sid": "NOVA",
        "any_org_piracy": 0,
    }

    assert history_row_matches_filter(row, "nova", "All") is True
    assert history_row_matches_filter(row, "missing", "All") is False
    assert history_row_matches_filter(row, "", "Piracy NO") is True
    assert history_row_matches_filter(row, "", "Piracy YES") is False


def test_history_piracy_prefers_any_org_value_when_present():
    assert history_row_has_piracy({"any_org_piracy": 1, "org_piracy": 0}) is True
    assert history_row_has_piracy({"any_org_piracy": 0, "org_piracy": 1}) is False
    assert history_row_has_piracy({"any_org_piracy": None, "org_piracy": 1}) is True


def test_history_flags_and_sort_keys_are_stable():
    row = {
        "handle": "ninjasniper98",
        "display_name": "",
        "main_org": "REDACTED",
        "any_org_piracy": None,
        "org_piracy": 0,
        "is_pinned": 1,
        "is_favorite": 1,
    }

    assert history_flags_text(row) == "Pinned, Favorite"
    assert history_sort_key(row, 0) == "ninjasniper98"
    assert history_sort_key(row, 1) == "redacted"
    assert history_sort_key(row, 2) == 0
    assert history_sort_key(row, 3) == "Pinned, Favorite"
