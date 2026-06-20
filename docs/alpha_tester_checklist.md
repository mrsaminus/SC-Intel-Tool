# Alpha Tester Checklist

Use this checklist when testing SC Intel Tool alpha builds or when reporting a
bug. The goal is practical tester feedback without sharing private local data.

## What To Test

- Launch the app from `SC-Intel-Tool.exe`.
- Open each navigation group and tab:
  - Home
  - Intel: Player Lookup, Search History, Watchlists
  - Industrial: Mining / Salvage, Trading, BP Overview
  - Reference: Item Finder, Wikelo Items
  - System: Activity Log, Notes, Settings
- Confirm your saved local data survives an app restart:
  - notes/tags
  - Search History
  - Wikelo checklist progress
  - owned blueprints/materials
  - Trading routes/presets
  - Watchlists
  - theme/settings
- Try at least one live lookup or refresh where relevant:
  - RSI Player Lookup
  - UEX Trading refresh
  - Wikelo refresh
  - BP Overview data load
- Try failure paths too:
  - disconnect network and confirm refreshes fail gracefully
  - cancel update/install prompts
  - leave optional fields blank

## Bug Report Info To Include

- App version.
- Whether you are running packaged `SC-Intel-Tool.exe` or source/dev mode.
- Windows version.
- What you clicked before the issue happened.
- What you expected to happen.
- What actually happened.
- Screenshot if it helps explain layout or display issues.
- The latest local log file if comfortable sharing it.
- Safe diagnostics copied from Settings > About SC Intel Tool > Copy Diagnostics.

Do not include:

- Private tokens or credentials.
- personal notes
- Search History contents
- player notes/tags
- watchlists
- saved routes
- local database contents
- OCR text or screenshots unless you intentionally choose to share them

## Logs

Logs are local only and are not sent anywhere automatically.

Default Windows location:

```text
%LOCALAPPDATA%\SC-Intel-Tool\logs\sc_intel_tool.log
```

The log is rotated locally when it grows. Older rotated logs may appear next to
the current log file.

## Safe Diagnostics

Settings includes a `Copy Diagnostics` button in the About section. It copies
safe local runtime information for bug reports:

- app version
- runtime mode
- Python/runtime version
- OS/platform
- redacted local paths
- database/log path locations
- expected runtime asset availability

Diagnostics intentionally do not include tokens, notes, history, watchlists,
saved data, OCR text or database contents.

## Version And Hash Verification

- Confirm the version in Settings.
- Download builds only from GitHub Releases.
- Compare the release SHA256 with the local file:

  ```powershell
  Get-FileHash .\SC-Intel-Tool.exe -Algorithm SHA256
  ```

## Known Alpha Limitations

- Builds are unsigned, so Windows SmartScreen warnings are expected.
- Live websites/APIs can change or fail.
- Some advanced Trading workflows are still alpha-quality and depend on current
  public UEX market data availability.
- Reward Scanner is alpha and depends on local capture/OCR behavior.
- UI polish is ongoing, especially around unusual window sizes and older themes.
- Supported release themes are SC Intel Dark, White Mode, Windows XP Luna,
  Windows XP Black Edition and Windows 95 Classic.

## Privacy

SC Intel Tool is local-only. It does not include telemetry, analytics, tracking,
cloud sync or automatic user reporting. Logs and diagnostics stay on your
machine unless you choose to share them.
