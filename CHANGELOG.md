# Changelog

## Unreleased

### Trading

- Reorganized Trading into workflow subtabs.
- Moved the existing UEX commodity workflow into the `UEX Trading` subtab.
- Added planned SC Trade Tools workflow tabs for Trade Routes, Best Buyer,
  En Route, Commodities and Shops.
- Added a token-free SC Trade Tools Commodities browser.
- Added optional local SC Trade Tools API token support in Settings.
- Added a token-free SC Trade Tools Shops browser.
- Added token-aware SC Trade Tools Best Buyer and En Route workflow tabs.
- Added graceful no-token states for token-gated SC Trade Tools workflows.
- Added searchable dropdown behavior across Trading selection fields.
- Added ship selection with local cargo-capacity autofill for Trading workflows.
- Added SC Trade Tools-backed Trade Routes workflow with token-aware fallback.
- Kept UEX trading behavior, filters, live refresh and SCU calculations unchanged.

### Maintenance

- Split Mining & Salvage GUI into focused modules.
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

- Improved table readability across Player Intel, Mining & Salvage and Item Finder views.
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
