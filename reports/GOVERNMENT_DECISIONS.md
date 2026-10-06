# Governments Decisions

Manifest: `manifests/governments.yml` (121 rows: 72 ok, 0 refused, 49 undecided).

| Object | Modifier | Argument | Official | Family | Decision |
|---|---|---|---|---|---|
| `GOVERNMENT_FASCISM` | `FASCISM_WAR_WEARINESS` | `Overall` | 1 | UNKNOWN | undecided |
| `GOVERNMENT_CHIEFDOM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_CHIEFDOM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_AUTOCRACY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_AUTOCRACY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_AUTOCRACY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_AUTOCRACY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_OLIGARCHY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_OLIGARCHY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_OLIGARCHY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_CLASSICAL_REPUBLIC` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_CLASSICAL_REPUBLIC` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_CLASSICAL_REPUBLIC` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_MONARCHY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_MONARCHY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_MONARCHY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_MONARCHY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_THEOCRACY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_THEOCRACY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_THEOCRACY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_THEOCRACY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_MERCHANT_REPUBLIC` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_MERCHANT_REPUBLIC` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_MERCHANT_REPUBLIC` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_MERCHANT_REPUBLIC` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_FASCISM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_FASCISM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_FASCISM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_FASCISM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_COMMUNISM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_COMMUNISM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_COMMUNISM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_COMMUNISM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_DEMOCRACY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_DEMOCRACY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_DEMOCRACY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_DEMOCRACY` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_CORPORATE_LIBERTARIANISM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_CORPORATE_LIBERTARIANISM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |
| `GOVERNMENT_CORPORATE_LIBERTARIANISM` | `` | `GovernmentSlotType slots` |  | UNKNOWN | undecided |

Full manifest is machine-readable; this report shows only rows needing humans.
Refused rows are never emitted as SQL (boolean unlocks, structural slots).
Undecided rows are the short human queue — no silent enhancements.

<!-- CURATED-BELOW (preserved across review regenerations) -->
## Policy slots: explicit design decision (evidence, not a number)

Observed in the official DB (Government_SlotCounts, 48 rows): per-type
counts range 1-5; the largest single entry is 5 (SLOT_WILDCARD in
Corporate Libertarianism, Digital Democracy, Synthetic Technocracy).
A literal x10 would yield up to 50 wildcard slots. No schema CHECK cap
was found and no UI maximum is evidenced in the database, so no
TECHNICAL_CLAMP value can be derived. Classification: DECISION_REQUIRED.
No reduced slot count is chosen for balance.

