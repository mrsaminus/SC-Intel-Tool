from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .best_buyer_tab import BestBuyerTab
from .commodities_tab import CommoditiesTab
from .en_route_tab import EnRouteTab
from .sc_trade_placeholder_tab import SCTradePlaceholderTab
from .shared import SC_TRADE_WORKFLOWS
from .shops_tab import ShopsTab
from .trade_routes_tab import TradeRoutesTab
from .uex_trading_tab import UEXTradingTab


class TradingTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.uex_trading_tab = UEXTradingTab()
        self.tabs.addTab(self.uex_trading_tab, "UEX Trading")

        self.sc_trade_tabs = {}
        for workflow in SC_TRADE_WORKFLOWS:
            if workflow["title"] == "Trade Routes":
                tab = TradeRoutesTab()
            elif workflow["title"] == "Commodities":
                tab = CommoditiesTab()
            elif workflow["title"] == "Shops":
                tab = ShopsTab()
            elif workflow["title"] == "Best Buyer":
                tab = BestBuyerTab()
            elif workflow["title"] == "En Route":
                tab = EnRouteTab()
            else:
                tab = SCTradePlaceholderTab(
                    workflow["title"],
                    workflow["purpose"],
                    workflow["url"],
                )
            self.sc_trade_tabs[workflow["title"]] = tab
            self.tabs.addTab(tab, workflow["title"])

        layout.addWidget(self.tabs)
        self.setLayout(layout)
