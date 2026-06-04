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
- ✓ Mining & Salvage GUI split into focused modules
- ✓ Item Finder GUI split into focused modules
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

### Completed Maintenance Refactor

The first large-file maintenance pass is complete.

- Mining & Salvage was split from one oversized file into focused modules.
- Item Finder was split from one oversized file into focused modules.
- Compatibility wrappers were kept for existing imports.
- Behavior and workflows were preserved.

Remaining optional cleanup:

- Player Lookup can be split later if it starts slowing feature work.
- Additional shared helpers can be extracted when duplication becomes clearer.

### 1. Trading MVP

Goal: build a simple commodity trading workflow first.

Scope:

- Commodity list
- Buy location
- Sell location
- Buy price
- Sell price
- Profit per unit
- Profit per SCU
- Total profit based on cargo capacity
- Basic filters:
  - commodity
  - system/location
  - minimum profit
- Use UEX live/cached data where practical
- Keep the first workflow simple

Out of scope for the first Trading MVP:

- Complex route optimization
- Multi-stop trading
- Risk modeling
- Automatic best route planner
- Fleet planning
- Market prediction
- OCR integration

Implementation phases:

Phase 1:

- Data model and source loading
- Trading tab table layout
- Simple buy/sell comparison

Phase 2:

- Cargo capacity input
- Profit calculations
- Filters and sorting

Phase 3:

- Route quality polish
- Saved/favorite routes later

### 2. Player Intel Expansion

Goal: make player/org context more useful for operational decisions.

- Add deeper organization analysis.
- Improve affiliation context and hidden/redacted messaging where RSI exposes it.
- Improve piracy/risk presentation without inventing data.
- Add player/org watchlists.
- Add custom tag management.

### 3. Wikelo Polish

Goal: make Wikelo tracking smoother without turning it into a spreadsheet clone.

- Improve grouped reward details.
- Add small quality-of-life improvements from user testing.
- Consider optional export/copy tools later.
- Keep checklist data local-only.

### 4. General Polish / Bugfixes

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
- Focused GUI modules for safer future maintenance

Needs work:

- Verify refinery formulas against current game data
- Improve sell-location recommendations
- Improve rock breaker scoring
- Improve equipment details

### Item Finder

Implemented:

- Live Cornerstone item lookup
- SC Focus ship sale/rental data
- Category filtering
- Location details
- Stable table sizing and readability
- Ship deduplication and special/Wikelo handling
- Location search by city, station and shop
- Focused GUI modules for safer future maintenance

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

- Build a small useful commodity route/profit workflow first.
- Avoid trying to solve every market scenario in the first pass.

MVP inputs and outputs:

- Commodity
- Buy location and buy price
- Sell location and sell price
- Profit per unit
- Profit per SCU
- Cargo capacity
- Total profit

MVP filters:

- Commodity
- System/location
- Minimum profit

First implementation phases:

- Phase 1: data loading, table layout and simple buy/sell comparison.
- Phase 2: cargo capacity, profit calculations, filters and sorting.
- Phase 3: route quality polish and saved/favorite routes later.

Out of scope for MVP:

- Multi-stop route optimization
- Risk modeling
- Automatic best-route planning
- Fleet planning
- Market prediction
- OCR integration

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
