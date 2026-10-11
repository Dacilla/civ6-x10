# Semantic Certification (Release 1)

## Root cause of the false "reviewed" classifications

`civ6x10/semantics.py::infer_family` returned confidence `"reviewed"` for
every heuristic branch, including the generic numeric residuum
(`Amount`/`Value`/`YieldChange`/… → `FLAT_AMOUNT`, no effect inspection).
`build_manifest` copied that string into `manifests/*.yml`, and
`production.build_production_registry` admitted every `confidence == reviewed`
row. So heuristic guesses — including grants, spatial budgets, discounts with
positive officials, and strength bonuses the regex missed — flowed straight
into the 729-entry native registry labeled as reviewed data.

Fix: the classifier now emits `auto_rule` (explicitly NOT proof).
Production eligibility requires CERTIFIED from `civ6x10/certification.py`:
sem-floor agreement, a curated override with rationale, or an allowlisted
plain-magnitude category under a silent floor row. Heuristic confidence is
never read by the gate. A closed world: unknown families, missing floor rows,
and uncertified discount/combat/probability claims raise `SemanticConflict`
and fail generation.

## Conflicts found and resolved (all against the 729-entry registry)

| # | Contradiction | Resolution |
|---|---|---|
| 12 | `GRANT_OBJECT` floor rows emitted as `ADDITIVE` (free units, spies, envoys, trade-route grants, free buildings) | Excluded: grants are `DECISION_REQUIRED` at fractional k |
| 12 | `SPATIAL_BUDGET` floor rows admitted (movement, range, ranged strike, joint-war range) | Excluded: budgets are not magnitudes |
| 13 rows (11 keys) | `DISCOUNT` floor rows emitted as `ADDITIVE` (positive-official discounts the sign heuristic missed) | 7 keys corrected to `DISCOUNT`/compound; 4 unit-maintenance keys reclassified flat gold (see audit) |
| 3 | `DEFEATED_STRENGTH_SCALING` rows multiplied | Excluded: `DECISION_REQUIRED` preserved |
| 64 | `MIXED_VALUE_DOMAIN` rows (scalar officials, vector siblings) admitted silently | Certified via 2 explicit per-effect overrides with rationale |
| 5 | Curated combat-point effects emitted as `ADDITIVE` (barbarian ×2, diplomatic, corps/army ×2, diplo-visibility) | Corrected to `COMBAT`/combat formula |
| 2 | `AUTO_THEME` slot thresholds (Amount=2/3) scaled | Excluded: eligibility thresholds, not magnitudes |
| 1 | `NATIONALIDENTITY` damage-reduction modifier (50) scaled as strength | Excluded: not strength points |
| 16 | Curated grant/boolean/sentinel effects (extra unit copies, free envoys, token doublers, -1 spy sentinel, eureka grants) | Excluded with per-effect rationale |
| 2 | Toqui governor-loyalty Amounts verified blank post-Add (stored-form proof pending) | Re-admitted in Phase 6B: the 6A.2 probe proved stored MATCH via store-lookup on load AND reload, so the temporary `EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE` exclusion was removed and both rows ship LOYALTY from traits |
| 33+ | Indivisible counts emitted unconditional (`FLAT_AMOUNT`, countLike=false) | Certified as count-like conditional (exact-integer applies, fractional refuses) |

Unresolved conflicts after the gate: **0** (`unresolved_conflicts: []`;
`SemanticConflict` would fail generation).

## New certified registry (Phase 6B current state)

- **1010 entries / 1006 unique definitions / 25 shared** (360 traits-only
  incl. Suleiman titles + 2 re-admitted Toqui loyalty rows, 284
  policies-only, 18 governments-only, 31 pantheons-only, 154 wonders-only =
  97 modifier-backed + 57 generated bridge helpers, 70 governors-only, 68
  suzerain-only, 25 shared policies+governments; 788 unconditional + 222
  count-like; kinds 973 ADDITIVE / 14 COMBAT / 23 DISCOUNT).
  Governors source: 54 `phase4a.1-governor-audit` + 16
  `phase6a-semantic-backlog`. Suzerain source: 47 `phase5a.1-suzerain-audit`
  + 21 `phase6a-semantic-backlog` (incl. Lahore COMBAT via
  `canonical_combat_bonus`, Valletta ×3 via `compound_discount`).
  Status: **CERTIFIED, awaiting Phase-6C targeted live validation** — the
  prior 971-entry slice stays LIVE_VALIDATED (tags below) but the 1010
  build is not.
  Frozen milestones: 684 Release-1 (`release1-684-live-validated`), 715
  Phase-2 (`phase2-715-live-validated`), 813 Phase-3
  (`phase3-813-live-validated`), 924 Phase-4B (`phase4b-924-live-validated`),
  971 Phase-5B (`phase5b-971-live-validated`); every earlier line persists
  byte-identical except the 3 intentional count-like reclassifications
  (Corporate Libertarianism, Coal, Iron — previously live-tested fractional
  writes, now exact-integral by reviewed correction).

### Engine-representability gate (Phase 3F + 3G)

`EFFECT_ADJUST_BUILDING_YIELD_CHANGE` applies `Amount` as an **integer** at
the application layer (live: helper 14.6 stored and MATCH, city Faith applied
14.0000; static: all 12 official definitions integral while the schema holds
fractions elsewhere). Two carriers dispatch this effect, and both are gated by
modifier-type-scoped curated entries in `rules/certified_overrides.yml`:
`MODIFIER_BUILDING_YIELD_CHANGE` (31 bridged Wonder helpers, Phase 3F) and
`MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_YIELD_CHANGE` (21 live-validated
Release-1 rows, Phase 3G). All 52 certify ADDITIVE with the mandatory integral
gate: `requested = official × k` writes when exactly integral, otherwise the
transform is refused and the definition keeps its official value (gameplay
`0 + V` = vanilla, never truncated, floored or rounded). Evidence, per-row
inventory and the closed-world affected-set proof live in
`docs/WONDER_AUDIT.md`.
At the live stored-FLOAT32 k=7.3 **for the validated 971 baseline**: 773
unconditional + 13 conditional write (**786**), 185 conditional refuse (31
Wonder bridge helpers + 21 Release-1 player-cities entries + 5 Governor
rows + 9 Bologna suzerain GP-point rows; 66 production entries protected in
total). **Phase-6B current-state expectation: 788 unconditional + 13
conditional write (801), 209 refuse** — the 39 new pairs contribute 18
writes + 21 refusals and the 3 accumulation reclassifications move
writes→refusals. At k=10 everything applies (Corporate Libertarianism 10,
Coal/Iron 20, Lahore ≈44.45, Valletta ≈99.90 compound). At k=10 all five governor integral
rows apply (appeal 1→10, four building yields 2→20), and all nine Bologna
rows apply as 10.- **599 unconditional** (every one transforms at k=7.3), **85 conditional
  count-like** (11 exact-integral apply at live FLOAT32 k=7.3, 74 fractional
  refuse safely). Static successful transforms at k=7.3: **610 of 684** —
  lower than the registry size by design (§10 honesty), and derived from the
  actual stored-float multiplier, not decimal 7.3 (see FLOAT32 exactness).
- Kinds: 664 ADDITIVE, 15 DISCOUNT, 7 COMBAT, 0 PROBABILITY (no probability
  rows in scope).
- 43 negative entries.
- 4 two-argument definitions keep both args (Amount + TurnsActive=10→73).

## Grant-object handling

All 12 sem-`GRANT_OBJECT` rows plus 10 curated grant/boolean rows (extra unit
copies ×2, free envoys ×2, influence-token doublers ×4, spy sentinel,
eureka-grant ×4 — 16 curated-effect exclusions total with AUTO_THEME ×2 and
damage-reduction ×1) are excluded. No grant enters production as a magnitude.

## Discount corrections

15 DISCOUNT entries, every one curated per effect (see Discount audit below).
Detection is effect-driven via the sem floor plus the curated table, never
sign-only (positive-percentage discounts were the original miss). The four
unit-maintenance rows are flat gold, not percent discounts (see audit).

## Combat corrections

7 COMBAT entries (1 formula-derived Toqui via the sem floor + 6 curated:
barbarian ×2, diplomatic, corps/army ×2, diplo-visibility). Rule: curated
per effect with strength-point rationale, never by keyword.
Damage-reduction and loyalty effects explicitly inspected and not treated
as strength.

## Spatial/threshold handling

All 12 sem-`SPATIAL_BUDGET` rows excluded (including 3 duration rows on
movement effects — half-scaling a movement bonus duration is incoherent).
`AUTO_THEME` 2/3 thresholds excluded explicitly. No movement/range/radius
scaling in Release 1.

## Count-like audit

85 conditional entries (full list in the coverage report; discrete-domain
rule: charges, slots, capacities, populations, quest counts, districts,
tiles, caps, GPP point amounts, alliance points, visibility levels,
appeal/spy/defense/power ratings, resource accumulation). Fractional results
refuse at runtime via the existing native `countLike` check.

## Certification sources (1010 entries, Phase 6B; from
`build/X10ProductionRegistry.inc.coverage.json`)

curated-category:FLAT_AMOUNT 483, FLAT_YIELD 237, PERCENT_BONUS 26,
PRODUCTION_PERCENT 10, LOYALTY 7, AMENITY 7, GOLD 5, DURATION 4,
GREAT_PERSON_POINTS 9, EXPERIENCE 1, HOUSING 2, GOVERNOR_TITLES 2,
TOURISM 1; curated-effect:mixed plot-yield 74 / city-yield 41;
curated-effect:discount 23 rows across 11 effects (incl. the Phase-6B
BUILDING_PURCHASE_COST ×3); curated-effect:flat-cost maintenance 4;
curated-effect:engine-integral 57 (56 building-yield-change + 1 appeal);
combat-points overrides 12; strong-family overrides 3 (completion percent
×2, Vatican pressure ×1); formula-derived COMBAT_STRENGTH_BONUS 2
(Toqui combat, Lahore).

Trust policy: FORMULA_DERIVED floor rows may directly certify a special
transform; AUTO_PATTERN / NEEDS_REVIEW rows inform but never certify COMBAT /
DISCOUNT / PROBABILITY without a curated override (all 22 sem DISCOUNT rows
are AUTO_PATTERN, so every discount certification is curated). Strong
exclusions stay conservative when heuristic (false exclusion is safe).
Regression test: every COMBAT/DISCOUNT/PROBABILITY entry sources from
`formula-derived:*` or `curated-effect:*` — never heuristic-floor-only.

## FLOAT32 count exactness

Live configuration arrives as stored FLOAT32 (7.3 → `9a99e940` →
7.300000190734863), so strict double equality rejects genuinely exact counts
(10×k = 73.0000019). The native rule propagates the source half-ULP:
`tol = |official|·kErr + 1e-9·max(1,|v|)`, accepting integer n only when
`|v−n| ≤ tol` (and `tol < 0.5` always). kErr comes from the config reader's
variant provenance (FLOAT32 half-ULP via nextafterf; 0 for INT32). At live k:
10→73 and 100→730 accept; 3→21.9, 2→14.6 refuse — proven by the compiled
parity harness against the raw bytes, mirrored in `civ6x10/transforms.py`.
No coarse epsilon: genuine fractions sit ≥0.2 from integers while tolerances
stay <1e-3 across the registry.

## Discount audit (12 effect types, one-time review + Phase-6B Valletta entry)

| Effect | Verdict | Rationale |
|---|---|---|
| ALL_UNITS_PURCHASE_COST | PERCENT | sibling +20 percent discounts; boundary −100 is the percent fixed point (free/doubled stays stable under compound; additive −730 would invent behavior) |
| BUILDING_PURCHASE_COST | PERCENT | Phase-6B Valletta entry: positive-means-discount proven cross-effect (CHEAPER naming + faith context; FLOWER_POWER −100 is the surcharge mirror); boundary +100 is the free fixed point under compound |
| GREAT_PERSON_PATRONAGE_DISCOUNT_PERCENT | PERCENT | PERCENT in the EffectType (Sundiata 20) |
| LEVIED_UNIT_UPGRADE_DISCOUNT_PERCENT | PERCENT | PERCENT in the ModifierType (75) |
| LEVY_DISCOUNT_PERCENT | PERCENT | Percent argument by name (50/75) |
| UNIT_UPGRADE_DISCOUNT_PERCENT | PERCENT | PERCENT in the ModifierType (50) |
| UNIT_UPGRADE_RESOURCE_COST_DISCOUNT | PERCENT | engine arg description: "integer percent value of discount" (50) |
| WMD_MAINTENANCE_MODIFIER | PERCENT | percent-scale 50 (flat gold would be 1–2 scale); thinner single-sample evidence, recorded explicitly |
| PLOT_PURCHASE_COST | PERCENT | tile costs scale with era (flat −20 incoherent late-game); −20 percent-scale |
| PLOT_PURCHASE_COST_TERRAIN | PERCENT | same (−50 terrain) |
| UNIT_MAINTENANCE_DISCOUNT | FLAT | flat gold-per-unit (±1/±2 breaks the percent-depth convention; Conscription −1, Levée −2, Harald −2, Elite +2 gold); fractional gold float-supported |
| UNIT_PURCHASE_COST | PERCENT | sibling +20/+30 percent faith discounts; boundary +100 is the free fixed point |

Generation fails if a release-slice discount row's effect lacks a table
entry (`conflict:unclassified-discount-effect`).

Machine-readable conflict ledger: `build/X10ProductionRegistry.inc.conflicts.csv`
(columns: modifier/effect/argument, sem family, proposed family, proposed
transform, certification source, resolution). Exclusions by reason in
`build/X10ProductionRegistry.inc.coverage.json`.
