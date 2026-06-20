from dataclasses import dataclass

from PySide6.QtCore import QObject, QThreadPool, Signal

from app.trading_data import format_trade_location
from app.trading_ship_cargo import trading_ship_names
from app.uex_client import fetch_all_commodity_prices

from ..workers import FunctionWorker


@dataclass(frozen=True)
class TradingReferenceCommodity:
    name: str


@dataclass(frozen=True)
class TradingReferenceCommodityType:
    display_name: str


@dataclass(frozen=True)
class TradingReferenceLocation:
    name: str


@dataclass(frozen=True)
class TradingReferenceShop:
    name: str
    display_name: str
    system: str
    location: str
    category: str
    hierarchy: str


@dataclass(frozen=True)
class TradingReferenceData:
    commodities: tuple
    commodity_types: tuple
    locations: tuple
    shops: tuple
    ships: tuple
    price_rows: tuple = ()
    source_error: str = ""


def load_trading_reference_data():
    ships = tuple(trading_ship_names())
    try:
        price_rows = tuple(fetch_all_commodity_prices())
    except Exception as exc:  # noqa: BLE001 - keep Trading usable when UEX is unavailable.
        return TradingReferenceData(
            commodities=(),
            commodity_types=(),
            locations=(),
            shops=(),
            ships=ships,
            price_rows=(),
            source_error=str(exc),
        )

    commodities = tuple(
        TradingReferenceCommodity(name)
        for name in sorted({
            row.commodity_name
            for row in price_rows
            if row.commodity_name and row.commodity_name != "Unknown"
        }, key=str.lower)
    )
    location_names = sorted({
        location_name(row)
        for row in price_rows
        if location_name(row) != "N/A"
    }, key=str.lower)
    shop_names = sorted({
        format_trade_location(row)
        for row in price_rows
        if format_trade_location(row) != "N/A"
    }, key=str.lower)
    locations = tuple(
        TradingReferenceLocation(name)
        for name in location_names
    )
    shops = tuple(
        TradingReferenceShop(
            name=name,
            display_name=name,
            system=first_part(name),
            location=location_without_system(name),
            category="UEX terminal",
            hierarchy=name,
        )
        for name in shop_names
    )
    return TradingReferenceData(
        commodities=commodities,
        commodity_types=(),
        locations=locations,
        shops=shops,
        ships=ships,
        price_rows=price_rows,
    )


def location_name(price_row):
    parts = [
        value
        for value in (
            price_row.star_system_name if price_row.star_system_name != "N/A" else "",
            price_row.location_name if price_row.location_name != "N/A" else "",
        )
        if value
    ]
    return " - ".join(parts) or "N/A"


def first_part(path):
    return (path or "N/A").split(" - ", 1)[0].strip() or "N/A"


def location_without_system(path):
    parts = [part.strip() for part in (path or "").split(" - ") if part.strip()]
    if len(parts) <= 1:
        return path or "N/A"
    return " - ".join(parts[1:])


class TradingReferenceService(QObject):
    loaded = Signal(object)
    error = Signal(object)
    state_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.data = None
        self.error_message = ""
        self.is_loading = False
        self._workers = set()

    def ensure_loaded(self):
        self.refresh(force=False)

    def refresh(self, force=False):
        if self.is_loading:
            self.state_changed.emit("loading")
            return

        if self.data is not None and not force:
            self.state_changed.emit("loaded")
            self.loaded.emit(self.data)
            return

        self.is_loading = True
        self.error_message = ""
        self.state_changed.emit("loading")

        worker = FunctionWorker(load_trading_reference_data)
        self._workers.add(worker)
        worker.signals.result.connect(self._on_loaded)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(lambda completed=worker: self._workers.discard(completed))
        QThreadPool.globalInstance().start(worker)

    def _on_loaded(self, data):
        self.data = data
        self.error_message = ""
        self.is_loading = False
        self.state_changed.emit("loaded")
        self.loaded.emit(data)

    def _on_error(self, exc):
        self.error_message = str(exc)
        self.is_loading = False
        self.state_changed.emit("failed")
        self.error.emit(exc)


_REFERENCE_SERVICE = None


def get_trading_reference_service():
    global _REFERENCE_SERVICE
    if _REFERENCE_SERVICE is None:
        _REFERENCE_SERVICE = TradingReferenceService()
    return _REFERENCE_SERVICE
