# City-State / Suzerain Semantic Audit (Phase 5A)

Regenerate with:

```powershell
python -m civ6x10 audit-suzerains --db data/local/DebugGameplay_official.sqlite `
    --coverage-csv data/local/trait_coverage.csv
```

Artifacts: `civ6x10/rules/suzerain_audit.yml` (checked-in machine audit),
`data/local/suzerain_effects.csv` (one row per reachable argument),
`data/local/suzerain_graph.json` (roots, edges, cycles, side paths).

**PHASE 5A IS AN AUDIT ONLY.** Nothing here is production: no
`manifests/suzerain.yml`, no registry rows, no owner bit `64` in
`civ6x10/production.py`, the CE fork, the controller or the packaged DLL.
The ~1750-line `civ6x10/suzerain.py` module is the audit engine; Phase 5B is a
separate, reviewed decision that consumes `suzerain_audit.yml`.

## 1. Scope

This module is the **10x Suzerain bonus** multiplier. The generic 1/3/6-envoy
tier bonuses shared by the Scientific/Cultural/Industrial/Militaristic/
Religious/Trade city-state "type" traits are **not** part of the graph and
are never swept in: the roots are the per-city-state traits' Suzerain-gated
`TraitModifiers` only.

## 2. Active City-State discovery (derived, never curated)

Membership comes from the shipped runtime DB, joined
`Civilizations` (`StartingCivilizationLevelType = CIVILIZATION_LEVEL_CITY_STATE`)
→ `CivilizationLeaders` → `Leaders_XP2` → `LeaderTraits`, requiring the mapped
leader to carry a non-null `MinorCivBonusType`. `LEADER_MINOR_CIV_%` names,
all `Leaders_XP2` rows, the legacy `trait_coverage.csv` and any wiki/list are
**not** used to decide membership.

| measure | count |
|---|---|
| active City-State civilizations | **48** |
| mapped minor leaders | **48** |
| active minor-civ traits | **48** |
| minor leaders present in `Leaders_XP2` | 50 |
| inactive/orphan minor leaders | **2** |
| active minor-civ trait roots that are NOT Suzerain-gated (flagged) | 0 |

Every active minor leader maps exactly one trait, and all 48 traits resolve
to exactly one `MinorCivBonusType`, so no city-state is silently dropped.

### Provenance and renames

Localization keys are recorded, not invented. Two active traits point at
renamed display names and must not be used to decide membership:
`MINOR_CIV_JAKARTA_TRAIT` → `LOC_LEADER_TRAIT_BANDAR_BRUNEI_NAME` and
`MINOR_CIV_PALENQUE_TRAIT` → `LOC_LEADER_TRAIT_MITLA_NAME`. The generic
`MINOR_CIV_DEFAULT_TRAIT` is internal-only and is not a root of any active
city-state.

## 3. Historical / orphan definitions

`Leaders_XP2` holds 50 minor leaders; two have no `CivilizationLeaders`
mapping and are therefore machine-accounted as `inactive_orphan`:

| LeaderType | `MinorCivBonusType` | carried traits |
|---|---|---|
| `LEADER_MINOR_CIV_CARTHAGE` | `MINOR_CIV_BONUS_MILITARISTIC` | `MINOR_CIV_CARTHAGE_TRAIT` |
| `LEADER_MINOR_CIV_STOCKHOLM` | `MINOR_CIV_BONUS_SCIENTIFIC` | `MINOR_CIV_STOCKHOLM_TRAIT` |

Both traits still exist in `Traits`/`LeaderTraits` and their Suzerain roots
still exist in `TraitModifiers`/`Modifiers`, but no civilization maps the
leader, so they are unreachable as Suzerain roots. They are recorded in the
manifest (`inactive_orphan_minor_leaders`) with the reason and the evidence,
never silently included and never silently dropped.

All 48 `CIVILIZATION_LEVEL_CITY_STATE` civilizations map to a leader, so
there is no orphan in the other direction.

## 4. Suzerain gating is proven, not assumed

Each root's `SubjectRequirementSetId` is resolved to its
`RequirementSetRequirements` and tested for a Suzerain requirement type
(`REQUIREMENT_PLAYER_IS_SUZERAIN`,
`REQUIREMENT_PLAYER_IS_SUZERAIN_BONUS_ENABLED`,
`REQUIREMENT_PLAYER_HAS_ACTIVE_ALLIANCE_OF_AT_LEAST_LEVEL`,
`REQUIREMENT_PLAYER_IS_SUZERAIN_OF_X`) — not inferred from the modifier's
name. A root whose set fails the test is **flagged**
(`not_suzerain_gated_roots`) rather than broadening the graph; the current DB
produces **0** such rows.

| root gate set | roots |
|---|---|
| `PLAYER_IS_SUZERAIN` | 88 |
| `PLAYER_IS_SUZERAIN_ALLY_LEVEL_1` | 1 |
| `PLAYER_IS_SUZERAIN_ALLY_LEVEL_2` | 1 |
| `PLAYER_IS_SUZERAIN_ALLY_LEVEL_3` | 1 |
| **total** | **91** |

The three alliance-level sets are Vilnius's Suzerain **and** alliance-level
variants (`REQUIREMENT_PLAYER_IS_SUZERAIN` **and**
`REQUIREMENT_PLAYER_HAS_ACTIVE_ALLIANCE_OF_AT_LEAST_LEVEL`); they remain in
scope because each set contains actual Suzerain-state proof. The alliance
condition narrows; it never proves on its own (Phase 5A.1 correction: an
alliance-level requirement alone, or a bonus-enabled check alone, is not
Suzerain gating). All 91 roots are `MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER`.

## 5. Closed modifier graph

Traversal follows `ModifierArguments.Name = 'ModifierId'` values that resolve
to a real `Modifiers.ModifierId`, recursively, with cycle detection.

| graph measure | count |
|---|---|
| root wrappers | 91 |
| modifier→modifier edges | 91 |
| reachable modifier definitions | **182** (91 roots + 91 nested) |
| cycles detected | 0 |
| max nesting depth | 1 |
| reachable argument rows | **246** |
| numeric argument rows | **74** |
| non-numeric / structural argument rows | **172** |
| definitions containing ≥1 numeric argument | **73** |

Every reachable argument row carries a disposition, including the 172
selector/structural ones, so the accounting is closed: no reachable cell is
left unclassified. Requirements are preserved per definition
(`OwnerRequirementSetId`, `SubjectRequirementSetId` and their resolved
`RequirementSetRequirements`), so filters are visible and never mistaken for
magnitudes.

## 6. Dispositions

### 6.1 Reachable argument rows (246)

| disposition | count |
|---|---|
| `CERTIFIED_CANDIDATE` | 47 |
| `DECISION_REQUIRED` | 21 |
| `EXCLUDED` | 178 |

Of the 74 numeric rows: 47 candidates, 21 decision-required, 6 excluded.

### 6.2 Side-path cells (243)

| side path | candidate | excluded | decision-required |
|---|---|---|---|
| unique improvements (9) | 0 | 150 | 58 |
| unique unit direct cells | 0 | 21 | 0 |
| unit promotion modifiers | 0 | 1 | 5 |
| unit-ability progression (`TypeTags` → `UnitAbilityModifiers`) | 0 | 0 | 3 |
| granted abilities | 0 | 3 | 2 |
| **total** | **0** | **175** | **68** |

No side-path cell is ever an automatic candidate: a value outside the
Suzerain modifier graph can only join the module after an explicit ownership
decision.

### 6.3 Semantic-family breakdown (numeric rows)

| family | candidate | excluded | decision-required |
|---|---|---|---|
| AMENITY | 2 | 0 | 0 |
| EXPERIENCE | 1 | 0 | 0 |
| FLAT_YIELD | 14 | 0 | 0 |
| GOLD | 3 | 0 | 0 |
| GREAT_PERSON_POINTS | 9 | 0 | 0 |
| PERCENT_BONUS | 13 | 0 | 1 |
| PERCENT_DISCOUNT | 3 | 0 | 3 |
| PRODUCTION_PERCENT | 2 | 0 | 0 |
| INDIVISIBLE_COUNT | 0 | 0 | 12 |
| LOYALTY | 0 | 0 | 4 |
| MULTIPLICATIVE_FACTOR | 0 | 0 | 1 |
| SPATIAL_BUDGET | 0 | 1 | 0 |
| BOOLEAN_UNLOCK | 0 | 3 | 0 |
| GRANT_OBJECT | 0 | 2 | 0 |
| SELECTOR | 0 | 172 | 0 |

## 7. Per-City-State summary

`CERT` = certified candidates, `EXCL` = excluded, `DEC` = decision-required
(reachable rows only; side paths are listed separately in §8).

| City-State | roots | CERT | EXCL | DEC |
|---|---|---|---|---|
| AKKAD | 2 | 0 | 4 | 0 |
| ANTANANARIVO | 1 | 1 | 2 | 0 |
| ANTIOCH | 1 | 1 | 2 | 0 |
| ARMAGH | 1 | 0 | 2 | 0 |
| AUCKLAND | 2 | 2 | 4 | 0 |
| AYUTTHAYA | 1 | 0 | 3 | 1 |
| BABYLON | 3 | 3 | 9 | 0 |
| BOLOGNA | 9 | 9 | 18 | 0 |
| BRUSSELS | 1 | 1 | 1 | 0 |
| BUENOS_AIRES | 1 | 1 | 1 | 0 |
| CAGUANA | 1 | 0 | 2 | 0 |
| CAHOKIA | 1 | 0 | 2 | 0 |
| CARDIFF | 3 | 0 | 6 | 3 |
| CHINGUETTI | 1 | 1 | 2 | 0 |
| FEZ | 1 | 1 | 2 | 0 |
| GENEVA | 1 | 1 | 2 | 0 |
| GRANADA | 1 | 0 | 2 | 0 |
| HATTUSA | 7 | 0 | 14 | 7 |
| HONG_KONG | 1 | 1 | 1 | 0 |
| HUNZA | 1 | 1 | 2 | 0 |
| JAKARTA | 1 | 1 | 2 | 0 |
| JERUSALEM | 1 | 0 | 2 | 0 |
| JOHANNESBURG | 2 | 2 | 4 | 0 |
| KABUL | 1 | 1 | 1 | 0 |
| KANDY | 2 | 0 | 5 | 1 |
| KUMASI | 2 | 2 | 4 | 0 |
| LAHORE | 1 | 0 | 2 | 0 |
| LA_VENTA | 1 | 0 | 2 | 0 |
| LISBON | 1 | 0 | 2 | 0 |
| MEXICO_CITY | 1 | 0 | 2 | 0 |
| MOHENJO_DARO | 1 | 0 | 2 | 0 |
| MUSCAT | 1 | 1 | 1 | 0 |
| NALANDA | 2 | 0 | 4 | 0 |
| NAN_MADOL | 1 | 1 | 2 | 0 |
| NAZCA | 1 | 0 | 2 | 0 |
| NGAZARGAMU | 3 | 3 | 6 | 0 |
| PALENQUE | 1 | 1 | 1 | 0 |
| PRESLAV | 3 | 0 | 3 | 3 |
| RAPA_NUI | 1 | 0 | 2 | 0 |
| SAMARKAND | 2 | 1 | 5 | 0 |
| SINGAPORE | 1 | 1 | 2 | 0 |
| TARUGA | 7 | 7 | 14 | 0 |
| VALLETTA | 5 | 0 | 10 | 3 |
| VATICAN_CITY | 1 | 0 | 1 | 1 |
| VILNIUS | 3 | 3 | 6 | 0 |
| WOLIN | 2 | 0 | 4 | 0 |
| YEREVAN | 1 | 0 | 2 | 0 |
| ZANZIBAR | 2 | 0 | 4 | 2 |

## 8. Side paths

### 8.1 Unique improvements (9)

Discovered mechanically from `EFFECT_ADJUST_PLAYER_VALID_IMPROVEMENT`
modifiers in the graph. Each improvement's owning trait is cross-checked
against `Improvements.TraitType`; all nine agree.

| improvement | city-state | improvement-side cells |
|---|---|---|
| `IMPROVEMENT_MONASTERY` | Armagh | 19 |
| `IMPROVEMENT_BATEY` | Caguana | 25 |
| `IMPROVEMENT_MOUND` | Cahokia | 24 |
| `IMPROVEMENT_ALCAZAR` | Granada | 17 |
| `IMPROVEMENT_COLOSSAL_HEAD` | La Venta | 26 |
| `IMPROVEMENT_MAHAVIHARA` | Nalanda | 29 |
| `IMPROVEMENT_NAZCA_LINE` | Nazca | 25 |
| `IMPROVEMENT_MOAI` | Rapa Nui | 25 |
| `IMPROVEMENT_TRADING_DOME` | Samarkand | 18 |

Every numeric gameplay column of `Improvements` is accounted: magnitude
columns (Housing, Appeal, ReligiousUnitHealRate, DefenseModifier,
YieldFromAppealPercent) are ownership decisions; placement rules
(`TilesRequired`, `ValidAdjacentTerrainAmount`, `MinimumAppeal`), boolean
flags, `PlunderAmount`/`DispersalGold` (paid to an attacker, not to the
bonus), `MovementChange`, and goody-hut/slot columns are structurally
excluded. `Improvement_YieldChanges`,
`Improvement_Adjacencies → Adjacency_YieldChanges`, `Improvement_Tourism`,
`ImprovementModifiers` and the valid-terrain/feature/resource/build-unit
selector tables are inventoried. `ScalingFactor = 100` for tourism is held as
the existing factor-versus-percent decision, not naïve multiplication.

### 8.2 Unique unit: `UNIT_LAHORE_NIHANG` (Lahore)

The `Units` table has 53 non-`UnitType` columns inspected. The audit emits
**21 `direct_cells`**, all excluded: null-valued columns are skipped, and
shipped zero-valued numeric cells are intentionally omitted (a zero cannot
change under any multiplier, so there is nothing to own or decide), except
`Combat`, `Cost`, `BaseMoves` and `BaseSightRange`, which are always recorded
even when zero. The unlock itself is a capability, so the unit's intrinsic
Combat (25), Cost (100), BaseMoves and the other emitted stats are not
claimed by the Suzerain multiplier.

The unit's promotion graph is inventoried as decisions (families now match
the effect-semantic floor; ownership stays a decision because the rows live
outside the Suzerain modifier graph):

| promotion | effect | value | family | requirement |
|---|---|---|---|---|
| `PROMOTION_NIHANG_FLANKED_BONUS` | `EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER` | 7 | `COMBAT_STRENGTH_BONUS` | `UNIT_IS_FLANKED_REQUIREMENTS` |
| `PROMOTION_NIHANG_MOVEMENT_BONUS` | `EFFECT_ADJUST_UNIT_MOVEMENT` | 1 | `SPATIAL_BUDGET` | none |
| `PROMOTION_NIHANG_NO_WOUNDED_PENALTY` | `EFFECT_ADJUST_UNIT_NO_REDUCTION_DAMAGE` | 1 | `BOOLEAN_UNLOCK` | none |
| `PROMOTION_NIHANG_FAITH_FOR_VICTORIES` | `EFFECT_ADJUST_UNIT_POST_COMBAT_YIELD` | 50 | `DEFEATED_STRENGTH_SCALING` | none |
| `PROMOTION_NIHANG_SUZERAIN_COMBAT_BONUS` | `EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER` | 10 | `COMBAT_STRENGTH_BONUS` | **`PLAYER_HAS_LAHORE_SUZERAIN_REQUIREMENTS`** |

The last row is flagged as the strongest side-path candidate: its own
requirement (`REQUIREMENT_PLAYER_IS_SUZERAIN_OF_X` →
`LEADER_MINOR_CIV_LAHORE`) proves the magnitude only exists while the player
is Lahore's Suzerain. It is still a decision, not an automatic claim, because
it lives in `UnitPromotionModifiers` rather than in the trait graph.

The Nihang's barracks/armory/academy strength bonuses are discovered
mechanically as `TypeTags` → `UnitAbilityModifiers`, never by name:

`UNIT_LAHORE_NIHANG` carries `CLASS_LAHORE_NIHANG` (its own tag: no other
unit carries it; the generic `CLASS_MELEE` / `CLASS_ALL_ERAS` tags are
excluded by that rule) →
`ABILITY_NIHANG_BARRACKS_STRENGTH`, `ABILITY_NIHANG_ARMORY_STRENGTH`,
`ABILITY_NIHANG_ACADEMY_STRENGTH` carry the same tag →
`UnitAbilityModifiers` →
`NIHANG_BARRACKS_STRENGTH` / `NIHANG_ARMORY_STRENGTH` /
`NIHANG_ACADEMY_STRENGTH`, each `Amount = 15`
(`EFFECT_ADJUST_UNIT_COMBAT_STRENGTH`, family `COMBAT_STRENGTH_BONUS`,
disposition `DECISION_REQUIRED`).

The grant provenance is retained per ability: `BUILDING_BARRACKS` and
`BUILDING_BASILIKOI_PAIDES` (sharing the Barracks grant),
`BUILDING_ARMORY`, and `BUILDING_MILITARY_ACADEMY` hand out the three
abilities through the corresponding `LAHORE_NIHANG_*_ABILITY` grant
modifiers. All three `Amount = 15` cells are machine-accounted in
`side_paths.units.UNIT_LAHORE_NIHANG.ability_modifiers` (new
`side_path_unit_ability_cells` bucket: 3 decision-required). They are
intrinsic progression bonuses of the unlocked unit, not clearly owned by the
Suzerain multiplier, so they stay decisions.

### 8.3 Granted abilities (3)

| ability | granted by | effect reached |
|---|---|---|
| `ABILITY_TRADE_ROUTE_PLUNDER_IMMUNITY_SEA` | Lisbon | `EFFECT_ADJUST_UNIT_TRADE_ROUTE_PLUNDER_IMMUNITY` (capability, no magnitude) |
| `ABILITY_WOLIN_NAVAL_UNITS` | Wolin | `EFFECT_ADJUST_GREAT_PEOPLE_POINTS_PER_KILL_BY_DEFEATED_STRENGTH`, Amount 25 (`DEFEATED_STRENGTH_SCALING`) |
| `ABILITY_WOLIN_LAND_UNITS` | Wolin | same effect, Amount 25 (`DEFEATED_STRENGTH_SCALING`) |

The Wolin magnitude is a coefficient/rate tied to defeated-unit strength,
not ordinary discrete `GREAT_PERSON_POINTS` (the floor row for the tuple is
unreviewed `MAGNITUDE_UNCLASSIFIED`; the audit override is explicit and
recorded in the side-path floor-consistency check). It is reached only
through the granted ability, so it is an explicit ownership decision rather
than a candidate — and a future production implementation must not inherit
the `GREAT_PERSON_POINTS` count-like gate merely because the result is
eventually paid as GP points.

### 8.4 Granted objects

Nine granted resource objects are recorded with the **grant quantity** only:
`RESOURCE_ALUMINUM`, `RESOURCE_COAL`, `RESOURCE_HORSES`, `RESOURCE_IRON`,
`RESOURCE_NITER`, `RESOURCE_OIL`, `RESOURCE_URANIUM` (Hattusa, +2/turn each)
and `RESOURCE_CINNAMON`, `RESOURCE_CLOVES` (Zanzibar, +1 each). No intrinsic
resource property is multiplied just because a city-state grants the resource,
and no selector (`ResourceType`, `UnitType`, `ImprovementType`, `YieldType`,
…) is ever treated as a magnitude.

Other object grants in the graph are structurally excluded: Kandy's relic
grant, Nalanda's free random technology, Jerusalem's holy-site-as-holy-city
toggle, Mohenjo-daro's fresh-water housing capability, Valletta's
faith-purchase enablers, Yerevan's unlimited apostle promotion choices, and
Akkad's wall-attack capability per promotion class.

## 9. Suzerain semantic families

| family | representative | classification |
|---|---|---|
| Great Person points | Bologna +1 ×9 | scalable magnitude (certified GREAT_PERSON_POINTS flow; `count_like` pattern is not matched by this effect) |
| city yield modifiers | Geneva +15%, Taruga +5% ×7, Vilnius +50% ×3 | percent magnitudes (ADDITIVE percent) |
| free/imported strategic resources | Hattusa +2 ×7, Zanzibar +1 ×2 | count-like whole-unit flow → decision |
| Great Work yields | Babylon +1/+1/+2 | scalable flat magnitudes |
| district yield modifiers | Vilnius +50% | percent magnitude; district requirement is a filter |
| building purchase discounts | Valletta −50 ×3 | effect absent from the curated discount table → decision |
| unit purchase discounts | Ngazargamu −20 ×3 | curated `PERCENT_DISCOUNT` (boundary −100 = free) |
| free power | Cardiff +2 ×3 | whole-unit power flow → decision |
| city identity/loyalty per turn | Preslav +2 ×3 | pressure rate → decision (Toqui-hold class) |
| city-state trade-route yields | Kumasi +2/+1 | scalable flat magnitudes |
| grant-yield-on-building-completion | Ayutthaya +10% culture | grant-on-completion percent → decision |
| plot yields | Auckland +1 ×2 | scalable flat plot yield (existing mixed-domain override) |
| yield by resource count | Johannesburg +1 ×2 | per-resource rate is the magnitude; the count is a combinator |
| freshwater housing | Mohenjo-daro `HasBonus=1` | capability toggle → excluded |
| wonder production | Brussels +15% | percent magnitude |
| international trade-route yields | Samarkand +1, Jakarta +1, Antioch +1, Hunza +0.2 | scalable flat gold yields |
| unit attack-experience | Kabul +100% | certified EXPERIENCE percent |
| amenities from city-states | Buenos Aires +1, Muscat +1 | scalar amenities |
| project production | Hong Kong +20% | percent magnitude |
| population-based initiation yield | Fez +20 science | scalable flat yield |
| natural-wonder relic grants | Kandy +1 | object grant → excluded |
| religious pressure on GP activation | Vatican City 400 | pressure rate → decision |
| unlocked improvements | 9 city-states | capability → side path (§8.1) |
| unlocked Nihang | Lahore | capability → side path (§8.2) |
| unlimited apostle promotions | Yerevan | capability → excluded |

## 10. Overlap with the production registry

The audited graph (182 modifier definitions, 74 numeric argument pairs) is
compared against the shipped `build/X10ProductionRegistry.inc` (920
registered definitions, 924 entries):

| measure | value |
|---|---|
| overlapping modifier ids | **0** |
| overlapping `(ModifierId, argument)` pairs | **0** |

No Suzerain row is already owned, so Phase 5B claims new rows with no shared
ownership to negotiate. Proposed owner bit **`64 = suzerain`** (report only);
the next free bit after that would be **`128`**.

## 11. Comparison with the legacy x10 Suzerain mod

`data/local/trait_coverage.csv` is historical evidence only and is never
certification evidence. It holds 103 `module=SUZERAIN` wrapper rows
(85 `COMPLETE`, 18 `MISSING`) covering 103 distinct modifier ids.

| legacy measure | value |
|---|---|
| active roots present in the legacy file | 91 |
| active roots multiplied (row COMPLETE) | **73** |
| active roots never multiplied (MISSING/ABSENT) | **18** |
| obsolete/orphan roots it touched | 12 (3 Carthage + 9 Stockholm) |
| numeric descendants of active roots | 74 |
| descendants it multiplied | **68** |
| descendants it never multiplied | **6** |
| multiplied → this audit certifies | 43 |
| multiplied → this audit refuses | **21** |
| multiplied → this audit excludes | **4** |

### Gaps the legacy mod left (roots never multiplied)

18 of the 91 active roots, spanning 11 city-states fully and 5 partially
(Valletta 2 of 5, Vilnius 3 of 3, Taruga 1 of 7, Nalanda 1 of 2, Samarkand
1 of 2). Six numeric descendants were therefore never scaled, including all
three Vilnius +50% theater-square culture modifiers, Taruga's coal +5%
science (while its six sibling resources were multiplied), and the
Jerusalem/Mohenjo-daro capability flags.

Note the *causation*: every missed root is a capability-only bonus
(improvement unlock, unit unlock, faith-purchase enable, holy-site toggle,
fresh-water housing) — the legacy `SET Value = Value * 10` had no numeric
column to write on those rows, so those bonuses stayed at the official value.

### Blanket ×10 multipliers this audit refuses

The legacy mod multiplied 21 numeric descendants that this audit refuses or
holds for review — count-like whole-unit flows (Cardiff power ×3, Hattusa
strategics ×7, Zanzibar luxuries ×2), loyalty/pressure rates (Preslav ×3,
Vatican City 400 → 4000), an uncurated building-purchase discount
(Valletta −50 ×3 → −500), a factor (`ScalingFactor` 150), and a
grant-on-completion percent (Ayutthaya 10 → 100).

Worse, it multiplied four descendants this audit **excludes outright**:

| modifier | argument | official | legacy result |
|---|---|---|---|
| `MINOR_CIV_MEXICO_CITY_REGIONAL_RANGE_BONUS` | Amount | 3 | +30 tiles of regional range |
| `MINOR_CIV_KANDY_GRANT_RELIC_BONUS` | Amount | 1 | 10 relics per natural wonder |
| `MINOR_CIV_NALANDA_FREE_TECHNOLOGY_MODIFIER` | Amount | 1 | 10 free random technologies |
| `MINOR_CIV_AYUTTHAYA_CULTURE_COMPLETE_BUILDING` | IncludeWonder | 0 | flag multiplied |

These are the concrete "broken multipliers" the audit was asked to find, and
they are precisely the reason the closed-world gate refuses to treat the
legacy mod as certification evidence.

### Bonuses the legacy mod never touched at all

The nine unique improvements' internal data, the Nihang's intrinsic stats and
promotions, and the two Wolin ability magnitudes appear in
`trait_coverage.csv` with no `referenced_object` rows at all, so the old
ecosystem never reached them.

## 12. Reproducibility

- The audit reads the official DB copy through `civ6x10.database.OfficialDb`-style
  `mode=ro` SQLite access and records the copy's path + SHA-256
  (`8d8149338398195dda727318ab168ce420419d60e04ea9ad9ad4c133786c27a1`).
- `--game-root` / `CIV6_GAME_ROOT` is accepted for provenance only. The local
  install exposes no unpacked `Base/Data` XML, so the runtime DB is the
  authoritative provenance source for membership in this phase.
- CI runs a synthetic fixture DB plus manifest invariants; the real-integration
  test group skips as a coherent module when the private copy is absent.
- Output is deterministic (sorted rows, stable ordering).
- Without `--coverage-csv` the legacy comparison records
  `available: false` rather than an empty analysis.
- Without the effect-semantic floor the side-path floor-consistency check
  records `available: false` (CI-safe); pass `--sem-floor-path` to enable it.
  The checked-in manifest was generated with the floor present: 32 side-path
  modifier-tuple cells checked, 15 agreements, 17 explicit overrides (all
  justified in `SIDE_PATH_EFFECT_RULES`; the Nihang combat/movement/faith
  rows agree, the Wolin rate and the Nihang base-strength rows override
  unreviewed floor rows with no production consequence while they stay
  decisions).

## 13. What Phase 5B would have to decide

The audit proposes **47 certified candidates** (the numeric rows the existing
certification gate already accepts: 35 ADDITIVE unconditional, 9 ADDITIVE
count-like — the nine Bologna GP-point rows — and 3 DISCOUNT unconditional;
see the dry-run certification test) and holds **21 decision-required numeric
rows**, plus the **68 decision-required side-path cells**. The full list of
candidates and their families is in `suzerain_audit.yml`
(`proposed_candidates`). No production artifact was created, and the
production registry, CE fork, controller and packaged DLL are unchanged.
