# Wonder Semantic Audit (Phase 3)

Source of truth: the authoritative clean official database
(`DebugGameplay_official.sqlite`, OFFICIAL_RUNTIME_BASELINE copy):
53 rows in `Buildings` with `IsWonder=1` (48 carry modifiers, 5 carry none:
Estadio Maracana, Hermitage, Panama Canal, Sydney Opera House,
Temple of Artemis).
Machine-readable dispositions: `civ6x10/rules/wonder_audit.yml`
(53 buildings, every production-relevant row mapped with an individual
rationale). Inventory: `data/local/wonder_effects.csv` (298 rows, via
`python -m civ6x10 inventory-wonders --db <official-copy>`; ATTACH children
resolved one level). Manifest: `manifests/wonders.yml` (298 rows: 260 ok
incl. 159 selectors, 1 refused boolean, 16 undecided + 21 non-ok numeric/
threshold rows).

## Disposition rollup

- COMPLETE (19): Amundsen Scott, Angkor Wat, Biosphere, Casa de
  Contratacion, Chichen Itza, Colosseum, Eiffel Tower, Etemenanki, Great
  Bath, Great Zimbabwe, Hagia Sophia, Hanging Gardens, Huey Teocalli,
  Machu Picchu, Oracle, Ruhr Valley, University of Sankore, Statue of
  Liberty, Taj Mahal (every numeric magnitude certified).
- PARTIAL (14): Broadway, Colossus, Golden Gate Bridge, Kotoku-in,
  Kilwa Kisiwani, Mahabodhi Temple, Mausoleum, Meenakshi Temple, Oxford
  University, Potala Palace, Pyramids, St. Basil's Cathedral, Torre de
  Belem, Statue of Zeus (one or more numerics excluded, noted per row).
- UNSUPPORTED / NONE (20): Alhambra, Apadana (token grant), Big Ben
  (slot + treasury multiplier), Bolshoi (civic grant), Cristo Redentor
  (unresolved ScalingFactor), Estadio (no modifiers), Forbidden City
  (wildcard slot), Great Library (tech grants), Great Lighthouse
  (embarked movement spatial + ability selectors), Hermitage (none),
  Jebel Barkal (deliberate grant-floor boundary, see below), Mont St.
  Michel (selector-only promotion), Orszaghaza (favor multiplier),
  Panama Canal (none), Petra (vector-valued Amount), Stonehenge (unit +
  great-person grants), Sydney Opera House (none), Temple of Artemis
  (none), Terracotta Army (selectors + XP sentinel exclusion), Venetian
  Arsenal (3 curated unit-copy exclusions).

Native rows added: **97 wonder-owned** (74 unconditional + 23 conditional),
plus Suleiman governor titles (traits-owned, newly certified by the narrow
Delta-on-GOVERNOR_POINTS rule — the only traits-side addition, reported
explicitly). Count-like added: 24 (23 wonder + Suleiman). No new transform
families: ADDITIVE throughout plus 2 curated DISCOUNT rows (Meenakshi guru
purchase, Oracle patronage). Bespoke pending: 0.

## Deliberate boundaries (reviewed, not overlooked)

- **Jebel Barkal iron:** `EFFECT_GRANT_FREE_RESOURCE_EXTRACTED` is
  GRANT_OBJECT in the sem floor while adjust-style extraction
  (`TRAIT_ACCUMULATE_MORE_COAL`) is a certified flow. Granting a new
  extraction vs adjusting an existing one is a real semantic difference;
  grants stay excluded without positive proof.
- **Big Ben treasury / Orszaghaza favor:** one-shot multipliers
  (+50 treasury, +100% suzerain favor). Scaling the percent (→ +500 /
  +1000) invents 6x/11x outcomes; repeated-application semantics are
  unresolved. Curated exclusions with rationale, never flat-multiplied.
- **Cristo / St. Basil ScalingFactor 200:** percent-vs-factor scaling
  unresolved; excluded with rationale rather than assumed.
- **Petra / Mausoleum vectors:** non-numeric multi-yield Amounts stay
  undecided; never split or scaled.
- **Casa de Contratacion governor titles (+3) and Suleiman (+1):** whole
  titles via a narrow, effect-specific Delta rule (new GOVERNOR_TITLES
  family + category + count pattern); conditional on integral results.
- **Diplomatic victory points (Mahabodhi 2, Potala 1, Statue of Liberty
  4) and Taj Mahal era score (1):** whole points via new count patterns;
  conditional on integral results.
- **Angkor/Eiffel housing & amenity-style ratings:** housing stays
  unconditional (baseline HOUSING handling preserved); appeal ratings are
  count-like (whole levels), consistent with the existing appeal rules.

## Historical Wonder mod, re-audited as behavioral comparison only

Workshop mod 1662972647 ("Wonder x10") multiplies `Value * 10` on targeted
`ModifierId`s plus direct table edits (`Building_YieldChanges`,
`Buildings.Housing`, `Building_GreatPersonPoints`, great-work slots).
Against current numeric wonder Amount rows (120): it would multiply 113,
of which **22 are rows we deliberately exclude** — free Archers/Spearmen/
Battering Ram/Monks/Gurus/Apostles/Builders/Traders, free Civics/Techs,
influence tokens, embarked movement, iron grants, treasury/favor
multipliers, XP sentinel, cheapest-building grant, naval copies. It
**misses 6 we certify** (Broadway culture, Casa titles, Mahabodhi/Potala
DVP, Oxford science, Ruhr production). Its table-level edits (yields,
housing, GPP, slots) bypass ModifierArguments entirely — a different
mechanism outside the native definition registry, not replicated. Nothing
from the workshop mod (IDs, SQL, assets) is used as source data.

## Phase 3B: direct-table inventory + generated modifierization bridge

Phase 3 inventoried only `BuildingModifiers` / attached modifier
definitions. The clean official DB carries substantial wonder gameplay data
in direct building tables that `civ6x10/wonder.py` never read. Phase 3B
closes that gap (`civ6x10/bridge.py`; inventory
`data/local/wonder_direct.csv` via
`python -m civ6x10 inventory-wonder-direct --db <official-copy>`).

### Expanded direct-effect inventory (closed world)

Schema scan over every `BuildingType`-keyed table in the official DB:

- Bridged gameplay magnitudes — `Building_YieldChanges` **31 wonder rows**,
  `Building_GreatPersonPoints` **20 wonder rows**, `Buildings.Housing`
  **3 rows**, `Buildings.Entertainment` **5 rows**: 59 cells spanning
  40 wonders.
- Structural / selector tables inventoried with explicit dispositions, never
  bridged: `Building_GreatWorks` 11 wonder rows (slots are structural
  capacity; per-slot non-unique yields and theming multipliers are
  slot-coupled mechanics, not plain city yields — audited field by field:
  `NumSlots`, `NonUniquePersonYield`, `NonUniquePersonTourism`,
  `ThemingYieldMultiplier`, `ThemingTourismMultiplier`), `Buildings`
  scope/defense keys (`RegionalRange`, `DefenseModifier`,
  `GrantFortification`, `AdjacentResource`), `Buildings_XP2` map flags
  (bridge/canal/flood), plus 8 further `BuildingType`-keyed gameplay
  tables proven to hold **zero** wonder rows
  (`Building_CitizenYieldChanges`, `Building_BuildChargeProductions`,
  `Building_ResourceCosts`, `Building_TourismBombs_XP2`,
  `Building_YieldChangesBonusWithPower`, `Building_YieldDistrictCopies`,
  `Building_YieldsPerEra`, `Adjacent_AppealYieldChanges`) — the scan ran,
  it did not silently skip them.
- Every bridged cell has a `direct:` disposition entry in
  `civ6x10/rules/wonder_audit.yml` with an individual rationale; regression
  tests pin the 31/20/8 counts so a future ModifierArguments-only audit
  cannot call itself complete.

### Corrected rollup (COMPLETE requires every source dispositioned)

- COMPLETE (**24**): all 19 Phase-3 COMPLETE minus the 12 that carried
  unhandled direct effects (now bridged), plus the 5 former NONE wonders —
  Estadio, Hermitage, Panama Canal, Sydney Opera House, Temple of Artemis —
  each now COMPLETE via bridged helpers (NONE had meant only "no
  BuildingModifiers", which was misleading).
- PARTIAL (**27**): Phase-3 PARTIAL (14) plus 13 former UNSUPPORTED wonders
  whose direct scalars now bridge while a modifier-backed exclusion remains.
- UNSUPPORTED (**2**): wonders with no certifiable magnitude in any source.
- Pin examples now covered: Hanging Gardens Housing 2, Great Bath
  Housing 3 + Entertainment 1, Amundsen Scott Scientist GPP 5, Angkor Wat
  Faith 2, Great Zimbabwe Gold 5 + Merchant GPP 2, Sankore Science 3 +
  Faith 1 + Scientist GPP 2, Colosseum Culture 2 + Entertainment 2
  (RegionalRange 6 stays structural-excluded).

### Bridge design (no new native arithmetic)

For each certifiable direct scalar V, generated guarded SQL zeroes the
direct cell and creates one helper modifier carrying `Amount=V` attached to
the wonder; the helper flows through the existing native registry
(official-mismatch guard, FLOAT32 k, count rules, store lookup). Invariant:
module OFF or k=1 → `0 + V` = vanilla; module ON at k → `0 + kV`.
Helper IDs are deterministic (`X10_<BUILDING>_<TAG>`, e.g.
`X10_PANAMA_CANAL_YIELD_GOLD`) from the generator, never handwritten; zero
official `X10_`-prefixed collisions exist. Families bridged:

- `Building_YieldChanges` → `MODIFIER_SINGLE_CITY_ADJUST_YIELD_CHANGE`
  (`EFFECT_ADJUST_CITY_YIELD_CHANGE`, flat city yield; official precedent:
  Monument culture at full loyalty, `COLLECTION_OWNER`).
- `Building_GreatPersonPoints` → `MODIFIER_SINGLE_CITY_ADJUST_GREAT_PERSON_POINT`
  (whole GPP; precedent: Divine Spark scientist, `BUILDING_IS_LIBRARY`
  requirement shape; conditional on integral results like all counts).
- `Buildings.Housing` → `MODIFIER_SINGLE_CITY_ADJUST_BUILDING_HOUSING`
  (precedent: Religious Community / Feed the World shrine housing).
- `Buildings.Entertainment` → `MODIFIER_SINGLE_CITY_ADJUST_ENTERTAINMENT`
  (precedent: Thermal Bath amenities).

Equivalence was proven per family on all five axes (owning city scope,
lifetime, stacking, yield/person type, local-vs-global) against official
single-city precedents sharing the same DynamicModifier collection
(`COLLECTION_OWNER`) and flag shape (RunOnce 0, NewOnly 0, Permanent 0,
Repeatable 0, no requirement sets — copied from the analogues). Excluded:
Great Work slots/theming, RegionalRange, DefenseModifier, canal/bridge/
flood flags, policy slots, grant mechanics, vector/boolean values.

### SQL safety (fail closed on drift)

Each helper INSERT fires only when its direct cell still holds the audited
official value (`... AND EXISTS (SELECT 1 FROM <table> WHERE <full
baseline incl. value>)`); each direct zeroing fires only when the cell
holds that value AND its helper exists. Drift (patch or another mod)
leaves vanilla untouched while the dormant registry row can never match at
runtime (official-mismatch guard). Statements are idempotent
(`NOT EXISTS` guards) and the bridge ships as an InGame `UpdateDatabase`
action (`Config/X10WonderBridge.sql`, wired in `X10.modinfo`) so helpers
exist before native populate.

### Totals (superseded by Phase 3C below)

59 helpers → 59 registry entries (39 unconditional + 20 count-like GPP);
final registry **872 entries / 868 definitions** (740 uncond + 132 cond;
static at FLOAT32 k=7.3: **752 writes / 120 refusals**). All 715 pre-Wonder
rows byte-identical; the 97 modifier-backed wonder rows unchanged.

## Phase 3C: corrected bridge semantic equivalence

The Phase-3B SQL architecture (guarded baseline predicates,
zero-only-if-helper-exists, idempotence, deterministic IDs) is retained.
Independent review found two equivalence defects, both corrected; all
figures below are derived from generation/tests, not targeted.

### A. Regional Entertainment excluded (Colosseum, Estadio)

`Buildings.Entertainment` participates in `RegionalRange` for Colosseum
(range 6) and Estadio (range 100000/global). The only official
regional-entertainment modifier,
`GREATPERSON_EXTRA_REGIONAL_BUILDING_ENTERTAINMENT`
(`MODIFIER_PLAYER_DISTRICT_ADJUST_EXTRA_REGIONAL_ENTERTAINMENT`,
`EFFECT_ADJUST_DISTRICT_EXTRA_REGIONAL_ENTERTAINMENT`), is a great-person
one-shot (RunOnce=1, Permanent=1, district-in-tile attachment target) —
entirely different lifetime, attachment, and scope from a persistent wonder
aura. No `BuildingModifiers`-attached regional-entertainment precedent
exists anywhere in the clean DB, so exact equivalence is unproven: both
cells keep their vanilla direct values (never zeroed), generate no helpers,
and both wonders are PARTIAL with the rationale recorded per cell. The
three `RegionalRange=0` Entertainment rows (Alhambra, Great Bath, Golden
Gate Bridge) retain the local Thermal Bath bridge. Regression test:
nonzero Entertainment + nonzero RegionalRange MUST NOT use
`MODIFIER_SINGLE_CITY_ADJUST_ENTERTAINMENT` (inventory absence + no helper
+ no zeroing + audit disposition agreement).

### B. Yields re-bridged as building yields

`Building_YieldChanges` helpers now use `MODIFIER_BUILDING_YIELD_CHANGE` /
`EFFECT_ADJUST_BUILDING_YIELD_CHANGE` with all three arguments
(`Amount` = audited value, `BuildingType` = owning wonder, `YieldType` =
direct row type), attached through the wonder's `BuildingModifiers` — the
same shape as the direct official precedents `ELECTRONICSFACTORY_CULTURE`
(own-building attach, Amount 4 + BuildingType + YieldType, COLLECTION_OWNER)
and `TSIKHE_FAITH_GOLDEN_AGE`. Building yield stays building yield; the
generic city-yield effect appears nowhere in helpers or SQL (tested).

### C. GPP and housing retained (documented, no mismatch)

- GPP: helper effect (`EFFECT_ADJUST_GREAT_PERSON_POINTS`) and collection
  (`COLLECTION_OWNER`) are identical to the official single-city shape;
  Divine Spark shows Firaxis scoping this exact type to a building
  (`BUILDING_IS_LIBRARY` subject requirement). Per-city owner-pooled whole-
  point flow is unchanged, so no category-sensitive downstream consumer sees
  a different event shape. Count-like (integral-only) behavior kept.
- Housing: helper effect (`EFFECT_ADJUST_BUILDING_HOUSING`) and collection
  (`COLLECTION_OWNER`) match the official shrine/temple housing modifiers
  (Religious Community, Feed the World — all-zero flags, unconditional
  shape). Per-city capacity is unchanged; the player-global housing variants
  (`MODIFIER_PLAYER_CITIES_...`) are never used.

### D. Corrected k=0/OFF invariant

The bridge zeroes the direct cell, so the gameplay total is always
`0 + helper(k)`: k=0 (native Off) and module OFF leave the helper at
official V (native never arms writes) → total V; k=1 → V; k>1 ON → kV.
The test now proves all four cases instead of modeling k=0 as helper-zero.

### Corrected rollup and totals (derived)

- Rollup: COMPLETE **22** / PARTIAL **29** / UNSUPPORTED **2** (Colosseum and
  Estadio move COMPLETE → PARTIAL on the regional exclusion).
- 57 helpers (31 building-yield + 20 count-like GPP + 3 housing + 3 local
  entertainment) → registry **870 entries / 866 definitions**
  (738 uncond + 132 cond; static at FLOAT32 k=7.3: **750 writes /
  120 refusals**).
- All 715 pre-Wonder rows and all 97 modifier-backed wonder rows unchanged.
