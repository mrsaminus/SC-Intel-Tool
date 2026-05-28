from dataclasses import dataclass

import requests


UEX_API_BASE = "https://api.uexcorp.uk/2.0"
UEX_TIMEOUT_SECONDS = 15


class UEXError(Exception):
    pass


@dataclass(frozen=True)
class UEXCommodityPrice:
    commodity_name: str
    price_sell: float | None
    terminal_name: str
    star_system_name: str
    location_name: str
    date_modified: int | None


def fetch_commodity_sell_prices(commodity_name):
    response = requests.get(
        f"{UEX_API_BASE}/commodities_prices",
        params={"commodity_name": commodity_name},
        timeout=UEX_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()
    records = extract_records(payload)
    prices = [
        normalize_price_record(record)
        for record in records
        if record.get("price_sell") not in (None, "", 0)
    ]

    prices.sort(
        key=lambda price: (
            -(price.price_sell or 0),
            price.terminal_name.lower(),
        )
    )
    return prices


def extract_records(payload):
    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        raise UEXError("Unexpected UEX response format.")

    for key in ("data", "results", "result"):
        value = payload.get(key)
        if isinstance(value, list):
            return value

    if all(key in payload for key in ("commodity_name", "terminal_name")):
        return [payload]

    status = payload.get("status")
    message = payload.get("message") or payload.get("error")
    if status and status != "ok":
        raise UEXError(str(message or status))

    return []


def normalize_price_record(record):
    return UEXCommodityPrice(
        commodity_name=str(record.get("commodity_name") or "Unknown"),
        price_sell=parse_number(record.get("price_sell")),
        terminal_name=str(record.get("terminal_name") or "N/A"),
        star_system_name=str(record.get("star_system_name") or "N/A"),
        location_name=best_location_name(record),
        date_modified=parse_int(record.get("date_modified")),
    )


def best_location_name(record):
    for key in (
        "outpost_name",
        "city_name",
        "space_station_name",
        "moon_name",
        "planet_name",
        "orbit_name",
    ):
        value = record.get(key)
        if value:
            return str(value)

    return "N/A"


def parse_number(value):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_int(value):
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None
