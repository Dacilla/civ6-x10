# Install the disposable X10 CE lifecycle test (local mod folder only).
# Never touches Workshop files, saves, settings, or the stock GameCore DLL.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $here 'assemble-live-test.ps1')
$src = Join-Path $here 'live-test-output\X10_CEFork_Test'
$mods = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'My Games\Sid Meier''s Civilization VI\Mods'
if (-not (Test-Path $mods)) { throw "Mods directory not found: $mods" }
$dst = Join-Path $mods 'X10_CEFork_Test'
if ($mods -match 'workshop') { throw "refusing: resolved path looks like Workshop: $mods" }
if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
Copy-Item $src $dst -Recurse -Force
Write-Host "installed: $dst"
Write-Host ''
Write-Host 'In-game steps (disposable profile recommended):'
Write-Host '  1. Additional Content: DISABLE Community Extension (Workshop).'
Write-Host '  2. Enable: X10 CE Native Write Test (version 2, write-enabled).'
Write-Host '  3. Single Player > Create Game > Gathering Storm, play as ROME (Trajan), Small map, 2 AI.'
Write-Host '  4. Start, reach the map, end 1 turn, save, exit to menu, reload once.'
Write-Host '  5. Send: %TEMP%\X10Lifecycle.log + %TEMP%\X10Probe.log.'
Write-Host 'Rollback any time: disable the mod (or run uninstall-live-test.ps1).'
