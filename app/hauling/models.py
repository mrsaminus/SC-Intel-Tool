from dataclasses import dataclass, field
from datetime import datetime, timezone


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
    remaining_scu: float | None = None
    pickups: tuple[HaulingStop, ...] = field(default_factory=tuple)
    destinations: tuple[HaulingStop, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
