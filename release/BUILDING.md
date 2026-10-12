# X10 v1.0.0-rc2 — build instructions

Two separate reproducibility paths. The clean civ6-x10 source snapshot
alone does NOT regenerate the 2481-entry registry from scratch (its
inputs are private audit material); use the exact-asset path for a
byte-verifiable engine binary.

## Exact engine binary (hash-verifiable corresponding build)

1. Checkout the engine source (exact, available now):
   `https://github.com/Dacilla/CivilizationVI_CommunityExtension-X10`
   branch `phase-8b-coverage` (CE fork) at commit `29e8b7f`.
   That commit already contains the exact generated
   `X10/X10ProductionRegistry.inc` used by the distributed DLL (2481
   entries / 2475 definitions; verify against the `registry_sha256` in
   `release-manifest.yml`).
2. Toolchain: MSBuild 17.14 (Visual Studio 2022), platform toolset v143,
   Windows SDK 10.0, configuration Release, platform x64:
   `msbuild CivilizationVI_CommunityExtension.sln /p:Configuration=Release
   /p:Platform=x64`
3. Output DLL must SHA-256 to:
   `e0486aee0844926c35c8770da937e5a9237db6778a13ea4fa4d1f8453cdea06c`
   (binary hash; MSVC builds are not claimed byte-reproducible across
   toolchains — this is a corresponding-source build, verified by hash).

## Controller (text-only)

The controller ships as source: `X10.modinfo`, `Config/X10Config.sql`
(preset dropdown, custom value, thirteen bool module checkboxes, default
preset ×10 Classic / all ON), `Config/X10Text.sql` (en_US setup text),
`Config/X10WonderBridge.sql` (non-destructive direct-table delta bridge),
`Config/X10SlotCopies.sql` (inert bonus-slot copies + filler policies),
`Config/Dummy.sql`, plus the four auxiliary text files. No compilation
is involved.

## Assembling the two Workshop staging directories

From the release source with a verified DLL available:

```powershell
pwsh -NoProfile -File release/assemble-release.ps1 `
  -OutDir release/out/1.0.0-rc2 `
  -DllPath <path to GameCore_XP2_CE_FinalRelease.dll> `
  -AllowPlaceholderUrls
```

The assembler verifies every input (exact DLL binary hash;
LF-normalized text hashes from `release-manifest.yml`), stages exactly
the `workshop_items` file lists (refusing probe content), and writes
`CHECKSUMS.sha256` over packaged bytes. Omit `-AllowPlaceholderUrls`
for a publish-ready build: any unresolved `PLANNED-PLACEHOLDER` source
URL then fails the assembly.
