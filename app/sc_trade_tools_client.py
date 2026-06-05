from dataclasses import dataclass
from urllib.parse import quote

import requests


SC_TRADE_TOOLS_API_BASE = "https://sc-trade.tools/api"
SC_TRADE_TOOLS_TIMEOUT_SECONDS = 20
SC_TRADE_TOOLS_TOKEN_SETTING = "sc_trade_tools_api_token"


class SCTradeToolsError(Exception):
    pass


@dataclass(frozen=True)
class SCTradeCommodity:
    name: str
    raw: dict


@dataclass(frozen=True)
class SCTradeCommodityType:
    name: str
    display_name: str
    parent: str
    raw: dict


@dataclass(frozen=True)
class SCTradeLocation:
    name: str
    location_type: str
    raw: dict


@dataclass(frozen=True)
class SCTradeShop:
    name: str
    display_name: str
    system: str
    location: str
    category: str
    hierarchy: str
    raw: dict


@dataclass(frozen=True)
class SCTradeTransaction:
    location: str
    shop: str
    action: str
    item_name: str
    price: float | None
    quantity_scu: float | None
    max_quantity_scu: float | None
    security_level: str
    faction: str
    hidden: bool
    raw: dict


@dataclass(frozen=True)
class SCTradeRoute:
    origin: str
    destination: str
    commodity: str
    profit: float | None
    profit_per_minute: float | None
    time_seconds: float | None
    raw: dict


def fetch_commodities_reference():
    return fetch_commodity_items(), fetch_commodity_item_types()


def fetch_commodity_items():
    payload = get_json("/commodity/items")
    return [
        SCTradeCommodity(
            name=str(record.get("name") or "Unknown"),
            raw=record,
        )
        for record in extract_records(payload)
    ]


def fetch_commodity_item_types():
    payload = get_json("/commodity/item-types")
    return [
        SCTradeCommodityType(
            name=str(record.get("name") or "Unknown"),
            display_name=str(record.get("displayName") or record.get("name") or "Unknown"),
            parent=str(record.get("parent") or "N/A"),
            raw=record,
        )
        for record in extract_records(payload)
    ]


def fetch_locations():
    payload = get_json("/locations")
    return [
        SCTradeLocation(
            name=str(record.get("name") or "Unknown"),
            location_type=str(record.get("type") or "N/A"),
            raw=record,
        )
        for record in extract_records(payload)
    ]


def fetch_commodity_shops(locations=None):
    payload = get_json("/commodity/shops")
    if locations is None:
        locations = fetch_locations()
    locations_by_name = {location.name: location for location in locations}
    shops = []
    for record in extract_records(payload):
        name = str(record.get("name") or "Unknown")
        parts = split_location_path(name)
        location_match = locations_by_name.get(name)
        shops.append(
            SCTradeShop(
                name=name,
                display_name=parts[-1] if parts else name,
                system=parts[0] if parts else "N/A",
                location=parts[-2] if len(parts) > 1 else "N/A",
                category=location_match.location_type if location_match else str(record.get("type") or "N/A"),
                hierarchy=" > ".join(parts[:-1]) if len(parts) > 1 else "N/A",
                raw=record,
            )
        )
    return shops


def fetch_shops_reference():
    locations = fetch_locations()
    return fetch_commodity_shops(locations), locations


def test_token_connection(token):
    token = normalize_token(token)
    if not token:
        return False

    # Token-required endpoint. Agricium is stable enough as a lightweight probe.
    get_json(f"/commodity/items/{quote('Agricium', safe='')}/transactions", token=token)
    return True


def fetch_best_buyers(token, commodity_name, quantity_scu=1):
    token = require_token(token)
    commodity_name = (commodity_name or "").strip()
    if not commodity_name:
        raise SCTradeToolsError("Commodity is required.")

    payload = post_json(
        "/tools/buyers",
        build_buyer_request(commodity_name, parse_float(quantity_scu, 1)),
        token=token,
    )
    return [transaction_from_record(record) for record in extract_records(payload)]


def fetch_en_route(
    token,
    origin,
    destination,
    commodity_name="",
    ship="Freelancer",
    investment=100000,
    allowable_detour=25,
):
    token = require_token(token)
    origin = (origin or "").strip()
    destination = (destination or "").strip()
    if not origin or not destination:
        raise SCTradeToolsError("Start location and destination are required.")

    payload = post_json(
        "/tools/itinerary",
        build_itinerary_request(
            origin=origin,
            destination=destination,
            commodity_name=commodity_name,
            ship=ship,
            investment=parse_float(investment, 100000),
            allowable_detour=parse_float(allowable_detour, 25),
        ),
        token=token,
    )
    return [route_from_record(record) for record in extract_records(payload)]


def get_json(path, token=None, params=None):
    return request_json("GET", path, token=token, params=params)


def post_json(path, json_body, token=None):
    return request_json("POST", path, token=token, json_body=json_body)


def request_json(method, path, token=None, params=None, json_body=None):
    headers = {}
    token = normalize_token(token)
    if token:
        headers["token"] = token

    try:
        response = requests.request(
            method,
            f"{SC_TRADE_TOOLS_API_BASE}{path}",
            headers=headers,
            params=params,
            json=json_body,
            timeout=SC_TRADE_TOOLS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SCTradeToolsError(format_request_error(exc)) from exc

    try:
        return response.json()
    except ValueError as exc:
        raise SCTradeToolsError("Unexpected SC Trade Tools response format.") from exc


def extract_records(payload):
    if isinstance(payload, list):
        return [record for record in payload if isinstance(record, dict)]

    if isinstance(payload, dict) and isinstance(payload.get("content"), list):
        return [record for record in payload["content"] if isinstance(record, dict)]

    raise SCTradeToolsError("Unexpected SC Trade Tools response format.")


def normalize_token(token):
    return (token or "").strip()


def require_token(token):
    token = normalize_token(token)
    if not token:
        raise SCTradeToolsError("SC Trade Tools token is not configured.")
    return token


def format_request_error(exc):
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            detail = response.text.strip()
        except ValueError:
            detail = ""
        if detail:
            return f"{response.status_code} {response.reason}: {detail}"
        return f"{response.status_code} {response.reason}"
    return str(exc)


def split_location_path(value):
    return [part.strip() for part in str(value or "").split(">") if part.strip()]


def build_buyer_request(commodity_name, quantity_scu):
    return {
        "commodityName": commodity_name,
        "commodityQuantityInScu": parse_int(quantity_scu, default=1, minimum=1),
        "isCargoStolen": False,
        "locationNames": [],
        "locationNamesType": "blacklist",
        "locationTypes": [],
        "locationTypesType": "blacklist",
        "factionNames": [],
        "factionsNamesType": "blacklist",
        "minSecurityLevel": 0,
        "supportedBoxSizeInScu": 1,
        "avoidHiddenLocations": True,
        "allowWaitTimes": False,
        "minInventorySizeInScu": 0,
    }


def build_itinerary_request(origin, destination, commodity_name, ship, investment, allowable_detour):
    commodity_name = (commodity_name or "").strip()
    commodity_names = [commodity_name] if commodity_name else []
    commodity_filter_type = "whitelist" if commodity_name else "blacklist"
    return {
        "origin": origin,
        "destination": destination,
        "allowableDetour": parse_int(allowable_detour, default=25, minimum=0, maximum=100),
        "locationNames": [],
        "locationNamesType": "blacklist",
        "locationTypes": [],
        "locationTypesType": "blacklist",
        "factionNames": [],
        "factionsNamesType": "blacklist",
        "minSecurityLevel": 0,
        "supportedBoxSizeInScu": 1,
        "avoidHiddenLocations": True,
        "commodityNames": commodity_names,
        "commodityNamesType": commodity_filter_type,
        "commodityTypes": [],
        "commodityTypesType": "blacklist",
        "maxVolume": 1,
        "investment": parse_int(investment, default=100000, minimum=1, maximum=100000000),
        "profitType": "pure",
        "ship": (ship or "Freelancer").strip() or "Freelancer",
        "maxStops": 3,
        "allowWaitTimes": False,
        "useAutoLoading": False,
        "smartFilters": False,
        "minInventorySizeInScu": 0,
    }


def transaction_from_record(record):
    return SCTradeTransaction(
        location=str(record.get("location") or "N/A"),
        shop=str(record.get("shop") or record.get("locationAndShop") or "N/A"),
        action=str(record.get("action") or "N/A"),
        item_name=str(record.get("itemName") or "N/A"),
        price=parse_optional_float(record.get("price")),
        quantity_scu=parse_optional_float(record.get("quantityInScu")),
        max_quantity_scu=parse_optional_float(record.get("maxQuantityInScu")),
        security_level=str(record.get("securityLevel") or "N/A"),
        faction=str(record.get("faction") or "N/A"),
        hidden=bool(record.get("isHidden")),
        raw=record,
    )


def route_from_record(record):
    commodity = extract_route_commodity(record)
    return SCTradeRoute(
        origin=format_transaction_location(record.get("origin")),
        destination=format_transaction_location(record.get("destination")),
        commodity=commodity,
        profit=parse_optional_float(record.get("profit")),
        profit_per_minute=parse_optional_float(record.get("profitPerMinute")),
        time_seconds=parse_optional_float(record.get("timeInSeconds")),
        raw=record,
    )


def extract_route_commodity(record):
    for key in ("commodity", "commodityName", "itemName"):
        if record.get(key):
            return str(record[key])

    for side in ("origin", "destination"):
        transaction = record.get(side)
        if isinstance(transaction, dict):
            item_name = transaction.get("itemName")
            if item_name:
                return str(item_name)

    for key in ("transactions", "steps", "edges"):
        value = record.get(key)
        if isinstance(value, list):
            names = []
            for item in value:
                if isinstance(item, dict):
                    name = item.get("itemName") or item.get("commodityName") or item.get("commodity")
                    if name and str(name) not in names:
                        names.append(str(name))
            if names:
                return ", ".join(names[:3])

    return "N/A"


def format_transaction_location(transaction):
    if isinstance(transaction, dict):
        location_and_shop = transaction.get("locationAndShop")
        if location_and_shop:
            return str(location_and_shop)

        location = str(transaction.get("location") or "").strip()
        shop = str(transaction.get("shop") or "").strip()
        if location and shop:
            return f"{location} > {shop}"
        if location:
            return location
        if shop:
            return shop

    if transaction:
        return str(transaction)
    return "N/A"


def parse_float(value, default=0):
    result = parse_optional_float(value)
    return default if result is None else result


def parse_int(value, default=0, minimum=None, maximum=None):
    number = parse_optional_float(value)
    if number is None:
        number = default
    number = int(number)
    if minimum is not None:
        number = max(number, minimum)
    if maximum is not None:
        number = min(number, maximum)
    return number


def parse_optional_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
