param(
    [string[]]$InstallerArgs = @()
)

$ErrorActionPreference = "Stop"
$tempDir = Join-Path $env:TEMP ("skyfall-install-" + [guid]::NewGuid().ToString("N"))
$repoDir = $PSScriptRoot
$clonedRepo = $false

$uninstallMode = $InstallerArgs -contains "--uninstall" -or $InstallerArgs -contains "uninstall"

try {
    if (-not $repoDir -or -not (Test-Path -LiteralPath (Join-Path $repoDir "setup.py"))) {
        if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
            throw "Git is required. Install Git for Windows and run this script again."
        }

        New-Item -ItemType Directory -Path $tempDir | Out-Null
        $repoDir = Join-Path $tempDir "SkyFall"
        Write-Host "  Downloading SkyFall..." -ForegroundColor Cyan
        & git clone --depth 1 --recurse-submodules --shallow-submodules https://github.com/Nighty3098/SkyFall $repoDir
        if ($LASTEXITCODE -ne 0) {
            throw "Could not clone SkyFall (exit code $LASTEXITCODE)."
        }
        $clonedRepo = $true
    }

    if ($uninstallMode) {
        Write-Host "  Starting uninstaller..." -ForegroundColor Cyan
    } else {
        Write-Host "  Starting installer..." -ForegroundColor Cyan
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 (Join-Path $repoDir "setup.py") @InstallerArgs
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python (Join-Path $repoDir "setup.py") @InstallerArgs
    } else {
        throw "Python 3 is required. Install it from python.org and run this script again."
    }
    if ($LASTEXITCODE -ne 0) {
        if ($uninstallMode) {
            throw "SkyFall uninstallation failed (exit code $LASTEXITCODE)."
        }
        throw "SkyFall installation failed (exit code $LASTEXITCODE)."
    }
} finally {
    if ($clonedRepo -and (Test-Path -LiteralPath $tempDir)) {
        Remove-Item -LiteralPath $tempDir -Recurse -Force
    }
}
