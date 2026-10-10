# Swap the installed production CE DLL + probe.lua for the Toqui scratch
# pair (Phase 6A.2 pressure-observability run). DISPOSABLE helper: not
# referenced by any modinfo, test, or workflow.
#
# Usage (PowerShell):
#   pwsh -NoProfile -File spike/toqui-probe/swap-to-scratch.ps1
#
# Preconditions: scratch DLL already built to C:\Users\alex\Desktop\Code\ce-test-build\
# (see spike/toqui-probe/README.md). Aborts unless the installed DLL is the
# pinned production build.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent (Split-Path -Parent $here)
$mods = Join-Path $env:USERPROFILE "Documents\My Games\Sid Meier's Civilization VI\Mods"
$engDll = Join-Path $mods 'CE-X10\Binaries\Win64\GameCore_XP2_CE_FinalRelease.dll'
$probeLua = Join-Path $mods 'X10_Probe_Test\probe.lua'
$scratchDll = 'C:\Users\alex\Desktop\Code\ce-test-build\GameCore_XP2_CE_FinalRelease.dll'
$scratchLua = Join-Path $here 'toqui_probe.lua'
$backupDir = Join-Path $env:TEMP 'x10-toqui-backup'
$expectedProd = (Get-Content (Join-Path $root 'spike\EXPECTED_DLL_SHA256.txt') -Raw).Trim().ToLower()

if (-not (Test-Path $scratchDll)) { throw "scratch DLL missing: $scratchDll (build it first, see README.md)" }
$installed = (Get-FileHash $engDll -Algorithm SHA256).Hash.ToLower()
if ($installed -ne $expectedProd) { throw "installed DLL is NOT the pinned production build: $installed" }
$scratch = (Get-FileHash $scratchDll -Algorithm SHA256).Hash.ToLower()
if ($scratch -eq $expectedProd) { throw "scratch DLL identical to production (rebuild with the scratch registry)" }

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
Copy-Item $engDll (Join-Path $backupDir 'GameCore_XP2_CE_FinalRelease.dll.prod') -Force
Copy-Item $probeLua (Join-Path $backupDir 'probe.lua.prod') -Force
@{ production_dll_sha256 = $installed;
   scratch_dll_sha256 = $scratch;
   swapped_utc = (Get-Date).ToUniversalTime().ToString('o') } |
  ConvertTo-Json | Out-File (Join-Path $backupDir 'swap-manifest.json') -Encoding ascii

Copy-Item $scratchDll $engDll -Force
Copy-Item $scratchLua $probeLua -Force
$now = (Get-FileHash $engDll -Algorithm SHA256).Hash.ToLower()
if ($now -ne $scratch) { throw "scratch DLL did not install cleanly" }
Write-Host "swapped: scratch DLL $scratch installed; production backed up to $backupDir"
Write-Host "run the game per spike/toqui-probe/README.md, then restore with restore-production.ps1"
