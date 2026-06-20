def filter_trade_routes(routes, origin="", destination="", commodity=""):
    origin_key = normalize(origin)
    destination_key = normalize(destination)
    commodity_key = normalize(commodity)
    return [
        route
        for route in routes
        if (not origin_key or origin_key in normalize(route.buy_location))
        and (not destination_key or destination_key in normalize(route.sell_location))
        and (not commodity_key or commodity_key in normalize(route.commodity))
    ]


def normalize(value):
    return " ".join(str(value or "").lower().split())
