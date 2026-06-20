# Contributing

SC Intel Tool is in active public alpha. The most useful contributions right now
are focused tester reports, small bug fixes and documentation corrections.

## Helpful Feedback

When reporting a bug, include:

- app version
- packaged build or source/dev mode
- Windows version
- steps to reproduce
- expected result
- actual result
- screenshot if it helps explain a layout issue
- safe diagnostics from Settings > About SC Intel Tool > Copy Diagnostics

Do not share private notes, lookup history, watchlists, saved routes, local
database files, private tokens or OCR screenshots unless you intentionally choose
to include them.

## Development Checks

Before proposing code changes, run:

```powershell
.\.venv\Scripts\python.exe -m compileall main.py app
.\.venv\Scripts\python.exe -m pytest
```

For release/build changes, also run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

## Project Boundaries

- Keep tester data local.
- Do not add telemetry, analytics, tracking or cloud sync.
- Keep public Trading workflows UEX-powered unless a future release explicitly
  designs another public data-source path.
- Keep documentation aligned with the current Home, Intel, Industrial,
  Reference and System navigation groups.
- The visible source is provided for transparency and collaboration; no
  open-source license is currently granted.
