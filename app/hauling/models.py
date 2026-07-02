from dataclasses import dataclass, field
from datetime import datetime, timezone


CONTRACT_STATE_PLANNED = "planned"
CONTRACT_STATE_LOADED = "loaded"
CONTRACT_STATE_DELIVERED = "delivered"
CONTRACT_STATE_FAILED = "failed"
CONTRACT_STATE_CANCELLED = "cancelled"
CONTRACT_STATES = (
    CONTRACT_STATE_PLANNED,
    CONTRACT_STATE_LOADED,
    CONTRACT_STATE_DELIVERED,
    CONTRACT_STATE_FAILED,
    CONTRACT_STATE_CANCELLED,
)

SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_COMPLETED = "completed"
SESSION_STATUS_ARCHIVED = "archived"
SESSION_STATUS_CANCELLED = "cancelled"
SESSION_STATUSES = (
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_ARCHIVED,
    SESSION_STATUS_CANCELLED,
)


def utc_timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class HaulingContract:
    id: str = ""
    pickup: str = ""
    delivery: str = ""
    commodity: str = ""
    scu: float = 0.0
    reward: float | None = None
    contract_name: str = ""
    source_text: str = ""
    confidence: float = 0.0
    status: str = "needs_review"
    state: str = CONTRACT_STATE_PLANNED
    created_at: str = field(default_factory=utc_timestamp)
    notes: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def route_key(self):
        return self.pickup, self.delivery

    @property
    def is_complete(self):
        return bool(self.pickup and self.delivery and self.commodity and self.scu > 0)


@dataclass(frozen=True)
class HaulingStop:
    location: str
    pickup_contracts: tuple[HaulingContract, ...] = field(default_factory=tuple)
    delivery_contracts: tuple[HaulingContract, ...] = field(default_factory=tuple)
    total_pickup_scu: float = 0.0
    total_delivery_scu: float = 0.0


@dataclass(frozen=True)
class HaulingManifest:
    contracts: tuple[HaulingContract, ...] = field(default_factory=tuple)
    selected_ship: str = ""
    ship_capacity_scu: float | None = None
    total_scu: float = 0.0
    loaded_scu: float = 0.0
    delivered_scu: float = 0.0
    remaining_scu: float | None = None
    total_contracts: int = 0
    planned_contracts: int = 0
    loaded_contracts: int = 0
    delivered_contracts: int = 0
    completion_percentage: float = 0.0
    pickups: tuple[HaulingStop, ...] = field(default_factory=tuple)
    destinations: tuple[HaulingStop, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class HaulingSession:
    id: int | None = None
    name: str = ""
    status: str = SESSION_STATUS_ACTIVE
    selected_ship: str = ""
    ship_capacity_scu: float | None = None
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    archived_at: str = ""
    total_scu: float = 0.0
    loaded_scu: float = 0.0
    delivered_scu: float = 0.0
    completion_percentage: float = 0.0
    notes: str = ""
    manifest: HaulingManifest = field(default_factory=HaulingManifest)
