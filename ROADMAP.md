# SC Intel Tool Roadmap

Last updated: 2026-05-29

SC Intel Tool is a Star Citizen intelligence and utility app for player lookup,
organization intel, mining and salvage planning, item finding, and later OCR/chat
scanning.

The app is built as a clean Python/PySide6 desktop application. Reference tools
and extracted data are used as inspiration and source material only; the app
implementation is rebuilt cleanly.

## Current Status

The project has moved beyond the original basic prototype. Player intel is close
to MVP quality, and Mining & Salvage now has several working tools.

### Main App Shell

Implemented:

- PySide6 desktop GUI
- Dark intel-style visual theme
- Main tabs:
  - Player Lookup
  - Search History
  - Mining & Salvage
  - Trading
  - Item Finder
  - Notes
  - Settings
- SQLite local database for player notes, tags, and lookup history
- Live data fetches for RSI, UEX, Cornerstone, and SC Focus where relevant
- External price/lookups are kept in memory unless explicitly stored as local app data

Needs work:

- Split large UI code into smaller modules as features grow
- Add a cleaner app configuration layer
- Add better error logging/debug output for live data failures
- Add packaging/release workflow

## Player Intel

### Implemented

- RSI player lookup by handle
- Enter-key lookup flow
- Profile card layout
- Avatar loading
- Citizen record, enlisted date, location, and fluency
- Main organization details:
  - Name
  - SID
  - Rank
  - Type
  - Commitment
  - Exclusivity
  - Member count
  - Piracy status
  - Logo
- Affiliated organization lookup
- Affiliate org cards with logo, SID, rank, member count, and piracy status
- Open RSI profile
- Open organizations page
- Open main org page
- Copy handle
- Local player notes
- Local player tags:
  - Unmarked
  - Friendly
  - Neutral
  - Hostile
  - Pirate
  - Scammer

### Search History

Implemented:

- Dedicated Search History tab
- One row per player handle
- Name, org, and piracy summary
- Piracy status includes both main org and affiliation orgs
- YES/NO color highlighting
- Filter by name, org, and SID
- Filter by piracy status
- Sortable columns
- Remove selected history row
- Clear all history
- Select a history row to load an intel-style detail card
- Stored fallback display if live lookup fails

Needs work:

- Dedicated watchlist separate from passive lookup history
- Last seen / last checked timestamps with clearer UI
- Export player intel/history
- Optional manual override for piracy/risk notes
- Custom tag management
- Better handling for RSI page changes and lookup throttling

## Organization Intel

Implemented inside Player Lookup:

- Main organization summary
- Affiliated organization summary
- Org logos
- Org profile links
- Piracy detection from org data

Needs work:

- Dedicated Organization Intel tab or submodule
- Organization search by SID/name
- Organization watchlist
- Relationship tracking:
  - Allies
  - Enemies
  - Neutral orgs
  - Known pirate/scammer orgs
- Organization risk score
- Member count tracking over time

## Mining & Salvage

Mining & Salvage is now a major app section with internal tabs.

### Overview

Implemented:

- Overview dashboard with clickable cards
- Data status summary
- Loaded mining reference data count
- Clear pointers to each mining subtool

Needs work:

- Better short explanations for new users
- Status indicators for live data freshness

### Ore Finder

Implemented:

- Search minerals by name
- Filter by system
- Filter by deposit type
- Show mineral, system, body/area, deposit, UEX sell, best UEX terminal, and notes
- Live UEX refresh for visible minerals
- Notes use clearer wording such as "No known location" and "Best location"
- Table layout now stretches/fits better

Needs work:

- Stronger grouping for duplicated mineral/body rows
- Better "best value" sorting
- Optional hide/show unavailable locations

### Locations

Implemented:

- Grouped location view
- Filter by system
- Filter by mining type
- Shows minerals available per body/location
- Uses mining reference data

Needs work:

- Better planning view for routes
- Highlight top bodies for selected ores
- Add known cave/asteroid/surface metadata where available

### Scan ID

Implemented:

- Scan signature identifier
- Supports exact values, approximate values, and ranges
- Uses scan signature chart data

Needs work:

- More operator-friendly result ranking
- Better explanation of overlapping scan values
- Optional quick-copy results

### Quality Bands

Implemented:

- Resource quality bands from uploaded/reference data
- Search/filter by resource
- Score band columns
- Matched band helper for entered quality score
- Uses verified quality-band HTML/data as source of truth

Needs work:

- Explain quality-score interpretation in the UI
- Optional color legend in the table itself

### Refinery

Implemented:

- Refinery sessions
- User-defined session names
- Multiple active session tabs
- Session timers that continue running while switching sessions
- Session history tab
- Remove selected history row
- Clear history
- Refinery station dropdown
- Refinery method dropdown
- Ore chooser
- Separate salvage material chooser
- Gem selling section for ROC/FPS mineables that cannot be refined
- QTY input in cSCU and SCU
- Yield display in cSCU and SCU
- Auto-estimated yield from refinery station and method
- Manual yield edits when in-game quote differs
- Refinery fee
- Sell Value and Net Value summary
- Live UEX refresh for selected materials
- UEX prices are in-memory only
- Sell Location Options for selected/refined materials
- Sell location table supports dynamic height and content-based column widths

Needs work:

- Verify refinery formulas against more current game data
- Verify salvage refinery yield/time behavior against current game data
- Add processing-time estimation from station/method/material data if available
- Add better "best sell location" recommendations
- Consider grouping sell locations by "buys all selected materials" versus partial matches
- Optional export/share session summary
- Persist saved refinery history only if the user wants it

### Rock Breaker

Implemented:

- Rock profile inputs:
  - Mass
  - Resistance
  - Instability
- Laser filter
- Baseline setup rows when no rock data is entered
- Analysis rows when rock stats are entered
- Laser/module power window estimates
- Risk notes
- Table layout improvements

Needs work:

- Improve calculation model with more in-game validation
- Add module/gadget selection
- Add recommended setup scoring
- Add warnings for impossible or high-risk rocks

### Equipment

Implemented:

- Equipment finder inside Mining & Salvage
- Search equipment
- Filter by type
- Filter by size
- Mining lasers
- Mining modules
- Mining gadgets
- Salvage equipment
- Shop/location data where available

Needs work:

- Improve equipment source freshness
- Add item details panel
- Link equipment rows to Item Finder where possible
- Add better recommendations based on mining mode

## Item Finder

Implemented:

- Dedicated main tab
- Live item lookup from Cornerstone
- Ship sale/rental lookup from SC Focus
- Cornerstone ships are skipped in favor of SC Focus ship data
- Automatic live data load on first search
- Live data refresh interval behavior
- Category filtering
- Availability shown as location count
- Items marked Not Sold are skipped
- Buy locations panel
- Open item and open location buttons
- Price formatting with thousands separators
- Tables use content-based widths with horizontal scroll
- Location search by city, station, and shop name using Cornerstone location inventory data

Needs work:

- Add more robust category coverage as Cornerstone changes
- Better loading/progress feedback because first live load can appear frozen
- Cache policy decision:
  - currently live/in-memory is preferred
  - future optional cache could be user-controlled
- Add favorite items/watchlist
- Add export/copy location results

## Trading

Implemented:

- Main Trading tab placeholder/shell

Needs work:

- Define exact scope:
  - commodity trading
  - hauling routes
  - buy/sell comparison
  - profit per SCU
  - risk notes
- Pull live price data from UEX
- Add route planner
- Connect refinery output and sell locations to Trading

## Notes

Implemented:

- Main Notes tab placeholder
- Player-specific notes already work in Player Lookup

Needs work:

- Global notes
- Watchlist notes
- Org notes
- Export/import notes
- Search notes

## Settings

Implemented:

- Main Settings tab
- Current app version display
- Check for updates button
- GitHub Releases link
- User data folder display
- Database path display
- Open user data folder action

Needs work:

- Theme/settings controls
- RSI timeout setting
- UEX timeout setting
- Live data refresh settings
- Database backup/restore
- Export/import user data
- OCR/chat scanner settings later

## Release, Packaging & Updates

Status: in progress.

This is required before the app is comfortable for other people to download and
use without a Python development setup.

Planned:

- Standalone Windows build script
- GitHub Releases for public downloads
- Version number visible in the app
- `Check for updates` button in Settings
- Update check against the latest GitHub Release
- Open release page when a newer version is available
- Release notes/changelog shown before updating
- Simple installer or portable zip release
- Clear separation between user data and app install files
- Database/user notes preserved during app updates
- Optional backup prompt before major updates
- SHA256 checksums for release artifacts
- Release build smoke test before publishing

Recommended update approach:

- Source/developer installs can update from git manually.
- Standalone user installs should update from GitHub Releases, not by running
  `git pull` inside the packaged app.
- The first version can simply open the newest GitHub Release page.
- A later version can add a smoother in-app downloader/installer flow.

Release workflow needs:

- Decide first public version tag, for example `v0.1.0-alpha.1`
- Add an app version constant
- Add changelog/release notes
- Add build script for standalone packaging
- Add GitHub Actions workflow for release builds
- Attach release artifacts to GitHub Releases
- Add code signing so Windows SmartScreen can show a trusted publisher
- Document install/update steps in README

## OCR / Chat Scanner

Status: not started.

Planned:

- Select chat region on screen
- OCR Star Citizen chat
- Extract player handles
- Auto lookup detected players
- Flag hostile/pirate/scammer players
- Save scan history
- Export scan results
- Optional auto-scan mode

Dependencies/decisions needed:

- OCR engine choice
- Region selector implementation
- Hotkey strategy
- How aggressive auto lookup should be
- Rate limiting and failure handling for RSI lookups

## Technical Debt / Refactor Targets

Important before the app grows much more:

- Split `app/gui.py` into smaller UI modules:
  - main_window.py
  - player_lookup_tab.py
  - search_history_tab.py
  - mining_tab.py
  - item_finder_tab.py
  - trading_tab.py
  - notes_tab.py
  - settings_tab.py
  - styles.py
- Split Mining & Salvage internals further if needed:
  - refinery_widget.py
  - ore_finder_widget.py
  - rock_breaker_widget.py
  - equipment_widget.py
- Move network calls out of direct GUI execution and into worker threads
- Add release/build automation for standalone downloads
- Add update-check service against GitHub Releases
- Add unit tests for parsers and calculations
- Add smoke tests for major tabs
- Add structured logging
- Add better handling for network failures
- Review all live data source assumptions

## Current Priority List

### Priority 1: Split `app/gui.py` --Complete--

This is the next major engineering task.

Goal:

- Preserve current functionality
- Keep the same UI and behavior
- Keep imports clean
- Keep `python main.py` working
- Move the main window to `app/gui/main_window.py`
- Move each main tab into its own file under `app/gui/`
- Move style/theme code to `app/gui/styles.py`

Initial target structure:

```text
app/gui/
|-- __init__.py
|-- main_window.py
|-- player_lookup_tab.py
|-- search_history_tab.py
|-- mining_tab.py
|-- trading_tab.py
|-- item_finder_tab.py
|-- notes_tab.py
|-- settings_tab.py
`-- styles.py
```

Out of scope for this priority:

- No redesign
- No behavior changes
- No worker-thread refactor yet
- No deeper Mining & Salvage internal split yet

Verification:

- App launches with `python main.py`
- All main tabs load
- Player lookup still works
- Search History still works
- Mining & Salvage tabs still load
- Item Finder still loads

### Priority 2: Move Network Calls To Worker Threads --Complete--

After the GUI split is complete and verified, move slow live-data calls out of
the GUI thread so the app does not appear frozen while fetching data.

Worker-thread order:

1. Item Finder live load
2. UEX refresh calls
3. Cornerstone item location lookups
4. RSI player/org lookups
5. SC Focus ship data refresh

Expected result:

- Buttons show clear loading states
- The app remains responsive during live lookups
- Errors are returned to the UI cleanly
- No behavior changes beyond better responsiveness

### Priority 2.1: Responsiveness Polish --Complete--

Tighten the remaining UI responsiveness issues before starting release work.

Implemented:

- Debounced local table filters for Mining & Salvage subtools
- Debounced Item Finder search/category filtering
- Debounced Search History filtering
- Reduced unnecessary table redraw work while filtering
- Ignored stale Item Finder location results when the selected item changes
- Ignored stale Search History detail results when another row is selected
- Verified quick typing/filtering with offscreen smoke tests

### Priority 3: Release Pipeline

Status: in progress.

Build the release/update foundation before the first alpha goes out.

Implemented:

- App version constant
- Version display in Settings/About
- `Check for updates` button
- Latest GitHub Release metadata check
- In-app `Install Update` flow for packaged Windows builds
- Release page button
- Packaged-build user data path for preserving SQLite data across updates
- Windows portable build script
- First Windows portable artifact built and smoke-tested
- README install/update/build instructions
- Changelog starter
- Release checklist in README
- Single-file Windows executable release
- First GitHub alpha releases published

Remaining:

- Confirm `Check for updates` can see the published release metadata
- Make release metadata publicly reachable before relying on in-app update checks
- Smoke-test automatic update from one packaged release to the next
- Add code signing certificate support to reduce Windows SmartScreen warnings
- Add GitHub Actions release build later if desired

Preferred release model:

- Single-file executable for normal users
- Portable zip/folder builds remain available for debugging
- Installer later if needed
- Update checks should use public GitHub Releases for normal users
- Packaged Windows builds should install updates directly from Settings
- Git updates should remain a developer/source-install workflow only

### Priority 4: Finish Mining & Salvage Core

Bring Mining & Salvage to alpha-ready quality.

- Verify refinery calculations and sell-location behavior
- Improve refinery formulas where better data is available
- Improve rock breaker recommendations
- Improve equipment details
- Add better sell location/routing logic
- Fix remaining Mining & Salvage UI layout issues
- Add basic smoke tests for major Mining & Salvage tabs

### Priority 5: First Alpha Release

Publish the first usable public build.

- Verify player lookup and history flows
- Verify Mining & Salvage core flows
- Add README with install/run/update instructions
- Add screenshots
- Build standalone Windows artifact
- Publish first GitHub alpha release
- Confirm `Check for updates` can see the release metadata

### Priority 6: Trading

- Build trading route/profit calculator
- Use UEX live data
- Connect refinery output to trading/selling decisions
- Add trading-specific smoke test

### Priority 6.1: App Update

- Publish a follow-up release with Trading included
- Confirm updater/release-page flow works from the previous alpha

### Priority 7: Watchlists And Organization Intel

- Add player watchlist
- Add org watchlist
- Add custom tags
- Add relationship/risk notes
- Add export/import for intel data

### Priority 7.1: App Update

- Publish a follow-up release with Watchlists and Organization Intel included
- Confirm existing user database data is preserved

### Priority 8: OCR / Chat Scanner

- Build region selector
- Add OCR pipeline
- Extract handles from chat
- Auto lookup with rate limiting
- Show scan results and warnings

### Priority 8.1: App Update

- Publish a follow-up release with OCR/chat scanner included
- Confirm update notes clearly explain the new permissions/dependencies

### Priority 9: New Features

Future feature ideas should be evaluated after the alpha/update cycle proves
that the app can ship, update, and preserve user data safely.

## Suggested Next Milestones

### Milestone 1: GUI Split

- Split the current `app/gui.py` into focused modules
- Keep behavior and UI unchanged
- Verify that the app launches and all tabs load

### Milestone 2: Worker Threads

- Move live data fetching out of the GUI thread
- Prioritize Item Finder, UEX, Cornerstone locations, and RSI lookup
- Add clearer loading and error states

### Milestone 3: Release Pipeline

- Add app versioning
- Add Check for Updates
- Add standalone Windows build
- Document install and update flow

### Milestone 4: Finish Mining & Salvage Core

- Improve refinery formulas
- Improve rock breaker recommendations
- Improve equipment details
- Add better sell location/routing logic

### Milestone 5: First Alpha Release

- Verify Player Intel and Mining & Salvage flows
- Add README and screenshots
- Publish first alpha build through GitHub Releases

### Milestone 6: Trading

- Build trading route/profit calculator
- Use UEX live data
- Connect refinery output to trading/selling decisions

### Milestone 6.1: Trading Update

- Publish a follow-up app release with Trading included

### Milestone 7: Watchlists and Organization Intel

- Add player watchlist
- Add org watchlist
- Add relationship/risk notes
- Add export/import for intel data

### Milestone 7.1: Watchlist Update

- Publish a follow-up app release with Watchlists and Organization Intel included

### Milestone 8: OCR / Chat Scanner

- Build region selector
- Add OCR pipeline
- Extract handles from chat
- Auto lookup with rate limiting
- Show scan results and warnings

### Milestone 8.1: OCR Update

- Publish a follow-up app release with OCR/chat scanner included

### Milestone 9: New Features

- Evaluate and prioritize new ideas after the release/update cycle is proven

## Product Direction

The desired feel is:

- Dark
- Clean
- Fast
- Useful
- Serious
- Expandable
- Star Citizen operational intel, not a toy utility

The app should prioritize practical workflows over decorative UI. Each section
should answer a real player question:

- Who is this player?
- What orgs are they connected to?
- Is there piracy/risk?
- Where can I mine or sell this?
- What is this scan signature?
- Which refinery/session is active?
- Where can I buy this item?
- What should I do next?
