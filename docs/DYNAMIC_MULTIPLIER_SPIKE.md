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

The probe mod (`spike/probe-mod/`) does NOT prove
`Advanced Setup parameter → GameConfiguration.GetValue`: `X10_PROBE_K` was
never declared in mod configuration, so `probe.lua` silently falls back to
7.3. It validates only vanilla `GameEffects` reads + Lua transform
arithmetic — useful but not load-bearing. The following are all PENDING:
definition mutation, first-attach timing, effect argument caching,
active-effect recalculation, AI symmetry, save/load reconstruction, double
application. Do not cite the read-only probe as a dynamic-multiplier test.

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
on REPEAT_GRANT/CHARGES/integer counts floors with min-1 (tested); slots and
booleans never scale.

## Manual test checklist (needs user game run)

1. Enable CE + X10Probe (disposable profile, no production mods).
2. New Gathering Storm game, Small map, 2 AI (fast loads).
3. Console/log: `[X10Probe] k=7.3`, three lines with official 3/50/5 and
   scaled 21.90/365.00/24.03.
4. Save, exit to menu, reload, confirm identical lines (no duplicates).
5. Report `Lua.log` excerpt + result. Total: ~10 minutes.

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
