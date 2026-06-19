from dataclasses import dataclass

import requests


SC_CRAFT_TOOLS_BASE_URL = "https://sc-craft.tools"
SC_CRAFT_BLUEPRINTS_API = f"{SC_CRAFT_TOOLS_BASE_URL}/api/blueprints"
SC_CRAFT_TIMEOUT_SECONDS = 20
SC_CRAFT_PAGE_LIMIT = 100
SC_CRAFT_MAX_PAGES = 40


class BlueprintsError(Exception):
    pass


@dataclass(frozen=True)
class BlueprintIngredient:
    slot: str
    name: str
    quantity: float | None
    unit: str
    min_quality: float | None
    quality_effects: tuple[str, ...]


@dataclass(frozen=True)
class BlueprintMission:
    name: str
    drop_chance: str
    mission_id: str = ""
    contractor: str = ""
    reputation_giver: str = ""
    reputation_rank: str = ""
    location: str = ""
    system: str = ""


@dataclass(frozen=True)
class BlueprintRecord:
    key: str
    blueprint_name: str
    crafted_item: str
    category: str
    ownable: bool
    craft_time_seconds: int | None
    ingredients: tuple[BlueprintIngredient, ...]
    missions: tuple[BlueprintMission, ...]
    patch: str
    source: str
    source_url: str
    raw: dict

    @property
    def source_summary(self):
        if not self.missions:
            return "Mission data unavailable"
        first = self.missions[0].name
        if len(self.missions) == 1:
            return first
        return f"{first} + {len(self.missions) - 1} more"

    @property
    def system(self):
        return "N/A"


def fetch_blueprints():
    session = requests.Session()
    session.headers.update({"User-Agent": "SC-Intel-Tool"})

    blueprints = []
    page = 1
    total_pages = None
    while page <= SC_CRAFT_MAX_PAGES:
        payload = fetch_blueprints_page(session, page)
        items = payload.get("items")
        if not isinstance(items, list):
            raise BlueprintsError("Unexpected blueprint response format.")

        blueprints.extend(blueprint_from_record(record) for record in items)
        pagination = payload.get("pagination") if isinstance(payload.get("pagination"), dict) else {}
        total_pages = parse_int(pagination.get("pages")) or total_pages
        if not items or (total_pages is not None and page >= total_pages):
            break
        page += 1

    blueprints.sort(key=lambda item: (item.category.lower(), item.blueprint_name.lower()))
    return blueprints


def fetch_blueprints_page(session, page):
    response = session.get(
        SC_CRAFT_BLUEPRINTS_API,
        params={"page": page, "limit": SC_CRAFT_PAGE_LIMIT},
        timeout=SC_CRAFT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise BlueprintsError("Unexpected blueprint response format.")
    return payload


def blueprint_from_record(record):
    blueprint_name = str(record.get("name") or "Unknown Blueprint")
    key = str(record.get("blueprint_id") or record.get("id") or blueprint_name)
    category = str(record.get("category") or "N/A")
    patch = str(record.get("version") or "N/A")
    return BlueprintRecord(
        key=key,
        blueprint_name=blueprint_name,
        crafted_item=blueprint_name,
        category=category,
        ownable=True,
        craft_time_seconds=parse_int(record.get("craft_time_seconds")),
        ingredients=tuple(parse_ingredient(item) for item in record.get("ingredients") or ()),
        missions=tuple(parse_mission(item) for item in record.get("missions") or ()),
        patch=patch,
        source="SC Craft Tools",
        source_url=SC_CRAFT_TOOLS_BASE_URL,
        raw=record if isinstance(record, dict) else {},
    )


def parse_ingredient(record):
    options = record.get("options") if isinstance(record.get("options"), list) else []
    first_option = options[0] if options and isinstance(options[0], dict) else {}
    return BlueprintIngredient(
        slot=str(record.get("slot") or "Material"),
        name=str(record.get("name") or first_option.get("name") or "Unknown"),
        quantity=parse_float(record.get("quantity_scu") or first_option.get("quantity_scu")),
        unit=str(first_option.get("unit") or "scu"),
        min_quality=parse_float(first_option.get("min_quality")),
        quality_effects=tuple(parse_quality_effect(effect) for effect in record.get("quality_effects") or ()),
    )


def parse_quality_effect(record):
    stat = str(record.get("stat") or "Quality")
    effect_type = str(record.get("type") or "")
    min_value = record.get("modifier_at_min")
    max_value = record.get("modifier_at_max")
    if min_value is None and max_value is None:
        return stat
    if effect_type == "multiplicative":
        effect_type = "multiplier"
    return f"{stat}: {min_value} -> {max_value} {effect_type}".strip()


def parse_mission(record):
    record = record if isinstance(record, dict) else {}
    return BlueprintMission(
        name=str(first_text(record, "name", "title", "mission_name", "missionName") or "Unknown mission"),
        drop_chance=str(first_text(record, "drop_chance", "dropChance") or ""),
        mission_id=str(first_text(record, "mission_id", "missionId", "id") or ""),
        contractor=str(first_text(
            record,
            "contractor",
            "contractor_name",
            "contractorName",
            "mission_giver",
            "missionGiver",
            "giver",
        ) or ""),
        reputation_giver=str(first_text(
            record,
            "reputation_giver",
            "reputationGiver",
            "reputation",
            "reputation_name",
            "reputationName",
            "faction",
        ) or ""),
        reputation_rank=str(first_text(
            record,
            "required_reputation_rank",
            "requiredReputationRank",
            "reputation_rank",
            "reputationRank",
            "rank",
            "rank_name",
            "rankName",
        ) or ""),
        location=str(first_text(
            record,
            "location",
            "location_name",
            "locationName",
            "mission_location",
            "missionLocation",
        ) or ""),
        system=str(first_text(record, "system", "star_system", "starSystem", "system_name", "systemName") or ""),
    )


def first_text(record, *keys):
    for key in keys:
        value = text_from_record_value(record.get(key))
        if value:
            return value
    return ""


def text_from_record_value(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("name", "display_name", "displayName", "label", "title"):
            nested = text_from_record_value(value.get(key))
            if nested:
                return nested
        return ""
    if isinstance(value, (list, tuple)):
        parts = [text_from_record_value(item) for item in value]
        return ", ".join(part for part in parts if part)
    text = str(value).strip()
    return text


def parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False
