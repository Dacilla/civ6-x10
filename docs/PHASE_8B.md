# Phase 8B — Playtest-1 closure + core coverage expansion

Registry: 1010 → **2481 entries** (2475 unique definitions, 26 shared;
1333 unconditional + 1148 count-like). Native: CE `86be003`, DLL
`85ea8752…8507` (new kinds VECTOR/DELTA/REPEAT, 13-module mask).
Status: static gates green; **under pre-publication gameplay validation**
(Playtest-2 matrix pending — this build is installed, not yet run).

Product bias for this pass: if an effect has a meaningful magnitude and
multiplying it is mechanically supported, it scales. Balance is never a
safety criterion. Engine/UI stability, softlocks, invalid state,
corruption, and ambiguous semantics are.

## 1. Playtest-1 findings → root cause → implementation

### F1. BRS/EPC stale preview (God King +1/+1)
Root cause: two-layer. (a) The EPC card body shows the STATIC Firaxis
description (`LOC_POLICY_GOD_KING_DESCRIPTION`), which no calculation
layer can change — see §12. (b) The RMA-computed `EffectContainer`
reads the SAME scaled definition store our native engine rewrites
(`RealModifierAnalysis.lua: FetchAndCacheData` does live
`GameInfo.Modifiers` + `DB.Query("SELECT * FROM ModifierArguments …")`
on first touch, memoized; EPC calls
`RMA.CalculateModifierEffect("Policy", policyType, 0, nil, nil)`).
God King's `EFFECT_ADJUST_CITY_YIELD_CHANGE` is in RMA's 55-effect
dispatcher with a `COLLECTION_PLAYER_CAPITAL_CITY` branch, so the
computed preview flows automatically once definitions scale.
Implementation: no shim — a Lua wrapper would only duplicate values
already correct in the shared store. Gap analysis (182 registry
effects absent from RMA's dispatcher) proves those surfaces never
displayed them in vanilla either: nothing regressed, nothing is stale
that wasn't already absent. Static text stays vanilla by design (§12).
Test evidence: automated — no BRS/EPC hard references in our tree
(no dependency when absent); live — Playtest-2 checklist item P1
(BRS Policy page God King must read +10/+10).
Remaining: verify live in Playtest 2.

### F2. Colosseum +0 Culture construction UI
Root cause: systemic, not Colosseum-specific. `X10WonderBridge.sql`
zeroed all 57 direct cells and replaced them with helper modifiers;
vanilla construction UI reads the direct table, so it showed +0 while
gameplay was correct.
Implementation: non-destructive delta architecture. Direct tables are
never zeroed (vanilla UI keeps reading truthful values); helpers are
stored inert (`Amount=0`) and the new native DELTA kind contributes
`official*(k-1)` for a total of `official*k`. Module-off/invalid-k
sessions see direct V + 0 = vanilla. All 57 helpers ride DELTA
(count-like: fractional deltas refuse, the direct value stands
alone). `X10BridgeDiag.zeroed` became `preserved` (direct intact AND
helper present).
Test evidence: `test_k0_and_off_leaves_vanilla`,
`test_refusal_leaves_helper_at_official`, delta math tests, 57 DELTA
entries in the registry, bridge/UI coverage per bridged field is the
DELTA certification itself (one row per cell, all count-like).
Remaining: verify live in Playtest 2 (Colosseum shows +2 Culture in
the build queue AND cities in range get +20).

### F3. Jebel Barkal +6 Iron left at +6
Root cause: `EFFECT_GRANT_FREE_RESOURCE_EXTRACTED` sat on the
GRANT_OBJECT floor (coarse `EFFECT_GRANT_*` pattern); the old audit
never distinguished recurring per-turn flows from one-time grants.
Implementation: the DB shows TWO Jebel modifiers — one-time
`JEBELBARKAL_GRANT_TWO_IRON` (+2, `EFFECT_GRANT_FREE_RESOURCE_IN_CITY`)
and recurring `JEBELBARKAL_GRANT_FOUR_IRON_PER_TURN` (+6,
RunOnce=0/Permanent=0). Both certify ADDITIVE count-like via new
strong-family overrides. ×10: 2→20 and 6→60. Custom 7.3: 43.8
refuses (stays 6).
Test evidence: regression test (`6×7.3` refuses), registry entries
present, strong-override ledger.
Remaining: verify live in Playtest 2 (+60/turn at ×10).

### F4. Wonder one-time grants excluded (Pyramids 1→10 Builders, etc.)
Root cause: same GRANT_OBJECT coarseness (plus explicit
`excluded_effects` for envoy/duplicate-token cases, which STAY
excluded).
Implementation: 8 grant-effect strong overrides (all count-like):
unit/civic/tech/GP-class grants, influence tokens (Kilwa one-time
only), cheapest building, both Jebel flows, air slots. Generalised
beyond wonders where the same tuple is one-time countable (Kupe
first-city Builder, Wu/Catherine spy units, non-capital cheapest
building). Repeatable-trigger grants (Apadana child — no floor row),
district-completion envoys, eureka boosts, relics, plot-coupled
resources, and -1 sentinels stay excluded with reasons.
Test evidence: `test_grant_object_cannot_emit_additive` allowlist,
count-like assertions, 22 `GRANT_UNIT_IN_CITY` entries.
Remaining: stress-test ×20/×50/×100 unit-spawn caps live
(placement failures, stacking, hangs — Playtest-2 checklist S1).

### F5. Petra vector missed (+20/+20/+10 expected)
Root cause: scalar-only machinery; `Amount=2,2,1` is non-numeric by
design, so the row died at the float gate.
Implementation: native VECTOR kind (kind=4) scaling each positional
element additively with strict all-numeric parsing, order preserved,
malformed/mixed fail closed; outputs must fit SSO-inline (<16 chars)
or the write refuses. Python mirror + 6-element exclusion gate
(`value:vector-too-long` — their high-k output can never fit, so they
can never apply at any k). Certified: Petra, Halicarnassus,
Cleopatra floodplains, Suleiman golden-age pair.
Test evidence: vector math/malformed tests, Petra regression
(`20,20,10`), 4 VECTOR entries, 6 `vector-too-long` exclusions.
Remaining: verify live in Playtest 2 (desert tiles +20/+20/+10).

### F6. Potala Palace +1 Diplomatic slot (softlock risk)
Root cause: implicit-+1 effects carry no numeric argument; the old
build left them vanilla.
Implementation: 7 base slot grants (4 wonder + Kublai/HRE/Plato
traits) each get 99 inert copies (`*_X10R002..100`,
`GovernmentSlotType=SLOT_NONE` — honors no government screen) via
generated `X10SlotCopies.sql`; the native REPEAT kind (kind=6)
rewrites copies N≤integral-k to the real slot type. Fractional k
activates zero copies (single vanilla slot, never rounded).
Module-off/invalid-k: all inert → vanilla. 99 wildcard filler
policies (`POLICY_X10_FILLER_WILDCARD_*`, shared Reserve Policy
text, Code of Laws) let the end-turn check pass. Old-mod precedent
used 9 static copies with no wildcard fillers (the exact softlock
reproduced here is avoided by construction).
Test evidence: repeat math (9 copies at ×10, refusal at 7.3),
693 REPEAT entries with aux/target metadata, manifest allows only
`SLOT_NONE` officials.
Remaining: live-prove Potala ×10 → 10 slots + end turn with fillers
+ save/reload; empirically probe +20/+50/+100 and set a TESTED cap
if the government screen breaks (checklist P2). `SLOT_NONE`
engine tolerance is the one structural risk: if the engine chokes on
the unknown slot type at load, fall back to a tested static cap with
an honest player-facing limitation note.

### F7. Generic envoy tiers (Trade +2 Gold stayed +2)
Root cause: the suzerain module swept only Suzerain-gated unique
traits; the 1/3/6-envoy generic type traits were never inventoried.
Implementation: token-gated wrappers (SMALL/MEDIUM/LARGE influence,
incl. the Papal Primacy variant) followed one hop to 55 leaf
magnitudes, same bit 64, module label broadened to
`Affects: City-State Bonuses`. Minor-owned always-on rows
(district-production 500, send-trade-route bonus) are the city-state
AI's own bonuses, not player rewards — excluded with reason.
Test evidence: 55 envoy rows, all certify; suzerain ownership 123;
module-off test covers the union bit.
Remaining: verify live (1-envoy +2→+20, 6-envoy tiers, unique
Suzerain still works, Custom 7.3 refusals on building-yield leaves).

## 2. Coverage implemented this phase

- Promotions & Abilities (257-def frontier → 315 entries, bit 128):
  combat→nonlinear COMBAT (72 formula-derived + 9 curated carriers),
  movement/sea/sight/range/attacks/charges count-like (spatial budgets
  reviewed, not refused), XP/heals/plunder/flanking flat, spy
  chance→PROBABILITY + spy times→DISCOUNT, WMD percents flat,
  negative combat debuffs flat (formula is bonus-only), base combat
  stats and capability unlocks excluded with reasons, -1 sentinels
  excluded, spy-level progression excluded (capped progression,
  unproven). Human-reviewable promotion/ability names ride every row.
- Age Dedications (54 commemoration rows → 43 entries, bit 256):
  GA bonuses + era-score quests (whole points), purchase discounts,
  boosts, GPP, trade yields, accumulation, tourism factor (percent,
  reviewed), free GDR grant, charges via ATTACH hop. Thresholds,
  selectors, and era windows untouched.
- Game Modes (bit 512, per-mode manifests from shipped overlays):
  Monopolies (industry/corporation/product yields + discounts),
  Heroes (recall discounts, lifespan durations, discovery gold;
  era-strength progression and hero-creation selectors excluded),
  Dramatic Ages (mode-only policy cards; 8 shared IDs excluded as
  leakage), Secret Societies remainder (vampire heal, loyalty damage,
  lifespans; unlocks/teleport/resurrect/favor-multiplier excluded),
  Apocalypse (emergency faith/unit rewards, soothsayer charges),
  Zombie/Barbarian/Shuffle (no certifiable magnitudes — documented).
- Religion beyond Pantheons (bit 1024, 31 entries): founder/enhancer/
  follower/worship magnitudes via one ATTACH hop (Tithe, Defender,
  Choral, World Church, Zen, Papal pressure burst, Monastic discount);
  adjacency-mirror selectors and spread multipliers excluded.
- Great People (bit 2048, 105 entries): one-shot yield/production/
  adjacency bursts scale flat; eureka boosts, relics, envoy grants,
  -1 sentinels, plot-coupled resources excluded (precedent).
- Projects (bit 4096, 13 entries): Bread & Circuses loyalty, Court
  Festival tourism/culture, project GPP-adjacent completions.
- Tribal Villages: DEFERRED — GoodyHutSubTypes lottery tables are a
  distinct mechanism (flag columns + subtype modifiers, random
  one-shot lottery); inventoried as the Playtest-2 follow-up, not
  silently absorbed.
- Appeal family: Eiffel/Golden Gate/Biosphere/Cleopatra/Amazon/
  Forestry/Great-Person appeal all scale at integer k (whole-level
  count-like); thresholds (`RequiredAppeal`, district rules) untouched.

## 3. Display architecture decision (§12)

- (B) Calculated displays (BRS/EPC): no work needed — they read the
  shared scaled store (§1-F1).
- (C) Direct-table UI (Colosseum +0): fixed by the DELTA bridge (§1-F2).
- (A) Static Firaxis text: RECOMMENDATION — do not rewrite. A
  description mixes multiplied and intentionally-unchanged effects, so
  naive number replacement lies; thousands of brittle LOC rows would
  rot on every game patch. The setup screen (multiplier + per-module
  tooltips) plus accurate calculated displays carry the information.
  Revisit only if Civ VI exposes a robust dynamic-description path.

## 4. Machine-readable outputs

- `manifests/{slots,envoys,promotions,dedications,modes,sweep}.yml`
  (+ vector patches in `wonders.yml`/`traits.yml`).
- `spike/8b/*_disposition.txt`: every skipped wrapper/leaf/flag and why.
- `civ6x10/rules/certified_overrides.yml`: all new entries carry
  rationale + evidence (strong/vector/delta/repeat/effect-arg).
- `civ6x10/rules/support_frontier.yml` v2 (phase 8B production block,
  prior-1010 retained).

## 5. Remaining issues (all live-validation, none static)

1. `SLOT_NONE` engine tolerance (P2).
2. Slot cap above ×10 unverified (P2).
3. ×20–×100 unit-spawn stress (S1).
4. BRS/EPC computed-preview confirmation (P1).
5. Colosseum regional correctness + UI (C1).
6. Monopolies/Heroes/Dramatic standard-game leakage re-proof (M1).
7. Great-Person burst stacking edge cases (G1).
