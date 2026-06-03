# Changelog

## Unreleased

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
