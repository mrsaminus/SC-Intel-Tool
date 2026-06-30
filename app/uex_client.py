import logging
from dataclasses import dataclass

import requests


UEX_API_BASE = "https://api.uexcorp.uk/2.0"
UEX_TIMEOUT_SECONDS = 15
logger = logging.getLogger(__name__)


class UEXError(Exception):
    pass


@dataclass(frozen=True)
class UEXCommodityPrice:
    commodity_name: str
    price_buy: float | None
    price_sell: float | None
    terminal_name: str
    star_system_name: str
    location_name: str
    date_modified: int | None


@dataclass(frozen=True)
class UEXPriceSnapshot:
    prices: tuple[UEXCommodityPrice, ...]
    cache_status: str
    source_error: str = ""
    last_updated: str = ""
    from_cache: bool = False


def fetch_commodity_sell_prices(commodity_name):
    try:
        response = requests.get(
            f"{UEX_API_BASE}/commodities_prices",
            params={"commodity_name": commodity_name},
            timeout=UEX_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("UEX commodity sell price request failed for %s: %s", commodity_name, exc)
        raise

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


def fetch_all_commodity_prices():
    try:
        response = requests.get(
            f"{UEX_API_BASE}/commodities_prices_all",
            timeout=UEX_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("UEX all commodity prices request failed: %s", exc)
        raise

    payload = response.json()
    return [
        normalize_price_record(record)
        for record in extract_records(payload)
    ]


def load_all_commodity_prices(force_refresh=False):
    from app.local_cache import (
        UEX_PRICES_CACHE_KEY,
        UEX_PRICES_SCHEMA_VERSION,
        cache_status,
        load_uex_prices_cache,
        mark_cache_error,
        save_uex_prices_cache,
    )

    if not force_refresh:
        cached_prices, metadata = load_uex_prices_cache()
        if cached_prices:
            return UEXPriceSnapshot(
                prices=tuple(cached_prices),
                cache_status=cache_status(UEX_PRICES_CACHE_KEY),
                source_error=metadata.error_message if metadata else "",
                last_updated=metadata.last_updated if metadata else "",
                from_cache=True,
            )

    try:
        prices = tuple(fetch_all_commodity_prices())
    except Exception as exc:
        cached_prices, metadata = load_uex_prices_cache()
        if cached_prices:
            mark_cache_error(
                UEX_PRICES_CACHE_KEY,
                "UEX public market prices",
                UEX_PRICES_SCHEMA_VERSION,
                str(exc),
            )
            return UEXPriceSnapshot(
                prices=tuple(cached_prices),
                cache_status="offline",
                source_error=str(exc),
                last_updated=metadata.last_updated if metadata else "",
                from_cache=True,
            )

        mark_cache_error(
            UEX_PRICES_CACHE_KEY,
            "UEX public market prices",
            UEX_PRICES_SCHEMA_VERSION,
            str(exc),
        )
        raise

    save_uex_prices_cache(prices)
    metadata = load_uex_prices_cache()[1]
    return UEXPriceSnapshot(
        prices=prices,
        cache_status="fresh",
        source_error="",
        last_updated=metadata.last_updated if metadata else "",
        from_cache=False,
    )


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
        price_buy=parse_number(record.get("price_buy")),
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
