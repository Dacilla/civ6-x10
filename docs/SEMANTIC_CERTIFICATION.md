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
| 2 | Toqui governor-loyalty Amounts verify blank post-Add (stored-form proof pending) | Temporarily excluded (`EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE`); re-certify via store-lookup witness |
| 33+ | Indivisible counts emitted unconditional (`FLAT_AMOUNT`, countLike=false) | Certified as count-like conditional (exact-integer applies, fractional refuses) |

Unresolved conflicts after the gate: **0** (`unresolved_conflicts: []`;
`SemanticConflict` would fail generation).

## New certified registry

- **872 entries / 868 unique definitions / 25 shared** (358 traits-only
  incl. Suleiman titles, 284 policies-only, 18 governments-only, 31
  pantheons-only, 156 wonders-only = 97 modifier-backed + 59 generated
  bridge helpers; 740 unconditional + 132 count-like).
  Frozen milestones: 684 Release-1 (`release1-684-live-validated`), 715
  Phase-2 (`phase2-715-live-validated`); every earlier line persists
  byte-identical, additions only.
- **599 unconditional** (every one transforms at k=7.3), **85 conditional
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

## Certification sources (entries)

curated-category:FLAT_AMOUNT 370, curated-category:FLAT_YIELD 215,
curated-effect:mixed plot-yield 41, curated-effect:mixed city-yield 22,
curated-effect:discount ×10 effects (15 entries), curated-effect:flat-cost
maintenance (4 entries), combat overrides 6, curated-category:PERCENT_BONUS 5,
curated-category:DURATION 4, curated-category:AMENITY 2,
curated-category:TOURISM 1, formula-derived:COMBAT_STRENGTH_BONUS 1.

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

## Discount audit (11 effect types, one-time review)

| Effect | Verdict | Rationale |
|---|---|---|
| ALL_UNITS_PURCHASE_COST | PERCENT | sibling +20 percent discounts; boundary −100 is the percent fixed point (free/doubled stays stable under compound; additive −730 would invent behavior) |
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
