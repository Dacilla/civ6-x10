# Install the production-candidate test set (local Mods folder only).
# Never touches Workshop files, saves, settings, or the stock GameCore DLL.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $here 'assemble-prod-test.ps1')
$src = Join-Path $here 'prod-test-output'
$mods = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'My Games\Sid Meier''s Civilization VI\Mods'
if (-not (Test-Path $mods)) { throw "Mods directory not found: $mods" }
if ($mods -match 'workshop') { throw "refusing: resolved path looks like Workshop: $mods" }
foreach ($m in @('CE-X10', 'X10', 'X10_Probe_Test')) {
    $dst = Join-Path $mods $m
    if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
    Copy-Item (Join-Path $src $m) $dst -Recurse -Force
    Write-Host "installed: $dst"
}
Write-Host ''
Write-Host 'In-game steps (disposable profile recommended):'
Write-Host '  1. Additional Content: DISABLE Community Extension (Workshop).'
Write-Host '  2. Enable: X10 CE Engine + X10 + X10 Production Probe.'
Write-Host '  3. Single Player > Create Game > Gathering Storm, play as ROME (Trajan), Small map, 2 AI.'
Write-Host '  4. Set X10 multiplier 7.3 (all supported modules ON).'
Write-Host '  5. Start, reach the map, end 1 turn, save, exit to menu, reload once.'
Write-Host '  6. Send: %TEMP%\X10Lifecycle.log + %TEMP%\X10Probe.log.'
Write-Host 'Rollback any time: disable the mods (or run uninstall-prod-test.ps1).'
