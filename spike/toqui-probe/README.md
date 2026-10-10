# Toqui / pressure observability probe (Phase 6A research, DISPOSABLE)

Status: **PREPARED, NOT RUN.** Nothing here is built, installed, or validated.
Running it requires a human live game (the definitions only populate inside
Civ VI) plus a scratch engine DLL. Do not run any step below until Phase 6A
review explicitly asks for the run.

## Question

The 2026-10-08 Toqui hold: `TOQUI_DOMESTIC_LOYALTY` /
`TOQUI_FOREIGN_LOYALTY` (`EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE`,
`Amount` 4 → 29.2) verified blank post-Add while 610 siblings MATCHed, so
the pair was excluded pending stored-form proof. The current store-lookup
code has since gained typed-or-consumed/unreadable tiers. This probe asks:
**with the CURRENT native code, do identity-pressure definitions read back
`MATCH via=store-lookup`, or still blank?** One run answers all eight
`NEEDS_LIVE_PROBE` rows at once (Toqui ×2, Bishop, Owls loyalty, Preslav
×3, Vatican).

## Files (research inputs only — never installed by any script)

- `ToquiTestRegistry.inc` — scratch 8-entry registry (same struct layout
  as the production `.inc`; 2 Toqui owners=32 + 6 pressure rows owners
  32/64). **NEVER** copy into `build/X10ProductionRegistry.inc`.
- `toqui_probe.lua` — disposable readback (corroboration only; the native
  `stored_after_add` lines are authoritative). **NEVER** reference from a
  `.modinfo`; not packaged by any script.

## Procedure (exact)

All commands in PowerShell. `<mods>` =
`$env:USERPROFILE\Documents\My Games\Sid Meier's Civilization VI\Mods`.

0. **Preconditions.** Working tree clean (`git status` shows nothing under
   `build/`, `controller/`, `civ6x10/`, `spike/EXPECTED_DLL_SHA256.txt`;
   CE fork `git status` clean). Record the production DLL hash from
   `spike/EXPECTED_DLL_SHA256.txt` (currently `b6862b28…fb20d`).
1. **Build the scratch DLL.** In the CE fork (branch `x10-lifecycle-log`):
   back up `X10/X10ProductionRegistry.inc` to a `*.bak` OUTSIDE the repo,
   copy `spike/toqui-probe/ToquiTestRegistry.inc` over it, then MSBuild
   Release x64 with
   `/p:OutDir=C:\Users\alex\Desktop\Code\ce-test-build\` (a SCRATCH dir —
   never `ce-native-build\`). Verify the scratch DLL exists there and its
   SHA-256 differs from production. Immediately `git checkout --
   X10/X10ProductionRegistry.inc` in the fork and confirm `git status` is
   clean again (the fork must never commit the scratch registry).
2. **Swap the installed DLL.** Back up
   `<mods>\CE-X10\Binaries\Win64\GameCore_XP2_CE_FinalRelease.dll` outside
   the Mods tree. Copy the scratch DLL into that path. Back up
   `<mods>\X10_Probe_Test\probe.lua`; copy `spike/toqui-probe/toqui_probe.lua`
   over it **under the name `probe.lua`** (the modinfo references that
   name; do not edit the modinfo).
3. **Game setup.** Gathering Storm, ROME (Trajan), Small, 2 AI, multiplier
   **7.3**, Workshop CE disabled, X10 CE Engine + X10 + X10 Production Probe
   enabled, Secret Societies ON, all modules ON. No Toqui/city-state needed.
4. **Run.** New game → reach map → end 1 turn → save → exit to menu →
   reload once → exit (the original hold appeared on BOTH load and reload,
   so both are required).
5. **Collect.** `%TEMP%\X10Lifecycle.log` + `%TEMP%\X10Probe.log`.
6. **Restore FIRST, before any analysis.** Copy the backed-up production DLL
   back, verify its SHA-256 equals `spike/EXPECTED_DLL_SHA256.txt`;
   restore the backed-up `probe.lua`; confirm `git status` clean in both
   repos (the only allowed deltas are the two returned log files, archived
   later under `spike/validation-evidence/`).

## Verdict criteria

For each of the eight ids, in EACH population session:

- `stored_after_add=<v> expected=<v> MATCH via=store-lookup` with
  approximately Toqui 29.2 / Bishop ~730.0 / Owls loyalty 29.2 / Preslav
  ~14.6 ×3 / Vatican ~2920.0 → **hold lifted for that definition** (re-
  certification path opens; still needs the normal manifest + gate review).
- blank post-Add / unreadable / mismatch → **hold stays** (row remains
  `NEEDS_LIVE_PROBE` or moves to excluded; no silent re-certification).

Both Toqui rows MATCH on load AND reload is required to lift the Toqui hold;
a split verdict keeps the hold. Partial MATCHes among the six siblings are
reported per definition — they do not lift each other.
