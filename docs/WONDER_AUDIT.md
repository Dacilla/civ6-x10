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
  (707 uncond + 163 cond; static at FLOAT32 k=7.3: **720 writes /
  150 refusals** - 30 of those refusals are Phase-3F integral-gated
  building-yield helpers, see below).


## Phase 3D: three missing helpers — DLC load order (diagnosed, fixed)

Phase-3C live validation was near-perfect (`writes=748 transform_refused=119
official_mismatch=0 post_add_match=748 mismatch=0 unreadable=0`) with both
witnesses MATCHING (Zeus 50→365, Panama helper 10→73 — the bridge
architecture is LIVE-PROVEN). But 748+119=867, not 750+120=870: exactly
three generated helpers never materialized (`definitions_added=3264 =
3210 + 54`).

### Exact cause per helper (proven, not inferred)

All three missing source cells live in ONE file:
`DLC/Portugal/Data/Portugal_Buildings.xml` — Torre gold (line 29), Torre
admiral GPP (line 34), **and Etemenanki science (line 27)**. At
X10WonderBridge execution time those rows were absent (EXISTS guards
correctly false → no helpers, no zeroing — fail-closed worked); Portugal's
`PortugalGameplay` UpdateDatabase action inserts them later. Runtime proof
from the live logs (no new run needed for the diagnosis):

- Etemenanki modifier-backed definitions (`ETEMENANKI_SCIENCE_FLOODPLAINS`,
  `..._PRODUCTION_MARSH`, …) populated and MATCHED → Babylon content
  enabled; only the bridge helper is missing → the row arrived after the
  bridge, not "never".
- Portugal content likewise enabled (`TRADE_PRODUCTION_FROM_FEITORIA`,
  `TRADE_GOLD_FROM_FEITORIA` 4→29.2 MATCHED) → Torre rows existed by
  populate time, yet no helpers → same late-arrival cause.
- Content-disabled and baseline-drift causes are thereby excluded for all
  three: the user's enabled content excludes nothing.

No native change (writer/store verification was clean: 748/748/0/0). No
load-order change (Civ VI offers no per-DLC ordering lever that survives
users without those DLCs — hard dependencies would disable X10 for them).

### Fix: deferred guarded triggers (order-agnostic, ownership-agnostic)

`X10WonderBridge.sql` now emits, per bridged cell, two deterministic
`AFTER INSERT` triggers alongside the unchanged immediate statements:

- `X10_TRG_<helper>` materializes the helper when a late row arrives WITH
  the baseline (WHEN = identical baseline predicate on NEW; zeroing stays
  conditional on helper existence; NOT EXISTS keeps idempotence).
- `X10_TRGD_<helper>` records late rows that BREAK the baseline
  (`origin='late-baseline-mismatch'`), guarded on helper absence so it can
  never overwrite a successful record.

Same fail-closed rules, deferred. Triggers also cover any future
late-loading content without further changes.

### Diagnostics (local-only dump, no native change)

New `X10BridgeDiag` table (helper, source table/key, expected, observed,
helper/attach/amount/zeroed flags, origin) written unconditionally at
bridge time and updated by triggers — distinguishing absent (observed NULL),
drifted, and bridged states. Dumped by the disposable probe via
`DB.Query` through the native logger (`[X10BridgeDiag]` lines in
`X10Lifecycle.log`, incl. `bridge_expected/materialized/unavailable`
summary). The table itself is inert data; log noise lives only in the
never-shipped probe. Runtime validation reports materialization separately
from transform refusals via this dump — the native writer is untouched.

### Corrected expected counts (derived, unchanged totals)

Registry still **870 entries**; with both DLC packs enabled the next run
must show `definitions_added=3267 writes=720 transform_refused=150
post_add_match=750 mismatch=0 unreadable=0` plus 57 `[X10BridgeDiag]` lines
(54 `origin=immediate`, 3 `origin=trigger`) and
`bridge_expected=57 bridge_materialized=57 bridge_unavailable=0`.
Panama witness preserved. If content is genuinely unowned, the diag shows
`bridge_unavailable=N` with vanilla untouched — legitimate, documented per
run, never a failure.

## Phase 3F: building-yield application is integral (engine representability)

The Phase-3E active-gameplay proof reached the real effect and exposed a
semantic constraint the definition store cannot show: the helper Amount 14.6
was stored and verified (`official=2 k=7.3 requested=14.6 stored_after_add=14.6
MATCH via=store-lookup`) yet the constructed Stonehenge contributed exactly
**14.0** Faith to its city (`faith_before=0.0000`, `faith_next_turn=14.0000`,
both read back with `%.4f` through `City:GetYield`).

### Engine-semantics conclusion: the effect applies Amount as an integer

Two hypotheses were separated using the evidence rather than assumed:

- **UI/readback rounding — rejected.** `City:GetYield` was read as a float and
  formatted `%.4f`; a fractional 14.6 would have printed `14.6000`, not
  `14.0000`.
- **Rounding to nearest — rejected.** 14.6 → 14 (nearest would be 15), so the
  conversion is truncation inside the effect/application layer.
- **Static corroboration.** All 12 official `MODIFIER_BUILDING_YIELD_CHANGE`
  definitions carry integral Amounts (2, 3, 4), while the same
  `ModifierArguments` schema elsewhere genuinely holds fractions (0.5, 0.6,
  -0.5, 0.2 — 11 rows). The integral domain is therefore a property of
  `EFFECT_ADJUST_BUILDING_YIELD_CHANGE`, not of the schema or of the data
  authoring convention.
- **No exact-equivalent fractional carrier.** The only other modifier type
  dispatching this effect (`MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_YIELD_CHANGE`)
  is player-scoped rather than building-scoped, and the city-scoped
  `MODIFIER_SINGLE_CITY_ADJUST_YIELD_CHANGE` (`EFFECT_ADJUST_CITY_YIELD_CHANGE`)
  changes the affected object from the building to the city, so building
  equivalence is unproven and it was not adopted. Integral-gated refusal is
  preferred over silently re-scoping the effect.

### Correction: integral-gated refusal (existing machinery, new scope)

The runtime integral gate already existed (registry `countLike` →
`X10Transforms::Apply` refuses fractional results, and generation's
`count_like_applies` mirrors it). Phase 3F adds a curated
`engine_integral_effects` rule scoped to
(`MODIFIER_BUILDING_YIELD_CHANGE`, `EFFECT_ADJUST_BUILDING_YIELD_CHANGE`,
`Amount`): the rows keep their **ADDITIVE** family and kind (these are additive
yields whose *engine representation* is integral — not conceptual object-count
grants) but gain the mandatory integral check. Consequences:

- `requested = official × k`; integral results write normally, fractional
  results are **refused** — the definition keeps its official value, so with
  the direct cell already zeroed gameplay is `0 + V` = vanilla V, never 0 and
  never an approximation.
- No floor/ceil/round anywhere; the refuse path is the same
  `transform-refused` counter already exercised by count-like rows.
- Registry-only change (no DLL rebuild: the native writer already reads
  `countLike` from the generated table).

### Affected-row inventory (all 31 bridged Building_YieldChanges helpers)

Every row below is `MODIFIER_BUILDING_YIELD_CHANGE` / `Amount`, official value
V, requested `V × 7.300000190734863`:

| Wonder | helper ID | V | requested at 7.3 | integral? |
|---|---|---|---|---|
| Oracle | X10_ORACLE_YIELD_CULTURE | 1 | 7.300000191 | refuse |
| Oracle | X10_ORACLE_YIELD_FAITH | 1 | 7.300000191 | refuse |
| Sankore | X10_UNIVERSITY_SANKORE_YIELD_FAITH | 1 | 7.300000191 | refuse |
| Angkor Wat | X10_ANGKOR_WAT_YIELD_FAITH | 2 | 14.600000381 | refuse |
| Colosseum | X10_COLOSSEUM_YIELD_CULTURE | 2 | 14.600000381 | refuse |
| Etemenanki | X10_ETEMENANKI_YIELD_SCIENCE | 2 | 14.600000381 | refuse |
| Great Library | X10_GREAT_LIBRARY_YIELD_SCIENCE | 2 | 14.600000381 | refuse |
| Mont St Michel | X10_MONT_ST_MICHEL_YIELD_FAITH | 2 | 14.600000381 | refuse |
| Potala Palace | X10_POTALA_PALACE_YIELD_CULTURE | 2 | 14.600000381 | refuse |
| Pyramids | X10_PYRAMIDS_YIELD_CULTURE | 2 | 14.600000381 | refuse |
| Stonehenge | X10_STONEHENGE_YIELD_FAITH | 2 | 14.600000381 | refuse |
| Colossus | X10_COLOSSUS_YIELD_GOLD | 3 | 21.900000572 | refuse |
| Great Lighthouse | X10_GREAT_LIGHTHOUSE_YIELD_GOLD | 3 | 21.900000572 | refuse |
| Meenakshi | X10_MEENAKSHI_TEMPLE_YIELD_FAITH | 3 | 21.900000572 | refuse |
| Potala Palace | X10_POTALA_PALACE_YIELD_FAITH | 3 | 21.900000572 | refuse |
| Statue of Zeus | X10_STATUE_OF_ZEUS_YIELD_GOLD | 3 | 21.900000572 | refuse |
| Sankore | X10_UNIVERSITY_SANKORE_YIELD_SCIENCE | 3 | 21.900000572 | refuse |
| Cristo Redentor | X10_CRISTO_REDENTOR_YIELD_CULTURE | 4 | 29.200000763 | refuse |
| Hagia Sophia | X10_HAGIA_SOPHIA_YIELD_FAITH | 4 | 29.200000763 | refuse |
| Jebel Barkal | X10_JEBEL_BARKAL_YIELD_FAITH | 4 | 29.200000763 | refuse |
| Machu Picchu | X10_MACHU_PICCHU_YIELD_GOLD | 4 | 29.200000763 | refuse |
| Mahabodhi | X10_MAHABODHI_TEMPLE_YIELD_FAITH | 4 | 29.200000763 | refuse |
| Orszaghaza | X10_ORSZAGHAZ_YIELD_CULTURE | 4 | 29.200000763 | refuse |
| Temple of Artemis | X10_TEMPLE_ARTEMIS_YIELD_FOOD | 4 | 29.200000763 | refuse |
| Forbidden City | X10_FORBIDDEN_CITY_YIELD_CULTURE | 5 | 36.500000954 | refuse |
| Great Zimbabwe | X10_GREAT_ZIMBABWE_YIELD_GOLD | 5 | 36.500000954 | refuse |
| Torre de Belem | X10_TORRE_DE_BELEM_YIELD_GOLD | 5 | 36.500000954 | refuse |
| Big Ben | X10_BIG_BEN_YIELD_GOLD | 6 | 43.800001144 | refuse |
| Estadio Maracana | X10_ESTADIO_DO_MARACANA_YIELD_CULTURE | 6 | 43.800001144 | refuse |
| Sydney Opera House | X10_SYDNEY_OPERA_HOUSE_YIELD_CULTURE | 8 | 58.400001526 | refuse |
| **Panama Canal** | **X10_PANAMA_CANAL_YIELD_GOLD** | **10** | **73.000001907** | **write** |

30 of 31 become refusals at the live stored-FLOAT32 k=7.3; Panama Canal
(10 → 73) stays eligible, confirming the gate rather than a blanket block.
At the default k=10 **all 31** write exactly (10, 20, 30, 40, 50, 60, 80, 100);
at k=7.5 the even-valued rows write (2 → 15 etc., 19 of 31).

### Deliberately out of scope (documented follow-up)

21 live-validated Release-1 entries share this effect under the player-scoped
carrier `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_YIELD_CHANGE`
(`TRAIT_IKANDA_*` ×10, `THIRDALTERNATIVE_*` ×10,
`MILITARYRESEARCH_*` ×3; Amounts 1, 2, 4). The same engine truncation applies
to them, so they should receive the identical gate — but they belong to the
live-validated Release-1 core and changing them alters proven counts, so they
are recorded here for a separately reviewed change rather than folded into
Phase 3F. The rule table is already scoped by modifier type, so extending it
is a one-line rules edit plus a recount.
