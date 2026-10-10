# Restore the production CE DLL + probe.lua after the Toqui scratch run
# (Phase 6A.2). MANDATORY after the game exits, even if the probe appears to
# fail. DISPOSABLE helper: not referenced by any modinfo, test, or workflow.
#
# Usage (PowerShell):
#   pwsh -NoProfile -File spike/toqui-probe/restore-production.ps1
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent (Split-Path -Parent $here)
$mods = Join-Path $env:USERPROFILE "Documents\My Games\Sid Meier's Civilization VI\Mods"
$engDll = Join-Path $mods 'CE-X10\Binaries\Win64\GameCore_XP2_CE_FinalRelease.dll'
$probeLua = Join-Path $mods 'X10_Probe_Test\probe.lua'
$backupDir = Join-Path $env:TEMP 'x10-toqui-backup'
$manifest = Join-Path $backupDir 'swap-manifest.json'
$expectedProd = (Get-Content (Join-Path $root 'spike\EXPECTED_DLL_SHA256.txt') -Raw).Trim().ToLower()

if (-not (Test-Path $manifest)) { throw "no swap manifest at $manifest (was swap-to-scratch.ps1 run?)" }
$man = Get-Content $manifest -Raw | ConvertFrom-Json
if ($man.production_dll_sha256.ToLower() -ne $expectedProd) {
  throw "swap manifest does not match pinned production hash; refusing to guess"
}
Copy-Item (Join-Path $backupDir 'GameCore_XP2_CE_FinalRelease.dll.prod') $engDll -Force
Copy-Item (Join-Path $backupDir 'probe.lua.prod') $probeLua -Force
$now = (Get-FileHash $engDll -Algorithm SHA256).Hash.ToLower()
if ($now -ne $expectedProd) { throw "RESTORE FAILED: installed DLL hash $now != $expectedProd" }
$repoProbe = Join-Path $root 'spike\X10_Probe_Test\probe.lua'
$instProbe = (Get-FileHash $probeLua -Algorithm SHA256).Hash
$repoHash = (Get-FileHash $repoProbe -Algorithm SHA256).Hash
if ($instProbe -ne $repoHash) { throw "probe.lua restore mismatch (installed vs repo)" }
Write-Host "restored: production DLL $now verified; probe.lua matches repo"
Write-Host "confirm both git working trees clean before analysis"
