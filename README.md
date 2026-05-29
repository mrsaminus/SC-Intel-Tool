# SC Intel Tool

SC Intel Tool is a Star Citizen desktop utility for player intel, organization context, mining and salvage planning, item finding, and later trading/watchlists/OCR.

## Current Status

The app is in active alpha development. Player Lookup, Search History, Mining & Salvage, and Item Finder are usable, while Trading, Watchlists, and OCR are planned.

## Run From Source

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Full Mining & Salvage reference data expects the local `reference_material/mining_warchest` folder used by the maintainer build.

## Updates

The Settings tab shows the current app version and includes a `Check For Updates` button.

For normal users, updates should come from GitHub Releases:

[SC Intel Tool Releases](https://github.com/mrsaminus/SC-Intel-Tool/releases)

Source/developer installs can update with git manually.

## User Data

Packaged Windows builds store user data outside the app install folder so updates do not remove notes or history.

Source/development runs use the workspace `sc_intel.db` by default.

The Settings tab shows the active user data folder and database path.

## Build A Windows Release

From the repository root:

```powershell
.\scripts\build_windows.ps1
```

The script installs runtime/dev requirements, builds a single-file Windows executable with PyInstaller, writes it to `dist/`, and prints the SHA256 checksum.

For a portable folder zip instead, run:

```powershell
.\scripts\build_windows.ps1 -Package OneDir
```

Release checklist:

1. Update `APP_VERSION` in `app/version.py`.
2. Update `CHANGELOG.md`.
3. Run smoke tests locally.
4. Run `.\scripts\build_windows.ps1`.
5. Create a GitHub Release with a matching tag, for example `v0.1.0-alpha.2`.
6. Upload the Windows executable and include the SHA256 checksum in the release notes.

## Roadmap

See `ROADMAP.md`.
