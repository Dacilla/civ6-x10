# Build the disposable Phase-7C.1 UX config-variant probe DLL (scratch only).
# Transiently patches the CE fork (new probe TU + guarded call site +
# X10_UX_PROBE define), builds Release|x64 to a SCRATCH output dir, records
# the hash, then FULLY restores the fork and verifies `git status` clean.
# The production DLL in ce-native-build is never touched; a scratch hash
# colliding with the production pin is refused.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
$fork = Join-Path (Split-Path -Parent $root) 'CivilizationVI_CommunityExtension-x10-spike'
$outDir = Join-Path (Split-Path -Parent $root) 'ce-ux-probe-build'
$pinFile = Join-Path $here 'UX_PROBE_DLL_SHA256.txt'
$prodPin = (Get-Content (Join-Path $here 'EXPECTED_DLL_SHA256.txt') -Raw).Trim().ToLower()

if (-not (Test-Path (Join-Path $fork 'CivilizationVI_CommunityExtension.vcxproj'))) {
    throw "fork not found at $fork"
}
$preStatus = (git -C $fork status --porcelain)
if ($preStatus) { throw "refusing: fork tree not clean before scratch build: $preStatus" }

Copy-Item (Join-Path $here 'ux-probe-src\X10UxProbe.cpp') (Join-Path $fork 'X10UxProbe.cpp') -Force
try {
    C:\Python314\python.exe (Join-Path $here 'ux-probe-src\apply_transient_patch.py') $fork
    if ($LASTEXITCODE -ne 0) { throw 'transient patch failed' }

    $candidates = @(
        'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe',
        'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe'
    )
    $msb = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $msb) {
        $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
        if (Test-Path $vswhere) {
            $msb = & $vswhere -latest -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe | Select-Object -First 1
        }
    }
    if (-not $msb -or -not (Test-Path $msb)) { throw 'MSBuild not found (need VS2022 + v143 + Win10 SDK)' }
    & $msb (Join-Path $fork 'CivilizationVI_CommunityExtension.sln') /p:Configuration=Release /p:Platform=x64 "/p:OutDir=$outDir\\" /m /v:minimal
    if ($LASTEXITCODE -ne 0) { throw 'scratch build failed' }
    $dll = Join-Path $outDir 'GameCore_XP2_CE_FinalRelease.dll'
    if (-not (Test-Path $dll)) { throw "scratch DLL missing: $dll" }
    $hash = (Get-FileHash $dll -Algorithm SHA256).Hash.ToLower()
    if ($hash -eq $prodPin) { throw 'scratch DLL hash collides with production pin (contamination)' }
    $hash | Out-File -NoNewline -Encoding ascii $pinFile
    Write-Host "scratch DLL: $hash"
} finally {
    git -C $fork checkout -- CivilizationVI_CommunityExtension.vcxproj X10Lifecycle.cpp
    Remove-Item (Join-Path $fork 'X10UxProbe.cpp') -Force -ErrorAction SilentlyContinue
}
$postStatus = (git -C $fork status --porcelain)
if ($postStatus) { throw "fork not restored clean: $postStatus" }
Write-Host 'fork restored clean; production DLL untouched.'
