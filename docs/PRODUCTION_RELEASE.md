# Production Release Track (Release 1)

Status vocabulary (do not conflate):

- **Four-ID architecture proof: LIVE_GAME_VERIFIED.** Native FLOAT32 config
  read, definition-population writes with `stored_after_add` MATCH, Rome
  runtime PASS, identical save/reload (2026-10-07, k=7.3).
- **729-entry production slice: STATICALLY VERIFIED, awaiting
  production-candidate live test.** All 729 generated entries transform at
  k=7.3 (native parity harness + `test_full_registry_transforms_at_k73`);
  runtime mismatch checks happen live against loaded definitions.
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
(registry: 394 traits-only, 292 policies-only, 18 governments-only,
25 shared; 722 unique definitions, 729 entries). A definition-level mutation
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
  (44 negative entries incl. all 8 discounts). Family validity stays
  per-transform (probability/discount ranges, combat log domain, count
  integrality — fractional counts refused, never floored).
- Multi-argument writer: `WriteDefinition` applies ALL matching entries per
  definition (7 two-argument definitions: Amount + TurnsActive); post-Add
  verification covers every touched element. One argument's refusal never
  blocks another.
- Compatibility: all build/ABI constants (PE identity, hook RVAs, config
  reader RVAs, manager offsets, vtable slot, variant layout, definition
  layout, SSO assumptions) live in `GameCoreCompatibilityProfile`
  (`X10Compat.h`); `Install` selects a profile or installs zero hooks.
- Hook rollback is X10-only and transactional (create-all then enable-all,
  unwinding only X10 hooks on failure). Upstream CE hooks are never
  disabled/removed by X10 failure paths.

## Public-data hygiene (explicit release decision, no legal claim made)

The CE-X10 tree currently carries the generated registry
(`X10/X10ProductionRegistry.inc`, ~746 lines: 729 Firaxis modifier IDs +
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
found=true`, 729-eligible write sequence with `stored_after_add MATCH` and no
unexpected MISMATCH, probe PASS lines, identical values across save/reload.
