# Beta Readiness Checklist

Use this checklist before promoting an alpha build to wider beta testing. The
goal is not perfection; it is a predictable, privacy-preserving build that
starts cleanly, keeps user data safe, and fails gracefully.

## 1. Source Validation

- Run:

  ```powershell
  .\.venv\Scripts\python.exe -m compileall main.py app
  .\.venv\Scripts\python.exe -m pytest
  ```

- Confirm the app starts from source:

  ```powershell
  .\.venv\Scripts\python.exe main.py
  ```

- Smoke test main tabs:
  - Home
  - Player Lookup
  - Search History
  - Mining / Salvage
  - Trading
  - Item Finder
  - Wikelo Items
  - BP Overview
  - Watchlists
  - Event Center
  - Notes
  - Settings

## 2. Privacy Verification

- Confirm no telemetry, analytics, tracking, crash reporting or cloud sync was
  added.
- Confirm user data remains local-only unless the user explicitly exports it.
- Confirm Reward Scanner remains off by default and only scans a user-selected
  region after a manual action.
- Confirm no screenshots, OCR text, notes, watchlists, player history or local
  database contents are uploaded to the developer.

## 3. User Data / Migration

- Fresh run creates:

  ```text
  %LOCALAPPDATA%\SC-Intel-Tool\sc_intel.db
  ```

- Source/dev overrides still work:

  ```powershell
  $env:SC_INTEL_DATA_DIR = "C:\Temp\SC-Intel-Tool-Data"
  $env:SC_INTEL_DB_PATH = "C:\Temp\SC-Intel-Tool-Data\sc_intel.db"
  ```

- Old local `.\sc_intel.db` migrates only when the AppData database does not
  already exist.
- Existing AppData database is never overwritten by migration.
- Verify persistence after restart:
  - Player notes/tags
  - Search History
  - Wikelo checklist
  - Owned blueprints/materials
  - Trading presets/routes
  - Watchlists
  - Event Center events
  - Theme/settings

## 4. Runtime Asset Verification

- Confirm packaged build includes required public assets:
  - app logo/icon
  - community badge
  - changelog
  - `app/assets/mining_public/`

- Confirm packaged build does not include:
  - `reference_material/`
  - local databases
  - cache/log/export/backup folders
  - temp folders
  - `__pycache__/`
  - `*.pyc`
  - maintainer-only notes

- Inspect PyInstaller archive:

  ```powershell
  .\.venv\Scripts\pyi-archive_viewer.exe -l -b .\dist\SC-Intel-Tool.exe |
      Select-String -Pattern "mining_public|reference_material|sc_intel.db|cache|logs|exports|backups|temp|__pycache__|.pyc"
  ```

  Expected: public runtime assets are present; private/local/generated data is
  absent.

## 5. Packaged Build

- Build:

  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
  ```

- Confirm `dist\SC-Intel-Tool.exe` exists.
- Confirm `dist` contains only expected release artifacts.
- Generate SHA256:

  ```powershell
  Get-FileHash .\dist\SC-Intel-Tool.exe -Algorithm SHA256
  ```

- Launch packaged executable from a clean folder.
- Confirm:
  - app opens without DLL/PyInstaller `_MEI` errors
  - app icon/window/taskbar branding is correct
  - AppData path is used, not executable folder
  - themes load
  - Settings opens and shows correct version/data paths

## 6. Feature Smoke Tests

### Player Lookup

- Visible-org lookup works.
- REDACTED-org lookup shows hidden/redacted state, not `0 linked orgs`.
- Notes/tags save locally.
- Search History receives and displays lookup data.

### Mining / Salvage

- Overview shows no false missing-reference warnings.
- Ore Finder finds `Laranite`.
- Locations finds a known mineral/location.
- Quality Bands loads.
- Equipment finds `Lancet`.
- Rock Breaker calculates with resistance `0`, `0.10` and `10`.
- Refinery opens and live UEX refresh fails gracefully if network is unavailable.

### Trading

- UEX Trading opens.
- Create Routes opens.
- Saved Routes opens.
- SC Trade Tools public reference tabs open.
- Token-gated public-build workflows degrade gracefully.
- Route copy/save/watch actions do not crash.

### BP Overview / Reward Scanner

- Blueprint Browser loads or fails gracefully.
- Owned blueprint/material persistence works.
- Reward Scanner is off by default.
- Region preview failure is handled without crashing.
- Pasted text matching works without OCR.

### Wikelo / Watchlists / Event Center

- Wikelo loads or fails gracefully.
- Checklist state persists after restart.
- Reset selected/all Wikelo progress only affects Wikelo checklist state.
- Watchlist entry/snapshot/event persistence works.
- Event Center filters and read/unread actions work.

## 7. Updater Verification

- Settings update check runs in background and does not freeze the UI.
- Prerelease version comparison handles alpha dot releases.
- Stable asset `SC-Intel-Tool.exe` is preferred.
- Legacy `*-windows.exe` assets are still accepted as fallback.
- Downloaded update size is checked against GitHub metadata when available.
- SHA256 digest is checked when GitHub asset metadata provides it.
- Installer PowerShell script parses.
- Installer replaces the executable and asks the user to restart manually.
- Auto-restart is not attempted.
- `.previous` rollback file is preserved on failure and cleaned after successful
  replacement.

## 8. Release Hygiene

- `git status --short` is clean before tagging.
- Version in `app/version.py` matches the tag.
- `CHANGELOG.md` has a concise entry.
- README/ROADMAP do not describe hidden or unavailable public features.
- Release notes include SHA256 and privacy statement.
- GitHub release is marked pre-release until beta.
- Artifact attached is exactly `SC-Intel-Tool.exe`.

## 9. Known Beta Limitations

- Builds are unsigned, so SmartScreen warnings are expected.
- Live data sources can fail or change format.
- Full OCR engine packaging is not yet guaranteed.
- SC Trade Tools token-backed workflows are intentionally not exposed in public
  Settings.
- Large GUI modules still need incremental refactor, especially Refinery,
  Search History, Trading tabs, Wikelo and Player Lookup.
