UNKNOWN = "Unknown"


def player_snapshot_from_lookup(data, tag="", notes=""):
    main_org_data = data.get("main_org") if isinstance(data.get("main_org"), dict) else {}
    main_org_redacted = bool(data.get("main_org_redacted") or main_org_data.get("redacted"))
    affiliations_redacted = bool(data.get("affiliations_redacted"))
    organizations_redacted = bool(data.get("organizations_redacted"))
    piracy_status = UNKNOWN if (main_org_redacted or affiliations_redacted) else (
        "YES" if (data.get("any_org_piracy") or main_org_data.get("piracy")) else "NO"
    )

    return {
        "handle": data.get("handle") or "",
        "display_name": data.get("display_name") or "",
        "citizen_record": data.get("citizen_record") or "",
        "enlisted": data.get("enlisted") or "",
        "location": data.get("location") or "",
        "fluency": data.get("fluency") or "",
        "main_org": org_name_value(data.get("main_org")),
        "org_sid": data.get("org_sid") or main_org_data.get("sid") or "",
        "org_rank": data.get("org_rank") or main_org_data.get("rank") or "",
        "org_type": data.get("org_type") or main_org_data.get("type") or "",
        "org_member_count": data.get("org_member_count") or main_org_data.get("member_count") or "",
        "main_org_redacted": main_org_redacted,
        "affiliations_redacted": affiliations_redacted,
        "organizations_redacted": organizations_redacted,
        "piracy_status": piracy_status,
        "org_piracy": bool(data.get("org_piracy") or main_org_data.get("piracy")),
        "any_org_piracy": bool(data.get("any_org_piracy") or main_org_data.get("piracy")),
        "profile_url": data.get("profile_url") or "",
        "organizations_url": data.get("organizations_url") or "",
        "org_url": data.get("org_url") or main_org_data.get("url") or "",
        "tag": tag or "",
        "notes": notes or "",
        "affiliations": [
            affiliation_snapshot(org)
            for org in data.get("affiliations", ())
        ],
    }


def player_snapshot_from_history(row):
    main_org = row.get("main_org") or ""
    redacted = main_org.upper() == "REDACTED"
    piracy_status = UNKNOWN if redacted else ("YES" if row.get("any_org_piracy") else "NO")
    return {
        "handle": row.get("handle") or "",
        "display_name": row.get("display_name") or "",
        "main_org": main_org,
        "org_sid": row.get("org_sid") or "",
        "main_org_redacted": redacted,
        "affiliations_redacted": False,
        "organizations_redacted": redacted,
        "piracy_status": piracy_status,
        "org_piracy": bool(row.get("org_piracy")),
        "any_org_piracy": bool(row.get("any_org_piracy")),
        "profile_url": row.get("profile_url") or "",
    }


def affiliation_snapshot(org):
    redacted = bool(org.get("redacted"))
    return {
        "relationship": org.get("relationship") or "Affiliation",
        "name": org.get("name") or "",
        "sid": org.get("sid") or "",
        "rank": org.get("rank") or "",
        "member_count": org.get("member_count") or "",
        "type": org.get("type") or "",
        "commitment": org.get("commitment") or "",
        "exclusivity": org.get("exclusivity") or "",
        "piracy": UNKNOWN if redacted else ("YES" if org.get("piracy") else "NO"),
        "url": org.get("url") or "",
        "logo_url": org.get("logo_url") or "",
        "redacted": redacted,
    }


def main_org_snapshot_from_lookup(data):
    main_org_data = data.get("main_org") if isinstance(data.get("main_org"), dict) else {}
    return {
        "relationship": "Main organization",
        "name": org_name_value(data.get("main_org")),
        "sid": data.get("org_sid") or main_org_data.get("sid") or "",
        "rank": data.get("org_rank") or main_org_data.get("rank") or "",
        "member_count": data.get("org_member_count") or main_org_data.get("member_count") or "",
        "type": data.get("org_type") or main_org_data.get("type") or "",
        "commitment": data.get("org_commitment") or main_org_data.get("commitment") or "",
        "exclusivity": data.get("org_exclusivity") or main_org_data.get("exclusivity") or "",
        "piracy": UNKNOWN if (data.get("main_org_redacted") or main_org_data.get("redacted")) else (
            "YES" if (data.get("org_piracy") or main_org_data.get("piracy")) else "NO"
        ),
        "url": data.get("org_url") or main_org_data.get("url") or "",
        "logo_url": data.get("org_logo") or main_org_data.get("logo_url") or "",
        "redacted": bool(data.get("main_org_redacted") or main_org_data.get("redacted")),
    }


def player_change_events(previous, current):
    if not previous:
        return []

    events = []
    previous_redacted = bool(previous.get("main_org_redacted") or previous.get("affiliations_redacted"))
    current_redacted = bool(current.get("main_org_redacted") or current.get("affiliations_redacted"))
    if previous_redacted != current_redacted:
        if current_redacted:
            message = "Organization visibility changed: current RSI profile is redacted/hidden."
        else:
            message = "Organization visibility changed: RSI organization data is visible again."
        events.append(("org_visibility_changed", "Important", message))

    previous_org = normalized_org_identity(previous)
    current_org = normalized_org_identity(current)
    if previous_org != current_org:
        previous_org_label = org_label(previous)
        current_org_label = org_label(current)
        if not previous_org and current_org:
            message = f"New main organization found: {current_org_label}"
            event_type = "new_org_found"
        else:
            message = (
                f"Main organization changed: "
                f"{previous_org_label} -> {current_org_label}"
            )
            event_type = "org_changed"
        events.append((event_type, "Important", message))

    previous_piracy = normalize_piracy_status(previous.get("piracy_status"))
    current_piracy = normalize_piracy_status(current.get("piracy_status"))
    if previous_piracy != current_piracy and UNKNOWN not in {previous_piracy, current_piracy}:
        events.append((
            "piracy_changed",
            "Important",
            f"Piracy status changed: {previous_piracy} -> {current_piracy}",
        ))

    profile_changes = []
    for field, label in (("display_name", "Display name"), ("location", "Location"), ("fluency", "Fluency")):
        old = previous.get(field) or ""
        new = current.get(field) or ""
        if old and new and old != new:
            profile_changes.append(f"{label}: {old} -> {new}")
    if profile_changes:
        events.append(("profile_changed", "Change", "; ".join(profile_changes)))

    return events


def org_change_events(previous, current):
    if not previous:
        return []

    events = []
    if bool(previous.get("redacted")) != bool(current.get("redacted")):
        events.append((
            "org_visibility_changed",
            "Important",
            "Organization visibility changed.",
        ))

    previous_piracy = normalize_piracy_status(previous.get("piracy"))
    current_piracy = normalize_piracy_status(current.get("piracy"))
    if previous_piracy != current_piracy and UNKNOWN not in {previous_piracy, current_piracy}:
        events.append((
            "piracy_changed",
            "Important",
            f"Organization piracy status changed: {previous_piracy} -> {current_piracy}",
        ))

    for field, label in (
        ("member_count", "Member count"),
        ("type", "Type"),
        ("commitment", "Commitment"),
        ("exclusivity", "Exclusivity"),
    ):
        old = previous.get(field) or ""
        new = current.get(field) or ""
        if old and new and old != new:
            events.append((
                "org_status_changed",
                "Change",
                f"{label} changed: {old} -> {new}",
            ))

    return events


def player_change_summary(previous, current):
    events = player_change_events(previous, current)
    if not previous:
        return "No previous lookup to compare yet."
    if not events:
        return "No meaningful change detected."
    return " | ".join(message for _event_type, _severity, message in events)


def normalized_org_identity(snapshot):
    org = org_name_value(snapshot.get("main_org")).strip().lower()
    sid = string_value(snapshot.get("org_sid")).strip().lower()
    if org in {"", "n/a", "none", "no main org"} and sid in {"", "n/a"}:
        return ""
    return f"{org}|{sid}"


def org_label(snapshot):
    return org_name_value(snapshot.get("main_org")) or string_value(snapshot.get("org_sid")) or "N/A"


def org_name_value(value):
    if isinstance(value, dict):
        return string_value(value.get("name"))
    return string_value(value)


def string_value(value):
    if value is None:
        return ""
    return str(value)


def normalize_piracy_status(value):
    if isinstance(value, bool):
        return "YES" if value else "NO"
    text = string_value(value).strip()
    if not text:
        return UNKNOWN
    if text.lower() in {"true", "yes", "y", "1"}:
        return "YES"
    if text.lower() in {"false", "no", "n", "0"}:
        return "NO"
    if text.lower() in {"unknown", "n/a", "na"}:
        return UNKNOWN
    return text.upper()
