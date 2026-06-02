import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from app.display_format import format_grouped_numbers


SCFOCUS_SHIPS_URL = "https://scfocus.org/ship-sale-rental-locations-history/"
SCFOCUS_TIMEOUT_SECONDS = 15
WIKELO_CATEGORY = "Wikelo"
SPECIAL_ACQUISITION_CATEGORY = "Special Acquisition Ships"
SPECIAL_ACQUISITION_CATEGORIES = {WIKELO_CATEGORY, SPECIAL_ACQUISITION_CATEGORY}


@dataclass(frozen=True)
class SCFocusShipLocation:
    location: str
    price: str
    verified: str
    url: str


@dataclass(frozen=True)
class SCFocusShipItem:
    item_id: str
    name: str
    category: str
    size: str
    sold: bool
    detail_url: str
    category_url: str
    effect: str
    source: str
    item_type: str
    availability: str
    locations: tuple[SCFocusShipLocation, ...]


def fetch_scfocus_ship_items():
    response = requests.get(
        SCFOCUS_SHIPS_URL,
        timeout=SCFOCUS_TIMEOUT_SECONDS,
        headers={"User-Agent": "SC-Intel-Tool"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    page_updated = extract_page_updated(soup)
    groups = {}

    for table in soup.find_all("table"):
        heading = table.find_previous(["h2", "h3", "h4"])
        heading_text = heading.get_text(" ", strip=True) if heading else ""
        category = classify_ship_table(table, heading_text)
        if not category:
            continue

        for row in table.find_all("tr"):
            cells = [
                cell.get_text(" ", strip=True)
                for cell in row.find_all(["th", "td"])
            ]
            parsed = parse_ship_row(cells, category, heading_text, page_updated)
            if not parsed:
                continue

            for ship_name, location, parsed_category in parsed:
                key = (parsed_category, ship_name.lower())
                group = groups.setdefault(key, {
                    "name": ship_name,
                    "category": parsed_category,
                    "locations": [],
                })
                group["locations"].append(location)

    items = []
    for group in groups.values():
        locations = tuple(group["locations"])
        name = group["name"]
        category = group["category"]
        items.append(SCFocusShipItem(
            item_id=f"{category}:{name}".lower(),
            name=name,
            category=category,
            size="Ship",
            sold=category not in SPECIAL_ACQUISITION_CATEGORIES,
            detail_url=SCFOCUS_SHIPS_URL,
            category_url=SCFOCUS_SHIPS_URL,
            effect=summarize_ship_locations(category, locations),
            source="SC Focus",
            item_type="Ship",
            availability=f"{len(locations)} location{'s' if len(locations) != 1 else ''}",
            locations=locations,
        ))

    items.sort(key=lambda item: (item.category, item.name.lower()))
    return items


def classify_ship_table(table, heading_text):
    header_text = " ".join(
        cell.get_text(" ", strip=True)
        for cell in table.find_all(["th", "td"])[:4]
    ).lower()
    heading_lower = heading_text.lower()

    if "rental" in header_text or "rental" in heading_lower:
        return "Ships for Rent"
    if "wikelo" in heading_lower:
        return WIKELO_CATEGORY
    if "executive hangar" in heading_lower or "earn" in header_text:
        return SPECIAL_ACQUISITION_CATEGORY
    if "sale location" in header_text or "showroom" in heading_lower or "ship shop" in heading_lower:
        return "Ships for Sale"

    return ""


def parse_ship_row(cells, category, heading_text, page_updated):
    if not cells:
        return None

    first = normalize_ship_name(cells[0])
    if not first or first.lower() == "ship":
        return None

    if category in SPECIAL_ACQUISITION_CATEGORIES:
        if len(cells) < 2:
            return None
        locations = []
        for location_text in special_acquisition_locations(cells[1:]):
            price = special_acquisition_method(heading_text, location_text)
            parsed_category = WIKELO_CATEGORY if price == WIKELO_CATEGORY else category
            locations.append((
                first,
                SCFocusShipLocation(
                    location=location_text,
                    price=price,
                    verified=page_updated,
                    url=SCFOCUS_SHIPS_URL,
                ),
                parsed_category,
            ))

        return locations
    else:
        if len(cells) < 3:
            return None
        price = normalize_price(cells[1])
        location_text = cells[2] or heading_text

    if not location_text:
        return None

    return [(first, SCFocusShipLocation(
        location=location_text,
        price=price,
        verified=page_updated,
        url=SCFOCUS_SHIPS_URL,
    ), category)]


def special_acquisition_locations(values):
    locations = []
    for value in values:
        text = re.sub(r"\s+", " ", value or "").strip(" -")
        if not text or text.lower() in {"location", "locations", "ship", "n/a", "na", "none", "-"}:
            continue
        locations.append(text)

    return locations


def summarize_ship_locations(category, locations):
    if category == WIKELO_CATEGORY:
        return f"Wikelo | {len(locations)} location{'s' if len(locations) != 1 else ''}"

    if category == SPECIAL_ACQUISITION_CATEGORY:
        return f"Special acquisition | {len(locations)} location{'s' if len(locations) != 1 else ''}"

    numeric_prices = [
        parse_price_number(location.price)
        for location in locations
    ]
    numeric_prices = [
        price
        for price in numeric_prices
        if price is not None
    ]
    if numeric_prices:
        return f"Lowest {min(numeric_prices):,} aUEC | {len(locations)} location{'s' if len(locations) != 1 else ''}"

    return f"{category.replace('Ships for ', '')} | {len(locations)} location{'s' if len(locations) != 1 else ''}"


def extract_page_updated(soup):
    text = soup.get_text("\n", strip=True)
    match = re.search(r"Page last updated:\s*([^\n]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return "SC Focus"


def normalize_ship_name(value):
    return re.sub(r"\s+", " ", value or "").strip(" -")


def special_acquisition_method(heading_text, location_text):
    text = f"{heading_text} {location_text}".lower()
    if "wikelo" in text:
        return WIKELO_CATEGORY
    if "executive hangar" in text:
        return "Executive Hangar"
    return "No aUEC price"


def normalize_price(value):
    price = re.sub(r"\s+", " ", value or "").strip()
    return format_grouped_numbers(price) or "N/A"


def parse_price_number(value):
    first_number = re.search(r"[\d,]+", value or "")
    if not first_number:
        return None

    try:
        return int(first_number.group(0).replace(",", "").replace(" ", ""))
    except ValueError:
        return None
