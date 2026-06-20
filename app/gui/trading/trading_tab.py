from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .best_buyer_tab import BestBuyerTab
from .commodities_tab import CommoditiesTab
from .create_routes_tab import CreateRoutesTab
from .en_route_tab import EnRouteTab
from .reference_data import get_trading_reference_service
from .saved_routes_tab import SavedRoutesTab
from .shops_tab import ShopsTab
from .trade_routes_tab import TradeRoutesTab
from .uex_trading_tab import UEXTradingTab


class TradingTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.reference_service = get_trading_reference_service()

        self.tabs = QTabWidget()
        self.uex_trading_tab = UEXTradingTab(self.reference_service)
        self.tabs.addTab(self.uex_trading_tab, "UEX Trading")
        self.saved_routes_tab = SavedRoutesTab()
        self.tabs.addTab(self.saved_routes_tab, "Saved Routes")
        self.create_routes_tab = CreateRoutesTab(self.reference_service)
        self.tabs.addTab(self.create_routes_tab, "Create Routes")
        self.trade_routes_tab = TradeRoutesTab(self.reference_service)
        self.tabs.addTab(self.trade_routes_tab, "Trade Routes")
        self.best_buyer_tab = BestBuyerTab(self.reference_service)
        self.tabs.addTab(self.best_buyer_tab, "Best Buyer")
        self.en_route_tab = EnRouteTab(self.reference_service)
        self.tabs.addTab(self.en_route_tab, "En Route")
        self.commodities_tab = CommoditiesTab(self.reference_service)
        self.tabs.addTab(self.commodities_tab, "Commodities")
        self.shops_tab = ShopsTab(self.reference_service)
        self.tabs.addTab(self.shops_tab, "Shops")

        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.reference_service.ensure_loaded()

    def on_tab_changed(self, index):
        widget = self.tabs.widget(index)
        if widget is self.saved_routes_tab:
            self.saved_routes_tab.refresh_routes()
