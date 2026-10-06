# Remove ONLY the disposable local test folder. Nothing else is touched.
$ErrorActionPreference = 'Stop'
$mods = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'My Games\Sid Meier''s Civilization VI\Mods'
$dst = Join-Path $mods 'X10_CEFork_Test'
if ($mods -match 'workshop') { throw "refusing: resolved path looks like Workshop: $mods" }
if (Test-Path $dst) {
    Remove-Item $dst -Recurse -Force
    Write-Host "removed: $dst"
} else {
    Write-Host "nothing installed at: $dst"
}
