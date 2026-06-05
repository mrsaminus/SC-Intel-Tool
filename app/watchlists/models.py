from dataclasses import dataclass, field


@dataclass(frozen=True)
class WatchlistEntry:
    id: int | None = None
    category: str = ""
    name: str = ""
    key: str = ""
    source: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    last_checked_at: str = ""
    last_status: str = ""
    is_active: bool = True
    unread_events: int = 0


@dataclass(frozen=True)
class WatchlistSnapshot:
    id: int | None = None
    watchlist_id: int | None = None
    checked_at: str = ""
    status: str = ""
    value: dict = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True)
class WatchlistEvent:
    id: int | None = None
    watchlist_id: int | None = None
    event_type: str = ""
    message: str = ""
    created_at: str = ""
    is_read: bool = False
