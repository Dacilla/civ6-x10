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
