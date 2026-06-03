# Applies the Phase-3 security overlay on top of Phase-2.
#
# Usage (from anywhere):
#   .\Phase-3\apply.ps1
#
# After running, Phase-2/ is the secure backend. Test it with:
#   cd Phase-2
#   docker compose up --build -d
#   docker compose exec api python seed.py

$ErrorActionPreference = "Stop"

$root    = Split-Path -Parent $PSScriptRoot
$overlay = Join-Path $root "Phase-3"
$target  = Join-Path $root "Phase-2"

if (-not (Test-Path $target)) {
    Write-Error "Phase-2 folder not found at $target"
    exit 1
}

Write-Host "Applying Phase-3 overlay onto Phase-2..." -ForegroundColor Cyan

# Files that should not be copied (they're the overlay's own docs/scripts)
$skip = @("README.md", "SECURITY.md", "apply.ps1")

Get-ChildItem -Path $overlay -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($overlay.Length + 1)
    $top = $rel.Split([IO.Path]::DirectorySeparatorChar, 2)[0]
    if ($skip -contains $top) { return }

    $dest = Join-Path $target $rel
    $destDir = Split-Path -Parent $dest
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    }
    Copy-Item -Path $_.FullName -Destination $dest -Force
    Write-Host "  -> $rel"
}

Write-Host "Done. Phase-2 is now the secure (Phase-3) backend." -ForegroundColor Green
Write-Host "Next: cd Phase-2; docker compose up --build -d"
