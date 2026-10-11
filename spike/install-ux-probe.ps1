# Install the disposable Phase-7C.1 UX probe set (local Mods folder only).
# Swaps the production RC DLL for the hash-pinned scratch UX probe DLL and
# installs the X10_UX_Prototype front-end mod. Never touches Workshop
# files, saves, settings, or the stock GameCore DLL.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
$codeRoot = Split-Path -Parent $root
$scratchDll = Join-Path $codeRoot 'ce-ux-probe-build\GameCore_XP2_CE_FinalRelease.dll'
$pinFile = Join-Path $here 'UX_PROBE_DLL_SHA256.txt'
$prodDll = Join-Path $codeRoot 'ce-native-build\GameCore_XP2_CE_FinalRelease.dll'

if (-not (Test-Path $pinFile)) { throw "scratch pin missing: build it first (build-ux-probe-dll.ps1)" }
$expected = (Get-Content $pinFile -Raw).Trim().ToLower()
if (-not (Test-Path $scratchDll)) { throw "scratch DLL missing: $scratchDll" }
$actual = (Get-FileHash $scratchDll -Algorithm SHA256).Hash.ToLower()
if ($actual -ne $expected) { throw "scratch DLL hash mismatch: got $actual, want $expected" }
if ($actual -eq (Get-Content (Join-Path $here 'EXPECTED_DLL_SHA256.txt') -Raw).Trim().ToLower()) {
    throw 'refusing: scratch DLL equals the production DLL (contamination)'
}
# Clear previous-run logs once per fresh install so the probe population
# is unambiguous.
foreach ($log in @('X10Lifecycle.log', 'X10Probe.log')) {
    $p = Join-Path ([IO.Path]::GetTempPath()) $log
    if (Test-Path $p) { Remove-Item $p -Force; Write-Host "cleared previous: $p" }
}
$mods = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'My Games\Sid Meier''s Civilization VI\Mods'
if (-not (Test-Path $mods)) { throw "Mods directory not found: $mods" }
if ($mods -match 'workshop') { throw "refusing: resolved path looks like Workshop: $mods" }
$engineDll = Join-Path $mods 'CE-X10\Binaries\Win64\GameCore_XP2_CE_FinalRelease.dll'
if (-not (Test-Path $engineDll)) { throw "RC engine DLL not installed (install the RC first)" }
$have = (Get-FileHash $engineDll -Algorithm SHA256).Hash.ToLower()
$prod = (Get-FileHash $prodDll -Algorithm SHA256).Hash.ToLower()
if ($have -ne $prod -and $have -ne $expected) { throw "unexpected DLL already in CE-X10: $have" }
Copy-Item $scratchDll $engineDll -Force
Write-Host "scratch UX probe DLL installed (was production RC: $($have -eq $prod))"
$protoSrc = Join-Path $here 'X10_UX_Prototype'
$protoDst = Join-Path $mods 'X10_UX_Prototype'
if (Test-Path $protoDst) { Remove-Item $protoDst -Recurse -Force }
Copy-Item $protoSrc $protoDst -Recurse -Force
Write-Host "installed: $protoDst"
Write-Host ''
Write-Host 'In-game steps (disposable profile recommended):'
Write-Host '  1. Additional Content: DISABLE Workshop CE + DISABLE X10 controller + DISABLE all probes.'
Write-Host '  2. Enable: X10 CE Engine (scratch UX build) + X10 UX Prototype.'
Write-Host '  3. Take screenshots A-E (see docs/UX_REVIEW.md).'
Write-Host '  4. Single Player > Create Game > Gathering Storm, ROME (Trajan), Small map, 2 AI.'
Write-Host '  5. Advanced Setup: preset Custom..., custom value 7.3, Governors checkbox OFF, rest ON.'
Write-Host '  6. Start, reach the map. No save/reload needed.'
Write-Host '  7. Send: %TEMP%\X10Lifecycle.log (X10_UX_* CONFIG lines are the evidence).'
Write-Host 'Restore any time: run restore-prod-rc.ps1 (verifies production hash back in place).'
