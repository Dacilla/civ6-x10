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
| 13 | `DISCOUNT` floor rows emitted as `ADDITIVE` (positive-official discounts the sign heuristic missed) | Corrected to `DISCOUNT`/compound semantics |
| 3 | `DEFEATED_STRENGTH_SCALING` rows multiplied | Excluded: `DECISION_REQUIRED` preserved |
| 64 | `MIXED_VALUE_DOMAIN` rows (scalar officials, vector siblings) admitted silently | Certified via 2 explicit per-effect overrides with rationale |
| 5 | Curated combat-point effects emitted as `ADDITIVE` (barbarian ×2, diplomatic, corps/army ×2, diplo-visibility) | Corrected to `COMBAT`/combat formula |
| 2 | `AUTO_THEME` slot thresholds (Amount=2/3) scaled | Excluded: eligibility thresholds, not magnitudes |
| 1 | `NATIONALIDENTITY` damage-reduction modifier (50) scaled as strength | Excluded: not strength points |
| 16 | Curated grant/boolean/sentinel effects (extra unit copies, free envoys, token doublers, -1 spy sentinel, eureka grants) | Excluded with per-effect rationale |
| 33+ | Indivisible counts emitted unconditional (`FLAT_AMOUNT`, countLike=false) | Certified as count-like conditional (exact-integer applies, fractional refuses) |

Unresolved conflicts after the gate: **0** (`unresolved_conflicts: []`;
`SemanticConflict` would fail generation).

## New certified registry

- **686 entries / 682 unique definitions / 25 shared** (traits-only 359,
  policies-only 284, governments-only 18, shared 25).
- **601 unconditional** (every one transforms at k=7.3), **85 conditional
  count-like** (11 exact-integral apply at k=7.3, 74 fractional refuse
  safely). Static successful transforms at k=7.3: **612 of 686** — lower
  than the registry size by design (§10 honesty).
- Kinds: 660 ADDITIVE, 19 DISCOUNT, 7 COMBAT, 0 PROBABILITY (no probability
  rows in scope).
- 43 negative entries (sentinel -1 excluded with its row).
- 4 two-argument definitions keep both args (Amount + TurnsActive=10→73).

## Grant-object handling

All 12 sem-`GRANT_OBJECT` rows plus 10 curated grant/boolean rows (extra unit
copies ×2, free envoys ×2, influence-token doublers ×4, spy sentinel,
eureka-grant ×4 — 16 curated-effect exclusions total with AUTO_THEME ×2 and
damage-reduction ×1) are excluded. No grant enters production as a magnitude.

## Discount corrections

19 DISCOUNT entries (8 previously correct + 11 corrected from `ADDITIVE`).
Rule: discount detection is effect-driven via the sem floor, never sign-only
(positive-percentage discounts were the miss). Regression test pins all 11
named discount definitions to `DISCOUNT`.

## Combat corrections

7 COMBAT entries (1 sem-certified Toqui + 6 curated: barbarian ×2,
diplomatic, corps/army ×2, diplo-visibility). Rule: curated per effect with
strength-point rationale, never by keyword. Damage-reduction and loyalty
effects explicitly inspected and not treated as strength.

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

category:FLAT_AMOUNT 370, category:FLAT_YIELD 215, override:mixed plot-yield
41, override:mixed city-yield 22, sem-floor:DISCOUNT 19, combat overrides 6,
category:PERCENT_BONUS 5, category:DURATION 4, category:AMENITY 2,
category:TOURISM 1, sem-floor:COMBAT 1.

Machine-readable conflict ledger: `build/X10ProductionRegistry.inc.conflicts.csv`
(columns: modifier/effect/argument, sem family, proposed family, proposed
transform, certification source, resolution). Exclusions by reason in
`build/X10ProductionRegistry.inc.coverage.json`.
