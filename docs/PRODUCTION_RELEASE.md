# Production Release Track (Release 1 + Phase 2)

## Module status

- Traits: **LIVE_VALIDATED** (tag `release1-684-live-validated`; evidence in
  `spike/validation-evidence/`).
- Policies: **LIVE_VALIDATED** (same tag/evidence).
- Governments: **LIVE_VALIDATED** (same tag/evidence).
- Pantheons: **CERTIFIED** (Phase 2: 23 pantheons audited, 31 native rows —
  28 unconditional + 3 count-like; 3 partial with documented exclusions;
  see `docs/PANTHEON_AUDIT.md`). Awaiting targeted live validation.
- Wonders: **CERTIFIED** (Phase 3 + 3B + 3C: 53 wonders audited — 22 complete,
  29 partial, 2 unsupported; 154 native rows = 97 modifier-backed + 57
  generated direct-table bridge helpers; see `docs/WONDER_AUDIT.md`).
  Awaiting targeted live validation.
- Governors / Suzerains: not started (remain unsupported).

Follow-up (not a blocker): the two excluded Toqui governor-pressure rows
await stored-form re-certification via the store-lookup witness.

Status vocabulary (do not conflate):

Status vocabulary (do not conflate):

- **Four-ID architecture proof: LIVE_GAME_VERIFIED.** Native FLOAT32 config
  read, definition-population writes with `stored_after_add` MATCH, Rome
  runtime PASS, identical save/reload (2026-10-07, k=7.3).
- **870-entry certified production slice (684 Release-1 + 31 Pantheon + 155
  Wonder/Suleiman incl. 57 bridge helpers): STATICALLY VERIFIED, awaiting targeted live test.**
  738 unconditional entries transform at any k; 132 count-like entries
  apply only on integral results under the FLOAT32-aware exactness rule
  (at live stored-float k=7.3: 750 static successes of 870 — honest
  fractional refusal, never flooring). Full gate in
  `docs/SEMANTIC_CERTIFICATION.md`, pantheon audit in
  `docs/PANTHEON_AUDIT.md`, wonder audit in `docs/WONDER_AUDIT.md`.
  The Toqui loyalty pair (`TOQUI_DOMESTIC/FOREIGN_LOYALTY`) is temporarily
  excluded pending stored-form re-certification (see below).
- **Workshop release: NOT READY.** No publish until the production-candidate
  live test passes and logs are reviewed.

## Packaging / dependency strategy (decided)

Separate dependency, not a bundle:

- **X10 CE Engine** (`CE-X10`, stable mod id
  `397f2070-dfde-4124-88ce-e34249fc8190`): carries the GameCore redirect
  (`EngineRedirect.sql`) + fork DLL. Versioned independently of tuning.
- **X10 controller** (stable mod id
  `55d7b934-62f9-46fb-a771-badf3d1a1538`): config (`X10Config.sql`), depends
  on the engine GUID + Gathering Storm. No DLL of its own.
- **X10 Production Probe** (DISPOSABLE, local tests only,
  `d904eb69-6ce8-43ac-960a-ac9120d89b4e`): temporary diagnostic readback,
  configured by `X10_MULTIPLIER`, never shipped.

Rationale: the engine (native, high-risk, rarely changes) and the controller
(config/semantics, evolves) have different review and rollback profiles.
Disabling the controller leaves stock behavior; disabling the engine removes
the GameCore replacement entirely. Install/uninstall helpers live in
`spike/install-prod-test.ps1` / `spike/uninstall-prod-test.ps1` (local Mods
folder only; Workshop paths refused).

## Shared-definition ownership (Release 1 rule)

25 modifier definitions are owned by both Policies and Governments
(registry: 358 traits-only, 284 policies-only, 18 governments-only,
31 pantheons-only, 154 wonders-only = 97 modifier-backed + 57 generated
bridge helpers, 25 shared policies+governments;
866 unique definitions, 870 entries: 738 unconditional + 132
count-like conditional). A definition-level mutation
is globally shared, so exact independent toggles are impossible. Conservative
rule: **a shared definition is transformed only if ALL owning supported
modules are enabled.** Disabling one module never leaves its mutation active
via another owner. Generation unions owners into a bitmask
(`1=traits 2=policies 4=governments`) and FAILS on duplicate rows that
disagree on official value / transform / family / count-like classification
(`RegistryConflict`) instead of silently choosing one. Canonical-tag counts
are never reported as full module coverage; reports carry unique entries +
ownership counts + shared-definition count.

## Multiplier and module semantics

- `X10_MULTIPLIER = 0` means **Off**: native does not arm writes, official
  definitions stay untouched, log line
  `X10 multiplier 0: controller OFF (definitions untouched)`.
  `k=1` is the identity multiplier.
- Pantheons / Governors / Wonders / Suzerain controls exist in the UI with
  default OFF for Release 1. Enabling one logs
  `X10_MODULE_<name> requested ON but unsupported in this build; ignored`
  and applies nothing.

## Native architecture notes

- Signed transforms: `FiniteSane` bound (`|v| <= 1e6`); negativity is valid
  (43 negative entries incl. 15 discounts + 4 flat-cost maintenance rows).
  Family validity stays
  per-transform (probability/discount ranges, combat log domain, count
  integrality — fractional counts refused, never floored).
- Multi-argument writer: `WriteDefinition` applies ALL matching entries per
  definition (4 two-argument definitions keep Amount + TurnsActive); post-Add
  verification covers every touched entry by logical identity (ID + argument
  + expected), resolved through the registered store — never a retained
  pre-Add pointer. One argument's refusal never blocks another.
- Post-Add witness tiers: textual definition retained → MATCH/MISMATCH
  (both increment `post_add_match`/`post_add_mismatch`); definition found
  but value blank/absent → typed-or-consumed (`post_add_unreadable`);
  lookup miss/fault/degraded path → unreadable. Exit summary is fully
  counter-derived and cannot report zero mismatches after a MISMATCH line.
- Compatibility: all build/ABI constants (PE identity, hook RVAs, config
  reader RVAs, manager offsets, vtable slot, variant layout, definition
  layout, SSO assumptions) live in `GameCoreCompatibilityProfile`
  (`X10Compat.h`); `Install` selects a profile or installs zero hooks.
- Hook rollback is X10-only and transactional (create-all then enable-all,
  unwinding only X10 hooks on failure). Upstream CE hooks are never
  disabled/removed by X10 failure paths.

## Toqui loyalty stored-form hold (2026-10-08)

Live runs showed `TOQUI_DOMESTIC_LOYALTY` / `TOQUI_FOREIGN_LOYALTY`
(`EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE`, Amount 4 → 29.2) verifying blank
post-Add while 610 siblings MATCH on both initial load and reload: the raw
string reads back empty (size 0, clean — not unreadable), unique to the two
definitions sharing that effect plus `OncePerCity` / `Domestic|ForeignCities`
flag args. Static analysis proves in-place post-Add string emptying but not
which engine op performs it (move/clear/realloc inside Add's store path).
Both entries are therefore **temporarily excluded** from the certified
registry (`excluded_effects` in `certified_overrides.yml`, rationale cites
this hold) until the store-lookup witness proves stored MATCH or typed-value
persistence live. Re-certification procedure: remove the exclusion entry,
regenerate, rebuild, run once, require `MATCH via=store-lookup` for both.

## Public-data hygiene (explicit release decision, no legal claim made)

The CE-X10 tree currently carries the generated registry
(`X10/X10ProductionRegistry.inc`: 813 certified Firaxis modifier IDs +
official values). Earlier project policy avoided publishing bulk extracted
Firaxis data. Decision for Release 1:

- The `.inc` becomes a **build artifact, not a source file**: it is
  generated during developer/release builds from local audited inputs
  (`python -m civ6x10 generate-registry`, manifests are local-only and
  gitignored) and gitignored in CE-X10 with a checked-in stub + generator
  pointer.
- AGPL corresponding-source for any distributed DLL is satisfied by
  publishing, with the binary release: the exact generator code, the
  profile/transform/version inputs, and the exact generated `.inc` used for
  that build (release asset, hash-pinned in `EXPECTED_DLL_SHA256.txt`).
  Anyone with a local official install can reproduce the inputs; the repo
  tree itself carries no bulk extracted data.

Migration is a pre-release step (tracked; the in-tree file remains until the
stub + CI generation check land). No Workshop publish before it.

## Phase-2 targeted live test (VALIDATED 2026-10-08)

Pantheon definitions populate from the database at load whether or not any
player founds them. Run produced `writes=638 transform_refused=77
official_mismatch=0 post_add_match=638 post_add_mismatch=0
post_add_unreadable=0 skipped_other=0` (evidence in
`spike/validation-evidence/`, tag `release1-684-live-validated` covers the
pre-pantheon core).

## Phase-3 targeted live test (one game, no save/reload)

Wonder definitions populate from the database at load whether or not any
wonder is built, so the definition-level proof needs no in-game action;
building the Statue of Zeus additionally proves the gameplay effect.

1. `pwsh -NoProfile -File spike/install-prod-test.ps1` (hash-verifies the
   current DLL, installs, clears previous-run logs once).
2. Disposable profile; disable Workshop CE; enable X10 CE Engine + X10 +
   X10 Production Probe.
3. Single Player > Create Game > Gathering Storm, ROME (Trajan), Small map,
   2 AI. Multiplier 7.3, all supported modules ON (wonders now supported).
4. Start, reach the map, end 1 turn. (Optional gameplay proof: build the
   **Statue of Zeus**, then inspect a city's anti-cavalry production
   tooltip for the transformed bonus.)
5. Send `%TEMP%\X10Lifecycle.log` (+ `%TEMP%\X10Probe.log`).

Pass target (one population, no reload required — save/reload determinism
already proven repeatedly):
`writes=750 transform_refused=120 official_mismatch=0 post_add_match=750
post_add_mismatch=0 post_add_unreadable=0 skipped_other=0`,
plus `STAUEZEUS_ANTI_CAVALRY_PRODUCTION
stored_after_add=365 expected=365 MATCH via=store-lookup`
AND the direct-bridge witness `X10_PANAMA_CANAL_YIELD_GOLD
stored_after_add=73 expected=73 MATCH via=store-lookup`
(Panama helper Amount 10 → 10×7.3, now carried as a building yield with
`BuildingType=BUILDING_PANAMA_CANAL` + `YieldType=YIELD_GOLD`).
If Zeus was built before the probe ran, expect the probe line
`... Amount=365 expected=365.00 PASS`; otherwise the probe reports the
handle ABSENT (not a failure — the native MATCH line is the proof).
The Panama helper populates from the database at load (bridge SQL attaches
it to the wonder), so its MATCH line needs no in-game action.

Phase-3D note (Portugal-pack load order): the 3C live run showed 748+119
with exactly three helpers unmaterialized — all three source rows arrive
via Portugal's gameplay update AFTER X10WonderBridge executes (proven from
the run logs; both DLC packs were enabled). The bridge SQL now carries
deferred guarded triggers + an `X10BridgeDiag` table; the next run must show
`definitions_added=3267 writes=750 transform_refused=120 post_add_match=750
mismatch=0 unreadable=0`, both MATCH witnesses (Zeus 365, Panama 73), and
57 `[X10BridgeDiag]` lines (54 immediate + 3 trigger) with
`bridge_materialized=57 bridge_unavailable=0`. Native DLL unchanged by 3D.

Gameplay proof for the helper mechanism (beyond definition-store
persistence): modifierization is a new gameplay path, so one practical
check is needed that a generated helper actually contributes to an active
building's output. Minimal dedicated local diagnostic (throwaway, never
shipped): a temporary probe-script addition that grants
`BUILDING_PANAMA_CANAL` to the capital on turn 1 and logs the city's
gold-per-turn delta in two runs of the same setup — k=1 (expect +10 vs the
pre-grant baseline) and k=7.3 (expect +73). No shipped code changes; the
bridge SQL + native write path are identical to the live run, only the
building placement is scripted because a natural canal wonder is
map-dependent. (The Zeus gameplay witness separately proves the shared
native write path affects live tooltips.)

## Production-candidate live test (run only on instruction)

Prerequisites: production DLL built, hash matches
`spike/EXPECTED_DLL_SHA256.txt`, package assembled via
`spike/assemble-prod-test.ps1`.

1. `pwsh -NoProfile -File spike/install-prod-test.ps1` (verifies hash,
   installs CE-X10 + X10 + X10_Probe_Test into the local Mods folder only).
2. Disposable profile recommended. Additional Content: DISABLE Workshop
   Community Extension; ENABLE X10 CE Engine + X10 + X10 Production Probe.
3. Single Player > Create Game > Gathering Storm, play ROME (Trajan), Small
   map, 2 AI. Set multiplier 7.3, all supported modules ON.
4. Start, reach the map, end 1 turn, save, exit to menu, reload once.
5. Send `%TEMP%\X10Lifecycle.log` + `%TEMP%\X10Probe.log`.
6. Rollback any time: disable the three mods (or
   `spike/uninstall-prod-test.ps1`).

Pass criteria: `compatibility profile` selected, `CONFIG key=X10_MULTIPLIER
found=true`, up to 750-eligible write sequence at live stored-float k=7.3
(738 unconditional + 12 exact-integral conditional under the
FLOAT32-quantization-aware rule) with `stored_after_add MATCH
via=store-lookup`, `post_add_mismatch=0`, `post_add_unreadable=0`, probe PASS
lines, identical values across save/reload. The exit summary is fully
counter-derived (`writes / transform_refused / official_mismatch /
post_add_match / post_add_mismatch / post_add_unreadable / skipped_other`):
it cannot report zero mismatches after a MISMATCH line.
