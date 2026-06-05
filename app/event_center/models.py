from dataclasses import dataclass, field


@dataclass(frozen=True)
class NotificationEvent:
    id: int | None = None
    category: str = ""
    source: str = ""
    entity_name: str = ""
    event_type: str = ""
    message: str = ""
    metadata: dict = field(default_factory=dict)
    severity: str = "Info"
    created_at: str = ""
    is_read: bool = False
