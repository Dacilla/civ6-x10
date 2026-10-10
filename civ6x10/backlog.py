"""Phase 6A: unified unresolved-semantic backlog.

AUDIT / RESEARCH ONLY. Mechanically imports every unresolved row from the
checked-in Governor (`governor_audit.yml`) and Suzerain (`suzerain_audit.yml`)
audits — never hand-copied — groups rows by semantic problem instead of only
by module, and resolves each row to exactly one of:

  RESOLVED_CANDIDATE / RESOLVED_CANDIDATE_COUNT_LIKE / RESOLVED_EXCLUDED /
  NEEDS_LIVE_PROBE / NEEDS_PRODUCT_DECISION / STILL_SEMANTICALLY_UNRESOLVED

No row disappears: the builder fails closed if any imported unresolved row
has no resolution. Nothing here is production: resolved candidates are a
PROPOSAL for a later Phase 6B, which must add the recorded gate evidence
(curated patterns/overrides) and re-validate. The 971-entry registry,
manifests, owner bits, native code and DLL are untouched by this module
(it cannot touch them: it only reads the two audit YAMLs and writes the
backlog artifact + proposed evidence patch).
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

# Resolution categories (closed world: every imported row gets exactly one).
RESOLVED_CANDIDATE = "RESOLVED_CANDIDATE"
RESOLVED_CANDIDATE_COUNT_LIKE = "RESOLVED_CANDIDATE_COUNT_LIKE"
RESOLVED_EXCLUDED = "RESOLVED_EXCLUDED"
NEEDS_LIVE_PROBE = "NEEDS_LIVE_PROBE"
NEEDS_PRODUCT_DECISION = "NEEDS_PRODUCT_DECISION"
STILL_SEMANTICALLY_UNRESOLVED = "STILL_SEMANTICALLY_UNRESOLVED"

RESOLUTIONS = frozenset({
    RESOLVED_CANDIDATE, RESOLVED_CANDIDATE_COUNT_LIKE, RESOLVED_EXCLUDED,
    NEEDS_LIVE_PROBE, NEEDS_PRODUCT_DECISION, STILL_SEMANTICALLY_UNRESOLVED,
})

# Problem groups (cross-module; each row keeps its module/root provenance).
GROUP_COUNT_LIKE = "whole-unit / count-like magnitudes"
GROUP_COMPLETION = "grant-on-completion percentages"
GROUP_DISCOUNT = "purchase discounts"
GROUP_PRESSURE = "loyalty / identity / religious pressure"
GROUP_HEALING = "healing semantics"
GROUP_FACTOR = "multiplicative / ScalingFactor semantics"
GROUP_COMBAT_EDGE = "combat-strength edge cases"
GROUP_SPY_PERCENT = "spy-yield percentages"
GROUP_GRIEVANCE = "grievance score / duration"
GROUP_OWNERSHIP = "unique-object ownership"
GROUP_DIRECT = "direct structural/internal Governor fields"
GROUP_SPATIAL = "spatial/capability values"

# Rule fields: (resolution, group, family, kind, transform, count_like,
#   owner, required_gate_evidence, k73_note, k10_note, native_support,
#   rationale). A candidate always names an EXISTING production kind and
# transform with precedent; rules never invent transforms.
#
# Keyed by (effect_type, argument, cell_kind) with cell_kind in {"modifier",
# "direct", "improvement", "unit"}. Per-modifier overrides (below) win over
# tuple rules where a row's fate turns on its own requirement, value, or
# provenance.
RULES: dict[tuple[str, str, str], tuple] = {}


def _rule(resolution, group, family, kind, transform, count_like, owner,
          gate_evidence, k73, k10, native, rationale):
    return (resolution, group, family, kind, transform, count_like, owner,
            gate_evidence, k73, k10, native, rationale)


# --- whole-unit quantities -------------------------------------------------
# Precedent: PUBLICWORKS/SERFDOM/PYRAMID/TRAIT builder charges, BIOSPHERE
# free power, SNOW/TUNDRA extraction and stockpile caps all certify as
# curated-category:FLAT_AMOUNT; count-like follows from the CHARGES family
# or a count_like_effects pattern. Where no pattern exists yet, the 6A
# proposal records the exact pattern addition 6B must land WITH the row:
# the gate dry run proves these would otherwise certify unconditional (as
# Corporate Libertarianism does today), so the patterns are load-bearing.
RULES[("EFFECT_ADJUST_UNIT_BUILD_CHARGES", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE_COUNT_LIKE, GROUP_COUNT_LIKE, "FLAT_AMOUNT",
    "ADDITIVE", "canonical_x10_multiply", True, "governors",
    "none (CHARGES pattern already covers this effect; verified by gate "
    "dry run)",
    "refuses at stored FLOAT32 k=7.3 (1/2 x 7.3 fractional)",
    "applies integrally (10/20/10/10 by row)",
    "already supported (count-like integral gate is live)",
    "whole build charges (Guildmaster +1, vampire +2/+1/+1); matches the "
    "four live production precedents for this exact tuple, all "
    "curated-category:FLAT_AMOUNT count-like",
)
RULES[("EFFECT_ADJUST_CITY_RELIGION_EXTRA_PROMOTIONS", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE_COUNT_LIKE, GROUP_COUNT_LIKE, "FLAT_AMOUNT",
    "ADDITIVE", "canonical_x10_multiply", True, "governors",
    "6B must add count_like_effects pattern RELIGION_EXTRA_PROMOTIONS "
    "(blast radius: this exact effect only)",
    "refuses at stored FLOAT32 k=7.3 (1 x 7.3 fractional)",
    "applies integrally (10)",
    "already supported once the pattern lands (integral gate is live)",
    "whole extra religious promotions (Patron Saint +1); single carrier, "
    "whole-unit flow; no spy/promotion-count cap in GlobalParameters that "
    "invalidates the transform (saturation at most)",
)
RULES[("EFFECT_ADJUST_CITY_EXTRA_ACCUMULATION", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE_COUNT_LIKE, GROUP_COUNT_LIKE, "FLAT_AMOUNT",
    "ADDITIVE", "canonical_x10_multiply", True, "governors",
    "6B must add count_like_effects pattern EXTRA_ACCUMULATION "
    "(blast radius: also matches _FOR_STRATEGIC_DIVERSITY and "
    "_SPECIFIC_RESOURCE siblings; TRAIT_ACCUMULATE_MORE_COAL/_IRON are in "
    "production unconditional today and would flip to count-like — 6B must "
    "review that as an intended fix, not a silent side effect)",
    "refuses at stored FLOAT32 k=7.3 (1 x 7.3 fractional)",
    "applies integrally (10)",
    "already supported once the pattern lands (integral gate is live)",
    "whole strategic-resource accumulation per turn (Defense Logistics +1); "
    "same whole-unit class as the live CORPORATE_LIBERTARIANISM row "
    "(currently unconditional — noted as follow-up, not changed here)",
)
RULES[("EFFECT_ADJUST_CITY_ATTACKS_PER_TURN", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE_COUNT_LIKE, GROUP_COUNT_LIKE, "FLAT_AMOUNT",
    "ADDITIVE", "canonical_x10_multiply", True, "governors",
    "6B must add count_like_effects pattern ATTACKS_PER_TURN "
    "(blast radius: this exact effect only)",
    "refuses at stored FLOAT32 k=7.3 (1 x 7.3 fractional)",
    "applies integrally (10)",
    "already supported once the pattern lands (integral gate is live)",
    "whole city attacks per turn (Embrasure +1); COMBAT_MAX_NUM_ATTACKS=1 is "
    "the base default which Embrasure itself already raises, so no hard cap "
    "invalidates the transform — merely very large at k=10",
)
RULES[("EFFECT_ADJUST_GOVERNOR_ALLIANCE_POINTS", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE_COUNT_LIKE, GROUP_COUNT_LIKE, "FLAT_AMOUNT",
    "ADDITIVE", "canonical_x10_multiply", True, "governors",
    "none (ALLIANCE_POINTS pattern already covers this effect; verified by "
    "gate dry run)",
    "refuses at stored FLOAT32 k=7.3 (2 x 7.3 = 14.6 fractional)",
    "applies integrally (20)",
    "already supported (count-like integral gate is live)",
    "whole alliance points (Khass Oda Bashi +2); ALLIANCE_POINTS_FOR_DEAL=2 "
    "shows points move in whole units",
)
RULES[("EFFECT_ADJUST_CITY_SPY_BONUS", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE_COUNT_LIKE, GROUP_COUNT_LIKE, "FLAT_AMOUNT",
    "ADDITIVE", "canonical_x10_multiply", True, "governors",
    "none (SPY_BONUS pattern already covers this effect; verified by gate "
    "dry run)",
    "refuses at stored FLOAT32 k=7.3 (3 x 7.3 = 21.9 fractional)",
    "applies integrally (30)",
    "already supported (count-like integral gate is live)",
    "whole defensive-spy levels (Local Informants +3); no spy-level cap in "
    "GlobalParameters invalidates the transform (saturation at most); "
    "ESPIONAGE_* counterspy modifiers confirm level semantics",
)
RULES[("EFFECT_ADJUST_RESOURCE_POWER_PROVIDED_GOVERNOR", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE_COUNT_LIKE, GROUP_COUNT_LIKE, "FLAT_AMOUNT",
    "ADDITIVE", "canonical_x10_multiply", True, "governors",
    "6B must add count_like_effects pattern RESOURCE_POWER_PROVIDED "
    "(blast radius: this exact effect only)",
    "refuses at stored FLOAT32 k=7.3 (1 x 7.3 fractional)",
    "applies integrally (10)",
    "already supported once the pattern lands (integral gate is live)",
    "whole power units granted per turn (Industrialist +1); same whole-unit "
    "class as the live BIOSPHERE free-power precedent",
)
RULES[("EFFECT_ADJUST_CITY_FREE_POWER", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE_COUNT_LIKE, GROUP_COUNT_LIKE, "FLAT_AMOUNT",
    "ADDITIVE", "canonical_x10_multiply", True, "suzerain",
    "none (FREE_POWER pattern already covers this effect; verified by gate "
    "dry run)",
    "refuses at stored FLOAT32 k=7.3 (2 x 7.3 = 14.6 fractional)",
    "applies integrally (20)",
    "already supported (count-like integral gate is live)",
    "whole power units granted per turn (Cardiff +2 x3); matches the live "
    "BIOSPHERE_MODIFIED_FREE_POWER precedent (same family, count-like)",
)
RULES[("EFFECT_ADJUST_PLAYER_FREE_RESOURCE_IMPORT_EXTRACTION", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE_COUNT_LIKE, GROUP_COUNT_LIKE, "FLAT_AMOUNT",
    "ADDITIVE", "canonical_x10_multiply", True, "suzerain",
    "6B must add count_like_effects pattern FREE_RESOURCE_IMPORT (covers "
    "both Hattusa EXTRACTION and Zanzibar IMPORT effects; blast radius: "
    "exactly those two effects)",
    "refuses at stored FLOAT32 k=7.3 (2 x 7.3 = 14.6 fractional)",
    "applies integrally (20)",
    "already supported once the pattern lands (integral gate is live)",
    "whole strategic-resource units extracted per turn (Hattusa +2 x7); "
    "grant QUANTITY scales; intrinsic resource properties never claimed",
)
RULES[("EFFECT_ADJUST_PLAYER_FREE_RESOURCE_IMPORT", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE_COUNT_LIKE, GROUP_COUNT_LIKE, "FLAT_AMOUNT",
    "ADDITIVE", "canonical_x10_multiply", True, "suzerain",
    "6B must add count_like_effects pattern FREE_RESOURCE_IMPORT (same "
    "entry as Hattusa above)",
    "refuses at stored FLOAT32 k=7.3 (1 x 7.3 fractional)",
    "applies integrally (10)",
    "already supported once the pattern lands (integral gate is live)",
    "whole luxury-resource units granted (Zanzibar +1 cinnamon/cloves); "
    "PRODUCT-INTENT CAVEAT: duplicate luxuries do not normally stack "
    "amenities, so 10 granted copies may not yield 10x amenity benefit — "
    "the QUANTITY scales, the utility may not; flagged, not blocking",
)

# --- spy-yield percent (identical-tuple production precedent) ----------------
# WU_ZETIAN_OFFENSIVE_SPY_{CULTURE,FAITH,SCIENCE} Percent=100 are live in
# production as curated-category:PERCENT_BONUS ADDITIVE (verified in the
# conflict ledger). Same modifier type, same effect, same argument.
RULES[("EFFECT_ADJUST_PLAYER_TARGET_CITY_SPY_YIELD_PERCENT", "Percent", "modifier")] = _rule(
    RESOLVED_CANDIDATE, GROUP_SPY_PERCENT, "PERCENT_BONUS",
    "ADDITIVE", "canonical_x10_multiply", False, "governors",
    "none (identical tuple already certifies in production; verified by "
    "gate dry run)",
    "writes 365.0 (50 x 7.3)",
    "writes 500.0",
    "already supported (ADDITIVE percent, no integral gate)",
    "percent of another city's yield stolen by spies (Owls +50% x4 science/"
    "culture/gold/faith); identical (modifier, effect, argument) tuple to "
    "the three live Wu Zetian rows, so this is precedent, not appearance",
)

# --- grant-on-completion percent (signed multi-carrier pattern) -------------
# Four carriers share the shape: Citadel +25 (faith), Ayutthaya +10
# (culture), Ramses -15 (culture, buildings) and Ramses +30 (culture,
# wonders, IncludeWonder=1). A SIGNED mix of penalty and bonus at the same
# argument is only coherent as a percent of production cost (a flat grant
# cannot be negative-meaningful here, and the IncludeWonder split tracks
# the percent base). ModifierType literally GRANT_YIELD_PER_BUILDING_COST.
RULES[("EFFECT_GRANT_CITY_YIELD_PERCENT_BUILDING_CREATED_COST", "BuildingProductionPercent", "modifier")] = _rule(
    RESOLVED_CANDIDATE, GROUP_COMPLETION, "PERCENT_BONUS",
    "ADDITIVE", "canonical_x10_multiply", False, None,
    "6B must add a mixed_overrides entry for "
    "(EFFECT_GRANT_CITY_YIELD_PERCENT_BUILDING_CREATED_COST, "
    "BuildingProductionPercent) -> ADDITIVE (same shape as the two live "
    "mixed overrides); the floor's GRANT_OBJECT row is AUTO_PATTERN "
    "heuristic, and the gate dry run proves the row is otherwise excluded "
    "by it",
    "writes 182.5 (25 x 7.3) / 73.0 (10 x 7.3), float-safe percents",
    "writes 250.0 / 100.0",
    "already supported once the mixed entry lands (ADDITIVE percent)",
    "percent of a completed building's production cost granted as yield "
    "(Citadel +25% faith, Ayutthaya +10% culture); owner follows the row "
    "(governors / suzerain). No transform design fork: additive percent "
    "scaling is the established PERCENT_BONUS reading (Geneva precedent). "
    "IncludeWonder stays a structural boolean, never a magnitude",
)

# --- purchase discount (positive-means-discount convention, proven) ---------
# DB values are POSITIVE on both effects (Ngazargamu +20 units, Valletta
# +50 buildings — the task's '-50'/'-20' prose signs are errata; verified
# against ModifierArguments). Positive must mean discount-percent because
# both IDs name CHEAPER/BONUS benefits: a flat-subtraction reading would
# make Valletta a surcharge. Cross-effect convention confirmed: FLOWER_
# POWER_PURCHASE_INCREASE Amount=-100 is a cost INCREASE, so negative =
# surcharge and positive = discount on this whole effect class. Valletta's
# faith-purchase pairing (enable + cheaper walls/castle/star fort) matches
# the known 50% game description.
RULES[("EFFECT_ADJUST_BUILDING_PURCHASE_COST", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE, GROUP_DISCOUNT, "PERCENT_DISCOUNT",
    "DISCOUNT", "compound_discount", False, "suzerain",
    "6B must add a discount_effects entry for "
    "EFFECT_ADJUST_BUILDING_PURCHASE_COST -> PERCENT_DISCOUNT (same shape "
    "as the live EFFECT_ADJUST_ALL_UNITS_PURCHASE_COST entry); the gate "
    "dry run proves the row otherwise fails closed "
    "(conflict:unclassified-discount-effect)",
    "writes 99.3654 via the repeated-discount formula (never 365.0)",
    "writes 99.9023",
    "already supported (DISCOUNT compound transform is live for Ngazargamu)",
    "50% faith-purchase discount on defensive buildings (Valletta x3); "
    "family preserved as audited (PERCENT_DISCOUNT), never relabelled",
)

# --- Suzerain-gated combat bonus (ownership proved by its requirement) -----
# NIHANG_SUZERAIN_COMBAT_BONUS Amount=+10 carries
# PLAYER_HAS_LAHORE_SUZERAIN_REQUIREMENTS
# (REQUIREMENT_PLAYER_IS_SUZERAIN_OF_X -> LEADER_MINOR_CIV_LAHORE): the
# magnitude exists ONLY while Lahore Suzerain status holds. The floor row
# for this tuple is COMBAT_STRENGTH_BONUS / FORMULA_DERIVED, so the gate
# passes today with no rule change. Qualitatively different from the
# intrinsic Barracks/Armory/Academy +15 progression (no Suzerain gate).
RULES[("EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER", "Amount", "unit")] = _rule(
    RESOLVED_CANDIDATE, GROUP_COMBAT_EDGE, "COMBAT_STRENGTH_BONUS",
    "COMBAT", "canonical_combat_bonus", False, "suzerain",
    "none (floor is FORMULA_DERIVED for this tuple; verified by gate dry "
    "run)",
    "writes 38.10 via the canonical b_k transform",
    "writes 44.45",
    "already supported (canonical combat transform is live)",
    "Lahore Suzerain-gated +10 combat strength; the unit-side-path row is "
    "claimed ONLY because its own requirement proves Suzerain ownership. "
    "Intrinsic Barracks/Armory/Academy +15, movement, flanking and "
    "post-combat faith stay outside Suzerain ownership (no '10x the "
    "unlocked unit' decision taken)",
)

# --- healing: full-heal cap, scaling is meaningless -------------------------
# COMBAT_MAX_HIT_POINTS=100 (GlobalParameters, official DB): units cannot
# hold more than 100 HP, so +100 HP/turn is already a full heal every turn.
# 1000 HP/turn heals nothing extra. Both rows are therefore caps/sentinels,
# not scalable magnitudes. Single carriers each; no corroborating usage.
RULES[("EFFECT_ADJUST_EXTRA_HEAL_GOVERNOR", "Amount", "modifier")] = _rule(
    RESOLVED_EXCLUDED, GROUP_HEALING, "FLAT_AMOUNT",
    "", "", False, "",
    "none (exclusion needs no gate change; note the gate WOULD admit this "
    "as flat HP, which is exactly why audit judgment — not the gate — must "
    "exclude it)",
    "n/a (excluded)",
    "n/a (excluded)",
    "n/a (excluded)",
    "governor healing (Laying on of Hands +100): full-heal cap at max HP; "
    "multiplying a cap is semantically wrong. Permanent until heal policy "
    "changes",
)
RULES[("EFFECT_ADJUST_CITY_RELIGIOUS_HEAL", "Amount", "modifier")] = _rule(
    RESOLVED_EXCLUDED, GROUP_HEALING, "FLAT_AMOUNT",
    "", "", False, "",
    "none (same gate-would-admit note as above)",
    "n/a (excluded)",
    "n/a (excluded)",
    "n/a (excluded)",
    "religious-unit healing (Laying on of Hands +100): same full-heal cap "
    "reasoning (religious units share the 100-HP maximum). Permanent until "
    "heal policy changes",
)

# --- grievance Turns: structural duration -----------------------------------
RULES[("EFFECT_ADJUST_GOVERNOR_GRIEVENCE_SCORE", "Turns", "modifier")] = _rule(
    RESOLVED_EXCLUDED, GROUP_GRIEVANCE, "FLAT_AMOUNT",
    "", "", False, "",
    "none (floor COUNT_OR_DURATION already strong-excludes; verified by "
    "gate dry run)",
    "n/a (excluded)",
    "n/a (excluded)",
    "n/a (excluded)",
    "grievance duration (Capou Agha Turns=1): '10x duration' is not part of "
    "any magnitude policy; durations stay structural. One scalable sibling "
    "never drags a duration with it",
)

# --- negative combat: mathematically unsupported transform ------------------
# b_k = 25*ln(k*(e^(b/25)-1)+1): at b=-5 the inner term is -0.3233 (k=7.3)
# and -0.8127 (k=10) — log-domain errors at both production multipliers
# (verified numerically). No principled penalty dual exists within the
# project's combat semantics (the transform preserves tenfold DAMAGE for
# bonuses; penalties are not bonuses). The gate certifies the row
# (formula-derived floor ignores value sign), so exclusion must live at the
# manifest/audit layer — which is what this resolution records.
RULES[("EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER", "Amount", "modifier")] = _rule(
    RESOLVED_EXCLUDED, GROUP_COMBAT_EDGE, "COMBAT_STRENGTH_BONUS",
    "", "", False, "",
    "none — and deliberately NOT a gate change: the gate correctly "
    "certifies positive bonuses, and must keep doing so. The exclusion is "
    "value-specific (official -5) and lives here",
    "n/a (excluded)",
    "n/a (excluded)",
    "no transform exists (canonical b_k undefined at both k)",
    "Sanguine intimidate -5: RESOLVED_EXCLUDED_UNSUPPORTED_TRANSFORM. "
    "Explicit and permanent until transform policy changes; never a vague "
    "decision, never an ad hoc negative formula",
)

# --- direct Governor TransitionStrength: structural weighting ----------------
# Governors-only table column, no modifier carrier, no other table or
# definition references it, values 100/150 track the appointment
# IdentityPressure scale (150 rows pair with 150-strength Defender... in
# fact two 150s exist). Engine-internal transition weighting, not a
# user-facing bonus. Never scale engine weighting to maximize coverage.
RULES[("TransitionStrength", "value", "direct")] = _rule(
    RESOLVED_EXCLUDED, GROUP_DIRECT, "FLAT_AMOUNT",
    "", "", False, "",
    "none (direct columns have no production carrier path at all)",
    "n/a (excluded)",
    "n/a (excluded)",
    "n/a (no carrier)",
    "governor transition weighting (100/150 x12): structural engine "
    "machinery, not a gameplay magnitude",
)

# --- loyalty / identity / religious pressure: observability PROVEN ---------
# Phase-6A.2 pressure probe (scratch 8-entry registry, k=7.3, load AND
# reload): all eight definitions returned
# `stored_after_add=<expected> expected=<expected> MATCH via=store-lookup`
# on BOTH sessions (evidence: spike/validation-evidence/X10Lifecycle.
# toqui-probe.log). The Toqui stored-form hold is therefore lifted per
# definition — one effect succeeding never auto-clears a sibling, so each
# row below carries its own gate result. Five distinct engine EffectTypes
# were tested; direct Governor columns were NOT (no carrier) and stay put.
RULES[("EFFECT_ADJUST_CITY_RELIGION_PRESSURE", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE, GROUP_PRESSURE, "LOYALTY",
    "ADDITIVE", "canonical_x10_multiply", False, "governors",
    "none (certifies today via curated-category:LOYALTY; verified by gate "
    "dry run AND by live MATCH 730.0 on load+reload)",
    "writes 730.0",
    "writes 1000.0",
    "already supported (ADDITIVE loyalty pressure is float-valued; live "
    "store-lookup MATCH on both sessions)",
    "religious pressure (Cardinal Bishop +100): storage observability "
    "proven live; semantics are plain loyalty pressure",
)
RULES[("EFFECT_ADJUST_CITY_IDENTITY_PER_TURN", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE, GROUP_PRESSURE, "LOYALTY",
    "ADDITIVE", "canonical_x10_multiply", False, None,
    "none (certifies today via curated-category:LOYALTY; verified by gate "
    "dry run AND by live MATCH on load+reload)",
    "writes 29.2 (Owls 4) / 14.6 (Preslav 2 x3)",
    "writes 40.0 / 20.0",
    "already supported (ADDITIVE loyalty pressure is float-valued; live "
    "store-lookup MATCH on both sessions)",
    "identity/loyalty per turn (Owls counterspies +4, Preslav +2 x3): "
    "storage observability proven live; owner follows the row (governors / "
    "suzerain)",
)
RULES[("EFFECT_GRANT_PLAYER_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED", "Amount", "modifier")] = _rule(
    RESOLVED_CANDIDATE, GROUP_PRESSURE, "LOYALTY",
    "ADDITIVE", "canonical_x10_multiply", False, "suzerain",
    "6B must add a mixed_overrides entry for "
    "(EFFECT_GRANT_PLAYER_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED, "
    "Amount) -> ADDITIVE: scalar pressure rate, not an object grant (same "
    "shape as the two live mixed overrides); the floor's GRANT_OBJECT row "
    "is AUTO_PATTERN heuristic. Storage observability proven live (MATCH "
    "2920.0 on load+reload)",
    "writes 2920.0",
    "writes 4000.0",
    "already supported once the mixed entry lands (ADDITIVE pressure)",
    "religious pressure per great person activated (Vatican City 400): "
    "storage observability proven live; semantics are a pressure rate",
)
RULES[("IdentityPressure", "value", "direct")] = _rule(
    STILL_SEMANTICALLY_UNRESOLVED, GROUP_PRESSURE, "LOYALTY",
    "", "", False, "",
    "unresolved (no modifier carrier path exists for direct table columns, "
    "and the pressure family hold is independently unresolved)",
    "n/a (unresolved)",
    "n/a (unresolved)",
    "no carrier",
    "direct Governor appointment loyalty (8/10 x12): magnitude confirmed as "
    "loyalty class, but no production carrier path exists and the family "
    "hold is unresolved — magnitude without mechanism",
)

# --- ScalingFactor: percent-of-base established, transform missing -----------
# Cross-carrier pattern proves base-inclusive percent (100 = 1x): Curator
# 200 = double, Reliquaries/GreatPerson 300 = triple, Cristo/Heritage/
# Printing/StBasil's 200 = double, Commemoration 150 = 1.5x, Kandy 150 =
# 1.5x. Bonus-only reading fits NONE of them (Curator would triple).
# Consequence: canonical multiply is WRONG for this shape (200 -> 2000 is
# 20x total = 19x bonus, not 10x bonus). The correct scaling is
# offset-aware, 100 + 10x(v-100): 200 -> 1100, 150 -> 600, 300 -> 2100.
# That transform does not exist in native code. No manufacture in 6A.
RULES[("EFFECT_ADJUST_CITY_TOURISM", "ScalingFactor", "modifier")] = _rule(
    STILL_SEMANTICALLY_UNRESOLVED, GROUP_FACTOR, "MULTIPLICATIVE_FACTOR",
    "", "", False, "",
    "blocked (would need a new offset-aware transform + native support + "
    "product sign-off; MULTIPLICATIVE_FACTOR stays strong-excluded)",
    "n/a (unresolved)",
    "n/a (unresolved)",
    "no valid transform (canonical multiply disproven for this shape)",
    "tourism ScalingFactor (Curator 200 x6): percent-of-base semantics "
    "ESTABLISHED from 19 carriers, but unshippable without an offset-aware "
    "transform. Same analysis covers Kandy relic 150 (same shape, same "
    "block)",
)
RULES[("EFFECT_ADJUST_CITY_GREATWORK_YIELD", "ScalingFactor", "modifier")] = _rule(
    STILL_SEMANTICALLY_UNRESOLVED, GROUP_FACTOR, "MULTIPLICATIVE_FACTOR",
    "", "", False, "",
    "blocked (same offset-aware-transform requirement as tourism "
    "ScalingFactor)",
    "n/a (unresolved)",
    "n/a (unresolved)",
    "no valid transform",
    "great-work yield ScalingFactor (Kandy relic 150): same base-inclusive "
    "percent shape as tourism; same block",
)

# --- single-carrier judgments without corroboration -------------------------
RULES[("EFFECT_ADJUST_CITY_STRATEGIC_RESOURCE_REQUIREMENT_MODIFIER", "Amount", "modifier")] = _rule(
    STILL_SEMANTICALLY_UNRESOLVED, GROUP_FACTOR, "MULTIPLICATIVE_FACTOR",
    "", "", False, "",
    "unresolved (single carrier; percent plausible but sign convention "
    "unproven — cf. the Valletta analysis, which had CHEAPER naming + "
    "faith context and still needed care)",
    "n/a (unresolved)",
    "n/a (unresolved)",
    "no valid transform (never multiply what merely resembles a percent)",
    "strategic-resource requirement (Black Marketeer 80): one carrier, no "
    "siblings, no text locally; percent-vs-factor-vs-flat unresolved",
)
RULES[("EFFECT_ADJUST_GOVERNOR_GRIEVENCE_SCORE", "Score", "modifier")] = _rule(
    STILL_SEMANTICALLY_UNRESOLVED, GROUP_GRIEVANCE, "FLAT_AMOUNT",
    "", "", False, "",
    "unresolved (note the gate WOULD admit this as flat, so audit judgment "
    "— not the gate — must hold it back)",
    "n/a (unresolved)",
    "n/a (unresolved)",
    "withheld (semantics unknown)",
    "grievance score (Capou Agha Score=1): single carrier; the DIRECTION is "
    "unknown (inflict vs suffer) so scaling could harm or help — no "
    "evidence either way; the Turns sibling is structural regardless",
)

# --- unique-object ownership: decided at product level, not schema level ----
# Intrinsic improvement cells and intrinsic unit/ability cells are
# structurally accounted but never auto-claimed. Improvement cells await the
# human product decision (narrow vs expanded ownership); intrinsic unit
# cells stay vanilla (no '10x the unlocked unit' decision taken).
RULES[("IMPROVEMENT_CELL", "value", "improvement")] = _rule(
    NEEDS_PRODUCT_DECISION, GROUP_OWNERSHIP, "",
    "", "", False, "",
    "human product decision required (recommendation: narrow ownership — "
    "see the §11 table; expanded ownership needs explicit override)",
    "n/a (undecided)",
    "n/a (undecided)",
    "withheld (ownership undecided)",
    "unlocked-improvement intrinsic cells (58): base/adjacency yields, "
    "housing/amenity/appeal, tourism factor — capability unlock vs benefit "
    "is a product question, see the nine-improvement table",
)
RULES[("UNIT_CELL", "value", "unit")] = _rule(
    RESOLVED_EXCLUDED, GROUP_OWNERSHIP, "",
    "", "", False, "",
    "none (stays vanilla by decision: no ownership path and no proposal to "
    "create one)",
    "n/a (excluded)",
    "n/a (excluded)",
    "n/a (not owned)",
    "intrinsic granted-unit/ability cells (flanking, movement, post-combat "
    "faith, no-wounded-penalty, Barracks/Armory/Academy +15, Wolin "
    "coefficients): no trait-graph membership, no Suzerain gate (except "
    "Lahore +10, resolved separately as a candidate) — stays vanilla "
    "unless a future design says '10x the unlocked unit'",
)

# --------------------------------------------------------------------------
# Per-modifier notes (documentation of routing; the tuple/cell-kind keys
# above already separate these rows — listed here so review can see every
# high-stakes row by name).
# --------------------------------------------------------------------------
# NIHANG_SUZERAIN_COMBAT_BONUS -> Lahore candidate rule (unit kind).
# SECRET_SOCIETY_INTIMIDATE_ADJACENT_ENEMIES_MODIFIER -> negative-combat
#   exclusion (modifier kind). The two share an effect/argument but never
#   collide: cell_kind separates graph rows from side-path rows.
# CARDINAL_LAYING_ON_OF_HANDS_{HEAL,RELIGIOUS_HEAL} -> healing exclusion.
# CAPOU_AGHA_ADJUST_GRIEVANCES Score -> unresolved; Turns -> excluded.
# BLACK_MARKETEER_STRATEGIC_RESOURCE_COST_DISCOUNT -> unresolved.
# Valletta x3 (Amount=+50, NOT -50: task prose erratum, verified in
#   ModifierArguments) -> discount candidate rule.
# Ngazargamu precedent: Amount=+20 (likewise positive-means-discount).

MODIFIER_NOTES = {
    "NIHANG_SUZERAIN_COMBAT_BONUS": "unit-kind combat candidate (own requirement proves ownership)",
    "SECRET_SOCIETY_INTIMIDATE_ADJACENT_ENEMIES_MODIFIER": "modifier-kind combat exclusion (value -5, transform undefined)",
    "CARDINAL_LAYING_ON_OF_HANDS_HEAL": "healing cap exclusion (100 HP max)",
    "CARDINAL_LAYING_ON_OF_HANDS_RELIGIOUS_HEAL": "healing cap exclusion (100 HP max)",
    "CAPOU_AGHA_ADJUST_GRIEVANCES": "Score unresolved / Turns structural",
    "BLACK_MARKETEER_STRATEGIC_RESOURCE_COST_DISCOUNT": "single-carrier factor, unresolved",
    "MINOR_CIV_VALLETTA_PURCHASE_CHEAPER_WALLS_BONUS": "discount candidate (+50 = 50% off)",
    "MINOR_CIV_VALLETTA_PURCHASE_CHEAPER_CASTLE_BONUS": "discount candidate (+50 = 50% off)",
    "MINOR_CIV_VALLETTA_PURCHASE_CHEAPER_STAR_BONUS": "discount candidate (+50 = 50% off)",
}


def _load_yaml(path):
    import yaml
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def import_governor_unresolved(audit) -> list[dict]:
    """29 reachable + 24 direct DECISION_REQUIRED rows, mechanically."""
    out = []
    for promo, p in (audit.get("promotions") or {}).items():
        for r in p.get("rows", []):
            if r.get("disposition") != "DECISION_REQUIRED":
                continue
            out.append({
                "source": "governors",
                "source_kind": "modifier",
                "root": r.get("root_governor"),
                "root_detail": r.get("root_promotion") or promo,
                "modifier_id": r["modifier_id"],
                "modifier_type": r.get("modifier_type"),
                "effect_type": r.get("effect_type"),
                "argument": r.get("argument"),
                "value": str(r.get("value")),
                "family": r.get("family"),
                "audit_disposition": r.get("disposition"),
                "audit_reason": r.get("reason"),
            })
    for c in audit.get("direct_cells") or []:
        if c.get("disposition") != "DECISION_REQUIRED":
            continue
        out.append({
            "source": "governors",
            "source_kind": "direct",
            "root": c.get("root"),
            "root_detail": c.get("cell"),
            "modifier_id": None,
            "modifier_type": None,
            "effect_type": c.get("cell"),
            "argument": "value",
            "value": str(c.get("value")),
            "family": c.get("family"),
            "audit_disposition": c.get("disposition"),
            "audit_reason": c.get("reason"),
        })
    return out


def import_suzerain_unresolved(audit) -> list[dict]:
    """21 main-graph numeric + 68 side-path DECISION_REQUIRED rows."""
    out = []
    for r in audit.get("rows") or []:
        if r.get("disposition") != "DECISION_REQUIRED" or not r.get("numeric"):
            continue
        out.append({
            "source": "suzerain",
            "source_kind": "modifier",
            "root": r.get("city_state"),
            "root_detail": f"{r.get('trait_type')} via {r.get('root_modifier_id')}",
            "modifier_id": r["modifier_id"],
            "modifier_type": r.get("modifier_type"),
            "effect_type": r.get("effect_type"),
            "argument": r.get("argument_name"),
            "value": str(r.get("argument_value")),
            "family": r.get("family"),
            "audit_disposition": r.get("disposition"),
            "audit_reason": r.get("reason"),
        })
    sp = audit.get("side_paths") or {}
    for imp, p in (sp.get("improvements") or {}).items():
        for c in p.get("cells", []):
            if c.get("disposition") != "DECISION_REQUIRED":
                continue
            out.append({
                "source": "suzerain",
                "source_kind": "improvement",
                "root": imp,
                "root_detail": c.get("cell"),
                "modifier_id": None,
                "modifier_type": None,
                "effect_type": None,
                "argument": c.get("cell"),
                "value": str(c.get("value")),
                "family": c.get("family"),
                "audit_disposition": c.get("disposition"),
                "audit_reason": c.get("reason"),
            })
    for unit, p in (sp.get("units") or {}).items():
        for m in p.get("promotion_modifiers", []):
            if m.get("disposition") != "DECISION_REQUIRED":
                continue
            out.append({
                "source": "suzerain",
                "source_kind": "unit",
                "root": unit,
                "root_detail": m.get("promotion"),
                "modifier_id": m.get("modifier_id"),
                "modifier_type": m.get("modifier_type"),
                "effect_type": m.get("effect_type"),
                "argument": m.get("argument_name"),
                "value": str(m.get("argument_value")),
                "family": m.get("family"),
                "audit_disposition": m.get("disposition"),
                "audit_reason": m.get("reason"),
            })
        for m in p.get("ability_modifiers", []):
            if m.get("disposition") != "DECISION_REQUIRED":
                continue
            out.append({
                "source": "suzerain",
                "source_kind": "unit",
                "root": unit,
                "root_detail": m.get("unit_ability"),
                "modifier_id": m.get("modifier_id"),
                "modifier_type": m.get("modifier_type"),
                "effect_type": m.get("effect_type"),
                "argument": m.get("argument_name"),
                "value": str(m.get("argument_value")),
                "family": m.get("family"),
                "audit_disposition": m.get("disposition"),
                "audit_reason": m.get("reason"),
            })
    for ab, p in (sp.get("abilities") or {}).items():
        for m in p.get("modifiers", []):
            if m.get("disposition") != "DECISION_REQUIRED":
                continue
            out.append({
                "source": "suzerain",
                "source_kind": "unit",
                "root": ab,
                "root_detail": m.get("modifier_id"),
                "modifier_id": m.get("modifier_id"),
                "modifier_type": m.get("modifier_type"),
                "effect_type": m.get("effect_type"),
                "argument": m.get("argument_name"),
                "value": str(m.get("argument_value")),
                "family": m.get("family"),
                "audit_disposition": m.get("disposition"),
                "audit_reason": m.get("reason"),
            })
    return out


def classify(row: dict) -> dict:
    """Apply tuple rules / class rules to one imported row (fail closed)."""
    kind = row["source_kind"]
    if kind in ("improvement",):
        key = ("IMPROVEMENT_CELL", "value", "improvement")
    elif kind == "unit":
        if row["modifier_id"] == "NIHANG_SUZERAIN_COMBAT_BONUS":
            key = (row["effect_type"], row["argument"], "unit")
        else:
            key = ("UNIT_CELL", "value", "unit")
    elif kind == "direct":
        key = (row["effect_type"], "value", "direct")
    else:
        key = (row["effect_type"], row["argument"], "modifier")
    rule = RULES.get(key)
    if rule is None:
        raise ValueError(
            f"no Phase-6A resolution for {row['source']}/{row['modifier_id'] or row['root']}:"
            f"{row['argument']}={row['value']} (fail closed)")
    (resolution, group, family, pkind, transform, count_like, owner,
     gate_evidence, k73, k10, native, rationale) = rule
    assert resolution in RESOLUTIONS
    if owner is None and resolution in (RESOLVED_CANDIDATE,
                                        RESOLVED_CANDIDATE_COUNT_LIKE):
        # rows whose owner follows their source module (e.g. the
        # grant-on-completion percent, which occurs in both modules)
        owner = {"governors": "governors", "suzerain": "suzerain"}[row["source"]]
    return {**row, "resolution": resolution, "group": group,
            "resolved_family": family, "production_kind": pkind,
            "transform": transform, "count_like": count_like,
            "proposed_owner": owner,
            "required_gate_evidence": gate_evidence,
            "k73_expectation": k73, "k10_expectation": k10,
            "native_support": native, "resolution_rationale": rationale}


def build_backlog(governor_audit_path, suzerain_audit_path) -> dict:
    """Assemble the unified backlog (deterministic, closed-world)."""
    gaudit = _load_yaml(governor_audit_path)
    saudit = _load_yaml(suzerain_audit_path)
    imported = (import_governor_unresolved(gaudit)
                + import_suzerain_unresolved(saudit))
    rows = [classify(r) for r in imported]
    rows.sort(key=lambda r: (r["resolution"], r["group"], r["source"],
                             str(r["modifier_id"] or r["root"]),
                             str(r["argument"])))
    by_resolution = dict(sorted(Counter(r["resolution"] for r in rows).items()))
    by_group_resolution = {}
    for r in rows:
        by_group_resolution.setdefault(r["group"], Counter())[r["resolution"]] += 1
    by_group_resolution = {g: dict(sorted(c.items()))
                           for g, c in sorted(by_group_resolution.items())}
    candidates = [
        {"modifier_id": r["modifier_id"], "argument": r["argument"],
         "value": r["value"], "family": r["resolved_family"],
         "kind": r["production_kind"], "transform": r["transform"],
         "count_like": r["count_like"], "owner": r["proposed_owner"],
         "effect_type": r["effect_type"],
         "modifier_type": r["modifier_type"],
         "source": r["source"], "root": r["root"],
         "gate_evidence": r["required_gate_evidence"],
         "k73": r["k73_expectation"], "k10": r["k10_expectation"]}
        for r in rows if r["resolution"] in (RESOLVED_CANDIDATE,
                                             RESOLVED_CANDIDATE_COUNT_LIKE)]
    # Production projection: source occurrences deduplicated to unique
    # (ModifierId, argument) pairs, because the native writer mutates the
    # definition once. Provenance from every occurrence is aggregated, never
    # dropped: e.g. SECRET_SOCIETY_GRANT_ONE_VAMPIRE_BUILD/Amount occurs
    # under both SANGUINE_PACT_3 and SANGUINE_PACT_4 but ships once.
    production_pairs = build_production_projection(rows)
    pair_counts = {
        "unique_production_pairs": len(production_pairs),
        "unique_governor_pairs": sum(
            1 for p in production_pairs if p["owner"] == "governors"),
        "unique_suzerain_pairs": sum(
            1 for p in production_pairs if p["owner"] == "suzerain"),
        "unique_non_count_like": sum(
            1 for p in production_pairs if not p["count_like"]),
        "unique_count_like": sum(
            1 for p in production_pairs if p["count_like"]),
        "kinds": dict(sorted(Counter(p["kind"] for p in production_pairs
                                     ).items())),
    }
    return {
        "audit": ("Phase 6A unified unresolved-semantic backlog (research "
                  "only; nothing here is production)"),
        "counts": {
            "imported_governor_reachable": sum(
                1 for r in rows if r["source"] == "governors"
                and r["source_kind"] == "modifier"),
            "imported_governor_direct": sum(
                1 for r in rows if r["source"] == "governors"
                and r["source_kind"] == "direct"),
            "imported_suzerain_main": sum(
                1 for r in rows if r["source"] == "suzerain"
                and r["source_kind"] == "modifier"),
            "imported_suzerain_side": sum(
                1 for r in rows if r["source"] == "suzerain"
                and r["source_kind"] in ("improvement", "unit")),
            "imported_total": len(rows),
        },
        "by_resolution": by_resolution,
        "by_group_resolution": by_group_resolution,
        "proposed_candidates": candidates,
        "proposed_production_pairs": production_pairs,
        "production_pair_counts": pair_counts,
        "probe_cleared_addendum": probe_cleared_addendum(),
        "proposed_existing_reclassifications":
            proposed_existing_reclassifications(),
        "proposed_gate_evidence": proposed_gate_evidence(),
        "rows": rows,
    }


def build_production_projection(rows: list[dict]) -> list[dict]:
    """Unique (ModifierId, argument) projection of candidate occurrences."""
    grouped: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        if r["resolution"] not in (RESOLVED_CANDIDATE,
                                   RESOLVED_CANDIDATE_COUNT_LIKE):
            continue
        grouped.setdefault((r["modifier_id"], r["argument"]), []).append(r)
    pairs = []
    for (mid, arg), occ in sorted(grouped.items()):
        first = occ[0]
        for o in occ[1:]:
            for field in ("value", "resolved_family", "production_kind",
                          "transform", "count_like", "proposed_owner",
                          "effect_type", "modifier_type"):
                if o[field] != first[field]:
                    raise ValueError(
                        f"occurrences of {(mid, arg)} disagree on {field}: "
                        f"{first[field]!r} vs {o[field]!r} (fail closed)")
        pairs.append({
            "modifier_id": mid, "argument": arg,
            "value": first["value"], "family": first["resolved_family"],
            "kind": first["production_kind"],
            "transform": first["transform"],
            "count_like": first["count_like"], "owner": first["proposed_owner"],
            "effect_type": first["effect_type"],
            "modifier_type": first["modifier_type"],
            "occurrences": len(occ),
            "sources": sorted([list(s) for s in
                               {(o["source"], str(o["root"]),
                                 str(o["root_detail"])) for o in occ}]),
        })
    return pairs


def proposed_existing_reclassifications() -> dict:
    """Already-shipped rows the 6A patterns would intentionally reclassify.

    Recorded for Phase-6B review: if the whole-unit semantic rule applies to
    Defense Logistics, it applies to the same mechanic's live rows. These
    change pre-6B `count_like` state and must be live-validated explicitly.
    """
    return {
        "note": ("PROPOSAL ONLY — intentional semantic correction, not a "
                 "workaround to evade. Completeness is verified mechanically "
                 "by test (no other current-production row changes)."),
        "rows": [
            {"modifier_id": "CORPORATE_LIBERTARIANISM_RESOURCE_EXTRACTION",
             "argument": "Amount", "effect_type":
                 "EFFECT_ADJUST_CITY_EXTRA_ACCUMULATION",
             "official": "1", "current_count_like": False,
             "proposed_count_like": True,
             "via_pattern": "EXTRA_ACCUMULATION",
             "live_k73_today": "7.3 (stored as float)"},
            {"modifier_id": "TRAIT_ACCUMULATE_MORE_COAL",
             "argument": "Amount", "effect_type":
                 "EFFECT_ADJUST_CITY_EXTRA_ACCUMULATION_SPECIFIC_RESOURCE",
             "official": "2", "current_count_like": False,
             "proposed_count_like": True,
             "via_pattern": "EXTRA_ACCUMULATION",
             "live_k73_today": "14.6 (stored as float)"},
            {"modifier_id": "TRAIT_ACCUMULATE_MORE_IRON",
             "argument": "Amount", "effect_type":
                 "EFFECT_ADJUST_CITY_EXTRA_ACCUMULATION_SPECIFIC_RESOURCE",
             "official": "2", "current_count_like": False,
             "proposed_count_like": True,
             "via_pattern": "EXTRA_ACCUMULATION",
             "live_k73_today": "14.6 (stored as float)"},
        ],
    }


def probe_cleared_addendum() -> dict:
    """Toqui rows cleared by the Phase-6A.2 pressure probe (NOT backlog rows).

    TOQUI_DOMESTIC/FOREIGN_LOYALTY are excluded in production and live in
    neither audit's decision queue, so they never enter the 142 imported
    occurrences. Both returned `stored_after_add=29.2 expected=29.2 MATCH
    via=store-lookup` on load AND reload (evidence:
    spike/validation-evidence/X10Lifecycle.toqui-probe.log), and both
    certify LOYALTY/ADDITIVE once the held-out exclusion is removed (gate
    dry run). They join the production projection as civilization-trait
    rows (Mapuche TRAIT_CIVILIZATION_MAPUCHE_TOQUI → owner traits).
    """
    return {
        "note": ("storage observability proven live on both sessions for "
                 "both rows; semantics are plain loyalty pressure. Joins "
                 "the production projection; the source backlog stays 142 "
                 "occurrences."),
        "log_evidence": "spike/validation-evidence/X10Lifecycle.toqui-probe.log",
        "pairs": [
            {"modifier_id": "TOQUI_DOMESTIC_LOYALTY", "argument": "Amount",
             "value": "4", "family": "LOYALTY", "kind": "ADDITIVE",
             "transform": "canonical_x10_multiply", "count_like": False,
             "owner": "traits",
             "effect_type": "EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE",
             "modifier_type":
                 "MODIFIER_PLAYER_GOVERNORS_ADJUST_GOVERNOR_IDENTITY_PRESSURE",
             "trait": "TRAIT_CIVILIZATION_MAPUCHE_TOQUI",
             "live_match": "29.2 on load and reload"},
            {"modifier_id": "TOQUI_FOREIGN_LOYALTY", "argument": "Amount",
             "value": "4", "family": "LOYALTY", "kind": "ADDITIVE",
             "transform": "canonical_x10_multiply", "count_like": False,
             "owner": "traits",
             "effect_type": "EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE",
             "modifier_type":
                 "MODIFIER_PLAYER_GOVERNORS_ADJUST_GOVERNOR_IDENTITY_PRESSURE",
             "trait": "TRAIT_CIVILIZATION_MAPUCHE_TOQUI",
             "live_match": "29.2 on load and reload"},
        ],
    }


def proposed_gate_evidence() -> dict:
    """Certification-rule additions 6B must land WITH the rows (NOT applied).

    Each entry records its blast radius against the CURRENT production
    registry so review can see what else moves. These are proposal data for
    review; applying them is a Phase-6B production change.
    """
    return {
        "note": ("PROPOSAL ONLY — not applied to certified_overrides.yml. "
                 "Each addition must land atomically with its rows, or the "
                 "rows would certify with the wrong shape (proven by gate "
                 "dry run)."),
        "count_like_effects_add": [
            {"pattern": "RELIGION_EXTRA_PROMOTIONS",
             "rationale": "extra religious promotions are whole promotions",
             "blast_radius": "EFFECT_ADJUST_CITY_RELIGION_EXTRA_PROMOTIONS only"},
            {"pattern": "EXTRA_ACCUMULATION",
             "rationale": "extra strategic accumulation is a whole-unit flow",
             "blast_radius": "EFFECT_ADJUST_CITY_EXTRA_ACCUMULATION (Defense "
                             "Logistics, the target) PLUS _FOR_STRATEGIC_"
                             "DIVERSITY and _SPECIFIC_RESOURCE siblings; "
                             "TRAIT_ACCUMULATE_MORE_COAL/_IRON are in "
                             "production unconditional today and would flip "
                             "to count-like — 6B must review that as an "
                             "intended fix, not a silent side effect"},
            {"pattern": "ATTACKS_PER_TURN",
             "rationale": "city attacks per turn are whole attacks",
             "blast_radius": "EFFECT_ADJUST_CITY_ATTACKS_PER_TURN only"},
            {"pattern": "RESOURCE_POWER_PROVIDED",
             "rationale": "granted power units are whole units",
             "blast_radius": "EFFECT_ADJUST_RESOURCE_POWER_PROVIDED_GOVERNOR only"},
            {"pattern": "FREE_RESOURCE_IMPORT",
             "rationale": "granted resource units are whole units",
             "blast_radius": "exactly the Hattusa EXTRACTION and Zanzibar "
                             "IMPORT effects"},
        ],
        "discount_effects_add": [
            {"effect": "EFFECT_ADJUST_BUILDING_PURCHASE_COST",
             "semantics": "PERCENT_DISCOUNT",
             "rationale": "positive-means-discount convention proven "
                          "cross-effect (CHEAPER naming + faith context; "
                          "FLOWER_POWER -100 is the surcharge mirror); "
                          "boundary +100 is the free fixed point under "
                          "compound",
             "blast_radius": "Valletta x3 only (effect-scoped)"},
        ],
        "mixed_overrides_add": [
            {"effect": "EFFECT_GRANT_CITY_YIELD_PERCENT_BUILDING_CREATED_COST",
             "argument": "BuildingProductionPercent", "kind": "ADDITIVE",
             "rationale": "scalar percent of production cost (signed "
                          "+25/+10/-15/+30 multi-carrier pattern); same shape "
                          "as the two live mixed overrides",
             "blast_radius": "Citadel + Ayutthaya rows (Ramses rows are out "
                             "of production scope and stay out)"},
            {"effect": "EFFECT_GRANT_PLAYER_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED",
             "argument": "Amount", "kind": "ADDITIVE",
             "rationale": "scalar pressure rate per activation, not an "
                          "object grant; Vatican storage proven live "
                          "(MATCH 2920.0 on load+reload); same shape as the "
                          "two live mixed overrides",
             "blast_radius": "Vatican row only (sole carrier of this effect)"},
        ],
        "exclusion_removals": [
            {"effect": "EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE",
             "action": "remove from excluded_effects",
             "rationale": "the 2026-10-08 stored-form hold is lifted: both "
                          "carriers MATCH via=store-lookup on load AND "
                          "reload with current native code (Phase-6A.2 "
                          "probe evidence); LOYALTY pressure is float-valued "
                          "(live-proven 21.9 precedent)",
             "blast_radius": "exactly the two Toqui carriers (verified: no "
                             "other Modifiers row dispatches this effect); "
                             "both join the projection as traits-owned"},
        ],
    }


def write_backlog(backlog: dict, out) -> None:
    import yaml
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Phase 6A unified semantic backlog (machine-generated research input)\n"
                 "# Built by civ6x10.backlog from the checked-in Governor + Suzerain audits.\n"
                 "# NOT production: candidates are a PROPOSAL for Phase 6B.\n")
        yaml.safe_dump(backlog, fh, sort_keys=True, allow_unicode=True,
                       width=120, default_flow_style=False)
