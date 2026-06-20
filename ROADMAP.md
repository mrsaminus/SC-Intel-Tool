# SC Intel Tool Roadmap

Last updated: 2026-06-12

SC Intel Tool is a Star Citizen desktop companion for player lookup, local
intel notes, mining and salvage planning, trading, item lookup, Wikelo tracking,
blueprint/crafting reference, watchlists and local app activity events.

The app is in public alpha. The priority before beta is stability, truthful UI,
local data safety, release reliability and tester-driven polish.

## Current Public App

### Home / Branding

- Command-board Home page with app branding.
- Capability overview for major workflows.
- Operational status strip and update status indicator.
- Automatic background update check on launch.
- Dynamic countdown timers.
- Community-made footer and About branding.

### Player Lookup / Search History

- RSI player lookup with avatar/profile card.
- Main organization and affiliation display.
- RSI REDACTED/hidden organization handling.
- Local notes, tags and search history.
- Piracy state shown conservatively from visible org data.
- Player/org watchlist actions and conservative change summaries.

### Mining / Salvage

- Ore Finder, Locations, Scan ID and Quality Bands.
- Refinery sessions, history, salvage materials and gem selling.
- Sell Location Options, Rock Breaker and Equipment tools.
- Packaged builds include the public/minimal bundled mining equipment data
  needed by the app.
- `reference_material/` is maintainer/dev-only and is not bundled wholesale in
  public releases.

### Trading

- Trading parent tab with workflow subtabs.
- UEX Trading is the main live commodity workflow.
- Create Routes is the smart UEX-backed route assistant for ship/cargo/budget
  planning.
- Trade Routes, Best Buyer and En Route now use public UEX price rows where the
  current data exposes enough buy/sell context.
- Saved Routes and Recent Routes are stored locally.
- UEX Trading presets are stored locally.
- Commodity, shop and location reference tools use UEX-derived public market
  rows and local ship cargo metadata.

### Item Finder

- Live item lookup for gear, ships and shopping intel.
- Cornerstone item/location data.
- SC Focus ship sale/rental data.
- Search by item, city, station or shop.
- Location details, ship deduplication and readable tables.

### Wikelo Items

- Wikelo reward browser.
- Grouped reward rows and trade-in option details.
- Local checklist persistence in SQLite.
- Reset selected reward / reset all progress.
- Retired item filtering.

### BP Overview / Crafting

- Native BP Overview and crafting reference workflow.
- Blueprint Browser with search and filters.
- Details panel with ingredients, quantities, quality/effect hints and mission
  drops where public data exposes them.
- Local-only owned blueprint tracking.
- Local-only owned crafting material tracking.
- Craftability and missing-material views.
- Reward Scanner alpha: optional, local-only, region-based and confirmation
  based.

### Watchlists

- Local Watchlists tab for Trading routes/commodities, items/ships, players and
  organizations.
- Manual refresh actions.
- Local snapshots and unread events.
- Activity Log integration.

### Activity Log

- Persistent local app events.
- Search, category filter, severity filter and unread-only toggle.
- Mark read, clear read and copy summaries.
- Receives events from Watchlists, Player Lookup, Search History, Trading and
  BP Overview.

### Notes

- General notes.
- Local player notes through Player Lookup.
- Changelog display.

### Settings / Updates

- App version and About section.
- Active data folder and database path display.
- Check for updates.
- Packaged Windows update install with manual restart.
- GitHub Releases link.

## Completed Alpha Foundation

- Initial pytest-based regression test foundation for updater/version handling,
  AppData paths, SQLite persistence, Mining public runtime data, Reward Scanner
  matching, Watchlists and Trading helpers.
- Maintainer beta-readiness checklist covering smoke tests, packaging, updater,
  migration, privacy and runtime asset validation.
- AppData user data storage and safe migration.
- Local-only SQLite persistence for notes, history, Wikelo progress, watchlists,
  trading presets/routes, owned blueprints and owned crafting materials.
- Windows packaged build pipeline with stable `SC-Intel-Tool.exe` filename.
- Manual-restart updater flow for PyInstaller OneFile reliability.
- Home redesign and branding pass.
- RSI REDACTED organization support.
- GUI split for Mining / Salvage and Item Finder modules.
- Worker-thread pass for slow live-data workflows.
- Table readability and layout polish across major workflows.

## Near-Term Alpha Priorities

### 1. Beta Readiness

- Keep public app scope stable.
- Fix tester-reported regressions.
- Improve launch/update reliability.
- Keep packaged build hygiene tight.
- Avoid major new feature branches before the beta stabilization pass.

### 2. Maintenance / Refactor

- Continue reducing oversized GUI modules when it is low risk.
- Refinery, Search History, Trading tabs, Wikelo and Player Lookup remain the
  highest-risk large modules for future behavior-preserving splits.
- Extract shared helpers only when duplication is obvious.
- Keep behavior-preserving refactors separate from feature work.

### 3. UX Polish

- Tighten layouts after real tester screenshots.
- Improve empty/loading/error states.
- Improve copy/export summaries where users actually need them.
- Keep Home informative without turning it into a cluttered dashboard.

### 4. Trading Polish

- Keep UEX Trading and Create Routes as the public operational trading tools.
- Improve saved/recent route organization.
- Improve route copy/export formatting.
- Consider optional route-quality enrichment from a trading tool only after the
  public UX and access handling have a proper design.

### 5. BP Overview / Crafting Polish

- Improve Blueprint category readability and filtering.
- Improve crafting material entry quality of life.
- Keep Reward Scanner optional, local-only and confirmation-based.
- Package or document OCR support only when it is reliable enough for normal
  users.

### 6. Watchlists / Activity Log Polish

- Improve manual refresh summaries.
- Add optional export/import later.
- Consider OS notifications later, after manual local events are stable.
- Keep everything local-only by default.

## Later Backlog

- Optional OCR improvements for Reward Scanner.
- Optional chat/OCR scanner after privacy and UX are fully designed.
- Optional import/export for notes, watchlists and saved routes.
- Optional backup/restore tools.
- Optional signed Windows releases to reduce SmartScreen warnings.
- Optional GitHub Actions release automation after alpha update flow has more
  mileage.

## Product Direction

SC Intel Tool should feel:

- Dark
- Clean
- Fast
- Practical
- Local-first
- Serious but approachable
- Operational, not noisy

Each section should answer a practical player question:

- Who is this player?
- What public org context is visible?
- What should I track?
- Where can I mine, refine, buy or sell this?
- What is this scan signature?
- Which refinery/session is active?
- What route or crafting decision is worth doing next?
