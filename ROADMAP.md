# SC Intel Tool Roadmap

Last updated: 2026-06-04

SC Intel Tool is a Star Citizen intelligence and utility app for player lookup,
organization context, mining and salvage planning, item finding, Wikelo
tracking, local notes, and future trading/watchlist/OCR workflows.

The app is currently in alpha. The priority is to keep shipping practical,
stable improvements while preserving local user data and keeping live data
requests transparent.

## Current Alpha Status

### Completed Alpha Foundation

- ✓ Home redesign into a command-board style landing page
- ✓ Update system stabilization
- ✓ AppData user data persistence and safe database migration
- ✓ Wikelo checklist persistence and reset controls
- ✓ RSI REDACTED organization support, including live visibility-restriction markup
- ✓ Updater reliability improvements
- ✓ Stable Windows executable filename: `SC-Intel-Tool.exe`
- ✓ GUI split into focused top-level tab modules
- ✓ Worker-thread pass for slow live-data workflows
- ✓ Release pipeline with Windows build script and GitHub pre-releases

### Usable Areas

- Home command board
- Player Lookup and Search History
- Mining & Salvage tools
- Item Finder
- Wikelo Items
- Notes
- Settings and update checks

### Still Early / Placeholder Areas

- Trading
- Watchlists
- Dedicated Organization Intel
- OCR / Chat Scanner

## Near-Term Alpha Priorities

### 1. Large File Split / Maintenance Refactor

Goal: reduce risk as the app grows.

- Split oversized GUI modules where safe, especially Mining & Salvage internals.
- Keep behavior unchanged.
- Preserve current UI and workflows.
- Improve maintainability for future feature work.
- Add focused smoke tests around split areas.

Suggested targets:

- `app/gui/mining_tab.py`
- `app/gui/item_finder_tab.py`
- Shared table/layout helpers if they become clearer after the split

### 2. Trading System Improvements

Goal: build the trading foundation without overpromising a giant system.

- Define the first useful trading workflow.
- Add commodity planning basics.
- Use UEX live data where appropriate.
- Show buy/sell comparison and profit per SCU.
- Later connect refinery outputs and sell-location planning.

### 3. Player Intel Expansion

Goal: make player/org context more useful for operational decisions.

- Add deeper organization analysis.
- Improve affiliation context and hidden/redacted messaging where RSI exposes it.
- Improve piracy/risk presentation without inventing data.
- Add player/org watchlists.
- Add custom tag management.

### 4. Wikelo Polish

Goal: make Wikelo tracking smoother without turning it into a spreadsheet clone.

- Improve grouped reward details.
- Add small quality-of-life improvements from user testing.
- Consider optional export/copy tools later.
- Keep checklist data local-only.

### 5. General Polish / Bugfixes

Goal: keep alpha builds comfortable to test.

- Fix layout issues found in real desktop use.
- Improve loading/error states.
- Keep update flow reliable.
- Add more small smoke tests for high-value workflows.

## Feature Areas

### Home

Implemented:

- Command-board landing page
- Capability overview
- Operational status strip
- Home update status indicator
- Automatic background update check on launch
- Countdown timers with dynamic add/remove behavior
- Local privacy/trust messaging

Needs work:

- Keep layout polished as more modules mature
- Avoid turning Home into a cluttered dashboard

### Player Lookup / Search History

Implemented:

- RSI player lookup
- Avatar/profile card
- Main org and affiliations
- Org logos
- Local notes and tags
- Search history with piracy summary
- Hidden/redacted org handling

Needs work:

- Watchlists
- Better org context
- Better risk/intel presentation
- Export/copy summaries
- Custom tag management

### Mining & Salvage

Implemented:

- Ore Finder
- Locations
- Scan ID
- Quality Bands
- Refinery sessions and history
- Salvage materials
- Gem selling
- Sell Location Options
- Rock Breaker
- Equipment finder

Needs work:

- Verify refinery formulas against current game data
- Improve sell-location recommendations
- Improve rock breaker scoring
- Improve equipment details
- Split large internal code safely

### Item Finder

Implemented:

- Live Cornerstone item lookup
- SC Focus ship sale/rental data
- Category filtering
- Location details
- Stable table sizing and readability
- Ship deduplication and special/Wikelo handling
- Location search by city, station and shop

Needs work:

- Better loading/progress feedback
- Favorites/watchlists
- More robust category coverage as sources change
- Export/copy location results

### Wikelo Items

Implemented:

- Dedicated Wikelo Items tab
- Grouped reward rows
- Details panel with required materials
- Checklist persistence in local SQLite
- Reset selected reward / reset all progress
- Retired item filtering

Needs work:

- More polish around grouped option details
- Optional export/copy checklist
- User feedback pass after more real use

### Trading

Status: placeholder/shell.

Near-term goal:

- Build a small useful route/profit workflow first.
- Avoid trying to solve every market scenario in the first pass.

### Notes

Implemented:

- Notes tab
- Changelog display
- Player-specific notes through Player Lookup

Needs work:

- Global notes improvements
- Search notes
- Import/export later

### Settings / Updates

Implemented:

- Version display
- Active data folder and database path display
- Check for updates
- Install Update for packaged Windows builds
- GitHub Releases link
- AppData migration visibility

Needs work:

- Backup/restore tools
- Optional live data timeout settings
- Code signing later to reduce SmartScreen warnings

## Later Backlog

### Watchlists and Organization Intel

- Player watchlist
- Org watchlist
- Relationship/risk notes
- Allies/enemies/neutral tracking
- Export/import intel data

### OCR / Chat Scanner

- Region selector
- OCR pipeline
- Extract handles from chat
- Auto lookup with rate limiting
- Scan history
- Warnings for known risk tags

### Release Automation

- Consider GitHub Actions build automation
- Consider signed Windows releases
- Keep manual release validation until alpha update flow has more real-world mileage

## Product Direction

The desired feel is:

- Dark
- Clean
- Fast
- Useful
- Serious
- Expandable
- Operational intel, not a toy utility

Each section should answer a practical player question:

- Who is this player?
- What orgs are they connected to?
- Is there known risk?
- Where can I mine, refine, buy or sell this?
- What is this scan signature?
- Which refinery/session is active?
- What should I track next?
