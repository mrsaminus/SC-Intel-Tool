# SC Intel Tool Roadmap

Last updated: 2026-06-05

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

Current status:

- Trading is now organized as a parent tab with workflow subtabs.
- UEX Trading is the active MVP workflow.
- Phase 1 complete: UEX live data loading and basic buy/sell comparison table.
- Phase 2 complete: cargo capacity, optional max investment, profit per SCU,
  estimated buy cost, estimated total profit, filtering and numeric sorting.
- Phase 3 complete: route quality filters and SCU-based calculations.
- SC Trade Tools Commodities subtab now uses token-free commodity endpoints.
- SC Trade Tools Shops subtab now uses token-free shop/location endpoints.
- Optional local SC Trade Tools API token support is available in Settings.
- Trading selection fields use searchable/type-filterable dropdowns.
- Ship selection can auto-fill Cargo SCU from local ship metadata where known.
- Token-free Trading reference data now auto-loads in the background for
  commodities, shops, locations and ships.
- Ship dropdowns are expanded with SC Trade Tools ship names; Cargo SCU remains
  local metadata or manual entry when unknown.
- Trade Routes, Best Buyer and En Route subtabs are token-aware and degrade
  gracefully when no token is configured.

Scope:

- Commodity list
- Buy location
- Sell location
- Buy price
- Sell price
- Buy/sell price per SCU
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

- Data model and source loading - complete
- Trading tab table layout - complete
- Simple buy/sell comparison - complete

Phase 2:

- Cargo capacity input - complete
- Profit calculations - complete
- Filters and sorting - complete

Phase 3:

- Route quality polish - complete
- Saved/favorite routes later

Trading data source notes:

- Current MVP source: UEX commodity price data.
- UEX Trading remains the active subtab for the current MVP.
- Commodities uses token-free SC Trade Tools commodity item and item-type
  endpoints as a reference browser.
- Shops uses token-free SC Trade Tools commodity shop and location endpoints.
- Trade Routes, Best Buyer and En Route use token-required SC Trade Tools tool endpoints
  when the user configures an optional token locally in Settings.
- SC Trade Tools API research completed; see `docs/trading_data_sources.md`.
- Recommendation: keep UEX as the primary MVP data source for now.
- SC Trade Tools is best treated as an optional token-backed source for route
  quality workflows because its most useful route/transaction endpoints require
  a token.
- Token-free SC Trade Tools endpoints may still be useful for commodity,
  shop, location, ship and crowdsourced listing metadata.
- Current Trading UX uses token-free SC Trade Tools reference data to avoid
  first-use manual dropdown loading.

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

Status: early usable MVP.

Near-term goal:

- Improve the small commodity route/profit workflow without jumping straight
  to full route optimization.
- Keep UEX Trading as the active MVP subtab.
- Keep SC Trade Tools subtabs as planned workflows until token/auth handling is
  intentionally designed.
- Avoid trying to solve every market scenario in the first pass.

MVP inputs and outputs:

- Commodity
- Buy location and buy price
- Sell location and sell price
- Buy/sell price per SCU
- Profit per SCU
- Cargo capacity
- Total profit

MVP filters:

- Commodity
- System/location
- Minimum profit

First implementation phases:

- Phase 1: data loading, table layout and simple buy/sell comparison - complete.
- Phase 2: cargo capacity, profit calculations, filters and sorting - complete.
- Phase 3: route quality polish and SCU calculation cleanup - complete.
- Phase 4: saved/favorite routes later.

Current subtab structure:

- UEX Trading - active MVP workflow.
- Commodities - token-free SC Trade Tools commodity reference browser.
- Shops - token-free SC Trade Tools shop/location reference browser.
- Trade Routes - token-aware SC Trade Tools trade route workflow.
- Best Buyer - token-aware SC Trade Tools buyer lookup workflow.
- En Route - token-aware SC Trade Tools along-route workflow.

Trading Data Sources:

- UEX remains the primary MVP source because it currently supports token-free
  live commodity price loading in the app.
- SC Trade Tools has useful public metadata endpoints for commodities, shops,
  locations, ships and crowdsourced commodity listings.
- SC Trade Tools trade routes, buyer-finder and itinerary workflows are
  available when a user configures an optional local API token in Settings.
- SC Trade Tools commodity transaction and commodity report endpoints still
  require a token and need a focused design pass before they become production
  workflows.
- Future path: consider SC Trade Tools as an opt-in/token-backed source for
  route optimization once the basic Trading workflow is stable.

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
