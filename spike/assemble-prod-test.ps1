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

# The probe is packaged strictly from its modinfo <Files> list: anything not
# referenced (e.g. the retired Phase-3E stonediag.lua, kept under spike/ for
# provenance) must never ship into the live test set.
$probeSrc = Join-Path $here 'X10_Probe_Test'
$probeDst = Join-Path $out 'X10_Probe_Test'
New-Item -ItemType Directory -Force -Path $probeDst | Out-Null
[xml]$probeXml = Get-Content (Join-Path $probeSrc 'X10_Probe_Test.modinfo') -Raw
$fileNodes = $probeXml.SelectNodes('/Mod/Files/File')
if ($null -eq $fileNodes -or $fileNodes.Count -eq 0) { throw 'probe modinfo lists no files' }
$files = @($fileNodes | ForEach-Object { $_.InnerText.Trim() } | Sort-Object -Unique)
foreach ($f in $files) {
    $src2 = Join-Path $probeSrc $f
    if (-not (Test-Path $src2)) { throw "probe file listed in modinfo missing: $f" }
    $dst2 = Join-Path $probeDst $f
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst2) | Out-Null
    Copy-Item $src2 $dst2 -Force
}
Copy-Item (Join-Path $probeSrc 'X10_Probe_Test.modinfo') (Join-Path $probeDst 'X10_Probe_Test.modinfo') -Force
Write-Host "probe files packaged: $($files -join ', ')"
Write-Host "assembled production candidate:"
Get-ChildItem $out | Select-Object Name
Write-Host "DLL hash verified: $actual"
