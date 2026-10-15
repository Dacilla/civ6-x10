# Phase 8B — Playtest-1 closure + core coverage expansion

Registry: 1010 → **2481 entries** (2475 unique definitions, 26 shared;
1333 unconditional + 1148 count-like). Native: CE `29e8b7f`, DLL
`e0486aee...0ea06c` (new kinds VECTOR/DELTA/REPEAT, 13-module mask).
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
6. Monopolies/Heroes/Dramatic standard-game leakage re-proof (MD1).
7. Great-Person burst stacking edge cases (G1).

## 6. Phase 8B.1 pre-Playtest-2 corrections (supersedes marked 8B claims)

Re-inspected from source at controller `11f389d` / CE `29e8b7f`.
No new gameplay families. Registry totals unchanged
(2481 / 2475 / 26 / 1333 / 1148; kinds hold).

### C1. F1 retracted: BRS/EPC previews do NOT see scaled values

The §1-F1 "shared scaled store" claim was wrong, and so is §3(B).
Exact barrier, verified in the installed mods (BRS 7.0,
`6f2888d4-79dc-415f-a8ff-f9d81d7afb53`; EPC `382a187f-…`):

- `RealModifierAnalysis.lua:1476` reads `GameInfo.Modifiers[id]`
  (gameplay SQLite) and `:1513` reads ModifierArguments through
  `DB.Query` (gameplay SQLite), memoized in `tModifiers`. CE
  transforms native GameCore definitions during population and never
  rewrites gameplay SQLite — so RMA computes from VANILLA values.
  This matches Playtest-1 evidence (God King ×10 live, EPC +1/+1).
- No post-population channel exists from GameCore memory back to UI
  Lua or SQLite. SQL-side scaling is impossible: UpdateDatabase runs
  unconditionally (k/modules unknown there) and scaled SQLite would
  double-scale through native population.
- Interception is sound but correction is not clean: every preview
  caller indexes the shared table at call time
  (`BRSPage_Policy.lua:82,102`, EPC `GovernmentScreen.lua:1028`;
  published by RMA `Initialize()`, `:2868-2875`), so wrapping
  `ExposedMembers.RMA.CalculateModifierEffect` would catch all
  policy/belief paths — but the wrapper would have to re-implement
  k + module mask + per-entry kind/count-like semantics in Lua
  (a second native implementation, unverifiable without a game
  runtime), coupled to cross-mod load order (BRS ImportFiles 1000,
  EPC 12000, RMA via AddUserInterfaces InGame). EPC without BRS
  shows static text and is unfixable additively anyway.
- Decision: NO shim shipped. P1 is an explicit KNOWN
  INCOMPATIBILITY (preview-only): BRS/EPC previews show vanilla
  values while gameplay is scaled (proven separately by native
  lifecycle logs + actual in-game yields). The old automated gate
  proved only non-dependency + God King registry presence, never
  preview compatibility; `test_brs_preview_divergence_is_documented`
  now pins the retraction. Static Firaxis text stays vanilla by
  design (unchanged).

### C2. F6 corrected: typed fillers (wildcard design was invalid)

- `GovernmentSlots` (official DB): only `SLOT_WILDCARD` has
  `AllowsAnyPolicy=1`; MILITARY/DIPLOMATIC/ECONOMIC/GREAT_PERSON are
  0. AllowsAnyPolicy is SLOT-side, so the 8B comment was backwards:
  99 `SLOT_WILDCARD` fillers could never fill Potala/Diplomatic,
  Alhambra/Military, or Big Ben/Economic bonus slots.
- Original Wonder-x10 (workshop `1662972647`, 2017) avoided the
  softlock with 30 TYPED manual blanks (10 MILITARY + 10 DIPLOMATIC
  + 10 ECONOMIC, `CIVIC_CODE_OF_LAWS`, `empty_policy_cards.sql`),
  zero Lua auto-slotting (`wonder_x_10.lua` has only
  Stonehenge/GreatLibrary/Terracotta handlers), +9 real slots per
  wonder. Author's admitted flaw, `wonder_modifer_x_10.sql:2-3`:
  "the additional policy slot may cause you not able to adapt any
  policies until you have enough policy cards".
- Blocker mechanics (base `GovernmentScreen.lua`): `:1397` disables
  Confirm while any slot is free (`bAnySlotsFree`); `:848`
  (`GetNumPolicySlotsOpen() > 0`) keeps the free-change prompt. Empty
  slots never crash end-turn — the softlock is an unconfirmable
  policy screen until every bonus slot holds a card.
- Investigation order result: (A) safe empty slots = vanilla
  behavior, insufficient alone (screen unconfirmable with free
  slots); (B) automatic fillers need game-runtime proof (no
  auto-slot code ships — same as the proven original); (C) manual
  typed fillers, the shipped fallback.
- Shipped: `FILLER_COUNTS` MILITARY 200 / DIPLOMATIC 100 / ECONOMIC
  200 / WILDCARD 200 (`civ6x10/eight_b.py`) — each type covers its
  maximum simultaneous bonus slots at ×100 with zero real cards
  assumed (MIL 2 sources, DIP 1, ECO 2, WILD 2; official per-type
  pools are MIL 39 / DIP 17 / ECO 39 / WILD 33+12). `Code of Laws`
  prereq (as the original). 700 identically-named Reserve cards in
  the picker is NOT an accepted cost until Playtest-2 step P0B passes
  (see §7): if the 700-card picker is materially unusable, the policy-slot
  architecture reopens. LOC fixed: SQL used
  `LOC_POLICY_X10_FILLER_DESCRIPTION`, text defines
  `LOC_POLICY_X10_FILLER_DESC` — SQL now uses DESC.
- `SLOT_NONE` kept as the inert ModifierArguments value (rewritten
  natively before engine use when armed). Tolerance is NOT
  statically provable (no official `GovernmentSlots` row) → gated by
  Playtest-2 step P0 boot smoke, then P2.

### C3. Checklist counts corrected (mechanically derived)

- Registry: 2481 total = 1788 non-REPEAT + 693 REPEAT
  (7 bases × aux 2..100). Native leaves `e.aux > copies + 1` idle
  (`X10Write.cpp:637-640`) without touching writes/post_add_match.
- ×10: active 7×9=63, idle 630, writes 1851, transform_refused 0,
  post_add_match 1851 (verified: every count-like official is
  integral at integral k; max 2 args per definition so the
  per-definition `touched[8]` witness never truncates).
- Full preset matrix (writes/idle): ×2 1795/686, ×3 1802/679,
  ×5 1816/665, ×10 1851/630, ×20 1921/560, ×50 2131/350,
  ×100 2481/0. ×100 is the only preset where all rows write.
- Custom 7.3, one EXIT value: writes 1353 (1333 unconditional +
  20 exact: 19 ADDITIVE + Panama DELTA 63), refused 1128
  (435 count-like fractions + all 693 REPEAT, non-integral k).
- R2 Petra witness corrected: `2,2,1 × 7.3 = 14.6,14.6,7.3`
  (vectors are not count-like), not `20,20,10`.
- `tests/test_phase8b1_counts.py` derives all of the above from the
  registry; stale decomposition comments in `test_production.py` /
  `test_building_yield_integral.py` corrected to match.

### C4. Secret Society ownership resolved: Game Modes owns all of it

- 22 governors-manifest rows (Owls 7, Voidsingers 3, Hermetic 10,
  Vampire builds 2) moved to modes ownership (bit 32 → 512).
  Governors checkbox is now simply "Affects: Governors"; modes
  description notes "Includes Secret Society bonuses."
- Mechanism: `is_secret_society_manifest_row`
  (`civ6x10/governors.py`, root_governor/object_id in the four
  society governor types) partitions at build time; the checked-in
  audits are untouched. `build_secret_society_mode_rows` feeds
  `eight_b.build_all`, which drops the 21 colliding heuristic
  overlay rows (governor-audit rows are the reviewed authority) —
  `modes_overlay_superseded_by_society=21`. No key collides with any
  other base manifest (verified). Registry totals unchanged; all 22
  solely modes-owned (pinned by test with exact IDs).

### C5. Colosseum DELTA kept provisional (scope evidence corrected)

- Culture +2 is host-city direct (`Building_YieldChanges`;
  per-city building yield, no regional scope in vanilla). Helper
  `X10_COLOSSEUM_YIELD_CULTURE` (`MODIFIER_BUILDING_YIELD_CHANGE`,
  `COLLECTION_OWNER`, own-building attach) is the exact official
  Electronics Factory shape — scope-faithful, no redesign.
- Loyalty +2 (`COLOSSEUM_IDENTITY`, `COLLECTION_PLAYER_CITIES` +
  `COLOSSEUM_REQUIREMENTS` plot-within-6) is regional in vanilla
  and stays regional: native rewrites only the Amount, never
  collection/requirements. Base-manifest ADDITIVE row, unchanged.
- Entertainment 2 / RegionalRange 6 aura was never bridged
  (documented exclusion) and stays vanilla — NOT scaled.
- C1 live proof required: build UI +2 (not +0); host culture ×10;
  in-range loyalty ×10; out-of-range vanilla; entertainment aura
  vanilla. There is no vanilla regional culture to scale; a live
  result showing regional culture would refute this analysis.

### C6. Release/documentation repair (§6 of the 8B.1 brief)

- `release-manifest.yml` header `(Phase 7C.3)` → 8B pre-publication;
  `source_release.build_assets` registry `entries: 1010` → 2481.
- `PUBLISH_CHECKLIST.md`: pre-upload smoke expectation corrected to
  the 8B EXIT values (1851/0/630/1851 at ×10); 1010/0 retained as
  the RC2 (DLL `3b6dc3…`) historical record only.
- `VALIDATION.md`: RC2/7C.2/1010 sections pinned to the staged RC2
  DLL `3b6dc3d26c3eab51fa5be4272252b926deaf10b6d4e7bedb094c2c6c8272ab14`;
  `e0486aee…` is the Phase-8B tree build only (pre-publication,
  gameplay validation pending). No historical evidence rewritten.

## 7. Phase 8B.2 final pre-Playtest-2 correction

### D1. Colosseum regional culture BLOCKER (8B.1-C5 was wrong)

The 8B.1 claim -- direct Building_YieldChanges are host-only -- is refuted
by official data: Factory-line +3 production is regional in every game yet
implemented ONLY by direct yields + RegionalRange=6, with no modifier at
all. Direct yields on ranged buildings propagate; Maracana (+6 culture,
range 100000) and Jebel Barkal (+4 faith, range 6) confirm the pattern.
The 8B.1 host-only helper therefore scaled only the host (host +20,
neighbors +2).

Fix (no destructive zeroing, registry untouched): the helper
X10_COLOSSEUM_YIELD_CULTURE rides the official regional graph --
MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE (official all-cities
shape: URBAN_PLANNING_ALLCITYPRODUCTION, Amount + YieldType, no
BuildingType arg) + SubjectRequirementSetId COLOSSEUM_REQUIREMENTS
(plot within 0-6 of a Colosseum; the set already gating regional
COLOSSEUM_IDENTITY loyalty). The direct +2 still propagates as vanilla
(UI still shows +2); the helper (stored 0) contributes +18 per eligible
city at x10. Out-of-range cities match neither path. Module-off /
invalid-k sessions see direct + inert 0.

Same-class limitation (deliberate, not overlooked): Maracana and Jebel
helpers stay host-only -- no official requirement set exists to gate on,
and inventing one needs runtime proof. Neighbors keep exact vanilla
values (never corrupted, incompletely scaled). Pinned by test so any
change is deliberate. Thermal Bath production was never bridged
(not IsWonder).

Static evidence: 8B.2 bridge validation on a scratch DB (57 helpers,
Colosseum args exactly Amount=0 + YieldType, requirement set intact,
direct +2 preserved). Live C1 proof still mandatory: a nearby city at
+2 is FAILURE.

### D2. Reserve picker UX (P0B gate, not an accepted cost)

The 6-C2 accepted-cost wording is retracted: 700 Code-of-Laws Reserve
cards stay implemented, but Playtest-2 step P0B (EPC stack, legality of
all four families, responsiveness, screenshot + Lua log on error) must
pass before the campaign. Material unusability reopens the policy-slot
architecture.

### D3. Installer defaults repaired

release/install-release-candidate.ps1 defaulted to a 1.0.0-rc2 dir with
the e048 hash, while RC2 actually contains 3b6dc3 -- failing its own
check. Defaults now track the current playtest build (1.0.0-8b staging +
ced8 DLL); explicit args install anything else.

### D4. Checklist IDs and R3

Modes check M1 collided with Monument M1, now MD1. R3 now covers Great
People and City Projects OFF isolation too, keeping the society-ownership
checks (Modes OFF skips 22 society rows; Governors OFF only the 48 base).

## 8. Phase 8B.3 regional wonder semantics closure

### E1. Host-only assertion removed (Jebel + Maracana fixed)

The 8B.2 test pinning Maracana/Jebel host-only helpers is rewritten:
both are regional vanilla effects (Jebel +4 Faith range 6 to owned
cities in range; Maracana +6 Culture range 100000 civilization-wide),
and host-only helpers under-scaled every non-host recipient.

- Jebel helper: MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE,
  Amount=0, YieldType=YIELD_FAITH, SubjectRequirementSetId =
  X10_JEBEL_BARKAL_REQUIREMENTS -- a generated set mirroring
  COLOSSEUM_REQUIREMENTS exactly (REQUIREMENT_PLOT_ADJACENT_
  BUILDING_TYPE_MATCHES + MinRange 0 + MaxRange 6 on
  BUILDING_JEBEL_BARKAL, wrapped in REQUIREMENTSET_TEST_ANY).
  Requirement DDL is baseline-guarded and idempotent on both the
  immediate and trigger paths. At x10: regional +4 + helper +36 = +40.
- Maracana helper: same carrier, Amount=0, YieldType=YIELD_CULTURE,
  no requirement (COLLECTION_PLAYER_CITIES already targets every
  owner city). At x10: +6 + +54 = +60 everywhere.
- Direct rows preserved (UI truthful); module OFF / invalid k sees
  direct + 0. Registry identities unchanged (same modifier IDs,
  Amount, officials, DELTA kind) -- the production .inc is
  byte-identical, so no CE rebuild.

### E2. Closed-world regional-yield guard

Mechanically derived universe (official DB): IsWonder=1 AND
RegionalRange>0 JOIN Building_YieldChanges = exactly three rows
(Colosseum culture, Jebel faith, Maracana culture), all bridged, all
now regionally carried. Thermal Bath is not IsWonder (out of bridge
scope, correctly untouched); Factory-line buildings are not wonders.
The guard test fails if any future regional direct Wonder yield lacks
a REGIONAL_YIELD_OVERRIDES carrier without a documented,
technically-justified exception (currently none), and fails on stale
override keys. No future MODIFIER_BUILDING_YIELD_CHANGE helper for a
regional direct Wonder yield is permitted by default.

### E3. Regional Entertainment feasibility: DEFERRED with blocker

Investigated, NOT shipped. Proven statically: official DLC mode files
add new DynamicModifiers rows (Ethiopia Secret Societies adds a new
ModifierType onto a known collection/effect pair), so row-addition is
an accepted pattern; EFFECT_ADJUST_CITY_ENTERTAINMENT exists with two
official single-city carriers (OWNER, PLAYER_CAPITAL_CITY);
subject-requirement gating on COLLECTION_PLAYER_CITIES is proven
(COLOSSEUM_IDENTITY). Exact blocker: NO official
(COLLECTION_PLAYER_CITIES x EFFECT_ADJUST_CITY_ENTERTAINMENT)
combination exists, so multi-city iteration of the entertainment
effect, stacking/bucket equivalence with the engine Entertainment/
RegionalRange aura path (additive vs double-count vs unread), and
load-time validation silence are all unprovable without booting the
game. Candidate design (not shipped): new DynamicModifier
MODIFIER_X10_PLAYER_CITIES_ADJUST_CITY_ENTERTAINMENT on
(COLLECTION_PLAYER_CITIES, EFFECT_ADJUST_CITY_ENTERTAINMENT);
Colosseum helper Amount=0 + COLOSSEUM_REQUIREMENTS (delta +18,
total +20 in range); Maracana helper Amount=0, no requirement
(total +20 everywhere); direct +2 rows preserved; module OFF gives
direct + 0. Future pass must prove: clean boot, no DynamicModifier
errors, amenity totals correct per city, no double application,
OFF-exact vanilla. Until then Colosseum/Maracana entertainment stays
vanilla (no regression, unchanged since 8B).

### E4. Checklist deltas (8B.3)

New J2 (Jebel +40 host/in-range, none outside; J1 iron unchanged),
new MC1 (Maracana +60 every city), C1 retained (+20 host and
in-range, none outside; nearby-at-+2 is FAILURE). R3 and MD1
unchanged from 8B.2.

## 9. Phase 8B.4 policy UX + display compatibility (campaign STOPPED)

Playtest-2 is stopped after real runtime evidence. No publication,
no new gameplay families, no native-semantics change.

### F1. P0 / P0B live results

- P0 PROVISIONALLY PASS (x10 Classic, 13 modules, Secret Societies):
  game boots, Government screen opens, SLOT_NONE/REPEAT activation
  does not crash. Native EXIT exactly:
  writes=1682 transform_refused=0 official_mismatch=0
  post_add_match=1682 (mismatch/unreadable/skipped 0) repeat_idle=630.
- P0B HARD FAIL: 700 Code-of-Laws Reserve cards flood the picker
  (borderline unusable, real cards buried) and filler LOC keys render
  literally. The mass-unlock architecture is rejected; localization
  alone cannot save it.

### F2. Mode-aware runtime expectations (R1 was wrong)

1851 assumes every definition present. In Secret-Societies-only games
169 mode definitions never load (Dramatic 58, Heroes 52, Monopolies 51,
Apocalypse 8; Zombie/Barbarians/Shuffle contribute zero entries):
1851 - 169 = 1682, exactly the observed EXIT. Absent definitions are
not skips/refusals/errors -- they never iterate (native counters
confirm: skipped_other=0). Standard R1/R2 pin 1682/1204; R1-ALL/R2-ALL
pin 1851/1353 for the all-relevant-modes configuration.
tests/test_mode_aware_runtime.py derives all of it from the registry +
manifest bundle attribution. PUBLISH_CHECKLIST smoke follows the
standard config (1682).

### F3/F4. Dormant fillers + on-demand manager (replaces mass unlock)

- Filler SQL now emits ExplicitUnlock=1, PrereqCivic NULL (22 official
  NULL-prereq precedents: government/special policies; ExplicitUnlock
  itself is officially unused -- the P0C experiment gates it).
  Scratch-DB validated: 700 dormant rows, unlock flag 1, no civic.
- X10SlotManager.lua (AddGameplayScripts, sim context -- the Wonder-x10
  precedent): reconciles human majors on WonderCompleted /
  GovernmentPolicyChanged / GovernmentChanged / CivicCompleted /
  TurnBegin / LoadScreenClose + PlayerTurnStarted/PlayerDoTurn (all
  hook attempts guarded). Deficit math is satisfiability-exact (typed
  slots same-type only, wildcards absorb surplus, great-person cards
  conservatively ignored); probe-gated (missing enumeration/unlock
  APIs abort loudly, unlocking nothing); idempotent via
  IsPolicyUnlocked; disarmed sessions no-op (manages + loud log only
  when config is unreadable). Ordinary Code of Laws: ZERO visible.
- No auto-slotting ships: slotting stays manual until a runtime pass
  proves RequestEnactPolicy/RequestPolicyChanges across wonder
  completion, government change, policy change, and save/reload.

### F5. Filler localization context

X10.modinfo loaded X10Text.sql FrontEnd-only, so gameplay screens
showed literal LOC keys. X10Text.sql now also loads via an InGame
UpdateText action (setup keys are harmless in-game). Test pins: every
LOC_ tag in the slot SQL exists in X10Text.sql, and X10Text.sql is
wired in both contexts.

### F6/F7. BRS/EPC is a blocker; cache-mutation prototype

Human screenshot: Discipline +5, God King +1/+1, Urban Planning +1
previews vs correctly scaled gameplay (native log proves
GOD_KING_GOLD 1 -> 10 MATCH). Known-limitation status revoked.
Constraints honored: no static-text rewrite, no blind aggregate
scaling -- BRS/EPC must compute from the same effective arguments.

Prototype design (built, runtime-gated in P1): FetchAndCacheData
returns the memoized table BY REFERENCE
(RealModifierAnalysis.lua:1471/1531; tModifiers never cleared by
RefreshBaseData), and every preview caller (BRSPage_Policy:82,102;
EPC GovernmentScreen:1028) indexes ExposedMembers.RMA at call time.
The compat layer therefore PATCHES THE CACHE instead of wrapping
math: per Calculate call (Policy/Belief only), for each registered
modifier of the object, recompute the argument from generated
registry data (same officials/kinds/count-like gates/owner bits/k as
native; values derived from OUR officials so re-patching is
idempotent and can never double-scale) and overwrite
Arguments[arg] in place, then delegate to the ORIGINAL function.
Thin wrapper, pcall-isolated, re-wrap-safe, silent no-op when BRS is
absent or X10 disarmed; count-like inexact stays vanilla (native
refuses too); REPEAT excluded (not numerical). Lua mirrors native
formatting (%.6g, %.2f combat) and float32-aware exactness
(frexp half-ULP; power-of-two kErr may differ 2x from nextafterf --
harmless: exact results match, near-misses don't occur in practice).

### F8. Static text separation

Firaxis prose keeps vanilla numbers by design (no mass regex). After
P1 proves calculated displays truthful, assess whether vanilla prose
+ correct EPC result reads clearly.

### Validation deltas (8B.4)

- New UI files (controller/X10/UI/): X10BRSData.lua (generated, 1788
  entries, committed, regen-checked by test), X10BRSCompat.lua,
  X10SlotManager.lua -- all staged via manifest pins; X10.modinfo
  hash re-pinned.
- No CE rebuild (registry byte-identical; compat is Lua-side).
- Human gates before any campaign resume: P0, P0B-replacement,
  P0C (incl. the ONE-filler ExplicitUnlock experiment), P1
  (God King +10/+10, Discipline ~+29, Urban Planning +10, 7.3
  agreement), R1/R1-ALL, R2/R2-ALL.

## 10. Phase 8B.4.1 runtime-wiring + slot-safety correction

No new gameplay families. No CE/native changes (registry byte-identical).

### G1. Compat script actually executes (ImportFiles did not run it)

ImportFiles only exposes files to the VFS; nothing executed the
compat layer, so P1 was testing an uninstalled wrapper. Fixed with
the BRS RealModifierAnalysis pattern: AddUserInterfaces creates a
minimal hidden X10BRSCompat UI context (X10BRSCompat.xml, same empty
shape as RealModifierAnalysis.xml), whose same-basename
X10BRSCompat.lua auto-executes and explicitly includes X10BRSData.lua
(bare-name include, the BRSPage_Policy-proven form -- which is why the
compat trio moved from UI/ to the mod root). P1 is invalid without
the Lua.log lines the file now emits first: context loaded /
generated data loaded: N entries / RMA found|deferred / installed.
(DevCE Playground was not found locally; BRS + CheatMenuPanel
modinfo patterns were used instead.)

### G2. Custom-0 disarms (native k==0 parity)

Both Lua gates accepted Custom 0 as armed. Fixed in ResolveArmed and
ShouldManage (custom <= 0 disarms, like preset Off; blank-as-0
covered); twin-tested.

### G3. Legality-matched deficit (type counting was insufficient)

Unlocked-but-obsolete/illegal cards could fake coverage. The manager
now filters IsPolicyObsolete and builds policy->slot eligibility with
CanSlotPolicy(index, slotIndex), maximum bipartite match (Kuhn
augmenting path), one Reserve filler per unmatched slot by slot type.
ProbePolicyAccess now checks all three methods with correct
(ok, value) handling and aborts loudly without them; unknown future
slot types report loudly instead of unlocking blindly.

### G4. Player enumeration (no #Players)

HumanMajors prefers PlayerManager.GetAliveMajors with a bounded
0..63 index-scan fallback; SP-only behavior preserved.

### G5. Trait coverage (audited call sites only)

LINK is exactly Policy/Belief/Trait: BRSPage_Policy:82/:102,
BRSPage_Minor:106/:166, EPC GovernmentScreen:1028 -- the complete
audited set. Generated data still covers the full non-REPEAT
registry, but only these three families have a consuming wrapper
path (stated in-code, not pretended otherwise).

## 11. Phase 8B.4.2 player enumeration + UI context fix

No gameplay-family expansion. No CE/native changes (registry
byte-identical).

### H1. HumanMajors consumed Player objects as IDs (manager did nothing)

GetAliveMajors() returns Player[], but the loop fed elements to an
ID-only consider() that rejects non-numbers -- while ipairs itself
succeeded, so the fallback never fired and zero players reconciled.
Fixed with three ordered stages, each running only if the previous
yielded zero usable candidates: GetAliveMajorIDs() numbers, then
GetAliveMajors() objects via GetID, then a bounded 0..63 index scan
(never #Players). A twin models the object shape so this exact bug
cannot recur. Kept: dormant fillers, Kuhn/CanSlotPolicy matching,
obsolete filtering, Custom-0 parity, no auto-slotting.

### H2. Compat context is the shared InGame host (not a custom name)

The custom Context=X10BRSCompat confused the host Context property
with the Lua-basename unit. BRS itself registers RealModifierAnalysis
under Context=InGame (as does the DevCE_Playground example), with
execution coming from same-basename XML/Lua pairing. Changed to
Context=InGame, keeping File X10BRSCompat.xml + X10BRSCompat.lua +
explicit bare-name data include. (DevCE Playground was not found
locally; BRS + CheatMenuPanel patterns used instead.)

## 12. Phase 8B.4.3 filler idempotence + trustworthy BRS logging

No new features. No CE/native changes (registry byte-identical).

### I1. Repeated Reserve unlock fixed (P0C blocker)

EligibleRealPolicies excluded every X10 filler, so each reconcile
matched only real cards, recomputed the full deficit, skipped the
already-unlocked fillers in UnlockDeficit, and unlocked the NEXT 8 --
flooding the picker 8/16/24 across TurnBegin/PolicyChanged runs.
Fixed as EligibleUnlockedPolicies: the matching universe is every
currently unlocked, non-obsolete policy (real AND unlocked X10
fillers); only LOCKED fillers are absent from it. Maximum matching
over that complete set makes satisfied slots stay matched (deficit 0
on re-run); only genuinely unmatched slots expose new locked
fillers. Twin cases pinned: A (10/2/0 -> 8), B (+8 unlocked -> 0),
C (20 slots -> 10), D (three rounds total 8, never 24). Type
legality stays engine-authoritative (CanSlotPolicy edges), never a
subtraction by type.

### I2. RMA Retry no longer logs false success

`if pcall(Install) then log` reported wrapper-active when Install
safely returned false (pcall yields execution_ok, not the return
value). Now `local ok, installed = pcall(Install)` with logging only
on (true, true); absent-RMA stays silent. P1's log gate is
trustworthy again. Twin + pattern regression pinned.

## 13. Phase 8B.4.4 source-driven Reserve policies

No new gameplay families. No CE/native changes (registry byte-identical).
No REPEAT-semantics change.

### J1. Confirmed failure: gameplay-side legality matching cannot work

Human Lua.log proved the 8B.4-8B.4.3 manager architecture dead:

  [X10SlotManager] policy-access probe failed
  (CanSlotPolicy unavailable); unlocking nothing [init]

  [X10SlotManager] policy-access probe failed
  (CanSlotPolicy unavailable); unlocking nothing [WonderCompleted]

immediately followed by `WonderBuiltPopup: _POTALA_PALACE`, while the
Government screen showed 10 Diplomatic slots. Therefore native REPEAT
multiplication WORKS, SLOT_NONE activation WORKS, and the filler
manager failed only because CanSlotPolicy is unavailable in the
gameplay-script execution context: zero fillers unlocked, Potala x10
softlocked. The matcher is removed, not repaired.

### J2. BRS/EPC calculated-preview PASS (witnesses, no regress)

Lua.log proved the compat layer executes and wraps:

  [X10BRSCompat] context loaded
  [X10BRSCompat] generated data loaded: 1788 entries
  [X10BRSCompat] installed ...
  [X10BRSCompat] RMA found; wrapper active

Human screenshots showed God King calculated footer +10 Faith/+10 Gold
and Urban Planning calculated footer +10 Production. Recorded as PASS
for those witnesses. Static Firaxis prose staying vanilla is separate
(by design). Compat code untouched by this pass.

### J3. Source-driven targets replace exact matching

For each active audited +1 slot source, extra X10 slots = k-1 at
integral armed k (x2->1, x3->2, x5->4, x10->9, x20->19, x50->49,
x100->99; integer Custom 7->6; fractional Custom 7.3->0 because native
REPEAT refuses; Off / Custom 0 / invalid -> disarmed, 0). The Lua
SOURCES table mirrors civ6x10.eight_b.SLOT_BASES exactly (seven
entries; parity test pins it -- never a second guessed list).

Per human player: targetReserveCount[slotType] = SUM(k-1 over every
active source of that slot type); toUnlock = target - alreadyUnlocked;
unlock only if positive. Real policies are NOT subtracted (bounded
over-supply intentional: 4 real Diplomatics + 9 Reserves visible is
acceptable). Second same-type sources accumulate (9 + 9 = 18).
Deterministic and trivially idempotent (9, then 0, 0).

### J4. Active-source detection + permanence

Wonders: actual owned completed building via player GetCities /
Members / GetBuildings HasBuilding (pcall-guarded; unknown fails
closed + loud). WonderCompleted triggers immediate reconcile; init /
LoadScreenClose reconcile covers saves. Civ/leader/trait sources:
PlayerConfigurations leader/civ names resolved against
GameInfo.LeaderTraits / CivilizationTraits (authoritative; unknown
fails closed). All sources permanent once active (wonder built,
leader/civ fixed at setup), which is the only reason one-way
UnlockPolicy is acceptable. Exception documented in-code: a lost wonder
city leaves its fillers unlocked (bounded over-supply, still slottable
nowhere harmful).

### J5. Deleted matcher + pruned events

Removed all gameplay-context legality machinery: CanSlotPolicy,
GetSlotType, IsPolicyObsolete matching, CurrentSlots, Kuhn maximum
matching, unmatched-slot deficit logic. Kept only human-player
discovery, active-source detection, IsPolicyUnlocked, UnlockPolicy,
configuration/module resolution. No remaining CanSlotPolicy call.
Event set is init + LoadScreenClose + WonderCompleted + TurnBegin;
PlayerTurnStarted / PlayerDoTurn (the >1000-line spam source) removed,
as are GovernmentPolicyChanged / GovernmentChanged / CivicCompleted.
Logging reports source activation (once), per-player targets, actual
unlocks, warnings/errors only -- silent when targets satisfied.

## 14. Phase 8B.5 Playtest-2 x10 closure (documentation only)

No production-code changes. No registry changes. No CE rebuild. No
gameplay-family expansion. No publication. Controller 67d8bde, CE
1e89e1b, DLL ced8f01750d22f44725ed61de7c0926c58e423388b3ee7fce0fd18522081b744
(verified unchanged).

### K1. Full x10 campaign result: PASS (provisional release-quality)

Human Playtest 2 completed a full x10 campaign: all 13 Overpowered
Bonuses categories enabled, Secret Societies enabled, no obvious
critical gameplay errors, no OB-caused crash, no persistent softlock,
no obvious catastrophic double-scaling, no category leakage severe
enough to block play, save/reload successful across multiple
sessions. Recorded as PLAYTEST 2 x10 -- PASS (PROVISIONAL
RELEASE-QUALITY GAMEPLAY PASS): a complete real campaign exercised
the expanded build without an obvious critical failure. NOT
exhaustive proof of every one of the 2481 registry entries.

### K2. Native multi-session evidence: P0 PASS

The archived log (`spike/validation-evidence/
X10Lifecycle.playtest2-x10-campaign.log`, copied from %TEMP%) holds
six recent x10 native sessions, every one the same clean EXIT:
definitions_added=4029, writes=1682, transform_refused=0,
official_mismatch=0, post_add_match=1682, post_add_mismatch=0,
post_add_unreadable=0, skipped_other=0, repeat_idle=630 (the expected
Secret-Societies-only population: 1619 present non-REPEAT + 63 active
REPEAT, 169 disabled-mode definitions absent, 630 idle by design).
The final session's CONFIG confirms all 13 module switches ON
(traits, policies, governments, pantheons, wonders, governors,
suzerain, promotions, dedications, modes, religion, greatpeople,
projects). The obsolete 1851 SS-only expectation is retired: 1851
remains only the theoretical all-relevant-optional-modes-loaded count
(TestAllModesValidation).

### K3. Policy-slot validation: P0B / P0C PASS

Potala Palace x10: Government displayed 10 Diplomatic slots, the
source-driven manager unlocked 9 Diplomatic Reserves (sufficient to
fill the multiplied slots), the menu stayed usable, policies were
confirmed, the turn continued/ended, next-turn reconciliation added
nothing, save/reload added nothing. Campaign save state:
BUILDING_POTALA_PALACE target Diplomatic = 9, have Diplomatic = 9.
A second simultaneous source survived save/reload without flooding:
BUILDING_FORBIDDEN_CITY target Wildcard = 9, have Wildcard = 9.
Picker usability (P0B) and the 8B.4.4 source-driven architecture
(P0C) are PASS; Potala and Forbidden City multi-source/save-load
witnesses are PASS.

### K4. BRS/EPC: P1 PASS for tested witnesses (limitation kept)

Compat context loads, loads the generated 1788-entry data, wraps
RMA.CalculateModifierEffect, and reports wrapper active. Calculated
witnesses: God King +10 Faith / +10 Gold, Urban Planning +10
Production. Static Firaxis prose may still state vanilla values
(e.g. God King body +1/+1 beside a +10/+10 calculated footer) --
documented as a known display limitation, NOT a gameplay/native
failure and NOT a compat-layer failure. No localization-number
rewriting in this pass.

### K5. Known intentional / unresolved items (status preserved)

A. Regional Wonder Entertainment/Amenities: Colosseum/Maracana
regional Entertainment remains vanilla; no safe proven
player-cities entertainment carrier shipped; NOT marked fixed.
B. Static descriptions: vanilla numbers may remain; calculated
BRS/EPC results are the compatibility target.
C. Optional modes: this campaign is not exhaustive runtime coverage
of Heroes, Monopolies, Dramatic Ages, Apocalypse when disabled;
their definitions' absence from SS-only sessions is expected, not
skip/error behavior.
D. Individual entries: campaign PASS does not human-validate each
of the 2481 entries.

### K6. Next test: Custom 7.3 (gate open, not run)

Expected SS-only native accounting, mechanically derived
(test_mode_aware_runtime.py::test_r2_ss_only_1204): writes=1204
(1187 unconditional + 17 exact count-like), transform_refused=1108,
all 693 REPEAT refuse. Purpose: exact whole/count-like refusal
(Eiffel +2, Jebel +6, Pyramids Builder), REPEAT refusal with zero
Reserve unlocks (slots stay vanilla +1), additive fractional values,
VECTOR element-wise (Petra 14.6/14.6/7.3), COMBAT (Discipline native
7.3 transform), DISCOUNT/DELTA spot checks, owner/module gating,
fractional BRS/EPC compatibility. No x50/x100 stress until 7.3
closes.
