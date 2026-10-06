"""Semantic family inference for RELEASE_1 scope.

Deterministic keyword rules over (ModifierType, EffectType, argument_name,
official values, sibling selectors). Every decision records its evidence;
ambiguous rows stay DECISION_REQUIRED rather than being guessed.
"""
from __future__ import annotations

import re

# argument names that are always selectors, never magnitudes
SELECTOR_ARGS = {
    "YieldType", "EraType", "BuildingType", "UnitPromotionClass",
    "UnitPromotionClassType", "AbilityType", "ModifierId", "RequirementId",
    "GovernmentSlotType", "GreatPersonClassType", "DistrictType",
    "ImprovementType", "ResourceType", "UnitType", "PromotionClass",
    "DomainType", "FeatureType", "TerrainType", "CivicType", "TechType",
    "BeliefType", "PolicyType", "GovernmentType", "UnitAbilityType",
    "UnitTag", "Tag", "CollectionType", "EffectType", "PrereqCivic",
    "PrereqTech", "LocationText", "Description", "Name",
}

DISCOUNT_HINT = re.compile(r"COST|MAINTENANCE|DISCOUNT|CHEAPER|REDUCE", re.I)
COMBAT_HINT = re.compile(r"COMBAT_STRENGTH", re.I)
PROB_HINT = re.compile(r"PROBABILITY|CHANCE|LIKELIHOOD", re.I)


def infer_family(modifier_type: str, effect_type: str, argument_name: str,
                 values: list[str]) -> tuple[str, str, str]:
    """Return (family, transform, confidence).

    confidence is 'reviewed' (family rule) or 'needs_human' (ambiguous).
    transform names a key in rules/transformations.yml.
    """
    mt = modifier_type or ""
    et = effect_type or ""
    arg = argument_name or ""

    if arg in SELECTOR_ARGS:
        return ("SELECTOR", "unchanged", "reviewed")

    nums: list[float] = []
    non_numeric = False
    for v in values:
        try:
            nums.append(float(v))
        except (TypeError, ValueError):
            if str(v).strip() not in ("", "None"):
                non_numeric = True
    if non_numeric and nums:
        return ("UNKNOWN", "decision_required", "needs_human")
    if not nums:
        # non-numeric reference argument with an unusual name: treat as
        # selector only when the effect taxonomy says reference; else refuse.
        if "GRANT" in mt or "EFFECT_GRANT" in et or arg.endswith("Type"):
            return ("SELECTOR", "unchanged", "reviewed")
        return ("UNKNOWN", "decision_required", "needs_human")

    # combat bonuses (formula, never flat x10)
    if arg == "Amount" and (COMBAT_HINT.search(et) or COMBAT_HINT.search(mt)):
        return ("COMBAT_STRENGTH_BONUS", "canonical_combat_bonus", "reviewed")
    if "DefeatedStrength" in arg or "DEFEATED" in et.upper():
        return ("DEFEATED_STRENGTH_SCALING", "canonical_x10_multiply", "reviewed")
    # discounts (negative percents on cost-like modifiers)
    if arg in ("Percent", "Amount") and DISCOUNT_HINT.search(mt + " " + et):
        if any(n < 0 for n in nums):
            return ("DISCOUNT", "compound_discount", "reviewed")
    # probabilities
    if PROB_HINT.search(arg) or PROB_HINT.search(et):
        return ("PROBABILITY", "repeated_probability", "reviewed")
    # durations / charges / spatial budgets
    if arg in ("TurnsActive", "Duration", "Turns"):
        return ("DURATION", "canonical_x10_multiply", "reviewed")
    if arg in ("Charges", "SpreadCharges", "BuilderCharges", "Spreads"):
        return ("CHARGES", "canonical_x10_multiply", "reviewed")
    if arg in ("Range", "SpreadRange"):
        return ("RANGE", "canonical_x10_multiply", "reviewed")
    if arg in ("Radius",):
        return ("RADIUS", "canonical_x10_multiply", "reviewed")
    if "Movement" in arg or arg in ("BaseMoves", "ExtraMoves"):
        return ("MOVEMENT", "canonical_x10_multiply", "reviewed")
    # named percent / yield semantics
    if arg == "Percent" and "PRODUCTION" in (mt + et).upper():
        return ("PRODUCTION_PERCENT", "canonical_x10_multiply", "reviewed")
    if arg == "Percent":
        return ("PERCENT_BONUS", "canonical_x10_multiply", "reviewed")
    if arg in ("PointsPerTurn", "Points"):
        return ("GREAT_PERSON_POINTS", "canonical_x10_multiply", "reviewed")
    if arg in ("Loyalty",):
        return ("LOYALTY", "canonical_x10_multiply", "reviewed")
    if arg in ("Amenities", "Amenity", "AddAmenity"):
        return ("AMENITY", "canonical_x10_multiply", "reviewed")
    if arg in ("Housing",):
        return ("HOUSING", "canonical_x10_multiply", "reviewed")
    if arg in ("Tourism", "TourismBomb"):
        return ("TOURISM", "canonical_x10_multiply", "reviewed")
    if arg in ("Experience", "UnitExperience", "XP"):
        return ("EXPERIENCE", "canonical_x10_multiply", "reviewed")
    if arg in ("Faith",):
        return ("FAITH", "canonical_x10_multiply", "reviewed")
    if arg in ("Gold",):
        return ("GOLD", "canonical_x10_multiply", "reviewed")
    # generic numeric residuum
    if arg in ("Amount", "Value", "YieldChange", "BonusRate", "YieldModifier",
               "NumSlots", "Cost", "Combat", "RangedCombat", "Bombard",
               "Strength"):
        fam = "FLAT_YIELD" if "YIELD" in (mt + et).upper() else "FLAT_AMOUNT"
        return (fam, "canonical_x10_multiply", "reviewed")
    # zero-only / boolean-shaped numerics stay human decisions
    if all(n == 0 for n in nums):
        return ("BOOLEAN_UNLOCK", "refused_no_multiplier", "needs_human")
    return ("UNKNOWN", "decision_required", "needs_human")
