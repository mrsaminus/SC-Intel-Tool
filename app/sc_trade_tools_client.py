from dataclasses import dataclass

import requests


SC_TRADE_TOOLS_API_BASE = "https://sc-trade.tools/api"
SC_TRADE_TOOLS_TIMEOUT_SECONDS = 20


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


def get_json(path):
    try:
        response = requests.get(
            f"{SC_TRADE_TOOLS_API_BASE}{path}",
            timeout=SC_TRADE_TOOLS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SCTradeToolsError(str(exc)) from exc

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
