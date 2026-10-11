# Restore the Phase-7B production RC after the UX probe run.
# Reinstalls the hash-verified production DLL, removes the disposable UX
# prototype mod, and verifies the fork tree is pristine. Never touches
# Workshop files, saves, settings, or the stock GameCore DLL.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
$codeRoot = Split-Path -Parent $root
$prodDll = Join-Path $codeRoot 'ce-native-build\GameCore_XP2_CE_FinalRelease.dll'
$prodPin = (Get-Content (Join-Path $here 'EXPECTED_DLL_SHA256.txt') -Raw).Trim().ToLower()

$mods = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'My Games\Sid Meier''s Civilization VI\Mods'
if (-not (Test-Path $mods)) { throw "Mods directory not found: $mods" }
if ($mods -match 'workshop') { throw "refusing: resolved path looks like Workshop: $mods" }
$engineDll = Join-Path $mods 'CE-X10\Binaries\Win64\GameCore_XP2_CE_FinalRelease.dll'
Copy-Item $prodDll $engineDll -Force
$have = (Get-FileHash $engineDll -Algorithm SHA256).Hash.ToLower()
if ($have -ne $prodPin) { throw "production restore mismatch: $have" }
Write-Host "production RC DLL restored: $have"
$protoDst = Join-Path $mods 'X10_UX_Prototype'
if (Test-Path $protoDst) { Remove-Item $protoDst -Recurse -Force; Write-Host 'prototype mod removed' }
$fork = Join-Path $codeRoot 'CivilizationVI_CommunityExtension-x10-spike'
$st = (git -C $fork status --porcelain)
if ($st) { throw "fork not pristine after probe (restore manually): $st" }
Write-Host 'fork tree pristine; RC state restored.'
