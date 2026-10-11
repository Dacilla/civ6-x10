<!-- GENERATED from civ6x10/rules/support_frontier.yml by spike/8a-frontier/projection.py; do not hand-edit. Pasted verbatim into docs/SUPPORT_FRONTIER.md. -->

### Table N1 — disposition totals in ROOT_OCCURRENCES (root table, ModifierId, argument)

| disposition | root occurrences |
|---|---|
| STRONG_CANDIDATE | 432 |
| CANDIDATE_COUNT_LIKE | 178 |
| NEEDS_SEMANTIC_RESEARCH | 132 |
| NEEDS_PRODUCT_DECISION | 270 |
| GLOBAL_OR_CROSS_PLAYER_LEAKAGE | 355 |
| EXISTING_AUDIT_EXCLUDED | 106 |
| STRUCTURAL_OR_FILTER | 481 |
| COST_OR_PRICE | 0 |
| TIMER_OR_DURATION | 37 |
| BASE_STAT_NOT_BONUS | 0 |
| MODE_SYSTEM_MECHANIC | 0 |
| NO_MEANINGFUL_MULTIPLIER_TARGET | 11 |
| ALREADY_SUPPORTED | 956 |
| TOTAL | 2958 |

### Table N2 — disposition totals in UNIQUE_DEFINITIONS (ModifierId, argument, cross-root deduplicated)

| disposition | unique definitions |
|---|---|
| STRONG_CANDIDATE | 432 |
| CANDIDATE_COUNT_LIKE | 176 |
| NEEDS_SEMANTIC_RESEARCH | 131 |
| NEEDS_PRODUCT_DECISION | 270 |
| GLOBAL_OR_CROSS_PLAYER_LEAKAGE | 355 |
| EXISTING_AUDIT_EXCLUDED | 106 |
| STRUCTURAL_OR_FILTER | 479 |
| COST_OR_PRICE | 0 |
| TIMER_OR_DURATION | 37 |
| BASE_STAT_NOT_BONUS | 0 |
| MODE_SYSTEM_MECHANIC | 0 |
| NO_MEANINGFUL_MULTIPLIER_TARGET | 11 |
| ALREADY_SUPPORTED | 931 |
| TOTAL | 2928 |

### Table N3 — definition-level actionable count (PROPOSED_PRODUCTION_PAIRS)

ACTIONABLE_UNIQUE_DEFINITIONS = 608
COVERAGE_DENOMINATOR = 1010 production pairs

### Table N4 — definition-level dispositions by proposed module (UNIQUE_DEFINITIONS)

| proposed module | unique defs | strong | count-like | research | product-dec | global | prior-excl | structural+other | supported |
|---|---|---|---|---|---|---|---|---|---|---|
| Already supported | 931 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 931 |
| Cross-module:Infrastructure+Tech/Civic | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| Eras | 38 | 13 | 25 | 0 | 0 | 0 | 0 | 0 | 0 |
| Eras & Diplomacy | 100 | 35 | 16 | 0 | 20 | 29 | 0 | 0 | 0 |
| Existing Governors module | 11 | 1 | 1 | 8 | 0 | 1 | 0 | 0 | 0 |
| Existing Policies module | 6 | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| Existing Traits module | 46 | 40 | 5 | 1 | 0 | 0 | 0 | 0 | 0 |
| Great People | 113 | 73 | 40 | 0 | 0 | 0 | 0 | 0 | 0 |
| Infrastructure | 141 | 0 | 0 | 0 | 141 | 0 | 0 | 0 | 0 |
| Minor City-States | 93 | 0 | 0 | 0 | 93 | 0 | 0 | 0 | 0 |
| None | 527 | 0 | 0 | 0 | 0 | 0 | 0 | 527 | 0 |
| None (global) | 2 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |
| None (never) | 323 | 0 | 0 | 0 | 0 | 323 | 0 | 0 | 0 |
| None (product call) | 15 | 0 | 0 | 0 | 15 | 0 | 0 | 0 | 0 |
| Other:system:buildingmodifiers | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Prior exclusions | 106 | 0 | 0 | 0 | 0 | 0 | 106 | 0 | 0 |
| Projects | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Promotions & Abilities | 257 | 205 | 52 | 0 | 0 | 0 | 0 | 0 | 0 |
| Religion | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Research pool | 122 | 0 | 0 | 122 | 0 | 0 | 0 | 0 | 0 |
| Tech/Civic | 18 | 7 | 11 | 0 | 0 | 0 | 0 | 0 | 0 |
| Tribal Villages | 22 | 8 | 14 | 0 | 0 | 0 | 0 | 0 | 0 |
| Wonders module | 18 | 7 | 11 | 0 | 0 | 0 | 0 | 0 | 0 |

SHARED_DEFINITIONS (multi-root) = 30

### Table N5 — per-mode discovery split (DISCOVERY ROWS, not candidates)

| mode | triples | unique pairs | numeric-scalar | structural/selector | in-registry | mode-only | candidates |
|---|---|---|---|---|---|---|---|---|
| apocalypse | 64 | 24 | 8 | 16 | 0 | 24 | PENDING |
| barbarian_clans | 0 | 0 | 0 | 0 | 0 | 0 | PENDING |
| dramatic_ages | 435 | 149 | 70 | 79 | 8 | 141 | PENDING |
| heroes_legends | 394 | 163 | 48 | 115 | 0 | 163 | PENDING |
| monopolies_corporations | 432 | 125 | 51 | 74 | 0 | 125 | PENDING |
| secret_societies | 391 | 134 | 39 | 95 | 22 | 112 | PENDING |
| tech_civic_shuffle | 0 | 0 | 0 | 0 | 0 | 0 | NONE_NO_TARGET |
| zombie_defense | 105 | 42 | 3 | 39 | 0 | 42 | PENDING |

Mode-level STRONG_CANDIDATE means the mode is worth a dedicated Phase-8 audit; overlay pair counts are discovery rows, not production candidates.
