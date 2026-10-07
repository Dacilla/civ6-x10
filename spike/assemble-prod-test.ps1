# Assemble the production-candidate local test set:
#   CE-X10 engine (modinfo + redirect + locally built DLL)
#   X10 controller (modinfo + config)
#   X10_Probe_Test (temporary diagnostic readback)
# DLLs stay local; the package output is gitignored.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
$dll = 'C:\Users\alex\Desktop\Code\ce-native-build\GameCore_XP2_CE_FinalRelease.dll'
$out = Join-Path $here 'prod-test-output'
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Force -Path $out | Out-Null

$expectedHash = (Get-Content (Join-Path $here 'EXPECTED_DLL_SHA256.txt') -Raw).Trim()
$actual = (Get-FileHash $dll -Algorithm SHA256).Hash.ToLower()
if ($actual -ne $expectedHash.ToLower()) {
    throw "DLL hash mismatch: got $actual, expected $expectedHash. Rebuild the fork first."
}

$engine = Join-Path $out 'CE-X10'
Copy-Item (Join-Path $root 'dependencies\CE-X10') $engine -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $engine 'Binaries\Win64') | Out-Null
Copy-Item $dll (Join-Path $engine 'Binaries\Win64\GameCore_XP2_CE_FinalRelease.dll') -Force

Copy-Item (Join-Path $root 'controller\X10') (Join-Path $out 'X10') -Recurse -Force
Copy-Item (Join-Path $here 'X10_Probe_Test') (Join-Path $out 'X10_Probe_Test') -Recurse -Force
Write-Host "assembled production candidate:"
Get-ChildItem $out | Select-Object Name
Write-Host "DLL hash verified: $actual"
