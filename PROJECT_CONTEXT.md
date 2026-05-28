Perfekt 😄 Da gjør vi det ordentlig én gang, så slipper vi halvrot senere.

**Slett alt** i `PROJECT_CONTEXT.md` og lim inn **hele denne**:

````md
# SC Intel Tool — Project Context

## Goal

Build a custom Star Citizen intelligence and utility app.

The goal is to create a serious, useful, expandable Star Citizen utility tool focused on:

- RSI player lookup
- Organization lookup
- Local player notes and tags
- Watchlists
- Mining intelligence
- Ore finding
- Refinery tools
- Profit tools
- OCR / chat scanning later
- Player intelligence tools
- NOVA-style operational utility

This project is being built as a completely new clean Python application.

Older extracted applications are used as **reference/inspiration only**, not as direct source code to patch or modify.

---

## Current App Status

A basic PySide6 application is already functional.

### Current Project Structure

```text
SC_IntelTool/
├─ main.py
├─ requirements.txt
├─ PROJECT_CONTEXT.md
└─ app/
   ├─ __init__.py
   ├─ database.py
   ├─ rsi_lookup.py
   └─ gui.py
````

### Current Features

* PySide6 GUI
* Dark UI
* Tab system
* Player Lookup tab
* Mining tab (placeholder)
* Notes tab (placeholder)
* Settings tab (placeholder)
* SQLite database
* Player lookup history
* Player notes
* Player tagging system
* Basic RSI player lookup

---

## Tech Stack

Use:

* Python
* PySide6
* requests
* beautifulsoup4
* lxml
* SQLite
* Pillow

### Preferred Architecture

* UI separated from logic
* Modular file structure
* SQLite for local data
* JSON/CSV/XLSX import support
* Readable, maintainable Python
* Clean expandable code

### Avoid

* Giant single-file scripts
* Tight coupling between UI and logic
* Tkinter unless legacy comparison requires it

---

## Reference Sources Used

The following tools/files have been analyzed and are used as reference material only.

---

### 1. SC_Player_Lookup.exe

Safely extracted without execution.

### Findings

* PyInstaller-packed Python application
* Main file appears to be:

```text
sc_lookup.pyw
```

### Technologies Used

* tkinter
* requests
* BeautifulSoup
* json
* keyboard
* win32gui
* win32api
* win32con

### Relevant Features

* RSI player lookup
* Organization lookup
* GUI
* Overlay / window handling
* Hotkeys
* Local config
* Local player data

---

### 2. SC_TOOLS-Chat_Reader-0.0.8-alpha.zip

Identified internally as:

```text
NovaScan
```

### Important Files

```text
scanner.py
ocr.py
scraper.py
results.py
region_selector.py
config.json
config.example.json
```

### Relevant Features

* OCR-based Star Citizen global chat scanner
* Username extraction
* RSI player lookup
* Organization lookup
* Piracy detection from org pages
* Screenshot region selector
* HTML report generation
* Auto-scan functionality

### Future Modules Inspired By This

* Chat Scanner
* Auto player lookup
* OCR username extraction
* Pirate warnings
* Exportable reports
* Scan history

---

### 3. ElguapoesWarchestV1.1.7-Windows.zip

Mining-related reference data.

### Useful Files Found

```text
Mineral_Where.txt
Mineral_Stats.xlsx
Refinery.xlsx
rock-breaking-calculator-data.json
Lasers and Modules Stats.csv
price_cache_default.json
market_cache_default.json
equipment_shops_cache_default.json
quantization_laranite.json
quantization_tungsten.json
```

Additional quantization JSON files exist for other minerals.

### Relevant Mining Data

* Ore locations
* Mineral stats
* Refinery data
* Mining lasers
* Mining modules
* Mining gadgets
* UEX price cache
* Market terminal data
* Equipment shop data
* Rock breaking data

### Future Mining Modules

* Ore Finder
* Best Location Finder
* Stanton/Pyro filtering
* Refinery Calculator
* Profit Calculator
* Rock Breaking Calculator
* Equipment Finder

---

## Planned App Sections

---

### Player Lookup

### Should Show

* RSI handle
* Display name
* Avatar
* Citizen Record
* Enlisted date
* Location
* Fluency
* Main organization
* Organization SID
* Organization rank (if available)
* Organization member count (if available)
* Profile URL

### Player Tools

* Save local notes
* Add local tags
* Open RSI profile
* Copy handle
* Lookup history
* Cached lookups
* Watchlist
* Last seen tracking (future)

### Tags

* Unmarked
* Friendly
* Neutral
* Hostile
* Pirate
* Scammer
* NOVA
* Defence
* Relief
* Skyline
* Frontiers
* Core
* B.A.L.D.E.R.

---

### Organization Intel

### Should Show

* Organization name
* SID
* Member count
* Archetype
* Commitment
* Visibility
* Recruiting status
* Roleplay status (if available)
* Links
* Piracy indicators

### Future Features

* Organization watchlist
* Organization risk score
* Known allies/enemies
* Relationship tracking

---

### Mining

### First Milestone

* Import/load mining data
* Search ore by name
* Show where ore can be found
* Filter by system:

  * Stanton
  * Pyro
* Show best locations

### Later Features

* Mineral stats
* Rock difficulty
* Laser recommendations
* Module recommendations
* Refinery calculator
* Profit calculator
* Equipment finder
* Price tracking

---

### Chat Scanner (Later Milestone)

### Planned Features

* Select chat region on screen
* OCR Star Citizen chat
* Extract player names
* Auto lookup players
* Auto flag hostile/pirate/scammer players
* Export scan results
* Save history
* Auto scanning

---

### Settings

### Planned Features

* Theme settings
* Data folder paths
* RSI timeout
* Cache settings
* Export/import
* OCR scan interval
* Chat region selection
* Database backup tools

---

## Development Rules

### Architecture Rules

* Build clean modules
* Keep UI separate from logic
* Avoid giant scripts
* Prefer maintainable code
* Build one working milestone at a time

### Data Rules

* SQLite for local storage
* JSON/CSV/XLSX importers
* Cache external lookups when reasonable
* Never rely entirely on live websites

### Safety Rules

* Never run unknown EXE files
* Treat extracted/decompiled code as reference only
* Rebuild functionality cleanly

---

## Current Development Priority

### Phase 1 — Player Lookup

Priority order:

1. Reliable RSI lookup
2. Better player card layout
3. Avatar support
4. Open RSI profile button
5. Enter key search
6. Better notes/tag UI
7. Lookup history panel
8. Lookup caching

### Phase 2 — Mining

After Player Lookup is stable:

1. Import mining data
2. Ore finder
3. Stanton/Pyro filtering
4. Best locations
5. Refinery tools
6. Profit calculations

### Phase 3 — OCR / Chat Scanner

After Mining:

1. OCR scanning
2. Username detection
3. Auto lookup
4. Pirate warnings
5. Export tools

---

## Desired Final Feel

The application should feel like a serious Star Citizen operational intelligence tool.

Desired feel:

* Dark
* Clean
* Fast
* Useful
* Professional
* Expandable
* Serious

The application should feel closer to a real operational utility program than a hobby script with buttons.
