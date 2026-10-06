# Dynamic Multiplier Spike

Target UX: per-module arbitrary multipliers (e.g. Traits 7.3×, Policies
4.25×) flowing Setup Parameter → `GameConfiguration.GetValue()` → X10
transform → CE/GameCore override → effect, with no per-multiplier SQL.

## Results

Generalized transforms implemented and tested (`civ6x10/transforms.py`,
`tests/test_dynamic_spike.py` 12 tests): `scale_flat`, `combat_bonus_for_multiplier`
(`b_k = 25·ln(k·(exp(b/25)−1)+1)`; +5 @7.3× = 24.03), probability
`1−(1−p)^k`, discount compounding. k=10
reproduces canonical values exactly. Config parsing (`civ6x10/config.py`,
range 0..100, 0=Off, unknown-module rejection, `reconstruction_key` for
save/reload identity) tested.

## Correction (2026-10-06 review): what the probe does NOT prove

The original probe mod (`spike/probe-mod/`) does NOT prove
`Advanced Setup parameter → GameConfiguration.GetValue`: `X10_PROBE_K` was
never declared in mod configuration, so `probe.lua` silently falls back to
7.3. It validates only vanilla `GameEffects` reads + Lua transform
arithmetic — useful but not load-bearing. A new probe
(`spike/native-probe/`) declares a real `X10_PROBE_K` text parameter
(default `7.3`) and fails loudly if it is missing.

## Native fork status (2026-10-07)

- Sibling clone: `../CivilizationVI_CommunityExtension-x10-spike`, branch
  `x10-lifecycle-log` (committed locally, never pushed upstream).
- Unmodified baseline builds: yes, MSVC 14.51 + SDK 26100, Release x64.
  Baseline DLL 2,667,008 B, SHA-256
  `7decd10c…5382ce`. (Upstream repo was missing `asmjit/x86/` at HEAD and
  expects prebuilt MinHook/Capstone libs; restored locally from asmjit
  1.13.0-era sources + fresh MinHook/Capstone builds. Workshop CE 1.3 DLL
  hash `36ba8715…` is untouched.)
- Logging fork builds: yes, same toolchain. Current DLL 2,671,616 B, SHA-256
  `4c2c1668…ad2258` (adds `X10Lifecycle.LogMsg` file-log helper). Hooks
  PopulateModifierDefinitions, AddModifierDefinition, both DynamicModifier
  ctors (all void-returning, fail-closed validation; Attach* skipped —
  struct returns need exact layout); Lua-init marker in gameplay
  `RegisterScriptData`; `X10Lifecycle.Ping()` for script liveness.
  Log: `%TEMP%\X10Lifecycle.log` with monotonic counters.
- LIVE observation received (see next section): ordering is populate → add →
  EXIT → first instantiation → Lua init; all 4 signatures PASS on the user
  build. Remaining pending: write implementation, save/load, symmetry. No
  write has been tested; do not cite arithmetic tests as live verification.

## LIVE RESULT (2026-10-07): gameplay Lua initializes TOO LATE

Live log from the logging-only fork (user GameCore `0xc60000`/`0x667c6f5b`,
all 4 signatures PASS, 4 hooks installed):

```text
PopulateModifierDefinitions ENTER
AddModifierDefinition...
PopulateModifierDefinitions EXIT
FIRST DynamicModifier instance (x3)
X10 gameplay Lua initialized
X10 probe gameplay script alive
```

Ordering: populate → add → EXIT → first instantiation → Lua init.
Therefore normal gameplay Lua CANNOT serve as the pre-attachment mutation
phase. The init-phase Lua setter is abandoned as the primary architecture;
the write prototype moves to native definition-construction/population
(see native fork branch `x10-lifecycle-log`). This is LIVE_GAME_VERIFIED,
not hypothetical.

## Native setup configuration: traced, no generic getter found

`GameConfiguration.GetValue` is `Lua::IGameConfiguration::lGetValue`
(0x6d8550). Disassembly shows it reads the Lua key, hashes it, and resolves
through Lua-bound helpers (import thunks at 0x9afd9a/0x9afdbe, string hash at
0x606270) — there is NO generic native `Configuration::Game::Instance`
value getter in the indexed symbols (only typed getters: era, speed,
handicap, seeds…). Conclusion: no named/supported native config reader was
identified. Follow-up routes: (a) disassemble deeper from `lGetValue` into
the variant store; (b) session-scoped generic in-fork registry fed from
frontend Lua; (c) save-persisted config on load. Per policy, no hardcoded
7.3 and no file-based production plumbing unless no engine route exists.

## Definition construction (static disassembly, 2026-10-07)

`SimpleModifierDefinition` ctor (0x92e6a0, 370 B) is fully readable: the
incoming rvalue is an INTERFACE (vtable + ~10 virtual getters, not raw
values); string members are built at this+0x18/0x58/0x78 via a string-copy
helper (0x76c40) with an SSO/empty pattern; ints at +0x38, uint16 stacking
limits at +0x98/+0x9a; the argument list member is built by 0x9294b0 from
the +0x48 getter. Next RE step (static, no game needed): disassemble
0x9294b0 + the string layout to pin the exact (name, value) element edit
point. Only then implement the write. Effect-arg caching is validated by
readback, not assumed.

## Save/load design

Derived state = f(official DB value, saved k). On load recompute and
compare-before-write: already-correct values are never rewritten, so no
double-application. `AffectsSavedGames` implications documented in the
extension API design (init-phase-only writes need no per-turn state).

## AI/player symmetry

Definition-level overrides (before attach) affect all players, AI, city
states, and barbarians uniformly — strictly better than per-player patching.
Confirmed by reference-held instance semantics; per-effect arg-caching
exceptions to be validated per family.

## Config UI: HYBRID

Presets now (Off/×2/×3/×5/×10/×20/×50/×100 generated SQL — shippable today);
arbitrary numeric input per module once the CE path validates. Fractional k
on REPEAT_GRANT/CHARGES/integer counts is DECISION_REQUIRED (no silent
flooring); slots and booleans never scale.

## Manual test checklist (superseded for ordering; write test pending)

The ordering run is DONE (see LIVE RESULT). The old read-only checklist is
retained for reference only:

1. Enable CE + X10Probe (disposable profile, no production mods).
2. New Gathering Storm game, Small map, 2 AI (fast loads).
3. Console/log: `[X10Probe] k=7.3`, three lines with official 3/50/5 and
   scaled 21.90/365.00/24.03.
4. Save, exit to menu, reload, confirm identical lines (no duplicates).
5. Report `Lua.log` excerpt + result. Total: ~10 minutes.

Next live step is the write build (definition-population overrides +
`GameEffects` readback + save/load), not a repeat of the ordering run.

## Risks

Per-effect arg caching at `Initialize` (unverified for some classes);
Lua game-start ordering vs bulk attach (load-bearing unknown); offset drift
on future GameCore patches (CE pins one build); Dev CE 251-function surface
untested as a whole (shortlist only). No upstream PR, no Dev CE dependency,
no raw-memory in production.

## Proposed generic CE addition (design only, no fork in this pass)

```lua
-- init-phase only (refused after first attach pass)
ModifierDefinitions.GetArgument(modifierId, argumentName) -> value|nil
ModifierDefinitions.SetArgument(modifierId, argumentName, value) -> true
-- raises clean Lua errors on: unknown id, unknown arg, type mismatch,
-- non-numeric where numeric required, call after init freeze.
-- Offsets hidden in CE. No X10 semantics. Deterministic. No RegisterProcessor.
```
