import re
import logging
from dataclasses import dataclass

import requests

from .version import APP_VERSION, GITHUB_RELEASES_API, GITHUB_RELEASES_URL

WINDOWS_EXECUTABLE_NAME = "SC-Intel-Tool.exe"
logger = logging.getLogger(__name__)


class UpdateCheckError(Exception):
    suppress_worker_traceback = True


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    release_name: str
    release_url: str
    published_at: str
    update_available: bool
    asset_name: str = ""
    asset_url: str = ""
    asset_size: int = 0
    asset_digest: str = ""


def check_for_updates(timeout=10):
    logger.info("Checking GitHub Releases for updates.")
    try:
        response = requests.get(
            GITHUB_RELEASES_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "SC-Intel-Tool",
            },
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        logger.warning("GitHub update check failed with HTTP %s.", response.status_code)
        raise update_error_from_response(response) from exc
    except requests.RequestException as exc:
        logger.warning("GitHub update check request failed: %s", exc)
        raise UpdateCheckError(f"Could not contact GitHub Releases: {exc}") from exc

    payload = response.json()
    if not isinstance(payload, list):
        raise UpdateCheckError("GitHub Releases response was not a release list.")

    release = next((item for item in payload if not item.get("draft")), None)
    if not release:
        raise UpdateCheckError("No GitHub Release has been published yet.")

    latest_version = str(release.get("tag_name") or release.get("name") or "").strip()
    if not latest_version:
        raise UpdateCheckError("Latest GitHub Release did not include a version tag.")

    asset = find_windows_asset(release) or {}
    update_available = is_newer_version(latest_version, APP_VERSION)
    logger.info(
        "Latest release found: current=%s latest=%s update_available=%s asset=%s size=%s digest=%s",
        APP_VERSION,
        latest_version,
        update_available,
        asset.get("name") or "",
        asset.get("size") or 0,
        bool(asset.get("digest")),
    )

    return UpdateInfo(
        current_version=APP_VERSION,
        latest_version=latest_version,
        release_name=str(release.get("name") or latest_version),
        release_url=str(release.get("html_url") or GITHUB_RELEASES_URL),
        published_at=str(release.get("published_at") or ""),
        update_available=update_available,
        asset_name=str(asset.get("name") or ""),
        asset_url=str(asset.get("browser_download_url") or ""),
        asset_size=int(asset.get("size") or 0),
        asset_digest=str(asset.get("digest") or ""),
    )


def find_windows_asset(release):
    assets = release.get("assets") or []
    if not isinstance(assets, list):
        return None

    executable_assets = [
        asset
        for asset in assets
        if str(asset.get("name") or "").lower().endswith(".exe")
    ]
    for asset in executable_assets:
        if str(asset.get("name") or "").lower() == WINDOWS_EXECUTABLE_NAME.lower():
            return asset

    for asset in executable_assets:
        name = str(asset.get("name") or "").lower()
        if "windows" in name:
            return asset

    return executable_assets[0] if executable_assets else None


def update_error_from_response(response):
    status = response.status_code
    if status == 404:
        return UpdateCheckError(
            "GitHub Releases could not be reached. The repository or release page is probably "
            "private, renamed, or unavailable. Make the repository public for automatic update "
            "checks, or open the release page in a browser while logged in."
        )
    if status == 403:
        return UpdateCheckError(
            "GitHub blocked the update check, likely because of rate limits or access rules. "
            "Try again later or open the release page in a browser."
        )

    return UpdateCheckError(
        f"GitHub update request failed: HTTP {status} {response.reason}."
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
    prerelease_key = prerelease_rank(suffix)
    return (*numbers[:3], release_rank, prerelease_key)


def prerelease_rank(suffix):
    if not suffix:
        return (999999, ())

    numbers = tuple(int(match.group(0)) for match in re.finditer(r"\d+", suffix))

    if "dev" in suffix:
        stage_rank = 0
    elif "alpha" in suffix:
        stage_rank = 1
    elif "beta" in suffix:
        stage_rank = 2
    elif "rc" in suffix:
        stage_rank = 3
    else:
        stage_rank = 4

    return (stage_rank, numbers)
