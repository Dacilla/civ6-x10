# Remove ONLY the disposable production-candidate folders. Nothing else touched.
$ErrorActionPreference = 'Stop'
$mods = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'My Games\Sid Meier''s Civilization VI\Mods'
if ($mods -match 'workshop') { throw "refusing: resolved path looks like Workshop: $mods" }
foreach ($m in @('CE-X10', 'X10', 'X10_Probe_Test')) {
    $dst = Join-Path $mods $m
    if (Test-Path $dst) {
        Remove-Item $dst -Recurse -Force
        Write-Host "removed: $dst"
    } else {
        Write-Host "nothing installed at: $dst"
    }
}
