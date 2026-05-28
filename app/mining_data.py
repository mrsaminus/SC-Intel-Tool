import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MINING_ROOT = PROJECT_ROOT / "reference_material" / "mining_warchest"

SECTION_RE = re.compile(r"\b(Surface|Asteroid)\s*:", re.IGNORECASE)
SYSTEM_MARKER_RE = re.compile(
    r"\((Stanton|Pyro|Nyx)\)|\b(Stanton|Pyro|Nyx|Pryo)\s*(?:Only)?\s*:",
    re.IGNORECASE,
)

STANTON_HINTS = {
    "hurston",
    "aberdeen",
    "arial",
    "ita",
    "magda",
    "daymar",
    "cellin",
    "yela",
    "lyria",
    "wala",
    "microtech",
    "calliope",
    "clio",
    "euterpe",
    "aaron halo",
    "yela belt",
    "arc-l",
    "cru-l",
    "hur-l",
    "mic-l",
    "mining bases",
    "olp",
    "all stanton",
}

PYRO_HINTS = {
    "pyro",
    "monox",
    "bloom",
    "ignis",
    "vatra",
    "adir",
    "fairo",
    "fuego",
    "vuur",
    "terminus",
    "rab",
    "rmb",
    "all rab",
}

NYX_HINTS = {
    "nyx",
    "glaciem",
    "keeger",
    "rock breaker",
}

SCAN_SIGNATURE_SPECS = [
    ("Quantainium", "Legendary", 2, 3170),
    ("Stileron", "Legendary", 2, 3185),
    ("Savrilium", "Legendary", 2, 3200),
    ("Ouratite", "Epic", 3, 3370),
    ("Riccite", "Epic", 3, 3385),
    ("Lindinium", "Epic", 3, 3400),
    ("Beryl", "Rare", 4, 3540),
    ("Taranite", "Rare", 4, 3555),
    ("Borase", "Rare", 4, 3570),
    ("Gold", "Rare", 4, 3585),
    ("Bexalite", "Rare", 4, 3600),
    ("Laranite", "Uncommon", 5, 3825),
    ("Aslarite", "Uncommon", 5, 3840),
    ("Titanium", "Uncommon", 5, 3855),
    ("Tungsten", "Uncommon", 5, 3870),
    ("Agricium", "Uncommon", 5, 3885),
    ("Torite", "Uncommon", 5, 3900),
    ("Hephaestanite", "Common", 6, 4180),
    ("Tin", "Common", 6, 4195),
    ("Quartz", "Common", 6, 4210),
    ("Corundum", "Common", 6, 4225),
    ("Copper", "Common", 6, 4240),
    ("Silicon", "Common", 6, 4255),
    ("Iron", "Common", 6, 4270),
    ("Aluminum", "Common", 6, 4285),
    ("Ice", "Common", 6, 4300),
    ("ROC Mineables", "ROC Mineables", 7, 4000),
    ("FPS Mineables", "FPS Mineables", 10, 3000),
    ("Salvage", "Salvage", 15, 2000),
]

QUALITY_BAND_RAW_VALUES = {
    # Values verified against the uploaded raw-game quality table.
    "Agricium": [346, 588, 667, 796, 852, 943, 971, 1000],
    "Aluminum": [318, 511, 614, 783, 896, 919, 953, 1000],
    "Aphorite": [348, 523, 686, 717, 861, 916, 975, 1000],
    "Aslarite": [287, 575, 602, 741, 854, 927, 963, 1000],
    "Beradom": [287, 578, 656, 723, 881, 937, 969, 1000],
    "Beryl": [324, 547, 677, 717, 860, 937, 955, 1000],
    "Bexalite": [302, 597, 632, 756, 875, 941, 959, 1000],
    "Borase": [359, 584, 976, 743, 892, 903, 976, 1000],
    "Caranite": [273, 554, 647, 716, 880, 909, 959, 1000],
    "Copper": [359, 593, 652, 742, 855, 917, 958, 1000],
    "Corundum": [None, 504, 665, 793, 886, 904, 971, 1000],
    "Dolivine": [304, 577, 621, 743, 886, 901, 957, 1000],
    "Feynmaline": [371, 561, 682, 769, 880, 906, 965, 1000],
    "Glacosite": [360, 567, 678, 724, 857, 916, 972, 1000],
    "Gold": [264, 553, 644, 786, 864, 916, 959, 1000],
    "Hadanite": [274, 526, 665, 762, 867, 916, 959, 1000],
    "Hephaestanite": [330, 572, 692, 758, 896, 916, 975, 1000],
    "Ice": [322, 561, 659, 714, 873, 922, 966, 1000],
    "Iron": [325, 521, 664, 710, 874, 907, 970, 1000],
    "Jaclium": [284, 576, 607, 781, 864, 941, 955, 1000],
    "Janalite": [269, 596, 632, 732, 898, 926, 964, 1000],
    "Laranite": [298, 510, 698, 707, 858, 910, 975, 1000],
    "Lindinium": [305, 585, 618, 729, 853, 930, 954, 1000],
    "Ouratite": [310, 523, 647, 779, 860, 912, 960, 1000],
    "Quantanium": [344, 514, 669, 762, 852, 901, 974, 1000],
    "Quartz": [330, 522, 641, 710, 899, 914, 969, 1000],
    "Riccite": [325, 525, 671, 743, 870, 942, 965, 1000],
    "Sadaryx": [258, 510, 688, 797, 865, 940, 971, 1000],
    "Saldynium": [301, 575, 674, 757, 861, 938, 955, 1000],
    "Savrilium": [322, 580, 636, 776, 878, 905, 967, 1000],
    "Silicon": [310, 510, 672, 782, 889, 926, 968, 1000],
    "Stileron": [330, 517, 681, 757, 874, 947, 972, 1000],
    "Taranite": [310, 525, 646, 718, 853, 925, 957, 1000],
    "Tin": [340, 537, 664, 704, 880, 940, 964, 1000],
    "Titanium": [295, 516, 622, 784, 866, 916, 959, 1000],
    "Torite": [262, 528, 661, 785, 873, 944, 951, 1000],
    "Tungsten": [363, 530, 662, 787, 858, 902, 964, 1000],
}

QUALITY_BAND_RAW_ALIASES = {
    "Carinite": "Caranite",
    "Quantainium": "Quantanium",
}


@dataclass(frozen=True)
class MineralLocation:
    mineral: str
    system: str
    body: str
    deposit_type: str
    notes: str = ""


@dataclass(frozen=True)
class MiningEquipment:
    name: str
    equipment_type: str
    size: str
    price: int | float | None
    shop_count: int
    best_shop: str
    best_location: str
    effect: str
    notes: str = ""


@dataclass(frozen=True)
class RockLaser:
    name: str
    size: int
    price: int | float | None
    min_power: float
    max_power: float
    extraction_power: float
    module_slots: int
    resistance_factor: float
    instability_factor: float
    optimal_charge_rate: float
    optimal_charge_window: float
    optimal_range: float
    max_range: float


@dataclass(frozen=True)
class RockModifier:
    name: str
    modifier_type: str
    price: int | float | None
    duration: str
    uses: str
    mining_laser_power: float
    resistance_factor: float
    instability_factor: float
    optimal_charge_rate: float
    optimal_charge_window: float
    cluster_modifier: float


@dataclass(frozen=True)
class QualityBandRow:
    resource: str
    values: list[int | None]


@dataclass(frozen=True)
class ScanSignatureRow:
    resource: str
    category: str
    max_multiplier: int
    values: list[int]


@dataclass(frozen=True)
class RefineryStation:
    display_name: str
    source_name: str
    system: str
    bonuses: dict[str, float]


@dataclass(frozen=True)
class RefineryMethod:
    name: str
    relative_time: float
    relative_cost: float
    yield_factor: float


@dataclass(frozen=True)
class MiningData:
    source_root: Path
    locations: list[MineralLocation]
    equipment: list[MiningEquipment]
    rock_lasers: list[RockLaser]
    rock_modules: list[RockModifier]
    rock_gadgets: list[RockModifier]
    quality_band_labels: list[str]
    quality_bands: list[QualityBandRow]
    scan_signatures: list[ScanSignatureRow]
    refinery_stations: list[RefineryStation]
    refinery_methods: list[RefineryMethod]
    errors: list[str]

    @property
    def minerals(self):
        return sorted({location.mineral for location in self.locations})


def load_mining_data(root=DEFAULT_MINING_ROOT):
    root = Path(root)
    errors = []

    locations = load_mineral_locations(root, errors)
    equipment, rock_lasers, rock_modules, rock_gadgets = load_mining_equipment(root, errors)
    quality_band_labels, quality_bands = load_quality_bands(root, errors)
    scan_signatures = load_scan_signatures()
    refinery_stations, refinery_methods = load_refinery_reference(root, errors)

    return MiningData(
        source_root=root,
        locations=locations,
        equipment=equipment,
        rock_lasers=rock_lasers,
        rock_modules=rock_modules,
        rock_gadgets=rock_gadgets,
        quality_band_labels=quality_band_labels,
        quality_bands=quality_bands,
        scan_signatures=scan_signatures,
        refinery_stations=refinery_stations,
        refinery_methods=refinery_methods,
        errors=errors,
    )


def load_mineral_locations(root, errors):
    path = root / "assets" / "Mineral Stats" / "Mineral_Where.txt"
    if not path.exists():
        errors.append(f"Missing mining location file: {path}")
        return []

    locations = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or " - " not in line:
            continue

        mineral, details = line.split(" - ", 1)
        for deposit_type, section_text in split_deposit_sections(details):
            for system, chunk_text in split_system_chunks(section_text):
                body_names, note = split_location_names(chunk_text)
                for body in body_names:
                    final_system = system if system != "Unknown" else infer_system(body)
                    locations.append(MineralLocation(
                        mineral=mineral.strip(),
                        system=final_system,
                        body=body,
                        deposit_type=deposit_type,
                        notes=note,
                    ))

    return locations


def split_deposit_sections(details):
    details = normalize_text(details)
    matches = list(SECTION_RE.finditer(details))
    if not matches:
        return [("General", details)]

    sections = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(details)
        section_text = details[start:end].strip(" .")
        if section_text:
            sections.append((match.group(1).title(), section_text))

    return sections


def split_system_chunks(section_text):
    section_text = normalize_text(section_text)
    matches = list(SYSTEM_MARKER_RE.finditer(section_text))
    if not matches:
        return [(infer_system(section_text), section_text)]

    chunks = []
    prefix = section_text[:matches[0].start()].strip(" .,:")
    if prefix:
        chunks.append((infer_system(prefix), prefix))

    for index, match in enumerate(matches):
        system = normalize_system(match.group(1) or match.group(2))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section_text)
        chunk_text = section_text[start:end].strip(" .,:")
        if chunk_text:
            chunks.append((system, chunk_text))

    return chunks


def split_location_names(text):
    text = normalize_text(text).strip(" .,:")
    if not text:
        return ["N/A"], ""

    note = ""
    best_match = re.search(r"\bBEST ONLY\b\s*\(([^)]+)\)", text, re.IGNORECASE)
    if best_match:
        note = "Best location"
        text = best_match.group(1)

    if re.search(r"\bNONE\b", text, re.IGNORECASE):
        return [text], "No known location"

    text = re.sub(r"\bBEST ONLY\b", "", text, flags=re.IGNORECASE).strip(" .,:")
    parts = [part.strip(" .") for part in text.split(",") if part.strip(" .")]
    return parts or [text], note


def load_mining_equipment(root, errors):
    path = root / "Calculator" / "rock-breaking-calculator-data.json"
    if path.exists():
        shops = load_equipment_shops(root, errors)
        return load_equipment_from_rock_data(path, shops, errors)

    fallback = root / "assets" / "Equipment" / "Lasers and Modules Stats.csv"
    if fallback.exists():
        return load_equipment_from_csv(fallback, errors), [], [], []

    errors.append(f"Missing mining equipment data under: {root}")
    return [], [], [], []


def load_quality_bands(root, errors):
    path = root / "assets" / "Equipment" / "qualityquantization"
    if not path.exists():
        errors.append(f"Missing quality quantization folder: {path}")
        return [], []

    labels = []
    rows = []
    for file_path in sorted(path.glob("quantization_*.json")):
        resource_key = file_path.stem.replace("quantization_", "")
        if resource_key.lower() == "template":
            continue

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Could not parse quality band file {file_path.name}: {exc}")
            continue

        bands = data.get("_RecordValue_", {}).get("qualityQuantization", {}).get("bands", [])
        if not labels and bands:
            labels = [
                f"{band.get('start', '?')}-{band.get('end', '?')}Q"
                for band in bands
            ]

        resource = normalize_resource_name(resource_key)
        values = [
            band.get("mappedValue")
            for band in bands
        ]
        raw_resource = QUALITY_BAND_RAW_ALIASES.get(resource, resource)

        rows.append(QualityBandRow(
            resource=resource,
            values=QUALITY_BAND_RAW_VALUES.get(raw_resource, values),
        ))

    rows.sort(key=lambda row: row.resource.lower())
    return labels, rows


def load_scan_signatures():
    return [
        ScanSignatureRow(resource, category, max_multiplier, [
            base_value * multiplier
            for multiplier in range(1, max_multiplier + 1)
        ])
        for resource, category, max_multiplier, base_value in SCAN_SIGNATURE_SPECS
    ]


def load_refinery_reference(root, errors):
    path = root / "assets" / "Refinery" / "Refinery.xlsx"
    if not path.exists():
        errors.append(f"Missing refinery data file: {path}")
        return [], []

    try:
        cells, max_row, max_column = read_xlsx_cells(path)
    except (OSError, KeyError, ET.ParseError, ValueError) as exc:
        errors.append(f"Could not parse refinery data file {path.name}: {exc}")
        return [], []

    stations = []
    for column in range(2, max_column + 1):
        source_system = str(cells.get((1, column), "")).strip()
        station_name = str(cells.get((2, column), "")).strip()
        if source_system.lower().startswith("refinery method"):
            continue
        if not station_name or station_name in {"Relative Time", "Relative Cost", "Yield"}:
            continue

        display_name, system = format_refinery_station_name(source_system, station_name)
        bonuses = {}
        for row in range(3, max_row + 1):
            material = canonical_refinery_material(cells.get((row, 1), ""))
            if not material:
                continue

            bonus = parse_float_value(cells.get((row, column), ""))
            if bonus is not None:
                bonuses[material] = bonus

        stations.append(RefineryStation(
            display_name=display_name,
            source_name=station_name,
            system=system,
            bonuses=bonuses,
        ))

    methods = []
    for row in range(3, max_row + 1):
        method_name = normalize_refinery_method_name(cells.get((row, 23), ""))
        if not method_name:
            continue

        yield_factor = parse_float_value(cells.get((row, 26), ""))
        if yield_factor is None:
            continue

        methods.append(RefineryMethod(
            name=method_name,
            relative_time=parse_float_value(cells.get((row, 24), "")) or 0,
            relative_cost=parse_float_value(cells.get((row, 25), "")) or 0,
            yield_factor=yield_factor,
        ))

    return stations, methods


def read_xlsx_cells(path):
    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    cell_re = re.compile(r"([A-Z]+)(\d+)")

    with ZipFile(path) as archive:
        shared_strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in shared_root.findall("a:si", namespace):
                shared_strings.append("".join(
                    text.text or ""
                    for text in item.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                ))

        sheet_root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    cells = {}
    max_row = 0
    max_column = 0
    for cell in sheet_root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
        reference = cell.attrib.get("r", "")
        match = cell_re.match(reference)
        if not match:
            continue

        column = column_name_to_number(match.group(1))
        row = int(match.group(2))
        max_column = max(max_column, column)
        max_row = max(max_row, row)

        value_node = cell.find("a:v", namespace)
        value = ""
        if value_node is not None and value_node.text is not None:
            value = value_node.text
            if cell.attrib.get("t") == "s":
                value = shared_strings[int(value)]

        cells[(row, column)] = value

    return cells, max_row, max_column


def column_name_to_number(value):
    number = 0
    for character in value:
        number = number * 26 + ord(character) - ord("A") + 1
    return number


def format_refinery_station_name(source_system, station_name):
    source = str(source_system or "").strip()
    station = str(station_name or "").strip()

    match = re.match(r"^(ARC|CRU|HUR|MIC)\s+L(\d+)$", source, re.IGNORECASE)
    if match:
        return f"{match.group(1).upper()}-L{match.group(2)}: {station}", "Stanton"

    gateway_codes = {
        "magnus gateway": "MAG",
        "nyx gateway": "NYX",
        "pyro gateway": "PYR",
        "stanton gateway": "ST",
        "terra gateway": "TER",
    }
    source_codes = {
        "stanton": "ST",
        "pyro": "PYR",
        "nyx": "NYX",
    }
    source_key = source.lower()
    station_key = station.lower()

    if source_key in source_codes and station_key in gateway_codes:
        return f"{source_codes[source_key]}-{gateway_codes[station_key]}: {station}", source.title()

    if source_key in {"pyro", "nyx"} and station_key in {"checkmate", "orbituary", "levski"}:
        return f"{station} Station", source.title()

    return station, source.title() if source else "Unknown"


def normalize_refinery_method_name(value):
    name = str(value or "").strip()
    if not name:
        return ""
    if name.lower() == "cormack":
        return "Cormack Method"
    return name


def canonical_refinery_material(value):
    name = str(value or "").strip()
    if not name:
        return ""

    aliases = {
        "pressurized ice": "Ice",
        "quantanium": "Quantainium",
    }
    return aliases.get(name.lower(), name)


def load_equipment_shops(root, errors):
    path = root / "defaults" / "equipment_shops_cache_default.json"
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Could not parse equipment shop cache: {exc}")
        return {}

    shops = data.get("equipment_shops", {})
    return shops if isinstance(shops, dict) else {}


def load_equipment_from_rock_data(path, shops, errors):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Could not parse rock/equipment data: {exc}")
        return [], [], [], []

    equipment = []
    rock_lasers = []
    rock_modules = []
    rock_gadgets = []
    for key, equipment_type, name_key in (
        ("miningLasers", "Laser", "Lasers"),
        ("miningModules", "Module", "Modules"),
        ("miningGadgets", "Gadget", "Gadgets"),
    ):
        for item in data.get(key, []):
            name = item.get(name_key)
            if not name:
                continue

            equipment.append(MiningEquipment(
                name=str(name),
                equipment_type=equipment_type,
                size=format_size(item.get("Size")),
                price=best_equipment_price(str(name), item.get("Price"), shops),
                shop_count=len(shops.get(str(name), [])),
                best_shop=best_equipment_shop(str(name), shops),
                best_location=best_equipment_location(str(name), shops),
                effect=summarize_equipment_effect(item, equipment_type),
                notes=summarize_equipment_notes(item, equipment_type),
            ))

            if equipment_type == "Laser":
                rock_lasers.append(RockLaser(
                    name=str(name),
                    size=int(parse_float_value(item.get("Size")) or 0),
                    price=item.get("Price"),
                    min_power=parse_float_value(item.get("MinPower")) or 0,
                    max_power=parse_float_value(item.get("MaxPower")) or 0,
                    extraction_power=parse_float_value(item.get("ExtractionPower")) or 0,
                    module_slots=int(parse_float_value(item.get("ModuleSlots")) or 0),
                    resistance_factor=parse_float_value(item.get("ResistanceFactor")) or 1,
                    instability_factor=parse_float_value(item.get("InstabilityFactor")) or 1,
                    optimal_charge_rate=parse_float_value(item.get("OptimalChargeRate")) or 1,
                    optimal_charge_window=parse_float_value(item.get("OptimalChargeWindow")) or 1,
                    optimal_range=parse_float_value(item.get("OptimalRange")) or 0,
                    max_range=parse_float_value(item.get("MaxRange")) or 0,
                ))
            elif equipment_type == "Module":
                rock_modules.append(load_rock_modifier(item, "Module", str(name)))
            elif equipment_type == "Gadget":
                rock_gadgets.append(load_rock_modifier(item, "Gadget", str(name)))

    return equipment, rock_lasers, rock_modules, rock_gadgets


def load_rock_modifier(item, modifier_type, name):
    return RockModifier(
        name=name,
        modifier_type=modifier_type,
        price=item.get("Price"),
        duration=str(item.get("Duration") or ""),
        uses=str(item.get("Uses") or ""),
        mining_laser_power=parse_float_value(item.get("MiningLaserPower")) or 1,
        resistance_factor=parse_float_value(item.get("ResistanceFactor")) or 1,
        instability_factor=parse_float_value(item.get("LaserInstability")) or 1,
        optimal_charge_rate=parse_float_value(item.get("OptimalChargeRate")) or 1,
        optimal_charge_window=parse_float_value(item.get("OptimalChargeWindow")) or 1,
        cluster_modifier=parse_float_value(item.get("ClusterModifier")) or 1,
    )


def load_equipment_from_csv(path, errors):
    try:
        rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    except csv.Error as exc:
        errors.append(f"Could not parse equipment CSV: {exc}")
        return []

    equipment = []
    current_type = "Module"
    for row in rows:
        name = (row.get("Name") or "").strip()
        category = (row.get("Modules") or "").strip()
        if category:
            current_type = category
        if not name:
            continue

        equipment.append(MiningEquipment(
            name=name,
            equipment_type=current_type,
            size="N/A",
            price=parse_price(row.get("Price")),
            shop_count=0,
            best_shop="N/A",
            best_location="N/A",
            effect=", ".join(
                value
                for value in (
                    row.get("Mining Laser Power"),
                    row.get("Resistance"),
                    row.get("Optimal Charge Window"),
                )
                if value
            ) or "N/A",
        ))

    return equipment


def best_equipment_price(name, fallback, shops):
    rows = shops.get(name, [])
    prices = [
        parse_float_value(row.get("price_sell"))
        for row in rows
        if parse_float_value(row.get("price_sell")) is not None
    ]
    return min(prices) if prices else fallback


def best_equipment_shop(name, shops):
    row = best_equipment_shop_row(name, shops)
    return row.get("shop_name", "N/A") if row else "N/A"


def best_equipment_location(name, shops):
    row = best_equipment_shop_row(name, shops)
    if not row:
        return "N/A"
    return row.get("location") or " - ".join(
        part
        for part in (
            row.get("star_system"),
            row.get("planet"),
            row.get("moon"),
            row.get("space_station"),
            row.get("city"),
            row.get("outpost"),
        )
        if part
    ) or "N/A"


def best_equipment_shop_row(name, shops):
    rows = shops.get(name, [])
    if not rows:
        return None

    return min(
        rows,
        key=lambda row: parse_float_value(row.get("price_sell")) or float("inf"),
    )


def summarize_equipment_effect(item, equipment_type):
    if equipment_type == "Laser":
        return (
            f"Power {item.get('MinPower', 'N/A')}-{item.get('MaxPower', 'N/A')} | "
            f"Extraction {item.get('ExtractionPower', 'N/A')} | "
            f"Slots {item.get('ModuleSlots', 'N/A')}"
        )

    labels = (
        ("MiningLaserPower", "Mining power"),
        ("ExtractionLaserPower", "Extraction"),
        ("ResistanceFactor", "Resistance"),
        ("LaserInstability", "Instability"),
        ("OptimalChargeRate", "Charge rate"),
        ("OptimalChargeWindow", "Charge window"),
        ("InertMaterials", "Inert"),
        ("ClusterModifier", "Cluster"),
    )

    effects = []
    for key, label in labels:
        value = item.get(key)
        if value in (None, "", 1, 1.0):
            continue
        if isinstance(value, (int, float)):
            effects.append(f"{label} x{value:g}")
        else:
            effects.append(f"{label} {value}")

    return ", ".join(effects) or "N/A"


def summarize_equipment_notes(item, equipment_type):
    if equipment_type == "Module":
        duration = item.get("Duration")
        uses = item.get("Uses")
        if duration or uses:
            return f"Duration {duration or 'N/A'} | Uses {uses or 'N/A'}"

    if equipment_type == "Laser":
        return f"Range {item.get('OptimalRange', 'N/A')}-{item.get('MaxRange', 'N/A')}"

    return ""


def parse_price(value):
    if not value:
        return None

    cleaned = re.sub(r"[^0-9.]", "", str(value))
    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_float_value(value):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_size(value):
    if value in (None, ""):
        return "N/A"

    try:
        return f"S{int(value)}"
    except (TypeError, ValueError):
        return str(value)


def normalize_resource_name(value):
    name = value.replace("_", " ").title().replace("Rawice", "Ice")
    if name.lower() == "quantainium":
        return "Quantainium"
    return name


def infer_system(value):
    value_lower = value.lower()
    if any(hint in value_lower for hint in STANTON_HINTS):
        return "Stanton"
    if any(hint in value_lower for hint in PYRO_HINTS):
        return "Pyro"
    if any(hint in value_lower for hint in NYX_HINTS):
        return "Nyx"
    return "Unknown"


def normalize_system(value):
    value = (value or "").strip().lower()
    if value == "pryo":
        return "Pyro"
    if value in ("stanton", "pyro", "nyx"):
        return value.title()
    return "Unknown"


def normalize_text(value):
    return re.sub(r"\s+", " ", value.replace("Pryo", "Pyro")).strip()
