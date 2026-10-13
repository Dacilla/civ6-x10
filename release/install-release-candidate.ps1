# Local-only playtest installer: installs exactly the assembled
# two-item staging tree into the user's Civ VI Mods directory.
#
# Refuses probe content, optionally backs up an existing install, reports
# the installed DLL hash. Never touches stock files or the upstream
# Workshop Community Extension directory. Human smoke test only.
#
# Phase 8B.2: defaults track the current playtest build (8B.1 staging +
# DLL). The old defaults (1.0.0-rc2 dir + e048 hash) were internally
# inconsistent — RC2 actually contains 3b6dc3 — and failed the script's
# own hash check. Pass explicit -StageDir/-ExpectedDllHash to install
# any other staging.
param(
    [string]$StageDir = (Join-Path $PSScriptRoot 'out' '1.0.0-8b' 'workshop'),
    [string]$ExpectedDllHash = 'ced8f01750d22f44725ed61de7c0926c58e423388b3ee7fce0fd18522081b744'
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
        # backups must live OUTSIDE Mods: Civ VI lists every subfolder
        # containing a .modinfo, so an in-place backup reads as a
        # duplicate mod with a colliding Mod ID.
        $bakRoot = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'X10-mod-backups'
        New-Item -ItemType Directory -Force -Path $bakRoot | Out-Null
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $bak = Join-Path $bakRoot ((Split-Path -Leaf $dst) + ".$stamp")
        Move-Item $dst $bak -Force
        Write-Host "backed up existing outside Mods: $dst -> $bak"
    }
    Copy-Item $src $dst -Recurse -Force
    Write-Host "installed: $dst"
}

$dll = Join-Path $mods 'CE-X10\Binaries\Win64\GameCore_XP2_CE_FinalRelease.dll'
$actual = (Get-FileHash $dll -Algorithm SHA256).Hash.ToLower()
Write-Host "installed DLL hash: $actual"
if ($actual -ne $ExpectedDllHash.ToLower()) { throw 'installed DLL hash mismatch' }
Write-Host 'RC installed. Enable X10 CE Engine + X10 (disable upstream CE, no probe).'
