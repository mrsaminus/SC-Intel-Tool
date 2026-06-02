import csv
import html
import re
from dataclasses import dataclass
from io import StringIO
from urllib.parse import quote

import requests


WIKELO_SHEET_ID = "1ji0q_pp6iW35RG1YyFEsv-lsmZOaCStJXGdIEdLLwhM"
WIKELO_SOURCE_URL = f"https://docs.google.com/spreadsheets/d/{WIKELO_SHEET_ID}/edit"
WIKELO_TIMEOUT_SECONDS = 18


@dataclass(frozen=True)
class WikeloRequirement:
    name: str
    quantity: str
    source: str = ""


@dataclass(frozen=True)
class WikeloItem:
    item_id: str
    item_name: str
    category: str
    item_type: str
    reward_method: str
    mission_name: str
    requirements: tuple[WikeloRequirement, ...]
    reward_item: str
    location: str
    source_sheet: str
    source_url: str
    notes: str
    updated: str
    retired: bool = False


FALLBACK_WIKELO_TABS = [
    "Ships 4.7",
    "Crimson Camo Monde Armor & R97 4.7",
    "Corbel Crush & Fresnel 4.7",
    "Tripledown \"Heatwave\" 4.6",
    "Strata \"Heatwave\" Armor 4.6",
    "Testudo & BoomTube Clanguard 4.5",
    "Palatino Mark I & F55 Mark I 4.5",
    "Fresnel \"Yormandi\" LMG 4.5",
    "Snow Armor & Sniper 4.5",
    "Bokto Armor 4.5",
    "Ana Endro Armor 4.5",
    "Prism Shotgun 4.5",
    "Parallax ARs 4.5",
    "ATLS IKTI (GEO) 4.5",
    "Glowy Armor 4.5",
    "Very Hungry 4.3.2",
    "Pearls -> Favors",
    "Carinite -> Favors",
    "Scrip -> Favors",
]


def fetch_wikelo_items():
    session = requests.Session()
    session.headers.update({"User-Agent": "SC-Intel-Tool"})
    tab_names = fetch_wikelo_tab_names(session)
    if not tab_names:
        tab_names = FALLBACK_WIKELO_TABS

    items = []
    for tab_name in latest_item_tabs(tab_names):
        rows = fetch_wikelo_sheet_rows(session, tab_name)
        items.extend(parse_wikelo_sheet(tab_name, rows))

    return sorted(deduplicate_items(items), key=lambda item: (item.category, item.item_name.lower()))


def fetch_wikelo_tab_names(session):
    response = session.get(WIKELO_SOURCE_URL, timeout=WIKELO_TIMEOUT_SECONDS)
    response.raise_for_status()
    return [
        clean_text(html.unescape(match.group(1)))
        for match in re.finditer(r'docs-sheet-tab-caption">(.*?)</div>', response.text)
    ]


def fetch_wikelo_sheet_rows(session, tab_name):
    url = (
        f"https://docs.google.com/spreadsheets/d/{WIKELO_SHEET_ID}/gviz/tq"
        f"?tqx=out:csv&sheet={quote(tab_name)}"
    )
    response = session.get(url, timeout=WIKELO_TIMEOUT_SECONDS)
    response.raise_for_status()
    return [
        [clean_text(cell) for cell in row]
        for row in csv.reader(StringIO(response.text))
    ]


def latest_item_tabs(tab_names):
    grouped = {}
    for tab_name in tab_names:
        if skip_wikelo_tab(tab_name):
            continue
        base = tab_base_name(tab_name)
        current = grouped.get(base)
        if not current or version_key(tab_name) > version_key(current):
            grouped[base] = tab_name

    return list(grouped.values())


def skip_wikelo_tab(tab_name):
    lowered = tab_name.lower()
    return (
        not tab_name
        or lowered.startswith("mia:")
        or "index" in lowered
        or "changes" in lowered
        or lowered.startswith("reputation")
    )


def tab_base_name(tab_name):
    text = re.sub(r"\b\d+\.\d+(?:\.\d+)?\b", "", tab_name)
    text = text.replace("Live", "").replace("PTU", "")
    return clean_text(text).lower()


def version_key(tab_name):
    match = re.search(r"\b(\d+)\.(\d+)(?:\.(\d+))?\b", tab_name)
    if not match:
        return (0, 0, 0)

    return tuple(int(part or 0) for part in match.groups())


def parse_wikelo_sheet(tab_name, rows):
    items = []
    title = sheet_title(tab_name, rows)
    updated = sheet_updated(rows)
    notes = sheet_notes(rows)

    items.extend(parse_favor_exchange(tab_name, rows, title, updated, notes))
    items.extend(parse_inline_mission_costs(tab_name, rows, title, updated, notes))
    items.extend(parse_cost_reward_blocks(tab_name, rows, title, updated, notes))
    return items


def parse_inline_mission_costs(tab_name, rows, title, updated, notes):
    items = []
    seen = set()
    for row_index, row in enumerate(rows):
        for column_index, cell in enumerate(row):
            match = re.search(r"Mission:\s*(.*?)\s*-\s*Cost:\s*(.*)", cell, re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            mission = clean_text(match.group(1))
            requirements = tuple(parse_requirements(match.group(2)))
            reward = nearest_reward_heading(rows, row_index, column_index) or title
            item = build_wikelo_item(
                tab_name,
                reward,
                mission,
                requirements,
                tab_name,
                updated,
                notes,
                row_metadata=" ".join(row),
            )
            key = item_identity(item)
            if key not in seen:
                seen.add(key)
                items.append(item)

    return items


def parse_cost_reward_blocks(tab_name, rows, title, updated, notes):
    items = []
    seen = set()
    for row_index, row in enumerate(rows):
        for column_index, cell in enumerate(row):
            if not is_cost_marker(cell):
                continue

            mission = mission_near(rows, row_index, column_index) or nearest_reward_heading(
                rows, row_index, column_index
            ) or title
            requirements, reward = collect_cost_reward_block(rows, row_index, column_index)
            if not requirements and not reward:
                continue

            reward_item = reward or nearest_reward_heading(rows, row_index, column_index) or title
            item = build_wikelo_item(
                tab_name,
                reward_item,
                mission,
                tuple(requirements),
                tab_name,
                updated,
                notes,
                row_metadata=" ".join(row),
            )
            key = item_identity(item)
            if key not in seen:
                seen.add(key)
                items.append(item)

    return items


def parse_favor_exchange(tab_name, rows, title, updated, notes):
    if "->" not in tab_name:
        return []

    items = []
    for row in rows:
        requirements = []
        reward = ""
        for cell in row:
            if "wikelo favor" in cell.lower():
                reward = clean_text(cell)
                continue
            requirements.extend(parse_requirements(cell))
        if requirements and reward:
            items.append(build_wikelo_item(
                tab_name,
                reward,
                title,
                tuple(requirements),
                tab_name,
                updated,
                notes,
                row_metadata=" ".join(row),
            ))
            break

    return items


def collect_cost_reward_block(rows, cost_row, column):
    requirements = []
    reward_lines = []
    in_reward = False
    inline_cost = re.sub(r"^Cost:\s*", "", rows[cost_row][column], flags=re.IGNORECASE).strip()
    requirements.extend(parse_requirements(inline_cost))

    for row_index in range(cost_row + 1, len(rows)):
        cell = cell_at(rows, row_index, column)
        if not cell:
            continue
        lowered = cell.lower()
        if lowered.startswith("reward"):
            in_reward = True
            trailing_reward = re.sub(r"^Reward:\s*", "", cell, flags=re.IGNORECASE).strip()
            if trailing_reward:
                reward_lines.append(trailing_reward)
            continue
        if lowered.startswith(("notes", "where to source", "further reading", "image credit")):
            break
        if in_reward:
            if is_generic_block_text(cell):
                continue
            reward_lines.append(cell)
            if reward_lines:
                break
        else:
            parsed = parse_requirements(cell)
            if parsed:
                requirements.extend(parsed)

    return requirements, clean_text(" ".join(reward_lines))


def mission_near(rows, row_index, column_index):
    for current_row in range(max(0, row_index - 6), min(len(rows), row_index + 2)):
        text = cell_at(rows, current_row, column_index)
        mission = extract_mission_name(text)
        if mission:
            return mission

    return ""


def extract_mission_name(text):
    if "mission name" not in text.lower():
        return ""
    lines = [line.strip(' "') for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if "mission name" in line.lower():
            trailing = re.sub(r"Mission name:\s*", "", line, flags=re.IGNORECASE).strip(' "')
            if trailing:
                return trailing
            if index + 1 < len(lines):
                return lines[index + 1].strip(' "')

    return ""


def nearest_reward_heading(rows, row_index, column_index):
    for column_offsets in ((0,), (-1, 1, -2, 2)):
        for current_row in range(row_index, max(-1, row_index - 9), -1):
            for offset in column_offsets:
                text = cell_at(rows, current_row, column_index + offset)
                if is_reward_heading(text):
                    return reward_heading_text(text)

    return ""


def is_reward_heading(text):
    if not text or len(text) > 90:
        return False
    if re.match(r"^\d+(?:\.\d+)?x?$", text.strip(), re.IGNORECASE):
        return False
    candidate = reward_heading_text(text)
    lowered = candidate.lower()
    if any(marker in lowered for marker in (
        "mission",
        "cost",
        "reward",
        "updated",
        "credit",
        "component",
        "class",
        "source",
        "wikelo sheet",
        "like my work",
        "cooler",
        "shield",
        "power plant",
        "quantum drive",
        "weapons",
    )):
        return False
    if parse_requirements(candidate):
        return False

    return bool(re.search(r"[A-Za-z0-9]", candidate))


def reward_heading_text(text):
    text = clean_text(text)
    datamining_match = re.search(r"WayfinderDrax\s+(.+)$", text, re.IGNORECASE)
    if datamining_match:
        return clean_text(datamining_match.group(1))

    return text.strip(" -:")


def parse_requirements(text):
    requirements = []
    for part in requirement_parts(text):
        match = re.match(r"^(\d+(?:\.\d+)?)\s*x?\s+(.+)$", part, re.IGNORECASE)
        if not match:
            continue
        quantity = f"{match.group(1)}x"
        name = clean_requirement_name(match.group(2))
        if name:
            requirements.append(WikeloRequirement(name=name, quantity=quantity))

    return requirements


def requirement_parts(text):
    normalized = str(text or "").replace("\r", "\n")
    normalized = re.sub(r"\s+\+\s+", "\n", normalized)
    parts = []
    for line in normalized.splitlines():
        line = line.strip()
        if not line:
            continue
        parts.extend(part.strip() for part in re.split(r",|;|\band\b", line) if part.strip())
    return parts


def clean_requirement_name(text):
    text = clean_text(text)
    text = re.sub(r"\bcredit\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -")


def build_wikelo_item(tab_name, reward, mission, requirements, source_sheet, updated, notes, row_metadata=""):
    reward_item = clean_reward_name(reward) or clean_reward_name(tab_name)
    mission_name = clean_text(mission) or clean_reward_name(tab_name)
    category, item_type = classify_wikelo_item(tab_name, reward_item, mission_name)
    method = mission_name if mission_name != reward_item else source_sheet
    retired = is_retired_wikelo_item(
        " ".join((reward_item, mission_name, tab_name, source_sheet, notes, row_metadata))
    )
    return WikeloItem(
        item_id=normalized_key(f"{source_sheet}|{reward_item}|{mission_name}|{requirements}"),
        item_name=reward_item,
        category=category,
        item_type=item_type,
        reward_method=method,
        mission_name=mission_name,
        requirements=tuple(requirements),
        reward_item=reward_item,
        location=wikelo_location_from_text(f"{tab_name} {notes}"),
        source_sheet=source_sheet,
        source_url=WIKELO_SOURCE_URL,
        notes=notes,
        updated=updated,
        retired=retired,
    )


def classify_wikelo_item(tab_name, reward, mission):
    reward_text = str(reward or "").lower()
    text = f"{reward} {mission} {tab_name}".lower()
    ship_words = ("ship", "ursa", "zeus", "apollo", "guardian", "intrepid", "fortune")
    weapon_words = (
        "rifle",
        "shotgun",
        "pistol",
        "smg",
        "lmg",
        "launcher",
        "railgun",
        "weapon",
        "gun",
        "sniper",
        "parallax",
        "fresnel",
    )
    armor_words = ("helmet", "core", "arms", "legs", "armor", "armour", "backpack", "set")

    if any(word in reward_text for word in ship_words):
        return "Ships", "Ship"
    if any(word in reward_text for word in weapon_words):
        return "Weapons", "Weapon"
    if any(word in reward_text for word in armor_words):
        return "Armor", "Armor"
    if any(word in text for word in ship_words):
        return "Ships", "Ship"
    if any(word in text for word in weapon_words):
        return "Weapons", "Weapon"
    if any(word in text for word in armor_words):
        return "Armor", "Armor"
    if "favor" in text or "scrip" in text or "pearl" in text or "carinite" in text:
        return "Favors", "Exchange"
    if any(word in text for word in ("component", "cooler", "power plant", "quantum", "shield")):
        return "Components", "Component"
    if any(word in text for word in ("atls", "tool", "tractor")):
        return "Tools", "Tool"

    return "Wikelo", "Mission"


def wikelo_location_from_text(text):
    lowered = text.lower()
    if "emporium" in lowered:
        return "Wikelo Emporium"
    if "microtech" in lowered:
        return "microTech"
    if "pyro" in lowered or "pryo" in lowered:
        return "Pyro"
    if "crusader" in lowered:
        return "Crusader"
    if "hurston" in lowered:
        return "Hurston"

    return "Wikelo"


def clean_reward_name(text):
    text = clean_text(text)
    text = re.sub(r"^Wikelo Sheet:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\d+(?:\.\d+)?\s*x?\s+(?=Wikelo Favor$)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+\.\d+(?:\.\d+)?\b", "", text)
    text = text.replace("Updated:", "")
    return clean_text(text.strip(" -:"))


def is_retired_wikelo_item(text):
    return "retired" in str(text or "").lower()


def sheet_title(tab_name, rows):
    for row in rows[:6]:
        for cell in row:
            if "wikelo sheet:" in cell.lower():
                return clean_reward_name(cell)
    return clean_reward_name(tab_name)


def sheet_updated(rows):
    for row in rows[:10]:
        row_text = " ".join(row)
        match = re.search(r"(Updated|Created):\s*([^:\n]+?)(?:\s{2,}|$)", row_text, re.IGNORECASE)
        if match:
            return clean_text(match.group(2))
    return ""


def sheet_notes(rows):
    notes = []
    capture = False
    for row in rows:
        row_text = clean_text(" ".join(cell for cell in row if cell))
        if not row_text:
            continue
        lowered = row_text.lower()
        if lowered.startswith("notes"):
            capture = True
            continue
        if lowered.startswith("further reading"):
            break
        if capture:
            notes.append(row_text)
            if len(" ".join(notes)) > 900:
                break

    return clean_text(" ".join(notes))


def clean_text(text):
    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in str(text or "").replace("\r", "\n").splitlines()
    ]
    return "\n".join(line for line in lines if line).strip()


def cell_at(rows, row_index, column_index):
    if row_index < 0 or row_index >= len(rows):
        return ""
    row = rows[row_index]
    if column_index < 0 or column_index >= len(row):
        return ""
    return row[column_index]


def is_cost_marker(text):
    return bool(re.match(r"^\s*Cost:\s*", text or "", re.IGNORECASE))


def is_generic_block_text(text):
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in ("image credit", "credit:", "thanks", "where to source"))


def deduplicate_items(items):
    deduped = {}
    for item in items:
        key = item_identity(item)
        current = deduped.get(key)
        if not current or version_key(item.source_sheet) > version_key(current.source_sheet):
            deduped[key] = item

    return list(deduped.values())


def item_identity(item):
    requirement_key = "|".join(
        f"{requirement.quantity}:{normalized_key(requirement.name)}"
        for requirement in item.requirements
    )
    return normalized_key(f"{item.item_name}|{item.mission_name}|{requirement_key}")


def normalized_key(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
