from dataclasses import dataclass

from PySide6.QtCore import QObject, QThreadPool, Signal

from app.sc_trade_tools_client import (
    fetch_commodity_item_types,
    fetch_commodity_items,
    fetch_commodity_shops,
    fetch_locations,
    fetch_ships,
)

from ..workers import FunctionWorker


@dataclass(frozen=True)
class TradingReferenceData:
    commodities: tuple
    commodity_types: tuple
    locations: tuple
    shops: tuple
    ships: tuple


def load_trading_reference_data():
    locations = tuple(sorted(fetch_locations(), key=lambda item: item.name.lower()))
    shops = tuple(sorted(fetch_commodity_shops(locations), key=lambda item: item.name.lower()))
    commodities = tuple(sorted(fetch_commodity_items(), key=lambda item: item.name.lower()))
    commodity_types = tuple(
        sorted(fetch_commodity_item_types(), key=lambda item: item.display_name.lower())
    )
    ships = tuple(sorted(fetch_ships(), key=lambda item: item.name.lower()))
    return TradingReferenceData(
        commodities=commodities,
        commodity_types=commodity_types,
        locations=locations,
        shops=shops,
        ships=ships,
    )


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
