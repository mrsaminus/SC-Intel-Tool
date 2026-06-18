SEARCH_HISTORY_FILTER_FIELDS = ("handle", "display_name", "main_org", "org_sid")


def history_row_has_piracy(row):
    if row.get("any_org_piracy") is not None:
        return bool(row.get("any_org_piracy"))

    return bool(row.get("org_piracy"))


def history_flags_text(row):
    flags = []
    if row.get("is_pinned"):
        flags.append("Pinned")
    if row.get("is_favorite"):
        flags.append("Favorite")
    return ", ".join(flags) if flags else ""


def history_row_matches_filter(row, query, piracy_filter):
    has_piracy = history_row_has_piracy(row)
    if piracy_filter == "Piracy YES" and not has_piracy:
        return False
    if piracy_filter == "Piracy NO" and has_piracy:
        return False

    if not query:
        return True

    searchable = " ".join(
        str(row.get(field) or "")
        for field in SEARCH_HISTORY_FILTER_FIELDS
    ).lower()
    return str(query).lower() in searchable


def history_sort_key(row, column):
    if column == 0:
        return (row.get("display_name") or row["handle"]).lower()
    if column == 1:
        return (row.get("main_org") or "").lower()
    if column == 2:
        return 1 if history_row_has_piracy(row) else 0
    if column == 3:
        return history_flags_text(row)

    return ""
