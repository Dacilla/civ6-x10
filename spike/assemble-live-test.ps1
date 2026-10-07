# Assemble the complete local test folder (DLL stays local, never committed).
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pkg = Join-Path $here 'live-test-package\X10_CEFork_Test'
$out = Join-Path $here 'live-test-output\X10_CEFork_Test'
$dll = 'C:\Users\alex\Desktop\Code\ce-native-build\GameCore_XP2_CE_FinalRelease.dll'
$expectedHash = '6545ff98f8d16c0bbd137c33e1a76ea81acdd116575fd41544ccc9d0db373b8b'

if (-not (Test-Path $dll)) { throw "fork DLL not built: $dll" }
$actual = (Get-FileHash $dll -Algorithm SHA256).Hash.ToLower()
if ($actual -ne $expectedHash) {
    throw "DLL hash mismatch: got $actual, expected $expectedHash. Rebuild the fork first."
}
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
Copy-Item $pkg $out -Recurse -Force
Remove-Item (Join-Path $out 'Binaries\Win64\README.txt') -Force -ErrorAction SilentlyContinue
Copy-Item $dll (Join-Path $out 'Binaries\Win64\GameCore_XP2_CE_FinalRelease.dll') -Force
Write-Host "assembled: $out"
Write-Host "DLL hash verified: $actual"
