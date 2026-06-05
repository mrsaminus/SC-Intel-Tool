from dataclasses import dataclass
import re

from app.ship_metadata import SHIP_METADATA, normalize_ship_name


SPREADSHEET_SOURCE = "Star_Citizen_Flight_Ready_SCU_Offisiell.xlsx"
LOCAL_METADATA_SOURCE = "app.ship_metadata"
RSI_SHIP_MATRIX_SOURCE = "RSI Ship Matrix"


@dataclass(frozen=True)
class TradingShipCargo:
    manufacturer: str
    cargo_scu: float
    role: str
    source: str


# Imported from the provided workbook sheet "SCU Kapasitet".
# Include every row where "SCU Kapasitet" is greater than zero.
SPREADSHEET_SHIP_CARGO = {
    'Hull C': TradingShipCargo('MISC', 4608, 'Tung ekstern frakt', SPREADSHEET_SOURCE),
    'Ironclad': TradingShipCargo('Drake', 2204, 'Tung pansret frakt / Sveiseverksted', SPREADSHEET_SOURCE),
    'Ironclad Assault': TradingShipCargo('Drake', 1440, 'Milit\xe6r transport / Gjenoppretting', SPREADSHEET_SOURCE),
    'Polaris': TradingShipCargo('RSI', 736, 'Capital-korvett', SPREADSHEET_SOURCE),
    'C2 Hercules': TradingShipCargo('Crusader', 696, 'Tung sivil frakt / Kj\xf8ret\xf8ytransport', SPREADSHEET_SOURCE),
    'Caterpillar': TradingShipCargo('Drake', 576, 'Modul\xe6r tungfrakt', SPREADSHEET_SOURCE),
    'M2 Hercules': TradingShipCargo('Crusader', 522, 'Tung milit\xe6r transport', SPREADSHEET_SOURCE),
    '890 Jump': TradingShipCargo('Origin', 484, 'Luksus mega-yacht', SPREADSHEET_SOURCE),
    'Carrack': TradingShipCargo('Anvil', 456, 'Langdistanse milit\xe6r utforskning', SPREADSHEET_SOURCE),
    'Reclaimer': TradingShipCargo('Aegis', 420, 'Tung opphugging (Salvage)', SPREADSHEET_SOURCE),
    'Starfarer': TradingShipCargo('MISC', 291, 'Tankskip og drivstoffraffinering', SPREADSHEET_SOURCE),
    'Starfarer Gemini': TradingShipCargo('MISC', 243, 'Milit\xe6rt tankskip / Tung st\xf8tte', SPREADSHEET_SOURCE),
    'A2 Hercules': TradingShipCargo('Crusader', 216, 'Tung bomber / Transport', SPREADSHEET_SOURCE),
    'Constellation Taurus': TradingShipCargo('RSI', 174, 'Medium dedikert frakt', SPREADSHEET_SOURCE),
    'Freelancer MAX': TradingShipCargo('MISC', 120, 'Bredboret medium frakt', SPREADSHEET_SOURCE),
    'Mercury Star Runner': TradingShipCargo('Crusader', 114, 'Data- og smuglerskip', SPREADSHEET_SOURCE),
    'Constellation Andromeda': TradingShipCargo('RSI', 96, 'Gunship / Allround frakt', SPREADSHEET_SOURCE),
    'Constellation Aquila': TradingShipCargo('RSI', 96, 'Utforskning / Kartlegging', SPREADSHEET_SOURCE),
    'RAFT': TradingShipCargo('ARGO', 96, 'Spesialisert container-frakt', SPREADSHEET_SOURCE),
    'Constellation Phoenix': TradingShipCargo('RSI', 80, 'Luksus persontransport', SPREADSHEET_SOURCE),
    'Corsair': TradingShipCargo('Drake', 72, 'Ekspedisjon / Tungt ildkraft-skip', SPREADSHEET_SOURCE),
    'Freelancer': TradingShipCargo('MISC', 66, 'Klassisk medium allrounder', SPREADSHEET_SOURCE),
    'C1 Spirit': TradingShipCargo('Crusader', 64, 'Moderne medium frakt', SPREADSHEET_SOURCE),
    'Hull A': TradingShipCargo('MISC', 64, 'Liten ekstern frakt', SPREADSHEET_SOURCE),
    'Cutlass Black': TradingShipCargo('Drake', 46, 'Flerbruk / Piratvirksomhet / Medium frakt', SPREADSHEET_SOURCE),
    '400i': TradingShipCargo('Origin', 42, 'Luksus stifinner / Utforskning', SPREADSHEET_SOURCE),
    '600i Explorer': TradingShipCargo('Origin', 40, 'Store luksus-ekspedisjoner', SPREADSHEET_SOURCE),
    'Hammerhead': TradingShipCargo('Aegis', 40, 'Milit\xe6rt gunship', SPREADSHEET_SOURCE),
    'Freelancer DUR': TradingShipCargo('MISC', 28, 'Utforskning / Drivstoffskanner', SPREADSHEET_SOURCE),
    'Freelancer MIS': TradingShipCargo('MISC', 28, 'Milit\xe6rt gunship / Missilb\xe5t', SPREADSHEET_SOURCE),
    'Nomad': TradingShipCargo('Consolidated', 24, 'Avansert starter med \xe5pent lasteplan', SPREADSHEET_SOURCE),
    '600i Touring': TradingShipCargo('Origin', 16, 'Luksus transport', SPREADSHEET_SOURCE),
    'Vulture': TradingShipCargo('Drake', 16, 'Lett solo-opphugging (Salvage)', SPREADSHEET_SOURCE),
    'Cutlass Red': TradingShipCargo('Drake', 12, 'Medisinsk evakuering (Ambulanse)', SPREADSHEET_SOURCE),
    '315p': TradingShipCargo('Origin', 12, 'Lett utforskning / Pathfinder', SPREADSHEET_SOURCE),
    'Avenger Titan': TradingShipCargo('Aegis', 8, 'Popul\xe6r og fleksibel kampsport-starter', SPREADSHEET_SOURCE),
    'Avenger Titan Renegade': TradingShipCargo('Aegis', 8, 'Kosmetisk variant av Titan', SPREADSHEET_SOURCE),
    '300i': TradingShipCargo('Origin', 8, 'Sivil luksustransport', SPREADSHEET_SOURCE),
    'Syulen': TradingShipCargo('Gatac', 6, 'Fremmedartet (Alien) starter', SPREADSHEET_SOURCE),
    'Aurora CL': TradingShipCargo('RSI', 6, 'Dedikert starter-frakt', SPREADSHEET_SOURCE),
    '135c': TradingShipCargo('Origin', 6, 'Lett luksusfrakt', SPREADSHEET_SOURCE),
    'Reliant Kore': TradingShipCargo('MISC', 6, 'Lett mini-hauler (Vingeskip)', SPREADSHEET_SOURCE),
    'Cutter': TradingShipCargo('Drake', 4, 'Robust, kompakt ekspedisjonsstarter', SPREADSHEET_SOURCE),
    'Mustang Alpha': TradingShipCargo('Consolidated', 4, 'Standard kvikk starter', SPREADSHEET_SOURCE),
    'C8X Pisces Expedition': TradingShipCargo('Anvil', 4, 'Avansert speider / Shuttle', SPREADSHEET_SOURCE),
    'C8 Pisces': TradingShipCargo('Anvil', 4, 'Standard shuttle', SPREADSHEET_SOURCE),
    '325a': TradingShipCargo('Origin', 4, 'Luksus jagerfly med bittelitt cargo', SPREADSHEET_SOURCE),
    '350r': TradingShipCargo('Origin', 4, 'Racing-skip med bittelitt cargo', SPREADSHEET_SOURCE),
    'Cutter Rambler': TradingShipCargo('Drake', 2, 'Langdistanse camper / Starter', SPREADSHEET_SOURCE),
    '100i': TradingShipCargo('Origin', 2, '\xd8konomisk luksusstarter', SPREADSHEET_SOURCE),
    '125a': TradingShipCargo('Origin', 2, 'Lett kampstarter', SPREADSHEET_SOURCE),
    'F7C Hornet Mk1 / Mk2': TradingShipCargo('Anvil', 2, "Med 'Store-All Cargo Box' montert", SPREADSHEET_SOURCE),
    'Redeemer': TradingShipCargo('Aegis', 2, 'Milit\xe6rt gunship (internt mini-grid)', SPREADSHEET_SOURCE),
}


# Supplemental public RSI Ship Matrix rows for ships named in Trading matching
# examples but not present in the provided workbook.
PUBLIC_RSI_SHIP_CARGO = {
    "Starlancer MAX": TradingShipCargo("MISC", 224, "Medium Freight", RSI_SHIP_MATRIX_SOURCE),
    "Starlancer TAC": TradingShipCargo("MISC", 96, "Patrol", RSI_SHIP_MATRIX_SOURCE),
}


MANUFACTURER_ALIASES = {
    "aegis": "aegis dynamics",
    "anvil": "anvil aerospace",
    "argo": "argo astronautics",
    "consolidated": "consolidated outland",
    "crusader": "crusader industries",
    "drake": "drake interplanetary",
    "gatac": "gatac manufacture",
    "greycat": "greycat industrial",
    "misc": "misc",
    "origin": "origin jumpworks",
    "rsi": "roberts space industries",
    "tumbril": "tumbril land systems",
}

MANUFACTURER_WORDS = {
    word
    for names in MANUFACTURER_ALIASES.items()
    for name in names
    for word in normalize_ship_name(name).split()
}

EXPLICIT_ALIASES = {
    "aurora mk i cl": "Aurora CL",
    "aurora mki cl": "Aurora CL",
    "c2 hercules starlifter": "C2 Hercules",
    "crusader c2 hercules starlifter": "C2 Hercules",
    "m2 hercules starlifter": "M2 Hercules",
    "crusader m2 hercules starlifter": "M2 Hercules",
    "a2 hercules starlifter": "A2 Hercules",
    "crusader a2 hercules starlifter": "A2 Hercules",
    "argo raft": "RAFT",
    "drake caterpillar": "Caterpillar",
    "misc hull c": "Hull C",
    "rsi constellation taurus": "Constellation Taurus",
    "drake cutlass black": "Cutlass Black",
    "crusader c1 spirit": "C1 Spirit",
    "misc freelancer max": "Freelancer MAX",
    "misc starlancer max": "Starlancer MAX",
    "zeus mk ii cl": "Zeus CL",
    "rsi zeus mk ii cl": "Zeus CL",
    "zeus mkii cl": "Zeus CL",
    "zeus mk ii es": "Zeus ES",
    "rsi zeus mk ii es": "Zeus ES",
    "zeus mk ii mr": "Zeus MR",
    "rsi zeus mk ii mr": "Zeus MR",
    "f7c hornet mk i": "F7C Hornet Mk1 / Mk2",
    "f7c hornet mk ii": "F7C Hornet Mk1 / Mk2",
}


def trading_ship_cargo_record(ship_name):
    canonical_name = canonical_trading_ship_name(ship_name)
    if not canonical_name:
        return None
    return trading_ship_cargo_records().get(canonical_name)


def trading_ship_cargo_scu(ship_name):
    record = trading_ship_cargo_record(ship_name)
    if not record or record.cargo_scu <= 0:
        return None
    return record.cargo_scu


def trading_ship_names(extra_ship_names=None):
    records = trading_ship_cargo_records()
    names = set(records)
    for ship_name in extra_ship_names or ():
        name = getattr(ship_name, "name", ship_name)
        canonical_name = canonical_trading_ship_name(name)
        if canonical_name and records[canonical_name].cargo_scu > 0:
            names.add(canonical_name)
    return sorted(names, key=lambda value: value.lower())


def trading_ship_cargo_records():
    records = {}
    for name, metadata in PUBLIC_RSI_SHIP_CARGO.items():
        records[name] = metadata
    for name, metadata in SHIP_METADATA.items():
        cargo_scu = metadata.cargo_scu
        if cargo_scu and cargo_scu > 0:
            records[name] = TradingShipCargo(
                manufacturer="N/A",
                cargo_scu=cargo_scu,
                role="N/A",
                source=LOCAL_METADATA_SOURCE,
            )
    records.update(SPREADSHEET_SHIP_CARGO)
    return records


def canonical_trading_ship_name(ship_name):
    normalized = normalize_trading_ship_name(ship_name)
    if not normalized:
        return ""

    explicit = EXPLICIT_ALIASES.get(normalized)
    if explicit and explicit in trading_ship_cargo_records():
        return explicit

    index = trading_ship_index()
    for candidate in normalized_candidates(normalized):
        if candidate in index:
            return index[candidate]

    return ""


def trading_ship_index():
    index = {}
    records = trading_ship_cargo_records()
    for name, metadata in records.items():
        add_index_entry(index, name, name)
        add_index_entry(index, f"{metadata.manufacturer} {name}", name)
        manufacturer_full_name = MANUFACTURER_ALIASES.get(normalize_trading_ship_name(metadata.manufacturer))
        if manufacturer_full_name:
            add_index_entry(index, f"{manufacturer_full_name} {name}", name)
    for alias, canonical in EXPLICIT_ALIASES.items():
        if canonical in records:
            index[normalize_trading_ship_name(alias)] = canonical
    return index


def add_index_entry(index, value, canonical_name):
    normalized = normalize_trading_ship_name(value)
    if normalized:
        index[normalized] = canonical_name


def normalized_candidates(normalized):
    candidates = [normalized]
    without_manufacturer = " ".join(
        part for part in normalized.split() if part not in MANUFACTURER_WORDS
    )
    if without_manufacturer and without_manufacturer not in candidates:
        candidates.append(without_manufacturer)

    without_starlifter = re.sub(r"\bstarlifter\b", "", without_manufacturer).strip()
    without_starlifter = re.sub(r"\s+", " ", without_starlifter)
    if without_starlifter and without_starlifter not in candidates:
        candidates.append(without_starlifter)

    return candidates


def normalize_trading_ship_name(name):
    text = normalize_ship_name(name)
    text = re.sub(r"\bmk ?1\b", "mk i", text)
    text = re.sub(r"\bmk ?2\b", "mk ii", text)
    text = re.sub(r"\bmki\b", "mk i", text)
    text = re.sub(r"\bmkii\b", "mk ii", text)
    return re.sub(r"\s+", " ", text).strip()
