from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ShipMetadata:
    min_crew: int | None
    max_crew: int | None
    cargo_scu: int | None


def normalize_ship_name(name):
    text = str(name or "").lower()
    text = text.replace("mk. ii", "mk ii").replace("mkii", "mk ii")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


SHIP_METADATA = {
    "100i": ShipMetadata(1, 1, 2),
    "125a": ShipMetadata(1, 1, 2),
    "135c": ShipMetadata(1, 1, 6),
    "300i": ShipMetadata(1, 1, 8),
    "315p": ShipMetadata(1, 1, 12),
    "325a": ShipMetadata(1, 1, 4),
    "350r": ShipMetadata(1, 1, 4),
    "400i": ShipMetadata(1, 3, 42),
    "600i Explorer": ShipMetadata(3, 5, 40),
    "600i Touring": ShipMetadata(3, 5, 16),
    "85X": ShipMetadata(1, 2, 0),
    "890 Jump": ShipMetadata(3, 5, 160),
    "A2 Hercules": ShipMetadata(1, 8, 216),
    "Arrow": ShipMetadata(1, 1, 0),
    "Aurora CL": ShipMetadata(1, 1, 6),
    "Aurora ES": ShipMetadata(1, 1, 3),
    "Aurora LN": ShipMetadata(1, 1, 3),
    "Aurora LX": ShipMetadata(1, 1, 3),
    "Aurora MR": ShipMetadata(1, 1, 3),
    "Avenger Stalker": ShipMetadata(1, 1, 0),
    "Avenger Titan": ShipMetadata(1, 1, 8),
    "Avenger Warlock": ShipMetadata(1, 1, 0),
    "Blade": ShipMetadata(1, 1, 0),
    "Buccaneer": ShipMetadata(1, 1, 0),
    "C1 Spirit": ShipMetadata(1, 2, 64),
    "C2 Hercules": ShipMetadata(1, 2, 696),
    "C8 Pisces": ShipMetadata(1, 3, 4),
    "C8R Pisces Rescue": ShipMetadata(1, 3, 0),
    "C8X Pisces Expedition": ShipMetadata(1, 3, 4),
    "Carrack": ShipMetadata(4, 6, 456),
    "Caterpillar": ShipMetadata(2, 4, 576),
    "Constellation Andromeda": ShipMetadata(3, 4, 96),
    "Constellation Aquila": ShipMetadata(3, 4, 96),
    "Constellation Phoenix": ShipMetadata(3, 4, 80),
    "Constellation Taurus": ShipMetadata(3, 4, 174),
    "Corsair": ShipMetadata(1, 4, 72),
    "Cutter": ShipMetadata(1, 1, 4),
    "Cutter Rambler": ShipMetadata(1, 1, 2),
    "Cutter Scout": ShipMetadata(1, 1, 2),
    "Cutlass Black": ShipMetadata(1, 3, 46),
    "Cutlass Blue": ShipMetadata(1, 3, 12),
    "Cutlass Red": ShipMetadata(1, 3, 12),
    "Cyclone": ShipMetadata(1, 2, 1),
    "Eclipse": ShipMetadata(1, 1, 0),
    "F7C Hornet Mk II": ShipMetadata(1, 1, 0),
    "F8C Lightning": ShipMetadata(1, 1, 0),
    "Freelancer": ShipMetadata(1, 4, 66),
    "Freelancer DUR": ShipMetadata(1, 4, 36),
    "Freelancer MAX": ShipMetadata(1, 4, 120),
    "Freelancer MIS": ShipMetadata(1, 4, 36),
    "Gladius": ShipMetadata(1, 1, 0),
    "Hammerhead": ShipMetadata(3, 9, 40),
    "Hawk": ShipMetadata(1, 1, 0),
    "Herald": ShipMetadata(1, 1, 0),
    "Hull A": ShipMetadata(1, 1, 64),
    "Hull C": ShipMetadata(2, 4, 4608),
    "M2 Hercules": ShipMetadata(1, 3, 522),
    "M50": ShipMetadata(1, 1, 0),
    "Mercury Star Runner": ShipMetadata(2, 3, 114),
    "Mole": ShipMetadata(1, 4, 96),
    "Mustang Alpha": ShipMetadata(1, 1, 4),
    "Mustang Beta": ShipMetadata(1, 1, 0),
    "Mustang Delta": ShipMetadata(1, 1, 0),
    "Mustang Gamma": ShipMetadata(1, 1, 0),
    "Nomad": ShipMetadata(1, 1, 24),
    "Pisces C8": ShipMetadata(1, 3, 4),
    "Prospector": ShipMetadata(1, 1, 32),
    "Prowler": ShipMetadata(1, 2, 0),
    "RAFT": ShipMetadata(1, 2, 96),
    "Razor": ShipMetadata(1, 1, 0),
    "Reclaimer": ShipMetadata(4, 5, 420),
    "Redeemer": ShipMetadata(3, 5, 2),
    "Reliant Kore": ShipMetadata(1, 2, 6),
    "Reliant Mako": ShipMetadata(1, 2, 0),
    "Reliant Sen": ShipMetadata(1, 2, 2),
    "Reliant Tana": ShipMetadata(1, 2, 1),
    "Retaliator": ShipMetadata(4, 7, 0),
    "Sabre": ShipMetadata(1, 1, 0),
    "Scorpius": ShipMetadata(1, 2, 0),
    "Starfarer": ShipMetadata(4, 7, 291),
    "Terrapin": ShipMetadata(1, 2, 0),
    "Vulture": ShipMetadata(1, 1, 12),
    "Zeus CL": ShipMetadata(1, 3, 128),
    "Zeus ES": ShipMetadata(1, 3, 32),
    "Zeus EX": ShipMetadata(1, 3, 32),
    "Zeus MR": ShipMetadata(1, 3, 16),
}


SHIP_METADATA_INDEX = {
    normalize_ship_name(name): metadata
    for name, metadata in SHIP_METADATA.items()
}

MANUFACTURER_WORDS = {
    "aegis",
    "anvil",
    "argo",
    "banu",
    "consolidated",
    "crusader",
    "drake",
    "esperia",
    "gatac",
    "greycat",
    "misc",
    "mirai",
    "origin",
    "rsi",
    "tumbril",
    "vanduul",
}


def ship_metadata_for(name):
    normalized = normalize_ship_name(name)
    if normalized in SHIP_METADATA_INDEX:
        return SHIP_METADATA_INDEX[normalized]

    without_manufacturer = normalize_ship_name(
        " ".join(
            part
            for part in normalized.split()
            if part not in MANUFACTURER_WORDS
        )
    )
    if without_manufacturer in SHIP_METADATA_INDEX:
        return SHIP_METADATA_INDEX[without_manufacturer]

    return None
