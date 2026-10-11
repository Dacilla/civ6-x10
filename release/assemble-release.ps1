# X10 release assembler (Phase 7B.1): deterministic two-item Workshop
# staging + source assets from release/release-manifest.yml (allowlist).
#
# No developer-machine paths, no whole-tree copies, no probe content.
# Text inputs are verified by LF-normalized hash and staged as LF bytes;
# the DLL is verified by exact binary hash. CHECKSUMS.sha256 records
# packaged bytes (distinct from normalized source hashes).
#
# Requires: PowerShell 7+, Python 3 with pyyaml (manifest parsing).
param(
    [Parameter(Mandatory = $true)][string]$OutDir,
    [Parameter(Mandatory = $true)][string]$DllPath,
    [string]$Manifest = (Join-Path $PSScriptRoot 'release-manifest.yml'),
    [switch]$AllowPlaceholderUrls
)
$ErrorActionPreference = 'Stop'

$OutDir = [IO.Path]::GetFullPath($OutDir)
$repoRoot = Split-Path -Parent $PSScriptRoot
$manifestJson = python -c "import yaml, json, sys; print(json.dumps(yaml.safe_load(open(sys.argv[1], encoding='utf-8'))))" $Manifest | Out-String
$man = $manifestJson | ConvertFrom-Json

function RepoBytes([string]$rel) {
    $p = Join-Path $repoRoot $rel
    if (-not (Test-Path $p)) { throw "manifest source missing: $rel" }
    return [IO.File]::ReadAllBytes($p)
}
function NormalizedHash([byte[]]$bytes, [string]$rel) {
    if ($rel.EndsWith('.dll')) {
        return ([Security.Cryptography.SHA256]::Create().ComputeHash($bytes) |
            ForEach-Object { $_.ToString('x2') }) -join ''
    }
    $text = [Text.Encoding]::UTF8.GetString($bytes).Replace("`r`n", "`n")
    $norm = [Text.Encoding]::UTF8.GetBytes($text)
    return (([Security.Cryptography.SHA256]::Create().ComputeHash($norm) |
        ForEach-Object { $_.ToString('x2') }) -join ''), $norm
}

# --- DLL gate: exact binary hash, scratch builds can never enter ---
if ($DllPath -like '*ce-test-build*') {
    throw "refusing DLL from scratch build tree ce-test-build: $DllPath"
}
if (-not (Test-Path $DllPath)) { throw "DLL not found: $DllPath" }
$dllBytes = [IO.File]::ReadAllBytes($DllPath)
$dllHash = ([Security.Cryptography.SHA256]::Create().ComputeHash($dllBytes) |
    ForEach-Object { $_.ToString('x2') }) -join ''
if ($dllHash -ne $man.dll_sha256.ToLower()) {
    throw "DLL hash mismatch: got $dllHash, want $($man.dll_sha256)"
}
Write-Host "DLL verified: $dllHash"

if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
$workshop = Join-Path $OutDir 'workshop'
$assets = Join-Path $OutDir 'source-assets'
New-Item -ItemType Directory -Force -Path $workshop, $assets | Out-Null

$staged = @()
foreach ($itemName in @('engine', 'controller')) {
    $item = $man.workshop_items.$itemName
    $dest = Join-Path $workshop $item.stage_dir
    foreach ($entry in @($item.runtime_files) + @($item.auxiliary_files)) {
        $rel = Join-Path $dest $entry.stage_path
        if ($entry.dll_input) {
            $dst = Join-Path $dest $entry.stage_path
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
            [IO.File]::WriteAllBytes($dst, $dllBytes)
        } else {
            $raw = RepoBytes $entry.source
            $hash, $norm = NormalizedHash $raw $entry.source
            if ($hash -ne $entry.sha256.ToLower()) {
                throw "source hash mismatch: $($entry.source): got $hash, want $($entry.sha256)"
            }
            $dst = Join-Path $dest $entry.stage_path
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
            [IO.File]::WriteAllBytes($dst, $norm)
            if ($entry.stage_path -like 'SOURCE.txt') {
                $txt = [Text.Encoding]::UTF8.GetString($norm)
                if (($txt -match 'PLANNED-PLACEHOLDER') -and -not $AllowPlaceholderUrls) {
                    throw "unresolved placeholder source URL in $($entry.source): publish-ready build refused (use -AllowPlaceholderUrls for RC)"
                }
                if ($txt -match 'PLANNED-PLACEHOLDER') {
                    Write-Host "WARNING: RC placeholder source URL staged from $($entry.source)"
                }
            }
        }
        $staged += $rel
    }
    # per-item checksum file over packaged bytes
    $lines = @()
    foreach ($f in ($staged | Where-Object { $_ -like "$dest*" } | Sort-Object)) {
        $h = ([Security.Cryptography.SHA256]::Create().ComputeHash([IO.File]::ReadAllBytes($f)) |
            ForEach-Object { $_.ToString('x2') }) -join ''
        $lines += "$h  " + [IO.Path]::GetRelativePath($OutDir, $f).Replace('\', '/')
    }
    [IO.File]::WriteAllLines((Join-Path $dest 'CHECKSUMS-item.sha256'), $lines)
}

# --- source assets (exact registry source + release docs) ---
foreach ($asset in $man.source_release.build_assets) {
    $raw = RepoBytes $asset.source
    if ($asset.sha256) {
        $hash, $norm = NormalizedHash $raw $asset.source
        if ($hash -ne $asset.sha256.ToLower()) {
            throw "asset hash mismatch: $($asset.source)"
        }
    } else {
        $norm = $raw
    }
    $dst = Join-Path $assets $asset.asset_path
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
    [IO.File]::WriteAllBytes($dst, $norm)
    $staged += $dst
}

# --- fail-closed staging audit ---
$all = Get-ChildItem $OutDir -Recurse -File | ForEach-Object { $_.FullName }
foreach ($bad in $man.forbidden_in_release) {
    $hit = $all | Where-Object { $_ -like "*$bad*" }
    if ($hit) { throw "forbidden release content staged: $($hit -join ', ')" }
}
$itemSums = @()
foreach ($itemName in @('engine', 'controller')) {
    $itemSums += Join-Path (Join-Path $workshop $man.workshop_items.$itemName.stage_dir) 'CHECKSUMS-item.sha256'
}
$expected = ($staged | Sort-Object) + $itemSums
$extra = $all | Where-Object { $_ -notin $expected -and (Split-Path -Leaf $_) -ne 'CHECKSUMS.sha256' }
if ($extra) { throw "unstaged/unexpected files in output: $($extra -join ', ')" }

$rootLines = @()
foreach ($f in ($all | Where-Object { (Split-Path -Leaf $_) -ne 'CHECKSUMS.sha256' } | Sort-Object)) {
    $h = ([Security.Cryptography.SHA256]::Create().ComputeHash([IO.File]::ReadAllBytes($f)) |
        ForEach-Object { $_.ToString('x2') }) -join ''
    $rootLines += "$h  " + [IO.Path]::GetRelativePath($OutDir, $f).Replace('\', '/')
}
[IO.File]::WriteAllLines((Join-Path $OutDir 'CHECKSUMS.sha256'), $rootLines)
Write-Host "assembled $($man.release_version): $($all.Count) files + CHECKSUMS.sha256"
