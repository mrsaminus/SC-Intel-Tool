import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

from .paths import get_user_data_dir, is_packaged_app


class UpdateInstallError(Exception):
    pass


@dataclass(frozen=True)
class DownloadedUpdate:
    path: Path
    size: int
    sha256: str


def download_update(update_info, timeout=120):
    if not update_info.asset_url:
        raise UpdateInstallError("This release does not include a downloadable Windows executable.")

    updates_dir = get_user_data_dir() / "updates"
    updates_dir.mkdir(parents=True, exist_ok=True)

    asset_name = safe_asset_name(update_info.asset_name, update_info.latest_version)
    target_path = updates_dir / asset_name
    temp_path = target_path.with_suffix(target_path.suffix + ".download")

    if temp_path.exists():
        temp_path.unlink()

    response = requests.get(
        update_info.asset_url,
        headers={"User-Agent": "SC-Intel-Tool"},
        stream=True,
        timeout=timeout,
    )
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise UpdateInstallError(f"Could not download update: {exc}") from exc

    hasher = hashlib.sha256()
    downloaded_size = 0
    with temp_path.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 512):
            if not chunk:
                continue
            handle.write(chunk)
            hasher.update(chunk)
            downloaded_size += len(chunk)

    if update_info.asset_size and downloaded_size != update_info.asset_size:
        temp_path.unlink(missing_ok=True)
        raise UpdateInstallError(
            f"Downloaded update size did not match GitHub metadata "
            f"({downloaded_size} bytes vs {update_info.asset_size} bytes)."
        )

    digest = hasher.hexdigest().lower()
    expected_digest = expected_sha256(update_info.asset_digest)
    if expected_digest and digest != expected_digest:
        temp_path.unlink(missing_ok=True)
        raise UpdateInstallError("Downloaded update failed SHA256 verification.")

    if target_path.exists():
        target_path.unlink()
    temp_path.replace(target_path)

    return DownloadedUpdate(path=target_path, size=downloaded_size, sha256=digest.upper())


def start_update_installer(downloaded_update):
    if os.name != "nt":
        raise UpdateInstallError("Automatic install is currently only available on Windows.")
    if not is_packaged_app():
        raise UpdateInstallError("Automatic install is only available in packaged Windows builds.")

    current_exe = Path(sys.executable).resolve()
    if not current_exe.exists():
        raise UpdateInstallError("Could not find the running app executable.")

    script_path = get_user_data_dir() / "updates" / "install_update.ps1"
    script_path.write_text(update_script(), encoding="utf-8")

    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-File",
            str(script_path),
            "-ProcessId",
            str(os.getpid()),
            "-Source",
            str(downloaded_update.path),
            "-Target",
            str(current_exe),
        ],
        close_fds=True,
    )


def safe_asset_name(asset_name, version):
    name = Path(str(asset_name or "")).name
    if not name.lower().endswith(".exe"):
        version_text = str(version or "latest").strip().removeprefix("v")
        name = f"SC-Intel-Tool-{version_text}-windows.exe"

    return name


def expected_sha256(asset_digest):
    digest = str(asset_digest or "").strip().lower()
    if digest.startswith("sha256:"):
        return digest.removeprefix("sha256:")

    return ""


def update_script():
    return r'''
param(
    [int]$ProcessId,
    [string]$Source,
    [string]$Target
)

$ErrorActionPreference = "Stop"
$LogPath = Join-Path (Split-Path -Parent $Source) "install_update.log"

function Write-UpdateLog {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $LogPath -Value "[$Timestamp] $Message"
}

try {
    Write-UpdateLog "Waiting for process $ProcessId to exit."
    $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($Process) {
        if (-not $Process.WaitForExit(60000)) {
            throw "SC Intel Tool did not close before the update timeout."
        }
    }

    Start-Sleep -Milliseconds 500

    $Backup = "$Target.previous"
    if (Test-Path -LiteralPath $Backup) {
        Remove-Item -LiteralPath $Backup -Force
    }
    if (Test-Path -LiteralPath $Target) {
        Copy-Item -LiteralPath $Target -Destination $Backup -Force
    }

    Write-UpdateLog "Installing $Source to $Target."
    Copy-Item -LiteralPath $Source -Destination $Target -Force
    Write-UpdateLog "Starting updated app."
    Start-Process -FilePath $Target
}
catch {
    Write-UpdateLog "Update failed: $($_.Exception.Message)"
    if ((Test-Path -LiteralPath "$Target.previous") -and -not (Test-Path -LiteralPath $Target)) {
        Copy-Item -LiteralPath "$Target.previous" -Destination $Target -Force
    }
}
'''
