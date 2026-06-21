# Changelog

## Unreleased

### Responsiveness

- Moved Reward Scanner capture/OCR, En Route matching and Create Routes route
  generation into background workers so the GUI remains responsive during
  heavier local workflows.
- Deferred nonessential startup auto-work so Trading reference data and Wikelo
  spreadsheet refreshes start on first use instead of during app launch.

## 0.1.0-alpha.8.8.3 - 2026-06-21

### UI / Navigation

- Reorganized the main navigation into grouped tabs: Home, Intel, Industrial,
  Reference and System.
- Improved navigation hierarchy so top-level grouped tabs stand apart from
  second-level group tabs and smaller module subtabs.
- Prepared the main navigation tab spacing for future icons without adding
  placeholder icons.
- Standardized Activity Log naming across public documentation and navigation.
- Added a Trading module header to match the Mining / Salvage module structure.
- Improved visual consistency across grouped modules.
- Standardized the Mining / Salvage module header wording.

### Themes

- Added Windows XP Black Edition as a supported release theme.
- Inspired the new theme by XP Royale Noir / XP Black community themes while
  preserving the XP green Home/start tab, blue chrome and dark content panels.

### Documentation / Hygiene

- Audited public documentation for current grouped navigation, Activity Log
  naming, UEX-powered Trading wording, supported themes and release hygiene.
- Updated release/build instructions and tester checklists for the current
  public alpha workflow.

## 0.1.0-alpha.8.8.2 - 2026-06-20

### Mining / Salvage

- Includes the Construction Pieces refinery coefficient fixes from
  `0.1.0-alpha.8.8.1`.
- Includes Dinyx/Dynix refinery method alias handling for Construction Pieces
  salvage refinement.
- Includes the Rock Breaker resistance fix so `0` resistance no longer collapses
  required power to zero.

### Settings

- Includes the Settings layout wrapping fix for reduced window widths and larger
  accessibility text sizes.

### Trading

- En Route now works in public builds using UEX prices from the latest refresh.
- Trade Routes and Best Buyer now use UEX-backed public market rows where enough
  buy/sell context is available.
- Commodities and Shops reference tabs now use UEX-derived public reference rows.
- Removed stale legacy Trading copy from public Trading/Settings UI.
- Added Railen Trading cargo metadata so it appears in ship selectors with
  `640 SCU`.

## 0.1.0-alpha.8.8.1 - 2026-06-19

### Mining / Salvage

- Fixed Rock Breaker resistance handling so `0` resistance means no added
  resistance instead of multiplying required power by zero.
- Added Rock Breaker regression tests for `0`, near-zero, decimal and percent
  resistance inputs so accepted formats continue to calculate sensible power.
- Fixed Construction Pieces refinery coefficient coverage for the reported
  `Dynix Solventation` spelling while preserving the existing `Dinyx
  Solventation` method name used by the app.
- Added regression tests for Construction Pieces refinery yields across
  Cormack Method, XCR Reaction, Kazen Winnowing, Thermonatic Deposition,
  Gaskin Process, Electrostarolysis, Dinyx/Dynix Solventation, Pyrometric
  Chromalysis and Ferron Exchange.
- Added an ore-yield control check so salvage coefficient fixes do not change
  ore refinery calculations.

### Settings

- Fixed Settings layout wrapping at reduced window widths and larger text sizes
  so About, runtime and local data path information remains readable.

## 0.1.0-alpha.8.8 - 2026-06-19

### Mining / Salvage

- Added Scan ID search by mineral/resource name while preserving exact, range,
  approximate and comma-separated signature searches.
- Fixed public Mining / Salvage data loading so packaged builds can use bundled
  public location data and built-in quality/refinery fallback tables without
  false missing-data warnings.
- Documented the Mining / Salvage public runtime data bundle and added a
  maintainer-only refresh helper for approved public mining data files.
- Improved Mining / Salvage Overview status wording for packaged/public data.
- Improved Refinery layout balance so the Selling / Profit Summary panel has
  more usable width.
- Fixed multi-material Refinery sell-location results to show shared combined
  sell locations instead of locations that only support one selected material.
- Clarified Rock Breaker resistance input and normalized `10`, `0.10`, `0.1`,
  `2` and similar entries as percentages.
- Fixed Rock Breaker calculations when resistance is entered as `0`.

### Accessibility / UI

- Added a local Appearance text-size setting with Normal, Large and Extra Large
  options to improve readability without changing workflows.

### BP Overview / Crafting

- Enriched mission/drop context display when the blueprint source provides real
  contractor, reputation, location or system fields.
- Kept BP mission context conservative so unavailable mission metadata is not
  inferred or fabricated.

### Hardening / Maintainability

- Added pre-8.8 Refinery regression coverage for session history snapshots,
  shared sell-location intersections, quantity/yield editing, value totals,
  fee handling and session recalculation.
- Improved Copy Diagnostics readability by replacing PyInstaller `_MEI...`
  extraction paths with a stable `<packaged_runtime>` alias.
- Extracted small pure helpers from Refinery and Search History to reduce large
  GUI module complexity without changing workflows.
- Added focused regression tests for Refinery helper math/formatting and Search
  History filtering/sorting helpers.
- Added local rotating file logging for startup, version/runtime paths, database
  path selection, updater checks, failed web requests and background task
  failures.
- Added a safe Copy Diagnostics helper in Settings for tester bug reports with
  redacted local paths and runtime asset status only.
- Hardened logging setup so logging initialization is idempotent and does not
  crash startup if file logging is unavailable.
- Added an initial pytest regression test foundation for version comparison,
  updater script safety, AppData path handling, SQLite persistence, Mining
  public runtime data, Reward Scanner matching, Watchlists and Trading helpers.
- Expanded hardening regression tests for settings fallback, diagnostics
  redaction, optional asset availability, updater no-digest handling, Wikelo
  grouping/checklist persistence and database initialization.
- Added a beta-readiness checklist for source validation, packaged build
  hygiene, updater checks, migration checks, privacy verification and runtime
  asset validation.
- Added an alpha tester checklist covering smoke-test areas, bug report info,
  local logs, SHA256 verification, known alpha limitations and diagnostics
  privacy.
- Updated maintainer release documentation to include compile and pytest
  validation before packaged release builds.

## 0.1.0-alpha.8.7 - 2026-06-13

### Community Branding

- Added new SC Intel Tool app branding/logo as the primary application identity.
- Updated the app/window icon and packaged build icon to use the new SC Intel Tool logo.
- Updated Home and Settings About branding around the new primary app logo.
- Added a UI/branding polish pass for Home, Settings and layout consistency.
- Added a tasteful Star Citizen community branding footer on Home and a matching
  About section in Settings with concise fan-made/legal and privacy wording.
- Kept the `Made By The Community` logo as a smaller community/trust badge.

### Trading

- Added `Create Routes`, a smart Trading workflow for generating UEX-backed routes
  from ship cargo capacity, optional investment budget, system/location filters,
  safety preferences and optimization mode.
- Added ranked Create Routes results with cargo used, investment, expected profit,
  profit per SCU, quality and route notes.
- Added Create Routes details with copy summary, save route and Watchlist actions
  using existing local Trading storage.
- Added local-only persistence for the last Create Routes ship, cargo, filter and
  optimization settings.

### Documentation / Polish

- Updated public alpha documentation to match the current app scope and Trading
  availability.
- Renamed the main tab label to `Mining / Salvage` so Qt does not treat `&` as
  a hidden mnemonic marker.
- Added an advanced Appearance theme system with persistent local theme selection.
- Limited public release theme selection to polished stable themes:
  SC Intel Dark, White Mode, Windows XP Luna and Windows 95 Classic.
- Hid manufacturer-inspired and other experimental themes from the public release
  theme picker until they can receive a fuller authenticity pass.
- Corrected the Windows XP theme toward a more authentic Luna Blue feel with raised
  glossy tabs, beveled panels, inset inputs and brighter early-2000s blue chrome.
- Added stronger Windows XP Luna chrome with a glossy top tab bar and Start-button-style
  inactive Home tab.
- Improved Windows 95 and Windows XP themes with more authentic Win9x and Luna-inspired styling.
- Polished checkbox/filter styling, tab/table states and Home operational status presentation
  through centralized theme color tokens.

## 0.1.0-alpha.8.6 - 2026-06-06

### BP Overview / Crafting

- Added local-only owned crafting material tracking.
- Added Crafting Materials subtab for manually entering material quantities.
- Added selected-blueprint craftability status with required, owned and missing material quantities.
- Added `Craftable only` blueprint filter as a first `What Can I Craft?` workflow.
- Added missing-material Watchlist action from Blueprint Details.
- Added Event Center events when owned crafting material quantities change.
- Improved quality scaling presentation with grouped readable stat ranges.
- Added Reward Scanner alpha foundation for local, optional blueprint reward matching.
- Reward Scanner is off by default, reads only a user-selected region when manually triggered,
  and never marks blueprints owned without user confirmation.
- Added conservative blueprint reward text matcher for pasted/OCR text.
- Added visual `Select Screen Region` overlay for choosing the reward popup area.
- Added `Preview Region` to capture and inspect the selected region once without running OCR.
- OCR engine integration remains deferred; Scan Once handles missing local OCR support gracefully.

### Stabilization

- Fixed pre-release tester issues before publishing alpha.8.6.
- Fixed BP Overview search so SC Craft Tools default-owned blueprints such as
  `Field Recon Suit Arms`, `Core`, `Helmet` and `Legs` remain visible.
- Improved BP category dropdown readability with wider field and popup sizing.
- Polished Mining Refinery layout so the selling/profit summary is more compact
  and sell-location options get more useful space.
- Confirmed the main mining tab label.
- Deduplicated Refinery sell-location rows by normalized location and material,
  using the best valid UEX sell value when duplicate source rows exist.
- Added a small bundled public mining equipment data set for packaged builds
  without bundling local `reference_material`.
- Removed `Diamond` from refinery ore buttons.
- Restored `Aslarite` as a refinery ore option.
- Ran BP Overview regression coverage for blueprint loading, craftability, Reward Scanner parsing,
  manual confirmation and Event Center integration.
- Prepared the app version for the next alpha build.

## 0.1.0-alpha.8.5 - 2026-06-06

### Release Stabilization

- Prepared the app for a larger public alpha release after Trading, Watchlists,
  Event Center, Player/org tracking and BP Overview additions.
- Audited build hygiene so local `reference_material` data remains excluded from
  public packaged releases.
- Kept advanced access storage local-only.
- Kept update install behavior on manual restart to avoid PyInstaller OneFile
  restart/DLL issues.
- Ran release-readiness validation across source, packaged build and live data sources.

### BP Overview / Crafting

- Added a new BP Overview main tab for Star Citizen blueprints and crafting.
- Added a Blueprint Browser powered by the public SC Craft Tools blueprint endpoint.
- Added blueprint search, category/source filters, owned-only and missing-only filters.
- Added recipe/details view with ingredients, quantities, quality/effect hints
  and mission/source context where available.
- Added Copy Recipe Summary for Discord-friendly crafting summaries.
- Added local-only `owned_blueprints` SQLite storage for owned blueprint tracking.
- Added an Owned Blueprints subtab for local progress review.
- Added SC Craft Tools and SCMDB data-source research documentation.
- Kept OCR/screen-reader capture, account sync and deeper inventory import out of scope for this alpha pass.

### Roadmap / Public Scope

- Clarified that public Player Lookup, Search History, Watchlists and Event Center stay neutral.
- Clarified that advanced private intel mapping is out of scope for the public app.

### Stabilization

- Ran a full alpha stabilization and regression pass after the Trading, Watchlists and Event Center additions.
- Moved the Event Center main tab after Wikelo Items so it sits with the tracking/workflow tools.
- No feature behavior changes intended in this pass.

### Event Center / Intel Tracking

- Added a new Event Center main tab for persistent local app events.
- Added local `notification_events` storage with categories, severity, read state and metadata.
- Watchlist events now also appear in Event Center.
- Added Player watchlists with manual RSI refresh and snapshot comparison.
- Added Organization watchlists with manual RSI org-detail refresh where public SID data is available.
- Added conservative Player/Org change events for redacted visibility changes, org changes,
  piracy status changes, lookup failures and recovered lookups.
- Added Player Lookup actions for quick re-check, Add Player to Watchlist and Add Main Org to Watchlist.
- Added Player Lookup change summary against the previous stored lookup.
- Added Search History pin/favorite flags, quick re-run lookup and watchlist actions.
- Added Search History change summaries when a fresh lookup is loaded.
- Event Center, Player/Org Watchlists and lookup-change tracking are local-only.

### Watchlists

- Added a new local-only Watchlists main tab.
- Added SQLite storage for watchlist entries, snapshots and unread events.
- Added Watchlists Overview, Trading, Items & Ships and Intel subtabs.
- Added manual refresh actions for selected/all active watches.
- Added copy summary, mark events read, enable/disable and delete watch actions.
- Added UEX Trading integration for watching selected commodities and complete routes.
- Added Saved Routes integration for adding saved/recent routes to Watchlists.
- Added Item Finder integration for adding selected items and ships to Watchlists.
- Item/Ship watches store current known metadata locally; live refresh remains planned.
- Player and organization watchlists now support manual refresh and local event tracking.

### Trading

- Reorganized Trading into workflow subtabs.
- Moved the existing UEX commodity workflow into the `UEX Trading` subtab.
- Added planned external trading workflow tabs for Trade Routes, Best Buyer,
  En Route, Commodities and Shops.
- Added an external trading reference Commodities browser.
- Added an external trading reference Shops browser.
- Added external trading Best Buyer and En Route workflow scaffolding.
- Added graceful unavailable states for external trading workflows.
- Added searchable dropdown behavior across Trading selection fields.
- Added ship selection with local cargo-capacity autofill for Trading workflows.
- Added external trading Trade Routes workflow scaffolding with public fallback.
- Added automatic public Trading reference-data loading for commodities,
  shops, locations and ships.
- Expanded Trading ship dropdowns with external trading reference ship names,
  while keeping Cargo SCU autofill limited to known local ship metadata.
- Filtered Trading ship dropdowns to only include ships with known Cargo SCU
  capacity.
- Restored full Trading cargo metadata from the provided `SCU Kapasitet`
  spreadsheet reference, with spreadsheet values taking priority over older
  local ship metadata.
- Added route quality indicators for UEX Trading, Trade Routes and En Route.
- Improved Trading route/buyer summaries with clearer buy/sell, cargo, cost,
  profit, source and warning details.
- Added Copy Route Summary actions for Trading route-style workflows.
- Improved unavailable, empty-result and request-failure states in Trading workflows.
- Added local Saved Routes and Recent Routes storage for complete Trading routes.
- Added a Saved Routes subtab with search, details, copy, delete saved and clear recent actions.
- Added UEX Trading presets for ship, cargo, investment and filter settings.
- Added Save Route actions where Trading workflows expose complete buy/sell route data.
- Added Copy Details actions for Commodities and Shops reference subtabs.
- Trading saved routes, recent routes and presets are local-only SQLite data.
- Kept UEX trading behavior, filters, live refresh and SCU calculations unchanged.

### Maintenance

- Split Mining / Salvage GUI into focused modules.
- Split Item Finder GUI into focused modules.
- Kept compatibility wrappers for existing imports.
- No behavior changes intended.
- Improves maintainability before Trading and Watchlists expansion.

## 0.1.0-alpha.8.4.2 - 2026-06-04

### Fixed

- Fixed live RSI REDACTED affiliation detection.
- Player Lookup now correctly detects hidden/redacted affiliations from real RSI markup.
- REDACTED affiliations no longer show as `0 linked orgs`.
- REDACTED affiliations no longer show as `No affiliations loaded`.
- Search History details now correctly display REDACTED affiliation state.
- Piracy now shows as `Unknown` when affiliation data is hidden.

### Updater Reliability

- Update install now finishes and asks users to manually start `SC-Intel-Tool.exe`.
- Disabled automatic restart after update install to avoid PyInstaller OneFile `_MEI/python312.dll` startup failures.
- Improved update reliability for alpha builds.

### Home / UX

- Final Home command-board polish.
- Improved Operational Status strip layout.
- Improved Home update status indicator.
- Automatic background update checks remain non-blocking.
- Improved timer panel behavior and layout stability.

## 0.1.0-alpha.8.4.1 - 2026-06-04

- Disabled automatic app restart after update install to avoid PyInstaller OneFile restart failures.
- Updater now asks users to start `SC-Intel-Tool.exe` manually after a successful replacement.

## 0.1.0-alpha.8.4 - 2026-06-03

### Home / UX

- Redesigned Home into a command-board style landing page.
- Added an operational status section with version, runtime, data path and update source.
- Added a compact update status indicator on Home.
- Added automatic background update checking on launch without blocking the UI.
- Improved Home countdown timer layout, panel balance and natural growth behavior.
- Polished capability overview cards and Home spacing.

### Updater

- Fixed PowerShell variable interpolation in the generated update installer script.
- Hardened the updater restart flow for packaged PyInstaller builds.
- Added safer restart verification before considering an update successful.
- Added rollback-safe behavior if the updated app fails to launch.
- Added cleanup of `.previous` after successful updated-app startup.
- Standardized Windows release artifacts on the stable filename `SC-Intel-Tool.exe`.

### Updates

- Fixed prerelease version comparison for alpha dot-chain versions.
- Fixed alpha.8.1 to alpha.8.2 update detection.
- Improved Home and Settings update availability consistency.
- Kept legacy versioned Windows executable assets as update fallback.

### Player Lookup

- Added support for RSI REDACTED organization data.
- Hidden main organizations now display as hidden/redacted instead of empty.
- Hidden affiliations now show redacted messaging instead of "No affiliations loaded."
- Piracy is shown as Unknown when organization data is hidden.

### Wikelo

- Added persistent Wikelo checklist state.
- Added reset controls for selected reward and all Wikelo progress.
- Improved Wikelo reward grouping and details display.
- Added retired item filtering.

### Data

- Moved user data to `%LOCALAPPDATA%\SC-Intel-Tool\` by default.
- Added safe migration from the old local app-folder database.
- AppData database is preferred when both old and new databases exist.
- Settings now shows active data and database paths.

## 0.1.0-alpha.8.3 - 2026-06-03

- Fixed Settings update UI availability detection so `Install Update` enables when a newer prerelease exists.

## 0.1.0-alpha.8.2 - 2026-06-03

- Fixed prerelease update detection so dot-chain alpha versions such as `alpha.8.1` and `alpha.8.2` compare correctly against `alpha.8`.

## 0.1.0-alpha.8.1 - 2026-06-03

- Fixed a PowerShell syntax error in the generated update installer script by using safe `${Path}:` variable interpolation.
- Changed Windows release builds to use the stable executable filename `SC-Intel-Tool.exe` while keeping versioning in tags, release notes and app metadata.
- Updated the in-app updater to prefer `SC-Intel-Tool.exe` release assets while still supporting legacy versioned Windows executable assets.

## 0.1.0-alpha.8 - 2026-06-03

- Moved local user data to `%LOCALAPPDATA%\SC-Intel-Tool\` by default with safe migration from the old local database.
- Added persistent Wikelo checklist progress and reset controls.
- Improved Wikelo reward grouping, retired-item filtering and required-material display.
- Improved Home countdown timers with dynamic naming and multiple independent timers.
- Improved Item Finder table usability, ship price display, duplicate handling and single-location display.
- Improved Refinery editing, small-window usability and salvage refinery yield handling.
- Expanded repository hygiene, privacy/user-data documentation and local artifact ignores.

## 0.1.0-alpha.7 - 2026-05-30

- Improved table readability across Player Intel, Mining / Salvage and Item Finder views.
- Added Refinery scroll/layout protection so small windows stay readable instead of compressing controls.
- Cleaned up unused imports and generated Python cache files.
- Improved README privacy, install, run and update guidance.

## 0.1.0-alpha.6 - 2026-05-29

- Hardened the Windows auto-update installer with post-copy hash checks, file unblocking, delayed restart and explicit working directory.
- Changed one-file Windows builds to extract runtime files beside the executable instead of the system Temp folder to reduce `_MEI` startup failures.

## 0.1.0-alpha.5 - 2026-05-29

- Added the BALDER icon to the app window and packaged Windows executable.
- Added a Changelog panel under Notes so users can see release changes in-app.

## 0.1.0-alpha.4 - 2026-05-29

- Added an in-app Install Update flow for packaged Windows builds.
- Improved update checks to select the Windows executable from GitHub Releases.
- Added clearer update-check messages when release metadata is private or unavailable.

## 0.1.0-alpha.3 - 2026-05-29

- Added Item Finder location searches for city, station and shop names using Cornerstone location inventory data.
- Improved the Item Finder results table so the Summary column fills remaining width by default.

## 0.1.0-alpha.2 - 2026-05-29

- Switched the default Windows release build to a single-file executable.
- Fixed bundled reference data lookup for packaged PyInstaller builds.

## 0.1.0-alpha.1 - 2026-05-29

- Split the GUI into focused modules under `app/gui/`.
- Moved live lookups and slow network calls to worker threads.
- Improved responsiveness for local table filtering.
- Added app version metadata.
- Added Settings update check against GitHub Releases.
- Added packaged-build user data path handling.
- Added Windows portable build script.
- Hardened the Windows build script against locked build files and native command failures.
- Verified the first portable Windows build with a packaged-app smoke test.
- Renamed unclear ship earning labels to special acquisition/Wikelo wording in Item Finder.
- Improved Item Finder availability wording, summary scrolling, and Cornerstone location separators.
- Added a dedicated Wikelo category for special-acquisition ships in Item Finder.
- Added horizontal padding to table cells across the app.
