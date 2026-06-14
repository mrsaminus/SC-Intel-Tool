__all__ = [
    "BestBuyerTab",
    "CommoditiesTab",
    "CreateRoutesTab",
    "EnRouteTab",
    "SavedRoutesTab",
    "ShopsTab",
    "TradeRoutesTab",
    "TradingTab",
    "UEXTradingTab",
]


def __getattr__(name):
    if name == "BestBuyerTab":
        from .best_buyer_tab import BestBuyerTab

        return BestBuyerTab
    if name == "CommoditiesTab":
        from .commodities_tab import CommoditiesTab

        return CommoditiesTab
    if name == "CreateRoutesTab":
        from .create_routes_tab import CreateRoutesTab

        return CreateRoutesTab
    if name == "EnRouteTab":
        from .en_route_tab import EnRouteTab

        return EnRouteTab
    if name == "SavedRoutesTab":
        from .saved_routes_tab import SavedRoutesTab

        return SavedRoutesTab
    if name == "ShopsTab":
        from .shops_tab import ShopsTab

        return ShopsTab
    if name == "TradeRoutesTab":
        from .trade_routes_tab import TradeRoutesTab

        return TradeRoutesTab
    if name == "TradingTab":
        from .trading_tab import TradingTab

        return TradingTab
    if name == "UEXTradingTab":
        from .uex_trading_tab import UEXTradingTab

        return UEXTradingTab

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
