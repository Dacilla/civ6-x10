# Unified Unresolved-Semantic Backlog (Phase 6A)

Regenerate with `python -m civ6x10 build-backlog`
(defaults: `civ6x10/rules/governor_audit.yml` +
`civ6x10/rules/suzerain_audit.yml` → `civ6x10/rules/semantic_backlog.yml`).

**RESEARCH ONLY — nothing here is production.** The 971-entry registry,
manifests, owner bits, native code and DLL are untouched. Resolved
candidates are a PROPOSAL for a later Phase 6B, which must land the recorded
gate evidence atomically with the rows and re-validate.

## 1. Imported scope (mechanically derived, no hand-copying)

| source | imported |
|---|---|
| Governor reachable `DECISION_REQUIRED` | 29 |
| Governor direct/structural `DECISION_REQUIRED` | 24 |
| Suzerain main-graph numeric `DECISION_REQUIRED` | 21 |
| Suzerain side-path `DECISION_REQUIRED` | 68 |
| **total** | **142** |

(Suzerain's 6 excluded numerics and all excluded selectors stay excluded as
audited; Toqui's held-out pair is excluded in production and is handled in
§9, not in the 142.)

## 2. Resolution summary

| resolution | count |
|---|---|
| `RESOLVED_CANDIDATE` | 10 |
| `RESOLVED_CANDIDATE_COUNT_LIKE` | 22 |
| `RESOLVED_EXCLUDED` | 25 |
| `NEEDS_LIVE_PROBE` | 6 (+2 Toqui, §9) |
| `NEEDS_PRODUCT_DECISION` | 58 |
| `STILL_SEMANTICALLY_UNRESOLVED` | 21 |

By problem group:

| group | resolutions |
|---|---|
| whole-unit / count-like magnitudes | 22 count-like |
| grant-on-completion percentages | 2 candidates |
| purchase discounts | 3 candidates |
| spy-yield percentages | 4 candidates |
| combat-strength edge cases | 1 candidate (Lahore +10), 1 excluded (Sanguine −5) |
| healing semantics | 2 excluded |
| grievance score / duration | 1 excluded (Turns), 1 unresolved (Score) |
| loyalty / identity / religious pressure | 6 probe, 12 unresolved (direct columns) |
| multiplicative / ScalingFactor | 8 unresolved |
| unique-object ownership | 58 product-decision, 9 excluded (intrinsic) |
| direct structural/internal Governor fields | 12 excluded (TransitionStrength) |

## 3. Whole-unit / count-like family (22 → candidates)

One cross-module rule: **a genuinely quantitative whole-unit argument is a
`FLAT_AMOUNT` scalar under the existing exact-integrality policy**
(integer k=10 applies; stored FLOAT32 k=7.3 refuses fractions; never
round/floor/ceil). No new formula. Precedent: PUBLICWORKS/SERFDOM/PYRAMID/
TRAIT builder charges, BIOSPHERE free power, SNOW/TUNDRA extraction and
stockpile caps — all live as `curated-category:FLAT_AMOUNT` count-like.

| rows | evidence |
|---|---|
| Guildmaster +1, vampire +2/+1/+1 charges | same exact tuple as the 4 live precedents |
| Patron Saint +1 promotion, Defense Logistics +1 accumulation, Embrasure +1 attack, Khass +2 alliance, Informants +3 spy levels, Industrialist +1 power | whole-unit flows; Khass/Informants patterns already exist |
| Cardiff +2 power ×3 | `FREE_POWER` pattern exists (BIOSPHERE precedent) |
| Hattusa +2 ×7, Zanzibar +1 ×2 | new `FREE_RESOURCE_IMPORT` pattern proposed (blast radius: exactly those two effects) |

Engine limits reviewed (`GlobalParameters`): `COMBAT_MAX_NUM_ATTACKS=1` is
the base default that Embrasure itself already raises — no hard cap makes
11 attacks invalid; no spy/promotion/power caps exist. Oversized results are
"merely very large", never invalid. Saturation (e.g. spy ranks) at most.

**Load-bearing gate note (verified by dry run):** Patron Saint, Defense
Logistics, Embrasure, Industrialist, Hattusa and Zanzibar currently
certify *unconditional* (no matching pattern) — exactly as Corporate
Libertarianism does today. The proposed `count_like_effects` additions
(`RELIGION_EXTRA_PROMOTIONS`, `EXTRA_ACCUMULATION`, `ATTACKS_PER_TURN`,
`RESOURCE_POWER_PROVIDED`, `FREE_RESOURCE_IMPORT`) must land WITH the rows
in 6B. Blast-radius exception: `EXTRA_ACCUMULATION` also matches the
`_FOR_STRATEGIC_DIVERSITY` / `_SPECIFIC_RESOURCE` siblings, whose
`TRAIT_ACCUMULATE_MORE_COAL/_IRON` rows ship unconditional today — 6B must
review flipping them as an intended fix, not a silent side effect.

**Zanzibar utility caveat:** duplicate luxuries do not normally stack
amenities, so 10 granted copies may not yield 10× benefit. The *quantity*
scales; the *utility* may not. Flagged for product awareness, not blocking
the quantity candidacy.

## 4. Valletta verdict: RESOLVED (PERCENT_DISCOUNT, compound)

`EFFECT_ADJUST_BUILDING_PURCHASE_COST`, Amount **+50** ×3 — **the task's
"−50" and the audit reason's "−50" are both errata; the DB holds +50
(verified in `ModifierArguments`)**, same sign class as Ngazargamu's +20
(the audit's "−20" prose likewise). Positive-means-discount is proven
cross-effect: both IDs name `CHEAPER`/`BONUS` benefits (flat subtraction
would make Valletta a surcharge), Valletta pairs with faith-purchase
enablers for the known 50% defensive-building discount, and
`FLOWER_POWER_PURCHASE_INCREASE Amount=-100` is the surcharge mirror
(negative = cost increase). Family `PERCENT_DISCOUNT`, existing
`DISCOUNT`/compound transform. **At k=10 the value is 99.90, at k=7.3 it is
99.37 — never ±500.** Requires a 6B `discount_effects` entry (effect-scoped;
blast radius: Valletta ×3 only — the gate fails closed without it, verified
by dry run). Proposed patch ships in `semantic_backlog.yml`
(`proposed_gate_evidence`), NOT applied to production.

## 5. Citadel / Ayutthaya verdict: RESOLVED (PERCENT_BONUS, additive)

Both use `EFFECT_GRANT_CITY_YIELD_PERCENT_BUILDING_CREATED_COST` with
`BuildingProductionPercent` 25 (faith) / 10 (culture). Four carriers share
the shape — Citadel, Ayutthaya, Ramses −15 (buildings) and Ramses +30
(wonders, `IncludeWonder=1`). A **signed** penalty/bonus mix at one argument
is only coherent as a percent of production cost, and the ModifierType
literally names `GRANT_YIELD_PER_BUILDING_COST`. Family `PERCENT_BONUS`,
kind `ADDITIVE`, canonical multiply (25→250 / 10→100; float-safe percents:
182.5/73.0 at k=7.3). No transform design fork: additive percent scaling is
the established reading (Geneva precedent). Requires a 6B `mixed_overrides`
entry (same shape as the two live ones; the floor's `GRANT_OBJECT` row is
`AUTO_PATTERN` heuristic and currently excludes the rows — verified by dry
run). `IncludeWonder` stays a structural boolean. Ramses rows corroborate
only; Ramses is out of production scope and stays out.

## 6. Loyalty / identity / religious pressure verdict: NEEDS_LIVE_PROBE

Five distinct engine EffectTypes — **not** assumed to share storage:

| effect | rows | official |
|---|---|---|
| `EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE` (Toqui, held) | 2 | 4 |
| `EFFECT_ADJUST_CITY_RELIGION_PRESSURE` | 1 (Bishop) | 100 |
| `EFFECT_ADJUST_CITY_IDENTITY_PER_TURN` | 4 (Owls 4, Preslav 2×3) | 4 / 2 |
| `EFFECT_GRANT_PLAYER_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED` | 1 (Vatican) | 400 |
| direct Governor `IdentityPressure` columns | 12 | 8 / 10 |

What blocks the four modifier effects is **observability, not semantics**:
the Toqui hold proved one pressure effect reads back blank post-Add, and no
sibling has a stored MATCH on record. The disposable probe in
`spike/toqui-probe/` (scratch 8-entry registry + readback + exact
build/swap/run/restore instructions) answers all eight at once. **A live
probe is genuinely required** — definitions only populate inside Civ VI —
so Phase 6A stops at preparation; the probe is not built, installed, or run
here, and the validated 971 build is untouched. Direct `IdentityPressure`
columns stay `STILL_SEMANTICALLY_UNRESOLVED` (magnitude confirmed as loyalty
class, but no modifier carrier path exists and the family hold is open).

## 7. Healing verdict: RESOLVED_EXCLUDED (both rows)

`CARDINAL_LAYING_ON_OF_HANDS_HEAL` and `..._RELIGIOUS_HEAL`, Amount=100:
`COMBAT_MAX_HIT_POINTS=100` (`GlobalParameters`, official DB) — units max
out at 100 HP, so +100 HP/turn is already a **full heal every turn**. 1000
HP/turn heals nothing extra. Both are full-heal caps/sentinels, not
scalable magnitudes. Single carriers each; no corroborating usage. The gate
*would* admit these as flat HP (verified by dry run) — which is exactly why
audit judgment, not the gate, must exclude them. Permanent until heal
policy changes. (Not classified as flat 100 HP merely from the argument
name.)

## 8. ScalingFactor verdict: semantics ESTABLISHED, unshippable without a new transform

19 tourism carriers + Kandy relic: values 150/200/300 track 1.5×/2×/3× game
behavior (Curator doubles, Reliquaries/GreatPerson triple, Cristo/Heritage/
Printing/StBasil's double, Commemoration 1.5×) — the bonus-only reading
fits none of them, so **ScalingFactor is base-inclusive percent
(100 = 1×)**. Consequence: canonical multiply is *wrong* for this shape
(200 → 2000 is 20× total = 19× bonus, not 10× bonus); correct scaling is
offset-aware, `100 + 10×(v−100)` → 200→1100, 150→600, 300→2100. That
transform does not exist in native code, and Phase 6A manufactures no
transforms. All 8 rows stay `STILL_SEMANTICALLY_UNRESOLVED` with the analysis
recorded; resolution needs (a) offset-aware transform design + native
support, (b) product sign-off. Same rule covers Black Marketeer's
single-carrier 80 only negatively: percent plausible, sign convention
unproven, no siblings — unresolved, never multiplied for resembling a
percent.

## 9. Negative-combat verdict: RESOLVED_EXCLUDED_UNSUPPORTED_TRANSFORM

Sanguine intimidate −5: `b_k = 25·ln(k·(e^(b/25)−1)+1)` has inner terms
−0.3233 (k=7.3) and −0.8127 (k=10) — log-domain errors at both production
multipliers (verified numerically). No principled penalty dual exists
within the project's combat semantics (the transform preserves tenfold
*damage* for *bonuses*). No ad hoc negative formula invented. Note the
subtlety the dry run exposed: the gate *certifies* the row
(formula-derived floor ignores value sign), so this exclusion must live at
the manifest/audit layer — which is what this resolution records.
Explicit and permanent until transform policy changes.

## 10. Lahore +10 verdict: RESOLVED_CANDIDATE (COMBAT)

`NIHANG_SUZERAIN_COMBAT_BONUS`, Amount=+10, `COMBAT_STRENGTH_BONUS`:
`PLAYER_HAS_LAHORE_SUZERAIN_REQUIREMENTS`
(`REQUIREMENT_PLAYER_IS_SUZERAIN_OF_X` → Lahore) proves the magnitude
exists only under Lahore Suzerain status — qualitatively different from the
intrinsic +15s. Floor is `FORMULA_DERIVED` for the tuple: gate passes today,
no rule change. Proposed 6B `COMBAT` candidate, canonical transform
(38.10 at k=7.3, 44.45 at k=10), owner suzerain. Intrinsic Barracks/Armory/
Academy +15, movement, flanking and post-combat faith stay outside Suzerain
ownership (no "10× the unlocked unit" decision taken).

## 11. Unique-improvement ownership table and recommendation

| improvement (city-state) | base yields | adjacency yields | housing / amenity / appeal | tourism / factor | if owned: candidate semantics | shared-scope leak? |
|---|---|---|---|---|---|---|
| Monastery (Armagh) | faith 2 | district faith 1 | housing 2, religious heal 15 | — | yields + housing + heal magnitudes | yes: conquered/city-state tiles |
| Batey (Caguana) | culture 1 | bonus-resource / entertainment culture 1→2 | — | ScalingFactor 100 | yields | yes |
| Mound (Cahokia) | food 0, gold 3 | district food 1 | housing 2, amenity (capped 1→2) | — | yields + housing + amenity | yes |
| Alcazar (Granada) | culture 2 | — | defense 4, appeal→science 50% | ScalingFactor 100 | yields + defense + appeal-% | yes |
| Colossal Head (La Venta) | culture 0, faith 2 | forest/jungle faith 1 | — | ScalingFactor 100 | yields | yes |
| Mahavihara (Nalanda) | faith 0, science 2 | campus/observatory science 1→2, holy-site/lavra faith 1 | housing 2 | — | yields + housing | yes |
| Nazca Line (Nazca) | — | faith/food/production 1 (5 defs) | appeal 1 | — | adjacency yields | yes |
| Moai (Rapa Nui) | culture 1 | self culture 1, coast/volcanic 1/2 | — | ScalingFactor 100 | yields | yes |
| Trading Dome (Samarkand) | gold 2 | luxury gold 1 | — | — | yields | yes |

Every improvement is a **global definition**: scaling it while the Suzerain
module is ON scales it for everyone holding those tiles — including a
conqueror who never earned suzerainty and the city-state itself. That
contradicts module ownership (the toggle must scope the benefit), and no
hybrid subset fixes conquest leakage (attached modifiers are global too).

**Recommendation: A — narrow ownership (ADOPTED for Phase-6B planning).**
The unlock remains a capability; intrinsic improvement data stays vanilla.
The Suzerain bonus is the 47 graph magnitudes. Option B (expanded) would
need an explicit human override accepting conquest leakage; it is NOT
taken here. All 58 cells stay `NEEDS_PRODUCT_DECISION` pending that human
call — this report recommends closing them as excluded-under-A when the
decision lands. Captured/pre-existing improvements must not become globally
stronger merely because the X10 Suzerain module is enabled.

## 12. TransitionStrength verdict: RESOLVED_EXCLUDED

12 direct Governor cells (100/150): `TransitionStrength` exists only on the
`Governors` table — no modifier carrier, no other table or definition
references it. Engine-internal transition weighting, never a user-facing
bonus. Structural; never scaled to maximize coverage.

## 13. Remaining Governor rows

- Capou Agha `Score=1` → `STILL_SEMANTICALLY_UNRESOLVED` (single carrier;
  grievance direction unknown — scaling could harm or help; `Turns=1` →
  `RESOLVED_EXCLUDED` as structural duration, floor agrees; one scalable
  sibling never drags a duration with it — each argument classified
  independently).
- Owls spy `Percent=50` ×4 → `RESOLVED_CANDIDATE` (Wu identical-tuple
  precedent; 365.0 at k=7.3, 500.0 at k=10).

## 14. Proposed Phase-6B candidate list (32 occurrences → 31 unique pairs)

10 unconditional (`owls×4` PERCENT_BONUS, Citadel/Ayutthaya PERCENT_BONUS,
Valletta×3 PERCENT_DISCOUNT, Lahore COMBAT) + 22 count-like occurrences
(charges ×4, Patron Saint, Defense Logistics, Embrasure, Khass, Informants,
Industrialist, Cardiff ×3, Hattusa ×7, Zanzibar ×2 — all `FLAT_AMOUNT`).
The vampire +1 build occurs under two promotions but mutates one definition,
so production sees **31 unique pairs** (14 Governor / 17 Suzerain; 10
non-count-like / 21 count-like; ADDITIVE 27 / DISCOUNT 3 / COMBAT 1).
Full per-row provenance, gate evidence, and k-expectations in
`semantic_backlog.yml` (`proposed_candidates` + `proposed_production_pairs`).
At k=7.3 the 21 unique count-like pairs all refuse (every official is 1/2/3);
at k=10 all apply. The three intentional existing reclassifications
(Corporate Libertarianism, Coal, Iron) move writes→refusals at k=7.3 and
must be live-validated explicitly in 6B.

## 15. No production changes (verified by test)

Registry stays 971 entries; CE fork `d17bdb6`; DLL `b6862b28…fb20d`;
both manifests, owner bits, and controller/native config unchanged —
asserted by `tests/test_semantic_backlog.py` (registry digest + file
digests + `MODULE_BITS`/`REGISTRY_MODULES` guards).
