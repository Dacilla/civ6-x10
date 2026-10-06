# Community Extension Evaluation (architecture spike)

Research copies (gitignored, not vendored): `research/CivilizationVI_CommunityExtension`
(Wild-W), `research/civ6-gamecore-reference` + `research/civ6-dev-ce` (cru121).

## 1. Installed CE

- Workshop path: `...\steamapps\workshop\content\289070\3277976174`
- Version: 1.3 (`.modinfo` GUID `3351473b-0746-417a-a618-2b66a04d8f3d`)
- DLL: `Binaries\Win64\GameCore_XP2_CE_FinalRelease.dll`, 2,657,792 bytes,
  SHA-256 `36ba8715…f846f662f`, PE link 2024-08-02.
- Layout: modinfo + 2 SQL + watermark UI + DLL. Loads via `GameCores` row
  (`DllPrefix = GameCore_XP2_CE`). `AffectsSavedGames = 0`.

## 2. GameCore identity

- `DLC\Expansion2\Binaries\Win64\GameCore_XP2_FinalRelease.dll`, 12,940,384 bytes,
  SHA-256 `324c51e9…11646c2e98`, PE link 2024-06-26, no version resource.
- Steam build 15296837. Reference repos target in-game build 15038592; no
  expected-DLL hash is recorded there, so the match is assessed as: CE linked
  ~5 weeks after this GameCore build (same generation), and the user runs CE
  with no load issues (empirical compatibility). Offset-level certainty
  requires the Frida/named-crash tooling in `civ6-gamecore-reference`
  (not run in this pass).

## 3. Capability inventory

Machine-readable: `spike/ce_capabilities.json`. CE v1.3 exposes 34 Lua
functions: 2 raw-memory (`Mem`, `ObjMem`), 1 call hook
(`RegisterCallEvent`), 1 processor (`RegisterProcessor` — AVOID, §5), 28
high-level mutators (governors, influence, trade posts, parks, espionage,
diplomacy, units), constants only otherwise. **No `GameEffects` table, no
modifier/argument setters, no `ModifierSystem` exposure.** Vanilla Lua has 39
read-only `GameEffects.*` getters (incl. `GetModifierArgumentString`).

## 4. RegisterProcessor hazard

Upstream stores a raw `lua_State*` + registry ref per name and `pcall`s it
from native hooks (`EventSystems.cpp:6-17,26-71`), plus a missing-return UB.
Dev CE replaces this with the engine's own `Lua::Utility::CallProcessor`
dispatcher + `GameEvents[name].Add(fn)` (tested 2026-10-04/05: PASS on
late-game save, save/load round-trip clean). **X10 impact: none for
init-time-only use** — different subsystem, no per-frame processors, no
stored states. Rule: never `pcall` a stored Lua state from native code; if a
processor is ever needed, copy the `GameProcessor::Call` pattern. X10 must
not depend on `RegisterProcessor` as shipped.

## 5. Modifier lifecycle (reference-confirmed)

DB (`Modifiers`/`ModifierArguments`/`DynamicModifiers`) → `PopulateModifierDefinitions`
(0x96f6c0) → `SimpleModifierDefinition` (args moved in; only a const
`GetArguments` accessor identified — no named/supported modifier-argument
setter was found in the indexed GameCore symbols or Lua APIs) →
`AddModifierDefinition`
(0x943110) → `AttachModifier[WithState]` → `DynamicModifier` ctor (holds
definition/collection/effect **references**, not copies) →
`Activate` → per-subject `Apply`. Paired `Apply/Remove` per effect,
`ApplyEffect/RemoveEffect/Activate/Deactivate`, `Clear*/Disable*`, and two
`…_ReapplyGameEffects` handlers all exist natively but **none is exposed to
Lua** (vanilla or Dev CE). Relevant primitives for this pass:
`PopulateModifierDefinitions`, `SimpleModifierDefinition::SimpleModifierDefinition`,
`SimpleModifierDefinition::GetArguments`, `ModifierSystem::AddModifierDefinition`,
`ModifierSystem::GetModifierDefinition`, `ModifierSystem::AttachModifier`,
`ModifierSystem::AttachModifierWithState`.

## 6. Verdict: YES_WITH_SMALL_CE_EXTENSION

- Definitions are structurally mutable (reference-held args), but no
  supported setter exists: not clean in current CE without raw-memory pokes.
- A small generic bridge (init-phase only) is feasible: `AddModifierDefinition`
  replacement or argument-list edit before attach; effects `Initialize` from
  the definition at attach time (per-effect arg caching unverified for a few
  classes — validate per family during review).
- Proposed generic API (`ModifierDefinitions.Get/SetArgument`, `Refresh`,
  init-phase restriction, no `RegisterProcessor`): see
  `docs/DYNAMIC_MULTIPLIER_SPIKE.md` §14.

## 7. Difficult classes

DB_ONLY_BEST: policy slots (no UI evidence), boolean unlocks, structural slots,
charges/counts (integer floors stay in SQL). CE_HIGH_LEVEL_API: governor
establish delays, influence points/tokens (already exposed).
SMALL_CE_EXTENSION: flat/percent/combat/probability/discount argument
overrides at init. DEV_CE_ONLY: effect-outcome replay workarounds (desync
risk on re-evaluation — not recommended for X10). RAW_MEMORY_ONLY: nothing in
production. UNRESOLVED: runtime-created modifiers, one-time rewards (needs
live testing).

## 8. Recommendation

**HYBRID, CE hard dependency acceptable.** Normal numeric DB modifiers stay
generated-SQL (deterministic, audited); CE dynamic path reserved for
arbitrary multipliers + special mechanics once the small generic extension
lands and is validated. Presets remain the shippable fallback. Full
comparison in `docs/DYNAMIC_MULTIPLIER_SPIKE.md` §16.
