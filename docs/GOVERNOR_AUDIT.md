# Governor Semantic Audit (Phase 4A.1)

Audit only: **no production registry rows, no module-owner bit, no controller
or bridge SQL change.** Regenerate with
`python -m civ6x10 audit-governors --db <official-copy>`
(`--game-root` / `CIV6_GAME_ROOT` for the mode payload).

## Discovery: schema-driven, not curated

Governor tables are found by scanning the real SQLite schema for any column
whose name contains "governor" (case-insensitive). The clean official DB has
**12** such tables, including the two that a curated list misses:

| table | governor columns | clean-DB rows |
|---|---|---|
| `GovernorModifiers` | `GovernorType` | 0 |
| `GovernorPromotionConditions` | `GovernorPromotionType` | 0 |
| `GovernorPromotionModifiers` | `GovernorPromotionType` | 75 |
| `GovernorPromotionPrereqs` | `GovernorPromotionType`, `PrereqGovernorPromotion` | 48 |
| `GovernorPromotionSets` | `GovernorType`, `GovernorPromotion` | 48 |
| `GovernorPromotions` | `GovernorPromotionType` | 48 |
| `GovernorReplaces` | `UniqueGovernorType`, `ReplacesGovernorType` | 0 |
| `Governors` | `GovernorType` | 8 |
| `GovernorsCannotAssign` | `GovernorType` | 0 |
| `Governors_XP2` | `GovernorType` | 1 |
| `GreatWorks_MODE` | `RequiredGovernor` | 0 |
| `SecretSocieties` | `GovernorType` | 0 |

Everything is dispositioned, including zero-row tables: `GovernorReplaces` and
`GreatWorks_MODE.RequiredGovernor` are structural/selective mappings, not
scalable magnitudes.

## Secret Societies: same framework, action-aware, mode-gated

The payload is resolved from the Ethiopia modinfo's own UpdateDatabase
actions/criteria, not a single hardcoded file. For the Gathering Storm
ruleset (`criteria=Ethiopia_Mode_Expansion2`) the mode loads:

| file (provenance) | action | criteria | bytes | sha256 |
|---|---|---|---|---|
| `DLC/Ethiopia/Data/Ethiopia_RemoveData_Expansion2.xml` | `EthiopiaGameplay_XP2` | `Ethiopia_Expansion2` | 996 | 76776e2760a5a00cf0bb2790dca2cc60... |
| `DLC/Ethiopia/Data/Ethiopia_Expansion2.xml` | `EthiopiaGameplay_XP2` | `Ethiopia_Expansion2` | 13210 | e9bf1f071eaad1cd4eaec7afe30160ae... |
| `DLC/Ethiopia/Data/Ethiopia_GameCapabilities.xml` | `EthiopiaGameplayXP2_MODE` | `Ethiopia_Mode_Expansion2` | 265 | 821da282bf45febc69fd6c17f39a1612... |
| `DLC/Ethiopia/Data/Ethiopia_SecretSocieties_MODE.xml` | `EthiopiaGameplayXP2_MODE` | `Ethiopia_Mode_Expansion2` | 100572 | 0199ba145c0ad41d777fd1d78e74b941... |
| `DLC/Ethiopia/Data/Ethiopia_SecretSocieties_Expansion2_MODE.xml` | `EthiopiaGameplayXP2_MODE` | `Ethiopia_Mode_Expansion2` | 453 | f1ec83a344a5c35671927808422f9373... |
| `DLC/Ethiopia/Data/Ethiopia_SecretSocieties_GranColombia_Maya_MODE.xml` | `EthiopiaGranColombiaMayaGameplay_MODE` | `Ethiopia_Mode_Expansion2_GranColombia_Maya` | 1387 | 601c6e524637c1cedee3f7e9121cbb0a... |

The Gran Colombia/Maya overlay is a *conditional* action
(`Ethiopia_Mode_Expansion2_GranColombia_Maya`) and is included/excluded
explicitly; it adds `GOVERNOR_PROMOTION_HERMETIC_ORDER_3` ->
`HERMETIC_ORDER_COMANDANTE_GENERAL_LEY_LINE_SCIENCE` (Amount=1).
All four societies are ordinary Governors on the same promotion framework.

Typo normalisation observed: **1** row(s)
(`ModifierID` -> `ModifierId`, counted *before* the fix).

## Counts (mechanically derived)

| metric | value |
|---|---|
| Governors | 12 (base 8 + Secret Society 4) |
| Promotions | 64 (base 48 + Secret Society 16) |
| Reachable numeric rows | 229 |
| Direct/structural cells | 234 |
| Unit-ability side path | 2 |

| disposition | rows |
|---|---|
| CERTIFIED_CANDIDATE | 54 |
| EXCLUDED | 146 |
| DECISION_REQUIRED | 29 |
| OUT_OF_GRAPH | 0 |

### Direct/structural cells (explicitly machine-accounted)

| cell group | disposition | rows |
|---|---|---|
| `AssignCityState` | EXCLUDED | 8 |
| `AssignToMajor` | EXCLUDED | 1 |
| `BaseAbility` | EXCLUDED | 12 |
| `CannotAssign` | EXCLUDED | 4 |
| `Column` | EXCLUDED | 64 |
| `DiscoverAtBarbarianCampBaseChance` | EXCLUDED | 1 |
| `DiscoverAtCityStateBaseChance` | EXCLUDED | 1 |
| `DiscoverAtGoodyHutBaseChance` | EXCLUDED | 1 |
| `DiscoverAtNaturalWonderBaseChance` | EXCLUDED | 1 |
| `EarliestGameEra` | EXCLUDED | 12 |
| `GlobalParameters` | EXCLUDED | 1 |
| `HiddenWithoutPrereqs` | EXCLUDED | 16 |
| `IdentityPressure` | DECISION_REQUIRED | 12 |
| `Level` | EXCLUDED | 64 |
| `RequiredGovernor` | EXCLUDED | 24 |
| `TransitionStrength` | DECISION_REQUIRED | 12 |

SecretSociety discovery chances are **one-off game-mode configuration**
(PROBABILITY/EXCLUDED) - never treated as a repeated-chance magnitude.
`MAX_GOVERNOR_APPOINTMENTS = 9` (raised by the mode payload) is likewise
configuration, not a magnitude.

## Corrected semantic dispositions

| case | old (4A) | now | rationale |
|---|---|---|---|
| Forestry Management appeal (Amount=1) | FLAT_YIELD candidate | **APPEAL, candidate + ENGINE-INTEGRAL gate** | project treats appeal ratings as whole levels; 1 x 7.3 = 7.3 must refuse |
| Serasker (Amount=10, `PLOT_10_TILES_AWAY_MAX_REQUIREMENTS`) | excluded (radius) | **Amount = COMBAT candidate; MaxDistance=10 / MinDistance=0 = EXCLUDED requirement filters** | magnitude and requirement scope are separate concerns |
| Sanguine intimidate (Amount=-5) | combat candidate | **DECISION_REQUIRED** | canonical `b_k = 25 ln(k(exp(b/25)-1)+1)` is undefined for b<0 (transform refuses at k=7.3 and k=10); no new negative formula introduced |
| Laying on of Hands (HEAL 100 / RELIGIOUS_HEAL 100) | first certified PERCENT_BONUS | **both DECISION_REQUIRED** | flat HP vs percent vs cap/sentinel unresolved; effect name is not evidence |

## Engine-integral rows (Phase 4B must inherit the gate)

| modifier | arg | value | note |
|---|---|---|---|
| `FORESTRY_MANAGEMENT_FEATURE_NO_IMPROVEMENT_APPEAL` | Amount | 1 | applied-integer effect |
| `RENEWABLE_ENERGY_IMPROVEMENT_BUILDING_GOLD` | Amount | 2 | applied-integer effect |
| `INDUSTRIALIST_COAL_POWER_PLANT_PRODUCTION` | Amount | 2 | applied-integer effect |
| `INDUSTRIALIST_OIL_POWER_PLANT_PRODUCTION` | Amount | 2 | applied-integer effect |
| `INDUSTRIALIST_NUCLEAR_POWER_PLANT_PRODUCTION` | Amount | 2 | applied-integer effect |

## Shared definitions (never double-scale)

Registry overlap check: 1 shared definition(s): `SULEIMAN_GOVERNOR_POINTS`

| modifier | arg | official | existing owner | governor disposition |
|---|---|---|---|---|
| `SULEIMAN_GOVERNOR_POINTS` | Delta | 1 | traits (GOVERNOR_TITLES) | EXCLUDED |

## Per governor (base)

| Governor | promotions | rows | cand/excl/decision |
|---|---|---|---|
| `GOVERNOR_IBRAHIM` | 6 | 11 | 3/5/3 |
| `GOVERNOR_THE_AMBASSADOR` | 6 | 7 | 1/5/1 |
| `GOVERNOR_THE_BUILDER` | 6 | 15 | 5/9/1 |
| `GOVERNOR_THE_CARDINAL` | 6 | 13 | 2/6/5 |
| `GOVERNOR_THE_DEFENDER` | 6 | 17 | 7/8/2 |
| `GOVERNOR_THE_EDUCATOR` | 6 | 22 | 6/10/6 |
| `GOVERNOR_THE_MERCHANT` | 6 | 23 | 9/14/0 |
| `GOVERNOR_THE_RESOURCE_MANAGER` | 6 | 18 | 6/10/2 |

## Per governor (Secret Societies)

| Governor | promotions | rows | cand/excl/decision |
|---|---|---|---|
| `GOVERNOR_HERMETIC_ORDER` | 4 | 44 | 10/34/0 |
| `GOVERNOR_OWLS_OF_MINERVA` | 4 | 17 | 2/10/5 |
| `GOVERNOR_SANGUINE_PACT` | 4 | 32 | 0/28/4 |
| `GOVERNOR_VOIDSINGERS` | 4 | 10 | 3/7/0 |

## Ownership design (report only)

- `MODULE_BITS` unchanged: traits 1, policies 2, governments 4, pantheons 8,
  wonders 16. **Next owner bit: 32 = governors** (then 64 = suzerain).
- Phase 4B needs `MODULE_BITS["governors"]=32`, a governor manifest stream,
  `s_modEnabled[6]` + `mask|=32` (native change -> DLL rebuild), reusing the
  existing "transform only when ALL owning modules are enabled" rule.

## Proposed Phase 4B candidate list

| family | effect | rows | official values |
|---|---|---|---|
| AMENITY | `EFFECT_ADJUST_DISTRICT_AMENITY` | 2 | 1 |
| AMENITY | `EFFECT_ADJUST_TRAIT_AMENITY` | 1 | 1 |
| APPEAL | `EFFECT_ADJUST_FEATURE_NO_IMPROVEMENT_APPEAL_GOVERNOR` | 1 | 1 |
| COMBAT_STRENGTH_BONUS | `EFFECT_ADJUST_CITY_AIR_DEFENSE_BONUS` | 1 | 25 |
| COMBAT_STRENGTH_BONUS | `EFFECT_ADJUST_CITY_COMBAT_BONUS` | 1 | 5 |
| COMBAT_STRENGTH_BONUS | `EFFECT_ADJUST_CITY_FRIENDLY_COMBAT_BONUS` | 1 | 5 |
| COMBAT_STRENGTH_BONUS | `EFFECT_ADJUST_CITY_INNER_DEFENSE` | 1 | 5 |
| COMBAT_STRENGTH_BONUS | `EFFECT_ADJUST_CITY_RELIGIOUS_COMBAT_BONUS` | 1 | 10 |
| COMBAT_STRENGTH_BONUS | `EFFECT_ADJUST_UNIT_AGAINST_DISTRICT_COMBAT_BONUS` | 1 | 10 |
| FLAT_YIELD | `EFFECT_ADJUST_BUILDING_YIELD_CHANGE` | 4 | 2 |
| FLAT_YIELD | `EFFECT_ADJUST_CITY_YIELD_PER_DISTRICT` | 1 | 2 |
| FLAT_YIELD | `EFFECT_ADJUST_CITY_YIELD_PER_POPULATION` | 2 | 1 |
| FLAT_YIELD | `EFFECT_ADJUST_PLAYER_YIELD_CHANGE_PER_GREAT_PERSON_CLASS_ON_RESOURCE` | 10 | 1 |
| FLAT_YIELD | `EFFECT_ADJUST_PLOT_YIELD` | 2 | 2 |
| FLAT_YIELD | `EFFECT_ADJUST_TRADE_ROUTE_YIELD_TO_OTHERS` | 1 | 2 |
| GOLD | `EFFECT_ADJUST_CITY_GOLD_FROM_CITIZENS` | 1 | 2 |
| GOLD | `EFFECT_ADJUST_CITY_YIELD_FROM_FOREIGN_TRADE_ROUTES_PASSING_THROUGH` | 1 | 3 |
| HOUSING | `EFFECT_ADJUST_DISTRICT_HOUSING` | 2 | 2 |
| PERCENT_BONUS | `EFFECT_ADJUST_CITY_GREAT_PERSON_POINTS_MODIFIER` | 1 | 100 |
| PERCENT_BONUS | `EFFECT_ADJUST_CITY_GROWTH` | 1 | 20 |
| PERCENT_BONUS | `EFFECT_ADJUST_CITY_RESOURCE_HARVEST_BONUS` | 1 | 50 |
| PERCENT_BONUS | `EFFECT_ADJUST_CITY_YIELD_MODIFIER` | 2 | 15 |
| PERCENT_BONUS | `EFFECT_ADJUST_CITY_YIELD_MODIFIER_FROM_FAITH` | 3 | 20 |
| PERCENT_BONUS | `EFFECT_ADJUST_DISTRICT_YIELD_MODIFIER` | 2 | 100 |
| PERCENT_BONUS | `EFFECT_ADJUST_PLAYER_GOLD_INTEREST_PERCENT` | 1 | 3 |
| PERCENT_BONUS | `EFFECT_GOVERNOR_ADJUST_CITY_TOKENS_GRANTED_MODIFIER` | 1 | 100 |
| PRODUCTION_PERCENT | `EFFECT_ADJUST_ALL_DISTRICTS_PRODUCTION` | 1 | 20 |
| PRODUCTION_PERCENT | `EFFECT_ADJUST_CITY_ALL_MILITARY_UNITS_PRODUCTION` | 1 | 20 |
| PRODUCTION_PERCENT | `EFFECT_ADJUST_CITY_CULTURE_BORDER_EXPANSION` | 1 | 20 |
| PRODUCTION_PERCENT | `EFFECT_ADJUST_PROJECT_PRODUCTION` | 4 | 30 |
| PRODUCTION_PERCENT | `EFFECT_ADJUST_SPACE_RACE_PROJECTS_PRODUCTION` | 1 | 30 |

Total Phase-4B candidate rows: **54** across 54 distinct modifier IDs.

## Reproducibility

- Explicit `--game-root` / `CIV6_GAME_ROOT`; without an install the audit
  degrades to base-only and integration tests skip as a coherent group
  rather than comparing a partial derivation against the manifest.
- Source-file identities + SHA-256 are recorded per mode file in the
  manifest (`mode_files`), so the checked-in audit documents exactly which
  official inputs produced it.
- CI exercises a synthetic fake Civ VI tree (main mode XML + Expansion2 +
  conditional Gran Colombia/Maya overlay) covering action merging, criteria
  selection, nested-row parsing and typo normalisation, plus manifest
  invariants that need no game data at all.