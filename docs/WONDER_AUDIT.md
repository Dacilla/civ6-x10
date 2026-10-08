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
