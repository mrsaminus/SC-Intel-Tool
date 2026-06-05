from .storage import add_notification_event


WATCHLIST_EVENT_SEVERITY = {
    "created": "Info",
    "updated": "Info",
    "value_changed": "Change",
    "no_data": "Warning",
    "recovered": "Change",
    "unprofitable": "Warning",
    "profitable": "Change",
    "refresh_pending": "Info",
    "planned": "Info",
    "lookup_failed": "Warning",
    "lookup_recovered": "Change",
    "org_changed": "Important",
    "org_visibility_changed": "Important",
    "piracy_changed": "Important",
    "profile_changed": "Change",
}


WATCHLIST_CATEGORY_MAP = {
    "trading_route": "Trading",
    "trading_commodity": "Trading",
    "item": "Item",
    "ship": "Item",
    "player": "Player",
    "org": "Organization",
}


def record_event(
    category,
    source,
    entity_name,
    event_type,
    message,
    metadata=None,
    severity="Info",
    dedupe=True,
):
    return add_notification_event(
        category=category,
        source=source,
        entity_name=entity_name,
        event_type=event_type,
        message=message,
        metadata=metadata or {},
        severity=severity,
        dedupe=dedupe,
    )


def record_watchlist_event(entry, event_type, message):
    category = WATCHLIST_CATEGORY_MAP.get(entry.category, "Watchlists")
    severity = WATCHLIST_EVENT_SEVERITY.get(event_type, "Info")
    return record_event(
        category=category,
        source=entry.source or "Watchlists",
        entity_name=entry.name,
        event_type=event_type,
        message=message,
        metadata={
            "watchlist_id": entry.id,
            "watchlist_category": entry.category,
            "watchlist_key": entry.key,
        },
        severity=severity,
    )


def copy_event_summary_text(event):
    return "\n".join((
        f"Time: {event.created_at}",
        f"Category: {event.category}",
        f"Source: {event.source or 'N/A'}",
        f"Entity: {event.entity_name or 'N/A'}",
        f"Event: {event.event_type}",
        f"Severity: {event.severity}",
        f"Read: {'Yes' if event.is_read else 'No'}",
        f"Message: {event.message}",
    ))
