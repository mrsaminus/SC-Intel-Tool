# Security Policy

SC Intel Tool is a local-first desktop app. It does not include telemetry,
analytics, tracking, crash reporting or cloud sync.

## Reporting A Vulnerability

Please report security issues privately. Use GitHub private vulnerability
reporting if it is available for the repository, or contact the maintainer
directly before opening a public issue.

Do not include private user data unless it is strictly necessary to demonstrate
the issue.

## Sensitive Data

Bug reports and diagnostics should not include:

- local database files
- player notes or tags
- search history
- watchlists
- saved routes
- OCR text or screenshots
- private tokens or credentials

The Settings > About SC Intel Tool > Copy Diagnostics helper is designed to
include only safe runtime information such as version, runtime mode, platform,
data/log path locations and runtime asset status.

## Supported Builds

Public alpha builds are unsigned and may show Windows SmartScreen warnings. Only
download packaged builds from GitHub Releases.
