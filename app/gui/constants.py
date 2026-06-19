TAG_COLORS = {
    "Unmarked": ("#5e737c", "#13202a"),
    "Friendly": ("#58e6a6", "#0f2a22"),
    "Neutral": ("#d1d9df", "#1c252d"),
    "Hostile": ("#ff6b6b", "#331718"),
    "Pirate": ("#ff9f43", "#321f0d"),
    "Scammer": ("#ff5fd2", "#321329"),
}

IMAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 SC-Intel-Tool",
}

SHIP_ORE_MATERIALS = [
    ("QUAN", "Quantainium"),
    ("STIL", "Stileron"),
    ("SAVR", "Savrilium"),
    ("RICC", "Riccite"),
    ("LIND", "Lindinium"),
    ("GOLD", "Gold"),
    ("BORS", "Borase"),
    ("BEX", "Bexalite"),
    ("TARA", "Taranite"),
    ("BERL", "Beryl"),
    ("AGRI", "Agricium"),
    ("TUNG", "Tungsten"),
    ("TITA", "Titanium"),
    ("LARA", "Laranite"),
    ("TORI", "Torite"),
    ("ASLA", "Aslarite"),
    ("ICE", "Ice"),
    ("QUAR", "Quartz"),
    ("HEPH", "Hephaestanite"),
    ("ALUM", "Aluminum"),
    ("TIN", "Tin"),
    ("COPP", "Copper"),
    ("CORU", "Corundum"),
    ("IRON", "Iron"),
    ("SILI", "Silicon"),
    ("INER", "Inert Materials"),
]

SALVAGE_REFINERY_MATERIALS = [
    ("RUBL", "Construction Rubble"),
    ("PIEC", "Construction Pieces"),
    ("CSAL", "Construction Salvage"),
]

GEM_SELLING_MATERIALS = [
    ("JANA", "Janalite"),
    ("HADA", "Hadanite"),
    ("FEYN", "Feynmaline"),
    ("BERA", "Beradom"),
    ("DOLV", "Dolivine"),
    ("GLAC", "Glacosite"),
    ("APHO", "Aphorite"),
    ("CARI", "Caranite"),
    ("JACL", "Jaclium"),
    ("SALD", "Saldynium"),
]

SHIP_REFINERY_MATERIALS = SHIP_ORE_MATERIALS + SALVAGE_REFINERY_MATERIALS + GEM_SELLING_MATERIALS

SALVAGE_REFINERY_DETAILS = {
    "Construction Rubble": {
        "density": "Highest density",
        "yield": "Lowest yield",
        "time": "Fastest refinery processing time",
        "yield_multiplier": 0.7,
    },
    "Construction Pieces": {
        "density": "Medium density",
        "yield": "Medium yield",
        "time": "Medium refinery processing time",
        "yield_multiplier": 1.0,
    },
    "Construction Salvage": {
        "density": "Lowest density",
        "yield": "Highest yield",
        "time": "Longest refinery processing time",
        "yield_multiplier": 1.3,
    },
}

REFINERY_STATIONS = [
    "Any refinery",
    "No Refinery (Sell Raw Ore)",
    "Arc-L1: Wide Forest Station",
    "Arc-L2: Lively Pathway Station",
    "Arc-L4: Faint Glen Station",
    "CRU-L1: Ambitious Dream Station",
    "HUR-L1: Green Glade Station",
    "HUR-L2: Faithful Dream Station",
    "ST-MAG: Magnus Gateway",
    "MIC-L1: Shallow Frontier Station",
    "MIC-L2: Long Forest Station",
    "MIC-L5: Modern Icarus Station",
    "ST-PYR: Pyro Gateway",
    "ST-TER: Terra Gateway",
    "Checkmate Station",
    "Orbituary Station",
    "Ruin Station",
    "PYR-ST: Stanton Gateway",
    "Levski Station",
    "NYX-ST: Stanton Gateway",
]

REFINERY_METHODS = [
    "Dinyx Solventation",
    "Cormack Method",
    "Electrostarolysis",
    "Ferron Exchange",
    "Gaskin Process",
    "Kazen Winnowing",
    "Pyrometric Chromalysis",
    "Thermonatic Deposition",
    "XCR Reaction",
]

REFINERY_METHOD_YIELD_FALLBACKS = {
    "Dinyx Solventation": 0.45,
    "Ferron Exchange": 0.45,
    "Pyrometric Chromalysis": 0.45,
    "Thermonatic Deposition": 0.382,
    "Electrostarolysis": 0.382,
    "Gaskin Process": 0.382,
    "Kazen Winnowing": 0.315,
    "Cormack Method": 0.315,
    "XCR Reaction": 0.315,
}

SALVAGE_REFINERY_METHOD_YIELD_FALLBACKS = {
    "Cormack Method": 0.14,
    "XCR Reaction": 0.14,
    "Kazen Winnowing": 0.14,
    "Thermonatic Deposition": 0.17,
    "Thermodeposition": 0.17,
    "Electrostarolysis": 0.17,
    "Electrostarlosis": 0.17,
    "Gaskin Process": 0.17,
    "Dinyx Solventation": 0.20,
    "Dynix Solventation": 0.20,
    "Pyrometric Chromalysis": 0.20,
    "Ferron Exchange": 0.20,
}
