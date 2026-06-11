param(
    [string]$Version = "",
    [ValidateSet("OneFile", "OneDir")]
    [string]$Package = "OneFile"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList
    )

    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath failed with exit code $LASTEXITCODE."
    }
}

function Remove-WithRetry {
    param(
        [string]$Path,
        [int]$Attempts = 6,
        [int]$DelaySeconds = 3
    )

    if (-not (Test-Path $Path)) {
        return
    }

    for ($Attempt = 1; $Attempt -le $Attempts; $Attempt++) {
        try {
            Remove-Item -LiteralPath $Path -Recurse -Force
            return
        }
        catch {
            if ($Attempt -eq $Attempts) {
                throw
            }

            Write-Warning "Remove attempt $Attempt failed because a build file is still locked. Retrying in $DelaySeconds seconds..."
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

function Compress-WithRetry {
    param(
        [string]$SourcePath,
        [string]$DestinationPath,
        [int]$Attempts = 6,
        [int]$DelaySeconds = 3
    )

    for ($Attempt = 1; $Attempt -le $Attempts; $Attempt++) {
        try {
            Compress-Archive -Path $SourcePath -DestinationPath $DestinationPath -Force
            return
        }
        catch {
            if ($Attempt -eq $Attempts) {
                throw
            }

            Write-Warning "Zip attempt $Attempt failed because a build file is still locked. Retrying in $DelaySeconds seconds..."
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

Push-Location $ProjectRoot
try {
    if (-not $Version) {
        $Version = (& $Python -c "from app.version import APP_VERSION; print(APP_VERSION)").Trim()
        if ($LASTEXITCODE -ne 0) {
            throw "Could not read app version."
        }
    }

    Invoke-Checked $Python @("-m", "pip", "install", "-r", "requirements.txt")
    Invoke-Checked $Python @("-m", "pip", "install", "-r", "requirements-dev.txt")

    $TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "SC-Intel-Tool-build"
    $TempBuild = Join-Path $TempRoot "build"
    $TempDist = Join-Path $TempRoot "dist"
    $TempSpec = Join-Path $TempRoot "spec"

    Remove-WithRetry $TempRoot
    New-Item -ItemType Directory -Force -Path $TempBuild, $TempDist, $TempSpec | Out-Null

    $AddDataArgs = @()
    if (Test-Path "reference_material") {
        Write-Host "reference_material found locally; intentionally not bundling it in public release builds."
    }

    $AppIconPath = Join-Path $ProjectRoot "app\assets\Balder.ico"
    if (Test-Path $AppIconPath) {
        $IconPath = (Resolve-Path $AppIconPath).Path
        $AddDataArgs += @("--add-data", "$IconPath;app/assets")
    } else {
        $IconPath = ""
        Write-Warning "app\assets\Balder.ico was not found. The build will use the default executable icon."
    }

    if (Test-Path "CHANGELOG.md") {
        $ChangelogPath = (Resolve-Path "CHANGELOG.md").Path
        $AddDataArgs += @("--add-data", "$ChangelogPath;.")
    } else {
        Write-Warning "CHANGELOG.md was not found. The packaged Notes tab will not include release notes."
    }

    $PyInstallerArgs = @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name", "SC-Intel-Tool",
        "--workpath", $TempBuild,
        "--distpath", $TempDist,
        "--specpath", $TempSpec
    )

    if ($IconPath) {
        $PyInstallerArgs += @("--icon", $IconPath)
    }

    $MiningPublicDataPath = Join-Path $ProjectRoot "app\assets\mining_public"
    if (Test-Path $MiningPublicDataPath) {
        $PyInstallerArgs += @("--add-data", "$((Resolve-Path $MiningPublicDataPath).Path);app/assets/mining_public")
    }

    if ($Package -eq "OneFile") {
        $PyInstallerArgs += @("--onefile", "--runtime-tmpdir", ".")
    }

    $PyInstallerArgs += $AddDataArgs + @("main.py")

    Invoke-Checked $Python $PyInstallerArgs

    New-Item -ItemType Directory -Force -Path "dist" | Out-Null

    if ($Package -eq "OneFile") {
        $Artifact = Join-Path "dist" "SC-Intel-Tool.exe"
        if (Test-Path $Artifact) {
            Remove-Item -LiteralPath $Artifact
        }

        Copy-Item -LiteralPath (Join-Path $TempDist "SC-Intel-Tool.exe") -Destination $Artifact
    } else {
        $Artifact = Join-Path "dist" "SC-Intel-Tool-$Version-windows-portable.zip"
        if (Test-Path $Artifact) {
            Remove-Item -LiteralPath $Artifact
        }

        $BuiltApp = Join-Path $TempDist "SC-Intel-Tool"
        Compress-WithRetry -SourcePath (Join-Path $BuiltApp "*") -DestinationPath $Artifact
    }

    $Hash = Get-FileHash -LiteralPath $Artifact -Algorithm SHA256

    Write-Host ""
    Write-Host "Build complete:"
    Write-Host "  $Artifact"
    Write-Host "SHA256:"
    Write-Host "  $($Hash.Hash)"
}
finally {
    Pop-Location
}
