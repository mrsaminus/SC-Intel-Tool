# SC Intel Tool

SC Intel Tool is a Star Citizen desktop utility for player intel, organization context, mining and salvage planning, item finding, and later trading/watchlists/OCR.

## Current Status

The app is in active alpha development. Player Lookup, Search History, Mining & Salvage, and Item Finder are usable, while Trading, Watchlists, and OCR are planned.

## Install And Run

### Development / Source Install

```powershell
python -m venv .venv
pip install -r requirements.txt
python main.py
```

Full Mining & Salvage reference data expects the local `reference_material/mining_warchest` folder used by the maintainer build.

### Packaged Release

Download the packaged release from [GitHub Releases](https://github.com/mrsaminus/SC-Intel-Tool/releases). For portable ZIP releases, extract the ZIP and run the executable inside the extracted folder. For current single-executable alpha releases, download and run the Windows executable directly.

## Updates

The Settings tab shows the current app version and includes a `Check For Updates` button.

For normal users, updates should come from GitHub Releases:

[SC Intel Tool Releases](https://github.com/mrsaminus/SC-Intel-Tool/releases)

The in-app update check uses GitHub's public Releases API, so the repository or
release metadata must be public for normal users.

Packaged Windows builds can install updates from the Settings tab. The app
downloads the newest Windows executable, closes itself, replaces the old
executable, and starts again. Source/developer installs should update with git
manually using `git pull`.

Packaged builds store user data outside the install folder, so updates should preserve notes and lookup history.

## Privacy

SC Intel Tool has no telemetry, analytics, tracking, or user reporting. Player notes, lookup history, settings, and local database data are not sent to the developer.

The app only makes outbound requests to public Star Citizen-related data sources needed for its features: RSI, UEX, Cornerstone, SC Focus, the public Wikelo Google Sheet, and GitHub Releases for update checking. All user data remains local unless the user explicitly exports it.

## User Data

Packaged Windows builds store user data outside the app install folder so updates do not remove notes or history.

Source/development runs use the workspace `sc_intel.db` by default.

The Settings tab shows the active user data folder and database path.

## Windows SmartScreen

Early alpha builds are unsigned, so Windows may show an "Unknown publisher" SmartScreen warning. Reducing this for normal users requires Authenticode code signing with a trusted certificate and release reputation over time.

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
5. Create a GitHub Release with a matching tag, for example `v0.1.0-alpha.6`.
6. Upload the Windows executable and include the SHA256 checksum in the release notes.

## Roadmap

See `ROADMAP.md`.
