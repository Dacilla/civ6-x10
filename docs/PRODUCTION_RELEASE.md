# Production Release Track (Release 1 + Phase 2)

## Module status

- Traits: **LIVE_VALIDATED** (tag `release1-684-live-validated`; evidence in
  `spike/validation-evidence/`).
- Policies: **LIVE_VALIDATED** (same tag/evidence).
- Governments: **LIVE_VALIDATED** (same tag/evidence).
- Pantheons: **LIVE_VALIDATED** (Phase 2, tag `phase2-715-live-validated`:
  23 pantheons audited, 31 native rows — 28 unconditional + 3 count-like;
  3 partial with documented exclusions; 638 writes + 77 refusals at k=7.3;
  see `docs/PANTHEON_AUDIT.md`).
- Wonders: **LIVE_VALIDATED** (Phase 3 + 3B + 3C, tag `phase3-813-live-validated`:
  53 wonders audited — 22 complete, 29 partial, 2 unsupported; 97
  modifier-backed rows plus the 57-helper guarded direct-table bridge;
  bridge diagnostics 57/57/0 and Zeus 365 + Panama 73 witness MATCH;
  see `docs/WONDER_AUDIT.md`).
- Governors: **LIVE_VALIDATED as the 54-row Phase-4B slice** (tag
  `phase4b-924-live-validated`: 54 audited candidate rows from
  `docs/GOVERNOR_AUDIT.md`, owner bit 32, `X10_MODULE_GOVERNORS` default ON;
  48 ADDITIVE + 6 COMBAT, 5 engine-integral-conditional. Governors ON:
  `writes=748 transform_refused=176 ... post_add_match=748 ...` with 49 of
  54 written and 5 integral refusals. Governors OFF: `writes=699
  transform_refused=171 ... skipped_other=54`, exactly 54
  `owners=0x20 not-all-enabled skipped` lines and zero Governor mutations.
  Evidence: `spike/validation-evidence/X10*924-gov*-live.log`).
  **Phase 6B extends Governors to 70 rows** (54 `phase4a.1-governor-audit` +
  16 `phase6a-semantic-backlog`, generated mechanically from
  `semantic_backlog.yml::proposed_production_pairs`; 64 ADDITIVE + 6 COMBAT,
  14 count-like): **CERTIFIED, awaiting Phase-6C targeted live validation**.
- Suzerains / City-states: **LIVE_VALIDATED as the 47-row Phase-5B slice**
  (Phase 5A.1 audit + Phase 5B production integration + Phase 5C live
  validation, tag `phase5b-971-live-validated`: 47 conservative numeric rows
  mechanically derived from `civ6x10/rules/suzerain_audit.yml`
  (`phase5a.1-suzerain-audit` source), owner bit 64, `X10_MODULE_SUZERAIN`
  default ON; 44 ADDITIVE — 35 unconditional + 9 count-like Bologna
  GP-point rows — and 3 DISCOUNT Ngazargamu rows with `compound_discount`.
  Suzerain ON: `writes=786 transform_refused=185 ... post_add_match=786 ...`
  with 38 of 47 written and 9 Bologna integral refusals. Suzerain OFF:
  `writes=748 transform_refused=176 ... skipped_other=47`, exactly 47
  `owners=0x40 not-all-enabled skipped` lines and zero Suzerain mutations.
  Evidence: `spike/validation-evidence/X10*971-suz*-live.log`).
  **Phase 6B extends Suzerain to 68 rows** (47 + 21
  `phase6a-semantic-backlog`; 61 ADDITIVE + 6 DISCOUNT incl. Valletta ×3 +
  1 COMBAT Lahore; 21 count-like): **CERTIFIED, awaiting Phase-6C targeted
  live validation**.
  Still out of scope: ScalingFactor rows, direct Governor IdentityPressure
  columns, unique-improvement intrinsic cells, Nihang intrinsic/progression
  cells, the Sanguine −5 penalty, healing, Kandy unresolved scaling and
  other held side paths. Narrow improvement ownership stays adopted
  (see `docs/SUZERAIN_AUDIT.md`, `docs/SEMANTIC_BACKLOG.md`).

- Phase 6B (cross-module backlog integration): **LIVE_VALIDATED as the
  1010-entry build** (Phase 6C, tag `phase6b-1010-live-validated`; see
  Phase-6C record below). 1010 entries /
  1006 unique / 25 shared; 788 unconditional + 222 count-like (973
  ADDITIVE / 14 COMBAT / 23 DISCOUNT). Static k=7.3 expectation: 801 writes
  / 209 refusals; at k=10 all 1010 apply. DLL
  `e33d84b83d752a9eb7b52b4740291c97183af4d079d1ca82b8bd9d92b5c4d619`;
  bridge SQL unchanged
  (`d0faabfa29c32360dd48718383af173424a3ab51589877f3b597bbcec0e205b1`).
  **Intentional correction:** Corporate Libertarianism / Coal / Iron were
  live-tested as fractional writes and are now count-like by reviewed
  correction (Phase 6C must confirm writes→refusals).

- Phase 6C targeted live validation: **VALIDATED 2026-10-11** (tag
  `phase6b-1010-live-validated`). Run A (all ON, load+reload identical):
  `writes=801 transform_refused=209 official_mismatch=0
  post_add_match=801 mismatch=0 unreadable=0 skipped_other=0`
  (`definitions_added=3336`). 39 new pairs: 18 writes with exact static
  values (Toqui 29.2 ×2, Bishop 730, Owls loyalty 29.2, Preslav 14.6 ×3,
  Vatican 2920, Citadel 182.5, Ayutthaya 73, Lahore 38.10 COMBAT, Valletta
  99.3654 ×3 DISCOUNT — compound, not 365/500) + 21 count-like refusals, 0
  skipped/mismatched/unreadable. The 3 accumulation rows refuse with zero
  write lines (previously 7.3/14.6/14.6 in 5C evidence — intentional
  change, not a regression). All §10 regressions hold (Groundbreaker 365,
  Garrison 24.04, Owls interest 21.9, Ley Line 7.3, Auckland 7.3,
  Antananarivo 14.6, Ngazargamu 80.3864, Zeus 365, Panama 73, bridge
  57/57/0). Run B (Governors OFF + Suzerain OFF, Secret Societies ON):
  `writes=698 transform_refused=174 post_add_match=698 skipped_other=138`
  with exactly the 70+68 manifest skip sets and zero masked mutations;
  Toqui still writes (traits owner proven), accumulations still refuse.
  Run-A-minus-masked == Run B exactly. A first Run-B attempt with Secret
  Societies OFF yielded 116 skips (22 mode-gated governor definitions
  absent from the DB); re-run with the mode ON gave the letter-perfect
  70/68. Evidence: `spike/validation-evidence/X10Lifecycle.1010-6C-run{AB}.log`,
  `X10Probe.1010-6C-run{AB}.log`.

- Phase 7C.2 UX integration (NOT live-validated yet): setup migrates to
  native Advanced Setup (preset dropdown `X10_MULTIPLIER_PRESET`,
  custom `X10_MULTIPLIER` text, seven bool `X10_MODULE_*` checkboxes,
  en_US localization, SP-only flags); native reader gains
  preset/custom/bool resolution with legacy fallback; new DLL
  `3b6dc3d2...ab14` (CE `0655190`); same 1010 gameplay set/transforms.
  Release candidate `1.0.0-rc2`, awaiting the 7C.2 validation matrix
  (preset-x10 1010/0, Custom-7.3 801/209, Custom-7.3-no-Gov 745/195/70,
  Off disarmed, probe-free RC2 smoke).

Follow-up (done in Phase 6B): the two Toqui governor-pressure rows were
re-admitted after the 6A.2 probe proved stored MATCH via store-lookup on
load AND reload; the temporary exclusion entry is removed.

## Status vocabulary (do not conflate)

- **Four-ID architecture proof: LIVE_GAME_VERIFIED.** Native FLOAT32 config
  read, definition-population writes with `stored_after_add` MATCH, Rome
  runtime PASS, identical save/reload (2026-10-07, k=7.3).
- **1010-entry certified production slice, CERTIFIED / awaiting Phase-6C
  targeted live validation** (684 Release-1 + 31 Pantheon + 155
  Wonder/Suleiman incl. 57 bridge helpers + 70 Governors + 68 Suzerain + 2
  re-admitted Toqui traits rows):
  static expectation at stored FLOAT32 k=7.3 is 801 writes / 209 refusals
  (788 unconditional + 13 exact-integral conditional write; 209 conditional
  refuse — honest fractional refusal, never flooring).
  The prior 971-entry slice (773 unconditional + 198 count-like; Suzerain
  ON: 786 writes / 185 refusals; OFF: 748 / 176 with 47 ownership skips;
  both `post_add_match` = writes, `post_add_mismatch` = 0) stays
  LIVE_VALIDATED for every component module in both ON and OFF states, but
  the 1010 build itself is NOT live-validated yet.
  66 of the baseline conditional entries are engine-integral
  entries — 31 Wonder bridge helpers, 21 Release-1 player-cities rows and
  5 Governor rows — plus 9 Bologna suzerain GP-point rows under the existing
  GREAT_PERSON_POINTS count-like policy, plus the Phase-6B count-like
  additions (incl. the 3 intentional accumulation reclassifications; see
  Phase 3F/3G/4B/5B/6B). Full gate in
  `docs/SEMANTIC_CERTIFICATION.md`, pantheon audit in
  `docs/PANTHEON_AUDIT.md`, wonder audit in `docs/WONDER_AUDIT.md`.
  The Toqui loyalty pair (`TOQUI_DOMESTIC/FOREIGN_LOYALTY`) was
  temporarily excluded in 5C and is re-admitted in 6B after the 6A.2
  store-lookup probe (see below).
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
(registry: 360 traits-only, 284 policies-only, 18 governments-only,
31 pantheons-only, 154 wonders-only = 97 modifier-backed + 57 generated
bridge helpers, 70 governors-only, 68 suzerain-only, 25 shared
policies+governments;
1006 unique definitions, 1010 entries: 788 unconditional + 222
count-like conditional). Governor entries are governor-only: the Suleiman
governor-title definition stays traits-owned, so Governors adds no new
shared definitions. Phase 6B adds no new shared definition. A definition-level mutation
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
- Governors is a supported module (default ON, bit 32), as is Suzerain
  (default ON, bit 64). All seven current modules are supported; there is no
  unsupported-module warning path in this build.

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

## Toqui loyalty stored-form hold (2026-10-08) — LIFTED in Phase 6B

Live runs showed `TOQUI_DOMESTIC_LOYALTY` / `TOQUI_FOREIGN_LOYALTY`
(`EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE`, Amount 4 → 29.2) verifying blank
post-Add while 610 siblings MATCH on both initial load and reload: the raw
string reads back empty (size 0, clean — not unreadable), unique to the two
definitions sharing that effect plus `OncePerCity` / `Domestic|ForeignCities`
flag args. Both entries were therefore **temporarily excluded** from the
certified registry pending the store-lookup witness. The Phase-6A.2 pressure
probe (8-entry scratch registry, k=7.3, load AND reload) returned
`MATCH via=store-lookup` for both carriers, lifting the hold: Phase 6B
removed the exclusion entry, re-admitted both rows as LOYALTY from traits
ownership (family via an exact EffectType+argument inference rule, covered
by a regeneration test), and ships them unconditionally. Obsolete
stored-form-hold exclusion text elsewhere is superseded by this note.

## Public-data hygiene (explicit release decision, no legal claim made)

The CE-X10 tree currently carries the generated registry
(`X10/X10ProductionRegistry.inc`: 1010 entries / 1006 unique definitions /
25 shared — certified ModifierIds + official values). Earlier project policy
avoided publishing bulk extracted Firaxis data. Decision for Release 1:

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
`writes=748 transform_refused=176 official_mismatch=0 post_add_match=748
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

Phase-3F/3G/4B note (engine-integral values): `writes`/`post_add_match` must
equal each other (748 = 748); `transform_refused` must be
924 − 748 = **176**. 31 of those refusals are Wonder bridge helpers, 21 are
Release-1 `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_YIELD_CHANGE` entries and 5
are Governor rows (appeal 1×7.3 = 7.3 plus four building yields 2×7.3 =
14.6) — all refused at fractional k by design (the engine applies these
Amounts integrally), never floored, ceil'd or rounded.
`X10_PANAMA_CANAL_YIELD_GOLD` 10 → 73 is the affected bridge helper that
does write, and at k=10 all four governor building yields write 20 and the
appeal row writes 10.

Phase-3D note (Portugal-pack load order): the 3C live run showed 748+119
with exactly three helpers unmaterialized — all three source rows arrive
via Portugal's gameplay update AFTER X10WonderBridge executes (proven from
the run logs; both DLC packs were enabled). The bridge SQL now carries
deferred guarded triggers + an `X10BridgeDiag` table; the next run must show
`definitions_added=3267 writes=748 transform_refused=176 post_add_match=748
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

Phase-6C pass criteria for the 1010 build (all modules ON, k=7.3):
`writes=801 transform_refused=209 official_mismatch=0 post_add_match=801
post_add_mismatch=0 post_add_unreadable=0 skipped_other=0`, including:
Toqui 29.2 ×2 MATCH, Bishop 730.0, Owls loyalty 29.2, Preslav 14.6 ×3,
Vatican 2920.0, Citadel 182.5, Ayutthaya 73.0, Lahore combat ≈38.10,
Valletta discount ≈99.37; Corporate Libertarianism / Coal / Iron now
refuse (retain vanilla 1 / 2 / 2); all 21 new count-like rows refuse;
module OFF runs skip exactly the owned rows (governors 70, suzerain 68)
with zero mutations. Save/reload identical.

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

Pass criteria (1010-entry Phase-6B build, VALIDATED 2026-10-11 — see
Phase-6C section above): `compatibility profile` selected, `CONFIG
key=X10_MULTIPLIER found=true`, `writes=801 transform_refused=209
official_mismatch=0 post_add_match=801 post_add_mismatch=0
post_add_unreadable=0 skipped_other=0` at live stored-float k=7.3 (788
unconditional + 13 exact-integral conditional write under the
FLOAT32-quantization-aware rule) with `stored_after_add MATCH
via=store-lookup`, probe PASS lines, identical values across save/reload.
Run B (Governors OFF + Suzerain OFF): `writes=698 transform_refused=174
post_add_match=698 skipped_other=138` (70 owner-0x20 + 68 owner-0x40
skips). The exit summary is fully
counter-derived (`writes / transform_refused / official_mismatch /
post_add_match / post_add_mismatch / post_add_unreadable / skipped_other`):
it cannot report zero mismatches after a MISMATCH line.
