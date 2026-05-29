# Changelog

## Unreleased

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
