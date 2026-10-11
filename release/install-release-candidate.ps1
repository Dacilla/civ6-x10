# Local-only RC smoke installer (Phase 7B.1): installs exactly the
# assembled two-item staging tree into the user's Civ VI Mods directory.
#
# Refuses probe content, optionally backs up an existing install, reports
# the installed DLL hash. Never touches stock files or the upstream
# Workshop Community Extension directory. Human smoke test only.
param(
    [string]$StageDir = (Join-Path $PSScriptRoot 'out' '1.0.0-rc1' 'workshop'),
    [string]$ExpectedDllHash = 'e33d84b83d752a9eb7b52b4740291c97183af4d079d1ca82b8bd9d92b5c4d619'
)
$ErrorActionPreference = 'Stop'

$probeHit = Get-ChildItem $StageDir -Recurse -File |
    Where-Object { $_.Name -in @('probe.lua', 'stonediag.lua') -or $_.Directory.Name -eq 'X10_Probe_Test' }
if ($probeHit) { throw "refusing: probe content in staging: $($probeHit.FullName -join ', ')" }

$mods = Join-Path ([Environment]::GetFolderPath('MyDocuments')) "My Games\Sid Meier's Civilization VI\Mods"
if ($mods -match 'workshop') { throw "refusing: resolved path looks like Workshop: $mods" }
if (-not (Test-Path $mods)) { throw "Mods directory not found: $mods" }

foreach ($item in @('X10-CE-Engine', 'X10')) {
    $src = Join-Path $StageDir $item
    if (-not (Test-Path $src)) { throw "staging item missing: $src" }
    $dst = Join-Path $mods ($item -replace '^X10-CE-Engine$', 'CE-X10')
    if (Test-Path $dst) {
        $bak = "$dst.rc-backup"
        if (Test-Path $bak) { Remove-Item $bak -Recurse -Force }
        Rename-Item $dst (Split-Path -Leaf $bak)
        Write-Host "backed up existing: $dst -> $bak"
    }
    Copy-Item $src $dst -Recurse -Force
    Write-Host "installed: $dst"
}

$dll = Join-Path $mods 'CE-X10\Binaries\Win64\GameCore_XP2_CE_FinalRelease.dll'
$actual = (Get-FileHash $dll -Algorithm SHA256).Hash.ToLower()
Write-Host "installed DLL hash: $actual"
if ($actual -ne $ExpectedDllHash.ToLower()) { throw 'installed DLL hash mismatch' }
Write-Host 'RC installed. Enable X10 CE Engine + X10 (disable upstream CE, no probe).'
