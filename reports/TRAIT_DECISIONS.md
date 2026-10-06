# Traits Decisions

Manifest: `manifests/traits.yml` (1520 rows: 1139 ok, 15 refused, 366 undecided).

| Object | Modifier | Argument | Official | Family | Decision |
|---|---|---|---|---|---|
| `TRAIT_CIVILIZATION_BUILDING_FILM_STUDIO` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_FOUNDING_FATHERS` | `TRAIT_ALL_DIPLO_POLICY_ARE_WILDCARDS` | `ReplacesAll` | 1 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_UNIT_AMERICAN_P51` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_BUILDING_MADRASA` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_LAST_PROPHET` | `TRAIT_SCIENCE_PER_FOREIGN_CITY_FOLLOWING_RELIGION` | `PerXItems` | 1 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_UNIT_ARABIAN_MAMLUK` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_IMPROVEMENT_OUTBACK_STATION` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_LAND_DOWN_UNDER` | `TRAIT_BREATHTAKING_CAMPUS` | `RequiredAppeal` | 4 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_LAND_DOWN_UNDER` | `TRAIT_BREATHTAKING_COMMERCIAL_HUB` | `RequiredAppeal` | 4 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_LAND_DOWN_UNDER` | `TRAIT_BREATHTAKING_HOLY_SITE` | `RequiredAppeal` | 4 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_LAND_DOWN_UNDER` | `TRAIT_BREATHTAKING_THEATER_DISTRICT` | `RequiredAppeal` | 4 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_LAND_DOWN_UNDER` | `TRAIT_CHARMING_CAMPUS` | `RequiredAppeal` | 2 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_LAND_DOWN_UNDER` | `TRAIT_CHARMING_COMMERCIAL_HUB` | `RequiredAppeal` | 2 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_LAND_DOWN_UNDER` | `TRAIT_CHARMING_HOLY_SITE` | `RequiredAppeal` | 2 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_LAND_DOWN_UNDER` | `TRAIT_CHARMING_THEATER_DISTRICT` | `RequiredAppeal` | 2 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_UNIT_DIGGER` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_BUILDING_TLACHTLI` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_UNIT_AZTEC_EAGLE_WARRIOR` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_BUILDING_PALGUM` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_UNIT_BABYLONIAN_SABUM_KIBITTUM` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_BARBARIAN` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_BARBARIAN_BUT_SHOWS_UP_IN_PEDIA` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_STREET_CARNIVAL` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_UNIT_BRAZILIAN_MINAS_GERAES` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_UNIT_BYZANTINE_DROMON` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_FACES_OF_PEACE` | `TRAIT_EMERGENCY_FAVOR_MODIFIER` | `Member` | 1 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_FACES_OF_PEACE` | `TRAIT_NO_SUPRISE_WAR_FOR_CANADA` | `Banned` | 1 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_FACES_OF_PEACE` | `TRAIT_TOURISM_INTO_FAVOR` | `Favor` | 1 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_IMPROVEMENT_ICE_HOCKEY_RINK` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_UNIT_CANADA_MOUNTIE` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_IMPROVEMENT_GREAT_WALL` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_UNIT_CHINESE_CROUCHING_TIGER` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_CREE_TRADE_GAIN_TILES` | `TRAIT_POTTERY_ADD_TRADER` | `AllowUniqueOverride` | 0 | BOOLEAN_UNLOCK | refused |
| `TRAIT_CIVILIZATION_CREE_TRADE_GAIN_TILES` | `TRAIT_TRADE_GAIN_TILES_EN_ROUTE` | `GainTileRadius` | 3 | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_IMPROVEMENT_MEKEWAP` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_UNIT_CREE_OKIHTCITAW` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_IMPROVEMENT_SPHINX` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_UNIT_EGYPTIAN_CHARIOT_ARCHER` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_ROYAL_NAVY_DOCKYARD` | `` | `` |  | UNKNOWN | undecided |
| `TRAIT_CIVILIZATION_UNIT_ENGLISH_SEADOG` | `` | `` |  | UNKNOWN | undecided |

Full manifest is machine-readable; this report shows only rows needing humans.
Refused rows are never emitted as SQL (boolean unlocks, structural slots).
Undecided rows are the short human queue — no silent enhancements.

<!-- CURATED-BELOW (preserved across review regenerations) -->
## Named human decision: Scythia / Saka Horse Archer

The existing mod rewrites the Saka Horse Archer as
Cost 100->260, Combat 20->1, Range 1->10 (a redesign, not a multiplier).
This project does NOT copy that redesign. The unit's numeric fields are
canonical-x10-eligible per-field, but the combined effect is a game-design
choice and stays in the human queue until decided.

