import re
from dataclasses import dataclass

import requests

from .version import APP_VERSION, GITHUB_RELEASES_API, GITHUB_RELEASES_URL


class UpdateCheckError(Exception):
    pass


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    release_name: str
    release_url: str
    published_at: str
    update_available: bool


def check_for_updates(timeout=10):
    response = requests.get(
        GITHUB_RELEASES_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "SC-Intel-Tool",
        },
        timeout=timeout,
    )

    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise UpdateCheckError("GitHub Releases response was not a release list.")

    release = next((item for item in payload if not item.get("draft")), None)
    if not release:
        raise UpdateCheckError("No GitHub Release has been published yet.")

    latest_version = str(release.get("tag_name") or release.get("name") or "").strip()
    if not latest_version:
        raise UpdateCheckError("Latest GitHub Release did not include a version tag.")

    return UpdateInfo(
        current_version=APP_VERSION,
        latest_version=latest_version,
        release_name=str(release.get("name") or latest_version),
        release_url=str(release.get("html_url") or GITHUB_RELEASES_URL),
        published_at=str(release.get("published_at") or ""),
        update_available=is_newer_version(latest_version, APP_VERSION),
    )


def is_newer_version(latest, current):
    latest_key = version_key(latest)
    current_key = version_key(current)
    return latest_key > current_key


def version_key(value):
    text = str(value or "").strip().lower()
    text = text.removeprefix("v")

    numeric_part, _, suffix = text.partition("-")
    numbers = [
        int(match.group(0))
        for match in re.finditer(r"\d+", numeric_part)
    ]
    while len(numbers) < 3:
        numbers.append(0)

    release_rank = 0 if suffix else 1
    suffix_rank = prerelease_rank(suffix)
    return (*numbers[:3], release_rank, suffix_rank)


def prerelease_rank(suffix):
    if not suffix:
        return 999999

    numbers = [int(match.group(0)) for match in re.finditer(r"\d+", suffix)]
    number = numbers[0] if numbers else 0

    if "dev" in suffix:
        return number
    if "alpha" in suffix:
        return 100 + number
    if "beta" in suffix:
        return 200 + number
    if "rc" in suffix:
        return 300 + number

    return 10 + number
