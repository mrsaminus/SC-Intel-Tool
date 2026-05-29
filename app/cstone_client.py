import html
import re
from dataclasses import dataclass

import requests

from app.display_format import format_grouped_numbers


CSTONE_HOME_URL = "https://finder.cstone.space"
CSTONE_TIMEOUT_SECONDS = 15

CSTONE_CATEGORIES = [
    {"label": "Armor - Helmets", "list_path": "/GetArmors/Helmets", "detail_path": "/FPSArmors1", "category_url": f"{CSTONE_HOME_URL}/FPSArmors?type=Helmets"},
    {"label": "Armor - Arms", "list_path": "/GetArmors/Arms", "detail_path": "/FPSArmors1", "category_url": f"{CSTONE_HOME_URL}/FPSArmors?type=Arms"},
    {"label": "Armor - Torsos", "list_path": "/GetArmors/Torsos", "detail_path": "/FPSArmors1", "category_url": f"{CSTONE_HOME_URL}/FPSArmors?type=Torsos"},
    {"label": "Armor - Backpacks", "list_path": "/GetArmors/Backpacks", "detail_path": "/FPSArmors1", "category_url": f"{CSTONE_HOME_URL}/FPSArmors?type=Backpacks"},
    {"label": "Armor - Legs", "list_path": "/GetArmors/Legs", "detail_path": "/FPSArmors1", "category_url": f"{CSTONE_HOME_URL}/FPSArmors?type=Legs"},
    {"label": "Armor - Undersuits", "list_path": "/GetArmors/Undersuits", "detail_path": "/FPSArmors1", "category_url": f"{CSTONE_HOME_URL}/FPSArmors?type=Undersuits"},
    {"label": "Clothing - Hats", "list_path": "/GetClothes/Hat", "detail_path": "/FPSClothes1", "category_url": f"{CSTONE_HOME_URL}/FPSClothes?type=Hat"},
    {"label": "Clothing - Eyewear", "list_path": "/GetClothes/Eyes", "detail_path": "/FPSClothes1", "category_url": f"{CSTONE_HOME_URL}/FPSClothes?type=Eyes"},
    {"label": "Clothing - Gloves", "list_path": "/GetClothes/Hands", "detail_path": "/FPSClothes1", "category_url": f"{CSTONE_HOME_URL}/FPSClothes?type=Hands"},
    {"label": "Clothing - Jackets", "list_path": "/GetClothes/Jacket", "detail_path": "/FPSClothes1", "category_url": f"{CSTONE_HOME_URL}/FPSClothes?type=Jacket"},
    {"label": "Clothing - Shirts", "list_path": "/GetClothes/Shirt", "detail_path": "/FPSClothes1", "category_url": f"{CSTONE_HOME_URL}/FPSClothes?type=Shirt"},
    {"label": "Clothing - Jumpsuits", "list_path": "/GetClothes/Jumpsuit", "detail_path": "/FPSClothes1", "category_url": f"{CSTONE_HOME_URL}/FPSClothes?type=Jumpsuit"},
    {"label": "Clothing - Legwear", "list_path": "/GetClothes/Legs", "detail_path": "/FPSClothes1", "category_url": f"{CSTONE_HOME_URL}/FPSClothes?type=Legs"},
    {"label": "Clothing - Footwear", "list_path": "/GetClothes/Feet", "detail_path": "/FPSClothes1", "category_url": f"{CSTONE_HOME_URL}/FPSClothes?type=Feet"},
    {"label": "Food", "list_path": "/GetFoods", "detail_path": "/Food1", "category_url": f"{CSTONE_HOME_URL}/Food"},
    {"label": "Drinks", "list_path": "/GetDrinks", "detail_path": "/Drinks1", "category_url": f"{CSTONE_HOME_URL}/Drinks"},
    {"label": "Medical Pens", "list_path": "/GetGadgets", "detail_path": "/Gadgets1", "category_url": f"{CSTONE_HOME_URL}/Gadgets"},
    {"label": "Hacking Chips", "list_path": "/GetHChips", "detail_path": "/HackingChips1", "category_url": f"{CSTONE_HOME_URL}/HackingChips"},
    {"label": "Flares", "list_path": "/GetFPSFlares", "detail_path": "/FPSFlares1", "category_url": f"{CSTONE_HOME_URL}/FPSFlares"},
    {"label": "Tools", "list_path": "/GetFPSTools", "detail_path": "/FPSTools1", "category_url": f"{CSTONE_HOME_URL}/FPSTools"},
    {"label": "Tool Attachments", "list_path": "/GetFPSToolAttachments", "detail_path": "/FPSToolAttachments1", "category_url": f"{CSTONE_HOME_URL}/FPSToolAttachments"},
    {"label": "MobiGlas", "list_path": "/GetmobiGlass", "detail_path": "/mobiGlass1", "category_url": f"{CSTONE_HOME_URL}/mobiGlass"},
    {"label": "FPS Weapons - Melee", "list_path": "/GetFPSWeaponMelee", "detail_path": "/FPSWeaponMelee1", "category_url": f"{CSTONE_HOME_URL}/FPSWeaponMelee"},
    {"label": "FPS Weapons - Thrown", "list_path": "/GetFPSWeaponThrown", "detail_path": "/FPSWeaponThrown1", "category_url": f"{CSTONE_HOME_URL}/FPSWeaponThrown"},
    {"label": "FPS Weapons - Ranged", "list_path": "/GetFPSWeapons", "detail_path": "/FPSWeapons1", "category_url": f"{CSTONE_HOME_URL}/FPSWeapons"},
    {"label": "FPS Magazines", "list_path": "/GetFPSMags", "detail_path": "/FPSMags1", "category_url": f"{CSTONE_HOME_URL}/FPSMags"},
    {"label": "FPS Attachments", "list_path": "/GetFPSAttachments", "detail_path": "/FPSAttachments1", "category_url": f"{CSTONE_HOME_URL}/FPSAttachments"},
    {"label": "Ship Weapons", "list_path": "/GetSWeapons", "detail_path": "/ShipWeapons1", "category_url": f"{CSTONE_HOME_URL}/ShipWeapons"},
    {"label": "Ship Turrets", "list_path": "/GetSTurrets", "detail_path": "/ShipTurrets1", "category_url": f"{CSTONE_HOME_URL}/ShipTurrets"},
    {"label": "Ship Bombs", "list_path": "/GetShipBombs", "detail_path": "/ShipBombs1", "category_url": f"{CSTONE_HOME_URL}/ShipBombs"},
    {"label": "Ship Bomb Launchers", "list_path": "/GetShipBombLaunchers", "detail_path": "/ShipBombLaunchers1", "category_url": f"{CSTONE_HOME_URL}/ShipBombLaunchers"},
    {"label": "Ship Missiles", "list_path": "/GetMissiles", "detail_path": "/ShipMissiles1", "category_url": f"{CSTONE_HOME_URL}/ShipMissiles"},
    {"label": "Ship Missile Racks", "list_path": "/GetMRacks", "detail_path": "/ShipMissileRacks1", "category_url": f"{CSTONE_HOME_URL}/ShipMissileRacks"},
    {"label": "Ship Coolers", "list_path": "/GetCoolers", "detail_path": "/ShipCoolers1", "category_url": f"{CSTONE_HOME_URL}/ShipCoolers"},
    {"label": "Ship Flight Blades", "list_path": "/GetShipFlightBlades", "detail_path": "/ShipFlightBlades1", "category_url": f"{CSTONE_HOME_URL}/ShipFlightBlades"},
    {"label": "Jump Drives", "list_path": "/GetJumpDrives", "detail_path": "/JumpDrives1", "category_url": f"{CSTONE_HOME_URL}/JumpDrives"},
    {"label": "Life Support", "list_path": "/GetLifeSupportGenerators", "detail_path": "/LifeSupportGenerators1", "category_url": f"{CSTONE_HOME_URL}/LifeSupportGenerators"},
    {"label": "Ship Power Plants", "list_path": "/GetPowers", "detail_path": "/ShipPowerPlants1", "category_url": f"{CSTONE_HOME_URL}/ShipPowerPlants"},
    {"label": "Ship Quantum Drives", "list_path": "/GetDrives", "detail_path": "/ShipQuantumDrives1", "category_url": f"{CSTONE_HOME_URL}/ShipQuantumDrives"},
    {"label": "Ship Radars", "list_path": "/GetRadars", "detail_path": "/Radars1", "category_url": f"{CSTONE_HOME_URL}/Radars"},
    {"label": "Ship Shields", "list_path": "/GetShields", "detail_path": "/ShipShields1", "category_url": f"{CSTONE_HOME_URL}/ShipShields"},
    {
        "label": "Mining Heads",
        "list_path": "/GetSMinings",
        "detail_path": "/ShipMiningHeads1",
        "category_url": f"{CSTONE_HOME_URL}/ShipMiningHeads",
    },
    {
        "label": "Ship Modifiers",
        "list_path": "/GetSMMods",
        "detail_path": "/ShipMiningMods1",
        "category_url": f"{CSTONE_HOME_URL}/ShipMiningMods",
    },
    {
        "label": "Handheld Modifiers",
        "list_path": "/GetFPSMMods",
        "detail_path": "/FPSMiningMods1",
        "category_url": f"{CSTONE_HOME_URL}/FPSMiningMods",
    },
    {"label": "Fuel Nozzles", "list_path": "/GetFuelNozzles", "detail_path": "/FuelNozzles1", "category_url": f"{CSTONE_HOME_URL}/FuelNozzles"},
    {"label": "Fuel Pods", "list_path": "/GetFuelPods", "detail_path": "/FuelPods1", "category_url": f"{CSTONE_HOME_URL}/FuelPods"},
    {"label": "Salvage Heads", "list_path": "/GetShipSalvageHeads", "detail_path": "/ShipSalvageHeads1", "category_url": f"{CSTONE_HOME_URL}/ShipSalvageHeads"},
    {"label": "Salvage Modifiers", "list_path": "/GetShipSalvageMods", "detail_path": "/ShipSalvageMods1", "category_url": f"{CSTONE_HOME_URL}/ShipSalvageMods"},
    {"label": "Ship Tractor Beams", "list_path": "/GetShipTractorBeams", "detail_path": "/ShipTractorBeams1", "category_url": f"{CSTONE_HOME_URL}/ShipTractorBeams"},
    {"label": "Ship Towing Beams", "list_path": "/GetShipTowingBeams", "detail_path": "/ShipTowingBeams1", "category_url": f"{CSTONE_HOME_URL}/ShipTowingBeams"},
    {"label": "Ship Modules", "list_path": "/GetShipModule", "detail_path": "/ShipModule1", "category_url": f"{CSTONE_HOME_URL}/ShipModule"},
    {"label": "Ship Liveries", "list_path": "/GetShipPaints", "detail_path": "/ShipPaints1", "category_url": f"{CSTONE_HOME_URL}/ShipPaints"},
    {"label": "Containers", "list_path": "/GetContainers", "detail_path": "/Containers1", "category_url": f"{CSTONE_HOME_URL}/Containers"},
    {"label": "Souvenirs / Flair", "list_path": "/GetSouvenirs", "detail_path": "/Souvenirs1", "category_url": f"{CSTONE_HOME_URL}/Souvenirs"},
    {"label": "Decorations", "list_path": "/GetDecorations", "detail_path": "/Decorations1", "category_url": f"{CSTONE_HOME_URL}/Decorations"},
    {"label": "Miscellaneous", "list_path": "/GetMisc", "detail_path": "/Misc1", "category_url": f"{CSTONE_HOME_URL}/misc"},
]

LOCATION_ROW_RE = re.compile(
    r"<tr>\s*"
    r'<td[^>]*>\s*<a[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<location>.*?)</a>\s*</td>\s*'
    r"<td[^>]*>(?P<price>.*?)</td>\s*"
    r"<td[^>]*>(?P<verified>.*?)</td>\s*"
    r"</tr>",
    re.IGNORECASE | re.DOTALL,
)


class CStoneError(Exception):
    pass


@dataclass(frozen=True)
class CStoneItem:
    item_id: str
    name: str
    category: str
    size: str
    sold: bool
    detail_url: str
    category_url: str
    effect: str
    source: str = "Cornerstone"
    item_type: str = "Equipment"
    availability: str = "Unknown"


@dataclass(frozen=True)
class CStoneLocation:
    location: str
    price: str
    verified: str
    url: str


def cstone_category_labels():
    return [category["label"] for category in CSTONE_CATEGORIES]


def cstone_category_url(label):
    for category in CSTONE_CATEGORIES:
        if category["label"] == label:
            return category["category_url"]

    return CSTONE_HOME_URL


def fetch_cstone_items(category_filter="All categories"):
    items = []
    for category in CSTONE_CATEGORIES:
        if category_filter != "All categories" and category["label"] != category_filter:
            continue

        try:
            records = fetch_cstone_json(category["list_path"])
        except (requests.RequestException, ValueError, CStoneError):
            continue

        for record in records:
            item_id = str(record.get("ItemId") or "")
            name = str(record.get("Name") or "").strip()
            if not item_id or not name:
                continue
            if str(record.get("Sold")) != "1":
                continue

            items.append(CStoneItem(
                item_id=item_id,
                name=name,
                category=category["label"],
                size=format_size(record.get("Size")),
                sold=True,
                detail_url=f"{CSTONE_HOME_URL}{category['detail_path']}/{item_id}",
                category_url=category["category_url"],
                effect=summarize_cstone_item(record, category["label"]),
                item_type=item_type_for_record(record, category["label"]),
                availability="Pending",
            ))

    items.sort(key=lambda item: (item.category, item.name.lower()))
    if not items:
        raise CStoneError("No Cornerstone item data could be loaded.")

    return items


def fetch_cstone_mining_items(category_filter="All categories"):
    if category_filter == "All categories":
        categories = ("Mining Heads", "Ship Modifiers", "Handheld Modifiers")
        items = []
        for category in categories:
            try:
                items.extend(fetch_cstone_items(category))
            except CStoneError:
                continue
        return sorted(items, key=lambda item: (item.category, item.name.lower()))

    return fetch_cstone_items(category_filter)


def fetch_cstone_item_locations(detail_url):
    response = requests.get(
        detail_url,
        timeout=CSTONE_TIMEOUT_SECONDS,
        headers={"User-Agent": "SC-Intel-Tool"},
    )
    response.raise_for_status()

    locations = []
    for match in LOCATION_ROW_RE.finditer(response.text):
        location = normalize_location_text(clean_html(match.group("location")))
        price = format_grouped_numbers(clean_html(match.group("price")))
        verified = clean_html(match.group("verified"))
        href = html.unescape(match.group("href"))
        if not location:
            continue

        locations.append(CStoneLocation(
            location=location,
            price=price,
            verified=verified,
            url=absolute_cstone_url(href),
        ))

    return locations


def fetch_cstone_json(path):
    response = requests.get(
        f"{CSTONE_HOME_URL}{path}",
        timeout=CSTONE_TIMEOUT_SECONDS,
        headers={"User-Agent": "SC-Intel-Tool"},
    )
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, list):
        raise CStoneError("Unexpected Cornerstone response format.")

    return payload


def summarize_cstone_item(record, category):
    if category == "Mining Heads":
        return " | ".join(filter(None, (
            format_range("Power", record.get("MinLaserPower"), record.get("MaxLaserPower")),
            format_percent("Resistance", record.get("ResistanceModifier")),
            format_percent("Window", record.get("OptimalChargeWindowSizeModifier")),
            format_value("Slots", record.get("Consumables")),
        ))) or "N/A"

    if category == "Ship Modifiers":
        return " | ".join(filter(None, (
            format_multiplier("Mining", record.get("MiningLaserPowerModifier")),
            format_percent("Resistance", record.get("ResistanceModifier")),
            format_percent("Inert", record.get("InertMaterialsModifiers")),
            format_value("Duration", record.get("Duration")),
        ))) or "N/A"

    if category == "Handheld Modifiers":
        return " | ".join(filter(None, (
            format_percent("Cluster", record.get("ClusterFactorModifier")),
            format_percent("Resistance", record.get("GResistanceModifier")),
            format_percent("Window", record.get("ChargeoptimalChargeWindowSizeModifier")),
            format_percent("Rate", record.get("ChargeoptimalChargeWindowRateModifier")),
        ))) or "N/A"

    return summarize_generic_cstone_item(record)


def item_type_for_record(record, category):
    for key in ("Type", "ItemClass", "Atype", "Model", "Grade"):
        value = record.get(key)
        if value not in (None, ""):
            return str(value)

    size = format_size(record.get("Size"))
    if size != "N/A":
        return size

    return category


def summarize_generic_cstone_item(record):
    fields = (
        ("Manu", "Manufacturer"),
        ("ItemClass", "Class"),
        ("Type", "Type"),
        ("Grade", "Grade"),
        ("Size", "Size"),
        ("Magcapacity", "Mag"),
        ("Personalalphadmg", "Damage"),
        ("Fpsmaxdps", "DPS"),
        ("Bulletspeed", "Speed"),
        ("DamageEnergy", "Energy"),
        ("DamagePhysical", "Physical"),
        ("CoolRate", "Cooling"),
        ("Powerdraw", "Power"),
        ("PowerToEM", "EM"),
        ("QuantumFuelRequirement", "Quantum fuel"),
        ("JumpRange", "Range"),
        ("Mass", "Mass"),
        ("Volume", "Volume"),
        ("Acargo", "Cargo"),
        ("Ccargo", "Cargo"),
    )
    parts = []
    for key, label in fields:
        value = record.get(key)
        if not is_meaningful_value(value):
            continue
        parts.append(f"{label} {format_number(value)}")
        if len(parts) == 4:
            break

    return " | ".join(parts) or "N/A"


def format_size(value):
    if value in (None, ""):
        return "N/A"

    try:
        return f"S{int(value)}"
    except (TypeError, ValueError):
        return str(value)


def format_range(label, minimum, maximum):
    if minimum in (None, "") and maximum in (None, ""):
        return ""

    return f"{label} {format_number(minimum)}-{format_number(maximum)}"


def format_percent(label, value):
    if value in (None, ""):
        return ""

    return f"{label} {format_number(value)}%"


def format_multiplier(label, value):
    if value in (None, ""):
        return ""

    return f"{label} x{format_number(value)}"


def format_value(label, value):
    if value in (None, ""):
        return ""

    return f"{label} {format_number(value)}"


def format_number(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)

    if abs(numeric - round(numeric)) < 0.001:
        return f"{numeric:.0f}"

    return f"{numeric:.2f}"


def is_meaningful_value(value):
    if value in (None, "", 0, 0.0):
        return False

    text = str(value).strip()
    return bool(text) and text.lower() not in {"n/a", "na", "none", "-", "<", ">"}


def normalize_location_text(value):
    text = str(value or "")
    text = re.sub(r"\s*[<>]\s*", " - ", text)
    text = re.sub(r"\s*-\s*", " - ", text)
    return re.sub(r"\s+", " ", text).strip(" -")


def clean_html(value):
    unescaped = html.unescape(value or "")
    no_tags = re.sub(r"<[^>]+>", "", unescaped)
    return re.sub(r"\s+", " ", no_tags).strip()


def absolute_cstone_url(href):
    if href.startswith("http://") or href.startswith("https://"):
        return href

    if not href.startswith("/"):
        href = f"/{href}"

    return f"{CSTONE_HOME_URL}{href}"
