import hashlib
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

from .paths import get_user_data_dir, is_packaged_app

WINDOWS_EXECUTABLE_NAME = "SC-Intel-Tool.exe"
logger = logging.getLogger(__name__)


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
    logger.info(
        "Downloading update asset=%s version=%s target=%s expected_size=%s digest_available=%s",
        asset_name,
        update_info.latest_version,
        target_path,
        update_info.asset_size,
        bool(update_info.asset_digest),
    )

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
        logger.error("Downloaded update size mismatch: got=%s expected=%s", downloaded_size, update_info.asset_size)
        raise UpdateInstallError(
            f"Downloaded update size did not match GitHub metadata "
            f"({downloaded_size} bytes vs {update_info.asset_size} bytes)."
        )

    digest = hasher.hexdigest().lower()
    expected_digest = expected_sha256(update_info.asset_digest)
    if expected_digest and digest != expected_digest:
        temp_path.unlink(missing_ok=True)
        logger.error("Downloaded update SHA256 mismatch.")
        raise UpdateInstallError("Downloaded update failed SHA256 verification.")

    if target_path.exists():
        target_path.unlink()
    temp_path.replace(target_path)
    logger.info("Update downloaded and verified: path=%s size=%s sha256=%s", target_path, downloaded_size, digest.upper())

    return DownloadedUpdate(path=target_path, size=downloaded_size, sha256=digest.upper())


def start_update_installer(downloaded_update):
    if os.name != "nt":
        raise UpdateInstallError("Automatic install is currently only available on Windows.")
    if not is_packaged_app():
        raise UpdateInstallError("Automatic install is only available in packaged Windows builds.")

    current_exe = Path(sys.executable).resolve()
    if not current_exe.exists():
        raise UpdateInstallError("Could not find the running app executable.")
    target_exe = current_exe.with_name(WINDOWS_EXECUTABLE_NAME)

    script_path = get_user_data_dir() / "updates" / "install_update.ps1"
    script_path.write_text(update_script(), encoding="utf-8")
    logger.info("Starting update installer script=%s source=%s target=%s", script_path, downloaded_update.path, target_exe)

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
            str(target_exe),
            "-ExpectedSize",
            str(downloaded_update.size),
            "-ExpectedSha256",
            downloaded_update.sha256,
        ],
        close_fds=True,
    )


def safe_asset_name(asset_name, version):
    name = Path(str(asset_name or "")).name
    if not name.lower().endswith(".exe"):
        name = WINDOWS_EXECUTABLE_NAME

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
    [string]$Target,
    [long]$ExpectedSize = 0,
    [string]$ExpectedSha256 = ""
)

$ErrorActionPreference = "Stop"
$LogPath = Join-Path (Split-Path -Parent $Source) "install_update.log"

function Write-UpdateLog {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $LogPath -Value "[$Timestamp] $Message"
}

function Get-Sha256 {
    param([string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Unblock-IfPossible {
    param([string]$Path)
    try {
        Unblock-File -LiteralPath $Path -ErrorAction SilentlyContinue
    }
    catch {
        Write-UpdateLog "Unblock skipped for ${Path}: $($_.Exception.Message)"
    }
}

function Show-UpdateMessage {
    param(
        [string]$Title,
        [string]$Message,
        [string]$Icon = "Information"
    )

    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            $Message,
            $Title,
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::$Icon
        ) | Out-Null
    }
    catch {
        Write-UpdateLog "Message display failed: $($_.Exception.Message)"
    }
}

try {
    Write-UpdateLog "Waiting for process $ProcessId to exit."
    $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($Process) {
        if (-not $Process.WaitForExit(60000)) {
            throw "SC Intel Tool did not close before the update timeout."
        }
    }

    Start-Sleep -Seconds 2

    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Downloaded update was not found: $Source"
    }

    if ($ExpectedSize -gt 0) {
        $SourceSize = (Get-Item -LiteralPath $Source).Length
        if ($SourceSize -ne $ExpectedSize) {
            throw "Downloaded update size changed before install. Expected $ExpectedSize bytes, got $SourceSize bytes."
        }
    }

    if ($ExpectedSha256) {
        $SourceHash = Get-Sha256 -Path $Source
        if ($SourceHash -ne $ExpectedSha256.ToUpperInvariant()) {
            throw "Downloaded update hash changed before install."
        }
    }

    Unblock-IfPossible -Path $Source

    $Backup = "$Target.previous"
    $InstallCandidate = "$Target.new"
    if (Test-Path -LiteralPath $InstallCandidate) {
        Remove-Item -LiteralPath $InstallCandidate -Force
    }
    if (Test-Path -LiteralPath $Backup) {
        Remove-Item -LiteralPath $Backup -Force
    }

    Write-UpdateLog "Copying update to install candidate $InstallCandidate."
    Copy-Item -LiteralPath $Source -Destination $InstallCandidate -Force

    if ($ExpectedSize -gt 0) {
        $CandidateSize = (Get-Item -LiteralPath $InstallCandidate).Length
        if ($CandidateSize -ne $ExpectedSize) {
            throw "Install candidate size mismatch. Expected $ExpectedSize bytes, got $CandidateSize bytes."
        }
    }

    if ($ExpectedSha256) {
        $CandidateHash = Get-Sha256 -Path $InstallCandidate
        if ($CandidateHash -ne $ExpectedSha256.ToUpperInvariant()) {
            throw "Install candidate hash mismatch."
        }
    }

    if (Test-Path -LiteralPath $Target) {
        Copy-Item -LiteralPath $Target -Destination $Backup -Force
    }

    Write-UpdateLog "Installing $InstallCandidate to $Target."
    Move-Item -LiteralPath $InstallCandidate -Destination $Target -Force
    Unblock-IfPossible -Path $Target

    if ($ExpectedSize -gt 0) {
        $TargetSize = (Get-Item -LiteralPath $Target).Length
        if ($TargetSize -ne $ExpectedSize) {
            throw "Installed executable size mismatch. Expected $ExpectedSize bytes, got $TargetSize bytes."
        }
    }

    if ($ExpectedSha256) {
        $TargetHash = Get-Sha256 -Path $Target
        if ($TargetHash -ne $ExpectedSha256.ToUpperInvariant()) {
            throw "Installed executable hash mismatch."
        }
    }

    if (Test-Path -LiteralPath $Backup) {
        Write-UpdateLog "Update installed successfully; removing backup $Backup."
        Remove-Item -LiteralPath $Backup -Force
    }
    else {
        Write-UpdateLog "Update installed successfully; no backup file was present."
    }

    Show-UpdateMessage `
        -Title "SC Intel Tool updated" `
        -Message "SC Intel Tool was updated successfully.`nPlease start SC-Intel-Tool.exe manually."
}
catch {
    Write-UpdateLog "Update failed: $($_.Exception.Message)"
    if (Test-Path -LiteralPath "$Target.new") {
        Remove-Item -LiteralPath "$Target.new" -Force
    }
    if (Test-Path -LiteralPath "$Target.previous") {
        try {
            Copy-Item -LiteralPath "$Target.previous" -Destination $Target -Force
            Write-UpdateLog "Rollback restored $Target from $Target.previous."
        }
        catch {
            Write-UpdateLog "Rollback restore failed: $($_.Exception.Message)"
        }
    }
    Show-UpdateMessage `
        -Title "SC Intel Tool update failed" `
        -Message "SC Intel Tool update failed.`n$($_.Exception.Message)`nThe previous executable was preserved for rollback." `
        -Icon "Error"
}
'''
