# Pantheon Semantic Audit (Phase 2)

Source of truth: the authoritative clean official database
(`DebugGameplay_official.sqlite`, OFFICIAL_RUNTIME_BASELINE copy):
23 rows in `Beliefs` with `BeliefClassType='BELIEF_CLASS_PANTHEON'`.
Machine-readable dispositions: `civ6x10/rules/pantheon_audit.yml`
(23 beliefs, every production row mapped, every rationale individual).
Inventory: `data/local/pantheon_effects.csv` (108 rows, via
`python -m civ6x10 inventory-pantheons --db <official-copy>`).
Manifest: `manifests/pantheons.yml` (108 rows: 101 ok incl. 67 selectors,
2 refused booleans, 5 undecided era/flag rows).

## Per-pantheon dispositions

| Pantheon | Effect | X10 interpretation | Mechanism | Disposition |
|---|---|---|---|---|
| City Patron Goddess | district production +25% | percent magnitude | ADDITIVE | CERTIFIED_NUMERIC |
| Dance of the Aurora | tundra + tundra-hills holy-site faith +1 ×2 | per-plot yields | ADDITIVE ×2 | CERTIFIED_NUMERIC |
| Desert Folklore | desert + desert-hills holy-site faith +1 ×2 | per-plot yields | ADDITIVE ×2 | CERTIFIED_NUMERIC |
| Divine Spark | great prophet/scientist/writer points +1 ×3 | whole GPP | ADDITIVE conditional | CERTIFIED_COUNT_LIKE ×3 |
| Earth Goddess | breathtaking-appeal plot faith +1 | plot yield (mixed override) | ADDITIVE | CERTIFIED_NUMERIC |
| Fertility Rites | free Builder | object grant | — | EXCLUDED (grant) |
| Fertility Rites | city growth +10% | growth percent | ADDITIVE | CERTIFIED_NUMERIC |
| Goddess of Festivals | plantation culture +1 | plot yield (mixed override) | ADDITIVE | CERTIFIED_NUMERIC |
| Goddess of Fire | volcanic plot faith +2 | plot yield (mixed override) | ADDITIVE | CERTIFIED_NUMERIC |
| Goddess of the Hunt | camp food +1, camp production +1 | plot yields (mixed override) | ADDITIVE ×2 | CERTIFIED_NUMERIC |
| God of Craftsmen | improved-strategic faith +1, production +1 | plot yields (mixed override) | ADDITIVE ×2 | CERTIFIED_NUMERIC |
| God of Healing | unit healing +30/turn | flat heal-rate magnitude | ADDITIVE | CERTIFIED_NUMERIC |
| God of the Forge | ancient/classical military production +25% | production percent (era bounds are selectors) | ADDITIVE | CERTIFIED_NUMERIC |
| God of the Open Sky | pasture culture +1 | plot yield (mixed override) | ADDITIVE | CERTIFIED_NUMERIC |
| God of the Sea | fishing-boat production +1 | plot yield (mixed override) | ADDITIVE | CERTIFIED_NUMERIC |
| God of War | faith per kill, 50% defeated-strength | overkill-margin scaling | — | EXCLUDED (defeated-strength, preserved DECISION_REQUIRED) |
| Initiation Rites | +50 faith on disperse, +100 heal on disperse | flat magnitudes | ADDITIVE ×2 | CERTIFIED_NUMERIC |
| Lady of the Reeds | marsh/oasis production +2 | plot yield (mixed override) | ADDITIVE | CERTIFIED_NUMERIC |
| Monument to the Gods | ancient/classical wonder production +15% | production percent (era/IsWonder selectors) | ADDITIVE | CERTIFIED_NUMERIC |
| Religious Idols | bonus-mine + luxury-mine faith +2 ×2 | plot yields (mixed override) | ADDITIVE ×2 | CERTIFIED_NUMERIC |
| Religious Settlements | border expansion +15 | expansion-rate magnitude | ADDITIVE | CERTIFIED_NUMERIC |
| Religious Settlements | free Settler | object grant | — | EXCLUDED (grant) |
| River Goddess | riverside holy-site amenity +2, housing +2 | amenity/housing magnitudes | ADDITIVE ×2 | CERTIFIED_NUMERIC |
| Sacred Path | jungle holy-site faith +1 | per-plot yield | ADDITIVE | CERTIFIED_NUMERIC |
| Stone Circles | quarry faith +2 | plot yield (mixed override) | ADDITIVE | CERTIFIED_NUMERIC |

Tallies: 23 pantheons — 20 completely supported, 3 partially supported
(Fertility Rites, God of War, Religious Settlements: one excluded numeric
each), 0 bespoke pending (no repetition mechanics required; every magnitude
is a single numeric argument). Native rows added: 31 (28 unconditional +
3 count-like). Excluded numerics: 2 object grants + 1 defeated-strength.

## Goddess of Festivals (resolved)

The historical mod (Workshop 938733933) targets
`GODDESS_OF_FESTIVALS_PLANTATION_TAG_FOOD_MODIFIER`, which matches **zero
rows** in the current clean database — a stale 2017-era ID, so its
`UPDATE ... WHERE ModifierId = ...` was a silent no-op. The live pantheon is
`GODDESS_OF_FESTIVALS_PLANTATION_CULTURE_MODIFIER` (+1 culture on
plantations). Disposition: neither omission of intent nor nonmultipliable —
a technical limitation of the old SQL mod (exact-ID matching with no
zero-row guard). Current disposition: CERTIFIED_NUMERIC (plot culture +1).

## Historical-mod coverage, reconfirmed on the current database

Running the old mod's 47 named ModifierIds against current numeric
definitions: **22/23 pantheons** have ≥1 numeric touched (reconfirms the
earlier audit; Festivals is the sole untouched pantheon). Caveats the old
count hides: Divine Spark 1/3, Hunt 1/2, Initiation 1/2 touched; Monument
targets wonder-specific IDs that no longer exist; Oral Tradition and
Goddess of the Harvest sections target content absent from the official
database entirely. Our bar is stricter: every numeric individually disposed
above. Nothing from the workshop mod (IDs, SQL, assets) is used as source
data — behavioral reference only.
