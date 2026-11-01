param(
    [string[]]$InstallerArgs = @()
)

$ErrorActionPreference = "Stop"
$tempDir = Join-Path $env:TEMP ("skyfall-install-" + [guid]::NewGuid().ToString("N"))
$repoDir = $PSScriptRoot
$clonedRepo = $false

try {
    if (-not $repoDir -or -not (Test-Path -LiteralPath (Join-Path $repoDir "setup.py"))) {
        if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
            throw "Git is required. Install Git for Windows and run this script again."
        }

        New-Item -ItemType Directory -Path $tempDir | Out-Null
        $repoDir = Join-Path $tempDir "SkyFall"
        & git clone --recurse-submodules https://github.com/Nighty3098/SkyFall $repoDir
        if ($LASTEXITCODE -ne 0) {
            throw "Could not clone SkyFall (exit code $LASTEXITCODE)."
        }
        $clonedRepo = $true
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 (Join-Path $repoDir "setup.py") @InstallerArgs
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python (Join-Path $repoDir "setup.py") @InstallerArgs
    } else {
        throw "Python 3 is required. Install it from python.org and run this script again."
    }
    if ($LASTEXITCODE -ne 0) {
        throw "SkyFall installation failed (exit code $LASTEXITCODE)."
    }
} finally {
    if ($clonedRepo -and (Test-Path -LiteralPath $tempDir)) {
        Remove-Item -LiteralPath $tempDir -Recurse -Force
    }
}
