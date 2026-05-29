# Changelog

## Unreleased

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
