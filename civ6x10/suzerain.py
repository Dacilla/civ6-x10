"""Phase 5A: closed-world City-State / Suzerain semantic audit.

AUDIT ONLY. This phase discovers every official City-State that is actually
active in the shipped runtime database, walks the Suzerain-gated modifier
graph reachable from its trait, dispositions every reachable argument against
the project's existing semantic vocabulary, inventories the unique-improvement
and unique-unit side paths, compares the result with the legacy x10
Suzerain mod's own coverage record, and proposes a conservative Phase 5B
production slice.

It writes NO production registry rows, implements no owner bit, and touches
no native/controller file: `civ6x10/rules/suzerain_audit.yml` is a reviewed
input to Phase 5B, exactly as `governor_audit.yml` was to Phase 4B.

Scope rule: the module is the **10x Suzerain bonus** multiplier. The generic
1/3/6-envoy tier bonuses shared by the Scientific/Cultural/... city-state
"type" traits are NOT part of the graph and are never swept in - the roots
are the per-city-state traits' Suzerain-gated TraitModifiers only.

Discovery is derived, never hard-coded:

* **Active membership** comes from
  `Civilizations.StartingCivilizationLevelType = CIVILIZATION_LEVEL_CITY_STATE`
  joined `CivilizationLeaders` -> `Leaders_XP2` -> `LeaderTraits`, requiring
  the mapped leader to carry a non-null `MinorCivBonusType`. `LEADER_MINOR_CIV-%`
  names, all `Leaders_XP2` rows, the legacy `trait_coverage.csv` and any
  wiki/list are explicitly NOT used to decide membership.
* **Suzerain gating** is proven by resolving each root's
  `SubjectRequirementSetId` to its `RequirementSetRequirements` and testing for
  an actual Suzerain-state requirement (`REQUIREMENT_PLAYER_IS_SUZERAIN` or
  `REQUIREMENT_PLAYER_IS_SUZERAIN_OF_X`), not from the modifier's name. An
  alliance-level requirement alone proves an alliance level, never Suzerain
  status; a bonus-enabled requirement alone is a global/config check.
* **The graph** follows `ModifierArguments.Name='ModifierId'` values that
  resolve to a real `Modifiers.ModifierId`, recursively, with cycle
  detection.
* **Unit-ability progression** is discovered mechanically as Unit TypeTags ->
  matching UnitAbility TypeTags -> UnitAbilityModifiers, with
  BuildingModifiers grant provenance retained. No name-prefix filter is used.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

# --------------------------------------------------------------------------
# Ownership design (report only - NOT implemented anywhere in Phase 5A).
# civ6x10.production.MODULE_BITS: traits 1, policies 2, governments 4,
# pantheons 8, wonders 16, governors 32 (implemented). Phase 5B would add
# 64 = suzerain; the next free bit after that would be 128.
# --------------------------------------------------------------------------
PROPOSED_SUZERAIN_MODULE_BIT = 64
PROPOSED_NEXT_MODULE_BIT_AFTER_SUZERAIN = 128

ACTIVE_CITY_STATE_LEVEL = "CIVILIZATION_LEVEL_CITY_STATE"

# Requirement types that prove Suzerain state (Phase 5A.1 corrected).
# Only these two are sufficient proof on their own:
# - REQUIREMENT_PLAYER_IS_SUZERAIN: the player is a Suzerain (of someone).
# - REQUIREMENT_PLAYER_IS_SUZERAIN_OF_X: the player is Suzerain of a specific
#   leader (used by side-path cases such as Lahore).
# The other two are additional FILTERS, never proof by themselves:
# - REQUIREMENT_PLAYER_IS_SUZERAIN_BONUS_ENABLED is a global/config enable
#   check, not player-state proof.
# - REQUIREMENT_PLAYER_HAS_ACTIVE_ALLIANCE_OF_AT_LEAST_LEVEL proves an
#   alliance level, NOT Suzerain status. The three Vilnius alliance-level
#   sets each contain BOTH an IS_SUZERAIN requirement AND an alliance-level
#   requirement; the alliance condition narrows, it does not prove.
SUZERAIN_STATE_PROOF_TYPES = {
    "REQUIREMENT_PLAYER_IS_SUZERAIN",
    "REQUIREMENT_PLAYER_IS_SUZERAIN_OF_X",
}
SUZERAIN_FILTER_TYPES = {
    "REQUIREMENT_PLAYER_IS_SUZERAIN_BONUS_ENABLED",
    "REQUIREMENT_PLAYER_HAS_ACTIVE_ALLIANCE_OF_AT_LEAST_LEVEL",
}
# Legacy name kept for compatibility; no longer used as the gate predicate.
SUZERAIN_GATE_REQUIREMENT_TYPES = (SUZERAIN_STATE_PROOF_TYPES
                                   | SUZERAIN_FILTER_TYPES)

# Arguments that name a type/target and are therefore never magnitudes.
SELECTOR_ARG_NAMES = {
    "ModifierId", "YieldType", "ImprovementType", "UnitType", "ResourceType",
    "GreatWorkObjectType", "GreatPersonClassType", "AbilityType",
    "PromotionClass", "DistrictType", "BuildingType", "SourceType",
    "UnitDomain", "DomainType", "EraType", "TerrainType", "FeatureType",
    "LeaderType", "Name", "Key",
}

# 0/1 configuration flags carried by otherwise-scalable effects.
BOOLEAN_ARG_NAMES = {"HasBonus", "IncludeWonder"}

# Curated semantic decisions for every effect that actually occurs in the
# reachable graph. Reuses the project's existing families instead of inventing
# Suzerain-specific synonyms.
CURATED_EFFECT_RULES = {
    # ---- scalable benefit magnitudes ------------------------------------
    "EFFECT_ADJUST_PLAYER_YIELD_MODIFIER_PER_EARNED_GREAT_PERSON": (
        "PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent yield modifier per earned great person (Antananarivo +2% "
        "culture per great person); percent magnitudes scale the effect"),
    "EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_DESTINATION_LUXURY_RESOURCE_FOR_INTERNATIONAL": (
        "GOLD", "CERTIFIED_CANDIDATE",
        "flat gold per luxury resource at the destination (Antioch +1); "
        "flat yield magnitude"),
    "EFFECT_ADJUST_CITY_GREATWORK_YIELD": (
        "FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat great-work yield change (Babylon +1/+2 science, Kandy +1 relic "
        "faith); float-safe yield magnitude (the ScalingFactor sibling is a "
        "separate, factor-vs-percent decision)"),
    "EFFECT_ADJUST_GREAT_PERSON_POINTS": (
        "GREAT_PERSON_POINTS", "CERTIFIED_CANDIDATE",
        "flat great-person points in cities with the matching building "
        "(Bologna +1 x9); certified GP point flow with a count-like gate"),
    "EFFECT_ADJUST_WONDER_PRODUCTION": (
        "PRODUCTION_PERCENT", "CERTIFIED_CANDIDATE",
        "percent wonder production (Brussels +15%)"),
    "EFFECT_ADJUST_OWNED_BONUS_RESOURCE_EXTRA_AMENITIES": (
        "AMENITY", "CERTIFIED_CANDIDATE",
        "extra amenity per owned bonus resource (Buenos Aires +1); amenities "
        "are float-valued in this project"),
    "EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_FOLLOWER": (
        "FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "faith per follower of the religion in the origin city (Chinguetti +1)"),
    "EFFECT_ADJUST_UNIT_INITIATION_YIELD_POPULATION": (
        "FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "science granted on unit initiation per city population (Fez +20); "
        "flat yield magnitude"),
    "EFFECT_ADJUST_CITY_YIELD_MODIFIER": (
        "PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent city yield modifier (Geneva +15% science, Taruga +5% per "
        "improved resource); reuses the certified mixed-domain ADDITIVE "
        "override that already covers this effect"),
    "EFFECT_ADJUST_CITY_GOLD_FROM_CITIZENS": (
        "GOLD", "CERTIFIED_CANDIDATE",
        "flat gold from citizens (Antioch-style +1); same certified GOLD "
        "flow magnitude as the Governor Tax Collector row"),
    "EFFECT_ADJUST_ALL_PROJECTS_PRODUCTION": (
        "PRODUCTION_PERCENT", "CERTIFIED_CANDIDATE",
        "percent all-projects production (Hong Kong +20%)"),
    "EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_PATH_TILE": (
        "GOLD", "CERTIFIED_CANDIDATE",
        "gold per path tile of an international trade route (Hunza +0.2); "
        "float-friendly gold yield magnitude"),
    "EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_POST_IN_FOREIGN_CITY": (
        "GOLD", "CERTIFIED_CANDIDATE",
        "gold per trading post in a foreign city (Jakarta +1)"),
    "EFFECT_ADJUST_YIELD_BY_NUMBER_OF_RESOURCES": (
        "FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat yield per resource type in the city (Johannesburg +1 "
        "production); the resource count is a combinator, not a magnitude"),
    "EFFECT_ADJUST_CITY_STATE_TRADE_ROUTE_DISTRICT_YIELD": (
        "FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat yield per city-state trade route to a district (Kumasi +2 "
        "culture / +1 gold)"),
    "EFFECT_ADJUST_CITY_AMENITIES_FROM_CITY_STATES": (
        "AMENITY", "CERTIFIED_CANDIDATE",
        "amenities from city-states in a commercial-hub city (Muscat +1)"),
    "EFFECT_ADJUST_DISTRICT_YIELD_CHANGE": (
        "FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat district yield change on/adjacent to coast (Nan Madol +2 "
        "culture)"),
    "EFFECT_ADJUST_CITY_GROWTH": (
        "PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent city growth in a campus city (Palenque +15%)"),
    "EFFECT_ADJUST_PLAYER_INTERNATIONAL_TRADE_ROUTE_YIELD_PER_IMPROVEMENT_IN_ORIGIN_CITY": (
        "FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat gold per trading dome in the origin city of an international "
        "trade route (Samarkand +1)"),
    "EFFECT_ADJUST_CITY_YIELD_PER_MAJOR_TRADE_PARTNER": (
        "FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat production per major-civ trade partner (Singapore +2)"),
    "EFFECT_ADJUST_PLOT_YIELD": (
        "FLAT_YIELD", "CERTIFIED_CANDIDATE",
        "flat shallow-water plot yield (Auckland +1 production, base and "
        "industrial-era variants); reuses the certified plot-yield ADDITIVE "
        "override; the era/terrain requirement is a filter, not a magnitude"),
    "EFFECT_ADJUST_DISTRICT_YIELD_MODIFIER": (
        "PERCENT_BONUS", "CERTIFIED_CANDIDATE",
        "percent theater-square culture (Vilnius +50% at alliance levels "
        "1/2/3); percent modifier scales the effect"),
    "EFFECT_ADJUST_UNIT_ATTACK_EXPERIENCE_MODIFIER": (
        "EXPERIENCE", "CERTIFIED_CANDIDATE",
        "percent attack-experience modifier for units (Kabul +100%); "
        "certified EXPERIENCE family"),
    "EFFECT_ADJUST_ALL_UNITS_PURCHASE_COST": (
        "PERCENT_DISCOUNT", "CERTIFIED_CANDIDATE",
        "percent land unit purchase cost reduction (Ngazargamu -20%); "
        "curated PERCENT_DISCOUNT (boundary -100 is the free fixed point)"),
    "EFFECT_ADJUST_BUILDING_PURCHASE_COST": (
        "PERCENT_DISCOUNT", "DECISION_REQUIRED",
        "building purchase cost reduction (Valletta -50 for walls, star fort, "
        "castle): the effect is NOT in the project's curated discount table, "
        "so the closed-world certification gate refuses it "
        "(conflict:unclassified-discount-effect). Percent-versus-flat "
        "semantics need a curated decision before it can ship."),
    # ---- resource grants: quantity only ---------------------------------
    "EFFECT_ADJUST_PLAYER_FREE_RESOURCE_IMPORT": (
        "INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "quantity of a granted luxury/special resource (Zanzibar +1 cinnamon "
        "and +1 cloves): the GRANT QUANTITY is scalable in principle, but "
        "resource imports are a whole-unit flow, so the count-like integral "
        "gate and the grant-ownership question both need review"),
    "EFFECT_ADJUST_PLAYER_FREE_RESOURCE_IMPORT_EXTRACTION": (
        "INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "quantity of a granted strategic resource extracted per turn (Hattusa "
        "+2 x7): a whole-unit strategic flow, so the count-like integral "
        "gate and the grant-ownership question both need review"),
    # ---- counts / whole-unit flows needing an integral gate --------------
    "EFFECT_ADJUST_CITY_FREE_POWER": (
        "INDIVISIBLE_COUNT", "DECISION_REQUIRED",
        "power granted free per turn (Cardiff +2 x3); granted power counts "
        "whole power units, so the effect is count-like - the family is not "
        "an allowlisted certified category in this project, so the closed "
        "world gate refuses until a curated count-like decision exists"),
    # ---- factor / unresolved scaling ------------------------------------
    "EFFECT_ADJUST_CITY_GREATWORK_YIELD__SCALINGFACTOR": (
        "MULTIPLICATIVE_FACTOR", "DECISION_REQUIRED",
        "great-work yield ScalingFactor (Kandy relic 150): factor-vs-percent "
        "unresolved (same precedent as the tourism ScalingFactor family)"),
    "EFFECT_GRANT_CITY_YIELD_PERCENT_BUILDING_CREATED_COST": (
        "PERCENT_BONUS", "DECISION_REQUIRED",
        "percent of a completed building's production cost granted as yield "
        "(Ayutthaya +10% culture); grant-on-completion percent semantics are "
        "unresolved (same precedent as the governor Citadel-of-God row)"),
    # ---- pressure / loyalty --------------------------------------------
    "EFFECT_ADJUST_CITY_IDENTITY_PER_TURN": (
        "LOYALTY", "DECISION_REQUIRED",
        "identity/loyalty per turn in a city with the matching building "
        "(Preslav +2 x3); same pressure class as the Governor Toqui hold, "
        "which is excluded pending store-lookup re-certification"),
    "EFFECT_GRANT_PLAYER_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED": (
        "LOYALTY", "DECISION_REQUIRED",
        "religious pressure per great person activated (Vatican City 400); "
        "a pressure rate, so it shares the loyalty/pressure hold"),
    # ---- grants / objects / capabilities --------------------------------
    "EFFECT_ADJUST_DISTRICT_EXTRA_REGIONAL_RANGE": (
        "SPATIAL_BUDGET", "EXCLUDED",
        "extra regional range in whole tiles (Mexico City +3); a spatial "
        "budget, not a benefit magnitude"),
    "EFFECT_GRANT_PLAYER_RANDOM_TECHNOLOGY": (
        "GRANT_OBJECT", "EXCLUDED",
        "grants one free random technology when the player has a Mahavihara "
        "(Nalanda); a technology grant, not a scalable magnitude"),
    "EFFECT_ADJUST_NATURAL_WONDER_RELIC": (
        "GRANT_OBJECT", "EXCLUDED",
        "grants a relic from each natural wonder (Kandy +1); a relic grant, "
        "not a scalable magnitude"),
    "EFFECT_TREAT_HOLY_SITE_AS_HOLY_CITY": (
        "BOOLEAN_UNLOCK", "EXCLUDED",
        "treats holy sites as holy cities (Jerusalem Value=1); a capability "
        "toggle, not a magnitude"),
    "EFFECT_ADJUST_CITIES_FRESHWATER_HOUSING_BONUS": (
        "BOOLEAN_UNLOCK", "EXCLUDED",
        "grants the fresh-water housing bonus to all cities (Mohenjo-daro "
        "HasBonus=1); a capability toggle, not a magnitude"),
    "EFFECT_ADJUST_PLAYER_VALID_IMPROVEMENT": (
        "GRANT_OBJECT", "EXCLUDED",
        "unlocks an improvement for the player (nine city-states); a "
        "structural capability - its attached data is audited as a side path"),
    "EFFECT_ADJUST_PLAYER_VALID_UNIT_BUILD": (
        "GRANT_OBJECT", "EXCLUDED",
        "unlocks a unit for the player (Lahore Nihang); a structural "
        "capability - its attached data is audited as a side path"),
    "EFFECT_GRANT_ABILITY": (
        "GRANT_OBJECT", "EXCLUDED",
        "grants a unit ability (Lisbon/Wolin); a capability grant - the "
        "ability's own modifier is a side path"),
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_PROMOTION_CLASS": (
        "BOOLEAN_UNLOCK", "EXCLUDED",
        "lets a promotion class attack walls all game (Akkad); a capability "
        "toggle per promotion class, not a magnitude"),
    "EFFECT_ENABLE_BUILDING_FAITH_PURCHASE": (
        "BOOLEAN_UNLOCK", "EXCLUDED",
        "enables faith purchase of buildings in a district (Valletta); a "
        "capability toggle, not a magnitude"),
    "EFFECT_GRANT_UNIT_TYPE_UNLIMITED_PROMOTION_CHOICES": (
        "BOOLEAN_UNLOCK", "EXCLUDED",
        "grants unlimited promotion choices for apostles (Yerevan); a "
        "capability toggle, not a magnitude"),
    "EFFECT_ATTACH_MODIFIER": (
        "GRANT_OBJECT", "EXCLUDED",
        "root wrapper attaching a nested modifier; the nested definition is "
        "audited through ModifierId traversal"),
    # ---- effects that only occur on the side paths (unique improvements) --
    "EFFECT_ADJUST_IMPROVEMENT_HOUSING": (
        "HOUSING", "DECISION_REQUIRED",
        "housing granted by an unlocked improvement; a magnitude attached to "
        "the improvement, not to the Suzerain bonus"),
    "EFFECT_ADJUST_IMPROVEMENT_AMENITY": (
        "AMENITY", "DECISION_REQUIRED",
        "amenity granted by an unlocked improvement; a magnitude attached to "
        "the improvement, not to the Suzerain bonus"),
}

# Arguments that are magnitudes on the side paths (unique units).
# Families here must match the existing effect-semantic floor where one
# exists; ownership stays DECISION_REQUIRED regardless (see
# classify_side_path_argument), so the family describes the number while the
# disposition records that it lives outside the Suzerain graph.
SIDE_PATH_EFFECT_RULES = {
    "EFFECT_ADJUST_UNIT_POST_COMBAT_YIELD": (
        "DEFEATED_STRENGTH_SCALING", "DECISION_REQUIRED",
        "post-combat yield scaled by defeated strength (Nihang faith 50%): "
        "the floor classifies PercentDefeatedStrength as "
        "DEFEATED_STRENGTH_SCALING, not a flat yield; unit-intrinsic "
        "magnitude reached only through the granted unit's promotion"),
    "EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER": (
        "COMBAT_STRENGTH_BONUS", "DECISION_REQUIRED",
        "combat-strength points (Nihang flanked +7, Suzerain-gated +10): "
        "the floor certifies this Amount as COMBAT_STRENGTH_BONUS "
        "(FORMULA_DERIVED); side-path ownership keeps it a decision"),
    "EFFECT_ADJUST_UNIT_COMBAT_STRENGTH": (
        "COMBAT_STRENGTH_BONUS", "DECISION_REQUIRED",
        "base combat-strength points (Nihang barracks/armory/academy +15): "
        "combat-strength points by definition, but intrinsic progression "
        "bonuses of the unlocked unit, so ownership stays a decision. "
        "NOTE: the floor row for this tuple is MAGNITUDE_UNCLASSIFIED / "
        "NEEDS_REVIEW (unreviewed), so this family is an explicit audit "
        "override with no production consequence while the row stays "
        "DECISION_REQUIRED."),
    "EFFECT_ADJUST_UNIT_MOVEMENT": (
        "SPATIAL_BUDGET", "DECISION_REQUIRED",
        "movement points (Nihang +1): the floor treats movement Amount as "
        "SPATIAL_BUDGET, not an automatically certified magnitude; "
        "unit-intrinsic magnitude reached only through the granted unit's "
        "promotion"),
    "EFFECT_ADJUST_UNIT_NO_REDUCTION_DAMAGE": (
        "BOOLEAN_UNLOCK", "DECISION_REQUIRED",
        "no-wounded-penalty capability (Nihang); unit-intrinsic capability "
        "reached only through the granted unit's promotion"),
    "EFFECT_ADJUST_GREAT_PEOPLE_POINTS_PER_KILL_BY_DEFEATED_STRENGTH": (
        "DEFEATED_STRENGTH_SCALING", "DECISION_REQUIRED",
        "great-person points per kill scaled by defeated strength (Wolin "
        "ability +25): a coefficient/rate tied to defeated-unit strength, "
        "NOT ordinary discrete GREAT_PERSON_POINTS. NOTE: the floor row for "
        "this tuple is MAGNITUDE_UNCLASSIFIED / NEEDS_REVIEW, so this family "
        "is an explicit audit override. The invariant it protects: a future "
        "production implementation must not inherit the GREAT_PERSON_POINTS "
        "count-like gate merely because the result is eventually paid as GP "
        "points."),
    "EFFECT_ADJUST_UNIT_TRADE_ROUTE_PLUNDER_IMMUNITY": (
        "BOOLEAN_UNLOCK", "EXCLUDED",
        "trade-route plunder immunity for a domain (Lisbon ability); a "
        "capability grant with no magnitude"),
}

# Numeric arguments whose effect-specific decision is keyed on the pair.
PAIR_EFFECT_RULES = {
    ("EFFECT_ADJUST_CITY_GREATWORK_YIELD", "ScalingFactor"):
        CURATED_EFFECT_RULES["EFFECT_ADJUST_CITY_GREATWORK_YIELD__SCALINGFACTOR"],
}

DEFAULT_RULE = ("DECISION_REQUIRED", "DECISION_REQUIRED",
                "no curated Suzerain semantics for this effect")


def _is_numeric(value) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def classify_argument(effect_type: str, argument_name: str, argument_value):
    """Classify one reachable argument into the audit vocabulary."""
    if argument_name in SELECTOR_ARG_NAMES:
        return {"family": "SELECTOR", "disposition": "EXCLUDED",
                "reason": "selector/type/reference argument, never a magnitude",
                "engine_integral": False}
    if not _is_numeric(argument_value):
        return {"family": "SELECTOR", "disposition": "EXCLUDED",
                "reason": "non-numeric reference value",
                "engine_integral": False}
    if argument_name in BOOLEAN_ARG_NAMES:
        return {"family": "BOOLEAN_UNLOCK", "disposition": "EXCLUDED",
                "reason": "0/1 configuration flag, not a benefit magnitude",
                "engine_integral": False}
    fam, disp, reason = PAIR_EFFECT_RULES.get(
        (effect_type, argument_name),
        CURATED_EFFECT_RULES.get(effect_type, DEFAULT_RULE))
    return {"family": fam, "disposition": disp, "reason": reason,
            "engine_integral": False}


def classify_side_path_argument(effect_type: str, argument_name: str,
                                argument_value) -> dict:
    """Classify an argument that is NOT in the Suzerain modifier graph.

    Side-path cells are never certified candidates on their own: a value can
    only join the 10x Suzerain module when it is semantically part of the
    Suzerain ability, which is an explicit ownership decision. This function
    therefore reports the family the row WOULD take and forces
    DECISION_REQUIRED for anything that is not structurally excluded.
    """
    if argument_name in SELECTOR_ARG_NAMES or not _is_numeric(argument_value):
        return classify_argument(effect_type, argument_name, argument_value)
    if argument_name in BOOLEAN_ARG_NAMES:
        return classify_argument(effect_type, argument_name, argument_value)
    fam, disp, reason = PAIR_EFFECT_RULES.get(
        (effect_type, argument_name),
        SIDE_PATH_EFFECT_RULES.get(effect_type,
                                   CURATED_EFFECT_RULES.get(effect_type,
                                                            DEFAULT_RULE)))
    if disp == "EXCLUDED":
        return {"family": fam, "disposition": "EXCLUDED", "reason": reason,
                "engine_integral": False}
    return {"family": fam, "disposition": "DECISION_REQUIRED",
            "reason": ("ownership decision: this value is semantically "
                       f"part of the {fam} family but lives OUTSIDE the "
                       "Suzerain modifier graph, so it is not claimed until "
                       "its ownership of the Suzerain ability is decided - "
                       + reason),
            "engine_integral": False}


# --------------------------------------------------------------------------
# Side-path semantic-floor consistency
# --------------------------------------------------------------------------
def side_path_cells_with_tuples(audit: dict) -> list[dict]:
    """Every side-path cell that carries an ordinary ModifierType/Effect/arg.

    Only these cells can be cross-checked against the effect-semantic floor;
    direct-table cells (Units/Improvements columns, yields, tourism, ...) have
    no modifier tuple and are therefore out of scope for this check.
    """
    out: list[dict] = []
    for unit_type, path in (audit.get("side_paths", {}).get("units") or {}).items():
        for m in path.get("promotion_modifiers", []):
            out.append({"cell": f"UnitPromotionModifiers.{m['modifier_id']}."
                                f"{m['argument_name']}",
                        "modifier_type": m["modifier_type"],
                        "effect_type": m["effect_type"],
                        "argument_name": m["argument_name"],
                        "audit_family": m["family"],
                        "audit_disposition": m["disposition"]})
        for m in path.get("ability_modifiers", []):
            out.append({"cell": f"UnitAbilityModifiers.{m['modifier_id']}."
                                f"{m['argument_name']}",
                        "modifier_type": m["modifier_type"],
                        "effect_type": m["effect_type"],
                        "argument_name": m["argument_name"],
                        "audit_family": m["family"],
                        "audit_disposition": m["disposition"]})
    for ab, path in (audit.get("side_paths", {}).get("abilities") or {}).items():
        for m in path.get("modifiers", []):
            out.append({"cell": f"UnitAbilityModifiers.{m['modifier_id']}."
                                f"{m['argument_name']}",
                        "modifier_type": m["modifier_type"],
                        "effect_type": m["effect_type"],
                        "argument_name": m["argument_name"],
                        "audit_family": m["family"],
                        "audit_disposition": m["disposition"]})
    for imp, path in (audit.get("side_paths", {}).get("improvements") or {}).items():
        for am in path.get("attached_modifiers", []):
            for c in path.get("cells", []):
                prefix = f"ImprovementModifiers.{am['modifier_id']}."
                if not c["cell"].startswith(prefix):
                    continue
                out.append({"cell": c["cell"],
                            "modifier_type": am["modifier_type"],
                            "effect_type": am["effect_type"],
                            "argument_name": c["cell"][len(prefix):],
                            "audit_family": c["family"],
                            "audit_disposition": c["disposition"]})
    out.sort(key=lambda c: c["cell"])
    return out


def check_side_path_floor_consistency(cells: list[dict],
                                      floor: dict) -> dict:
    """Cross-check side-path families against the effect-semantic floor.

    `floor` maps (modifier_type, effect_type, argument_name) -> row with at
    least `semantic_family` and `confidence`. Every agreement and every
    explicit override is recorded; nothing is silently re-labelled.
    """
    details: list[dict] = []
    for c in cells:
        key = (c["modifier_type"], c["effect_type"], c["argument_name"])
        frow = floor.get(key)
        if frow is None:
            details.append({**c, "floor_family": None,
                            "floor_confidence": None,
                            "agreement": None,
                            "note": "no floor row for this tuple"})
            continue
        ff = frow.get("semantic_family")
        agreement = (c["audit_family"] == ff)
        details.append({**c, "floor_family": ff,
                        "floor_confidence": frow.get("confidence"),
                        "agreement": agreement,
                        "note": ("agreement" if agreement
                                 else "explicit audit override, justified in "
                                      "SIDE_PATH_EFFECT_RULES")})
    return {
        "cells_checked": len(details),
        "agreements": sum(1 for d in details if d["agreement"] is True),
        "disagreements": sum(1 for d in details if d["agreement"] is False),
        "no_floor_row": sum(1 for d in details if d["agreement"] is None),
        "details": details,
    }


def load_floor_for_consistency(sem_floor_path: str | Path | None,
                               root: str | Path | None = None) -> dict | None:
    """Load the effect-semantic floor when available, else None (CI-safe).

    `sem_floor_path`, when given, wins. Otherwise the conventional
    `data/local/effect_semantics.csv` next to `root` is used when present.
    A missing file is not an error: the caller records `available: false`.
    """
    if sem_floor_path:
        p = Path(sem_floor_path)
        if not p.is_file():
            return None
    else:
        base = Path(root) if root else Path(".")
        p = base / "data" / "local" / "effect_semantics.csv"
        if not p.is_file():
            return None
    with open(p, encoding="utf-8", newline="") as fh:
        return {(r["modifier_type"], r["effect_type"], r["argument_name"]): r
                for r in csv.DictReader(fh)}

# --------------------------------------------------------------------------
# Active City-State discovery (authoritative, derived from the runtime DB)
# --------------------------------------------------------------------------
ACTIVE_DISCOVERY_SQL = """
SELECT c.CivilizationType, c.Name AS CivilizationName,
       cl.LeaderType, l.Name AS LeaderName,
       x.MinorCivBonusType, lt.TraitType
FROM Civilizations c
JOIN CivilizationLeaders cl ON cl.CivilizationType = c.CivilizationType
JOIN Leaders l             ON l.LeaderType = cl.LeaderType
JOIN Leaders_XP2 x         ON x.LeaderType = cl.LeaderType
JOIN LeaderTraits lt       ON lt.LeaderType = cl.LeaderType
WHERE c.StartingCivilizationLevelType = ?
ORDER BY c.CivilizationType, lt.TraitType
"""

ORPHAN_DISCOVERY_SQL = """
SELECT l.LeaderType, l.Name AS LeaderName, x.MinorCivBonusType
FROM Leaders l
JOIN Leaders_XP2 x ON x.LeaderType = l.LeaderType
WHERE x.MinorCivBonusType IS NOT NULL AND x.MinorCivBonusType <> ''
  AND l.LeaderType NOT IN (SELECT LeaderType FROM CivilizationLeaders)
ORDER BY l.LeaderType
"""


def discover_city_states(db) -> list[dict]:
    """Active City-States: civilization level + leader mapping + minor trait.

    Membership is derived from the shipped `Civilizations` /
    `CivilizationLeaders` / `Leaders_XP2` / `LeaderTraits` chain only.
    """
    rows = []
    for r in db.execute(ACTIVE_DISCOVERY_SQL, (ACTIVE_CITY_STATE_LEVEL,)):
        d = dict(r)
        d["trait_name"] = _lookup(db, "Traits", "TraitType",
                                  d["TraitType"], "Name")
        d["minor_civ_bonus_name"] = _lookup(
            db, "MinorCivBonuses", "MinorCivBonusType",
            d["MinorCivBonusType"], "Name")
        d["provenance"] = {
            "source": "official runtime DB",
            "chain": ("Civilizations.StartingCivilizationLevelType="
                      + ACTIVE_CITY_STATE_LEVEL
                      + " -> CivilizationLeaders -> Leaders_XP2 -> LeaderTraits"),
            "minor_civ_bonus_present": bool(d["MinorCivBonusType"]),
        }
        rows.append(d)
    return rows


def discover_orphan_minor_leaders(db, active_leader_types: set) -> list[dict]:
    """Minor leaders present in the DB but with no CivilizationLeaders mapping.

    These are historical / orphan definitions. They are accounted, never
    silently included and never silently dropped: they cannot reach a trait
    root because no civilization maps the leader.
    """
    out = []
    for r in db.execute(ORPHAN_DISCOVERY_SQL):
        d = dict(r)
        assert d["LeaderType"] not in active_leader_types
        traits = [t["TraitType"] for t in db.execute(
            "SELECT TraitType FROM LeaderTraits WHERE LeaderType=?",
            (d["LeaderType"],))]
        d["traits"] = traits
        d["status"] = "inactive_orphan"
        d["reason"] = ("minor leader with no CivilizationLeaders mapping: no "
                       "civilization is this city-state, so the trait is "
                       "unreachable as a Suzerain root")
        d["provenance"] = {
            "source": "official runtime DB",
            "evidence": "Leaders_XP2.MinorCivBonusType present AND "
                        "LeaderType absent from CivilizationLeaders",
        }
        out.append(d)
    return out


def _lookup(db, table: str, key_col: str, key, value_col: str):
    row = db.execute(
        f'SELECT "{value_col}" AS v FROM "{table}" WHERE "{key_col}"=?',
        (key,)).fetchone()
    return row[0] if row else None


# --------------------------------------------------------------------------
# Suzerain gating proof
# --------------------------------------------------------------------------
def requirement_set_requirements(db, set_id) -> list[dict]:
    if not set_id:
        return []
    out = []
    for r in db.execute(
            """SELECT r.RequirementId, r.RequirementType, ra.Name, ra.Value
               FROM RequirementSetRequirements s
               JOIN Requirements r ON r.RequirementId = s.RequirementId
               LEFT JOIN RequirementArguments ra ON ra.RequirementId = r.RequirementId
               WHERE s.RequirementSetId = ? ORDER BY r.RequirementId""",
            (set_id,)):
        out.append(dict(r))
    return out


def is_suzerain_gated(db, requirement_set_id) -> tuple[bool, list[dict]]:
    """True when the set proves the subject is a Suzerain (or Suzerain+ally).

    Proof requires an actual Suzerain-state requirement
    (REQUIREMENT_PLAYER_IS_SUZERAIN or REQUIREMENT_PLAYER_IS_SUZERAIN_OF_X).
    An alliance-level requirement alone proves an alliance level, not Suzerain
    status; a bonus-enabled requirement alone is a global/config check, not
    player-state proof. Either may narrow a Suzerain-gated set, but neither
    gates on its own.
    """
    reqs = requirement_set_requirements(db, requirement_set_id)
    gated = any(r["RequirementType"] in SUZERAIN_STATE_PROOF_TYPES
                for r in reqs)
    return gated, reqs


# --------------------------------------------------------------------------
# Modifier graph (roots + recursive ModifierId traversal, cycle-safe)
# --------------------------------------------------------------------------
def _modifier_row(db, modifier_id):
    return db.execute("SELECT * FROM Modifiers WHERE ModifierId=?",
                      (modifier_id,)).fetchone()


def _modifier_arguments(db, modifier_id) -> list[dict]:
    return [dict(r) for r in db.execute(
        "SELECT * FROM ModifierArguments WHERE ModifierId=? ORDER BY Name",
        (modifier_id,))]


def _effect_for(db, modifier_type):
    row = db.execute("SELECT EffectType, CollectionType FROM DynamicModifiers "
                     "WHERE ModifierType=?", (modifier_type,)).fetchone()
    return (dict(row) if row else
            {"EffectType": None, "CollectionType": None})


def build_graph(db, active: list[dict]) -> dict:
    """Closed modifier graph rooted at the active Suzerain TraitModifiers.

    Follows only `ModifierArguments.Name='ModifierId'` values that resolve to
    a real `Modifiers.ModifierId`, recursively. Cycles are detected and
    recorded, not assumed absent.
    """
    roots: list[dict] = []
    not_gated: list[dict] = []
    for row in active:
        trait = row["TraitType"]
        for tm in db.execute(
                """SELECT tm.ModifierId, m.ModifierType,
                          m.OwnerRequirementSetId, m.SubjectRequirementSetId,
                          m.RunOnce, m.Permanent, m.NewOnly, m.Repeatable
                   FROM TraitModifiers tm
                   JOIN Modifiers m ON m.ModifierId = tm.ModifierId
                   WHERE tm.TraitType = ? ORDER BY tm.ModifierId""",
                (trait,)):
            root = dict(tm)
            gated, reqs = is_suzerain_gated(db, root["SubjectRequirementSetId"])
            root["trait_type"] = trait
            root["city_state"] = row["CivilizationType"]
            root["leader"] = row["LeaderType"]
            root["gated"] = gated
            root["gate_requirements"] = reqs
            root["gate_set"] = root["SubjectRequirementSetId"]
            if gated:
                roots.append(root)
            else:
                root["flag"] = ("active minor-civ trait root that is NOT "
                                "Suzerain-gated (flagged, not silently "
                                "included)")
                not_gated.append(root)

    definitions: dict[str, dict] = {}
    edges: list[dict] = []
    cycles: list[dict] = []

    def visit(modifier_id, path, depth):
        """Depth-first traversal; returns the recorded definition id."""
        m = _modifier_row(db, modifier_id)
        if m is None:
            return None
        m = dict(m)
        eff = _effect_for(db, m["ModifierType"])
        node = definitions.setdefault(modifier_id, {
            "modifier_id": modifier_id,
            "modifier_type": m["ModifierType"],
            "effect_type": eff["EffectType"],
            "collection_type": eff["CollectionType"],
            "owner_requirement_set_id": m["OwnerRequirementSetId"],
            "subject_requirement_set_id": m["SubjectRequirementSetId"],
            "subject_requirements": requirement_set_requirements(
                db, m["SubjectRequirementSetId"]),
            "owner_requirements": requirement_set_requirements(
                db, m["OwnerRequirementSetId"]),
            "run_once": m["RunOnce"], "permanent": m["Permanent"],
            "new_only": m["NewOnly"], "repeatable": m["Repeatable"],
            "arguments": _modifier_arguments(db, modifier_id),
            "depth": depth, "path": list(path),
            "referenced_by": [],
        })
        node["depth"] = min(node["depth"], depth)
        for a in node["arguments"]:
            if a["Name"] != "ModifierId":
                continue
            target = a["Value"]
            if _modifier_row(db, target) is None:
                continue
            if target in path + [modifier_id]:
                cycles.append({"from": modifier_id, "to": target,
                               "path": list(path) + [modifier_id]})
                continue
            edges.append({"from": modifier_id, "to": target,
                          "argument": "ModifierId"})
            node["referenced_by"] = node["referenced_by"]
            visit(target, path + [modifier_id], depth + 1)
        return modifier_id

    for root in roots:
        visit(root["ModifierId"], [], 0)

    return {"roots": roots, "not_gated_roots": not_gated,
            "definitions": definitions, "edges": edges, "cycles": cycles}

# --------------------------------------------------------------------------
# Reachable argument rows with dispositions
# --------------------------------------------------------------------------
def build_rows(db, graph: dict) -> list[dict]:
    """One row per reachable (modifier, argument), each with a disposition."""
    root_by_modifier = {r["ModifierId"]: r for r in graph["roots"]}
    root_of_definition: dict[str, tuple[dict, str]] = {}

    # map every reachable definition to its owning root (a definition can be
    # reachable from more than one root; the first sorted root wins)
    for root in sorted(graph["roots"], key=lambda r: r["ModifierId"]):
        stack = [(root["ModifierId"], root["ModifierId"])]
        seen = set()
        while stack:
            cur, came_from = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            root_of_definition.setdefault(cur, (root, came_from))
            for e in graph["edges"]:
                if e["from"] == cur:
                    stack.append((e["to"], cur))

    rows: list[dict] = []
    for modifier_id in sorted(graph["definitions"]):
        node = graph["definitions"][modifier_id]
        root, via = root_of_definition[modifier_id]
        is_root = (modifier_id == root["ModifierId"])
        for arg in node["arguments"]:
            cls = classify_argument(node["effect_type"], arg["Name"],
                                    arg["Value"])
            rows.append({
                "row_id": f"{modifier_id}:{arg['Name']}",
                "city_state": root["city_state"],
                "leader": root["leader"],
                "trait_type": root["trait_type"],
                "root_modifier_id": root["ModifierId"],
                "root_gate_set": root["gate_set"],
                "is_root": is_root,
                "reached_via": via,
                "depth": node["depth"],
                "path": node["path"],
                "modifier_id": modifier_id,
                "modifier_type": node["modifier_type"],
                "effect_type": node["effect_type"],
                "collection_type": node["collection_type"],
                "owner_requirement_set_id": node["owner_requirement_set_id"],
                "subject_requirement_set_id": node["subject_requirement_set_id"],
                "subject_requirements": node["subject_requirements"],
                "owner_requirements": node["owner_requirements"],
                "argument_name": arg["Name"],
                "argument_type": arg["Type"],
                "argument_value": arg["Value"],
                "numeric": _is_numeric(arg["Value"]),
                "family": cls["family"],
                "disposition": cls["disposition"],
                "reason": cls["reason"],
                "engine_integral": cls["engine_integral"],
                "provenance": {"source": "official runtime DB",
                               "table": "ModifierArguments"},
            })
    rows.sort(key=lambda r: r["row_id"])
    return rows


# --------------------------------------------------------------------------
# Side paths: unique improvements
# --------------------------------------------------------------------------
IMPROVEMENT_UNLOCK_EFFECT = "EFFECT_ADJUST_PLAYER_VALID_IMPROVEMENT"

# Every numeric gameplay column of the official Improvements table, each with
# an explicit ownership decision. Structural/placement/boolean columns are
# recorded once per improvement instead of per-column.
IMPROVEMENT_COLUMN_RULES = {
    # plausible part of the unlocked improvement's benefit -> ownership review
    "Housing": ("HOUSING", "DECISION_REQUIRED",
                "base housing of the unlocked improvement: plausibly part of "
                "the ability but needs an explicit ownership decision"),
    "Appeal": ("APPEAL", "DECISION_REQUIRED",
               "base appeal of the unlocked improvement: a property of the "
               "improvement itself, not of the Suzerain grant"),
    "ReligiousUnitHealRate": ("FLAT_AMOUNT", "DECISION_REQUIRED",
                              "per-turn religious-unit healing on the "
                              "improvement: a property of the improvement"),
    "DefenseModifier": ("FLAT_AMOUNT", "DECISION_REQUIRED",
                        "district defense granted by the unlocked "
                        "improvement (Alcazar +4): a magnitude, but attached "
                        "to the improvement rather than the Suzerain bonus"),
    "YieldFromAppealPercent": ("PERCENT_BONUS", "DECISION_REQUIRED",
                               "percent of appeal converted to a yield by the "
                               "unlocked improvement (Alcazar 50): factor-vs-"
                               "percent scaling unresolved"),
    "PlunderAmount": ("GOLD", "EXCLUDED",
                      "plunder paid to an ATTACKER when the improvement is "
                      "pillaged; not a benefit of the Suzerain bonus at all"),
    "DispersalGold": ("GOLD", "EXCLUDED",
                      "gold dispersed when the improvement is removed by a "
                      "goody hut; not part of the Suzerain bonus"),
    "MovementChange": ("MOVEMENT", "EXCLUDED",
                       "terrain movement cost of the improvement's plot; a "
                       "structural terrain property"),
    "TilesRequired": ("INDIVISIBLE_COUNT", "EXCLUDED",
                      "placement rule (tiles that must be converted); a "
                      "structural constraint, not a magnitude"),
    "ValidAdjacentTerrainAmount": ("INDIVISIBLE_COUNT", "EXCLUDED",
                                   "placement rule (adjacent terrain count "
                                   "requirement); structural"),
    "MinimumAppeal": ("APPEAL", "EXCLUDED",
                      "placement requirement (minimum appeal); structural, "
                      "not a magnitude"),
    "Goody": ("BOOLEAN_UNLOCK", "EXCLUDED",
              "goody-hut flag; structural configuration"),
    "TilesPerGoody": ("INDIVISIBLE_COUNT", "EXCLUDED",
                      "goody-hut placement rule; structural"),
    "GoodyRange": ("INDIVISIBLE_COUNT", "EXCLUDED",
                   "goody-hut range rule; structural"),
    "AirSlots": ("SLOT_CAPACITY", "EXCLUDED",
                 "air slots on the improvement; structural capacity"),
    "WeaponSlots": ("SLOT_CAPACITY", "EXCLUDED",
                    "weapon slots on the improvement; structural capacity"),
    "Buildable": ("BOOLEAN_UNLOCK", "EXCLUDED", "structural configuration"),
    "BarbarianCamp": ("BOOLEAN_UNLOCK", "EXCLUDED", "structural configuration"),
}

# Columns that are 0/1 flags or placement rules: accounted per improvement as
# a structural list rather than one row per column.
IMPROVEMENT_STRUCTURAL_COLUMNS = [
    "SameAdjacentValid", "RequiresRiver", "EnforceTerrain", "BuildInLine",
    "CanBuildOutsideTerritory", "BuildOnFrontier", "OnePerCity",
    "GrantFortification", "Coast", "AdjacentSeaResource",
    "RequiresAdjacentBonusOrLuxury", "Workable", "GoodyNotify",
    "NoAdjacentSpecialtyDistrict", "RequiresAdjacentLuxury", "AdjacentToLand",
    "Removable", "OnlyOpenBorders", "Capturable", "RemoveOnEntry",
]

IMPROVEMENT_SELECTOR_COLUMNS = [
    "Name", "Description", "Icon", "PrereqTech", "PrereqCivic", "PlunderType",
    "Domain", "YieldFromAppeal", "ImprovementOnRemove", "TraitType",
]

# Numeric magnitude columns of the side-path tables that ARE treated as
# substantive magnitudes (but still ownership-reviewed).
SIDE_PATH_MAGNITUDE_RULES = {
    "YieldChange": ("FLAT_YIELD", "DECISION_REQUIRED",
                    "flat yield of the unlocked improvement / adjacency; a "
                    "substantive magnitude, but whether it is part of the "
                    "Suzerain ability is an ownership decision"),
    "Amount": ("FLAT_YIELD", "DECISION_REQUIRED",
               "flat magnitude attached to the unlocked improvement through "
               "ImprovementModifiers; ownership decision required"),
    "ScalingFactor": ("MULTIPLICATIVE_FACTOR", "DECISION_REQUIRED",
                      "ScalingFactor=100 for improvement tourism: factor-vs-"
                      "percent analysis required (the project already holds "
                      "this open for wonders), not naive multiplication"),
    "TilesRequired__adjacency": ("INDIVISIBLE_COUNT", "EXCLUDED",
                                 "adjacency placement rule (tiles required to "
                                 "qualify); structural"),
    "ConsumesCharge": ("CHARGES", "EXCLUDED",
                       "builder charges consumed to build the improvement; "
                       "structural build cost"),
}


def discover_improvement_unlocks(graph: dict) -> dict[str, list[dict]]:
    """Mechanically discover the unlocked improvements from the graph."""
    out: dict[str, list[dict]] = defaultdict(list)
    for row_key, node in graph["definitions"].items():
        if node["effect_type"] != IMPROVEMENT_UNLOCK_EFFECT:
            continue
        for arg in node["arguments"]:
            if arg["Name"] != "ImprovementType":
                continue
            out[arg["Value"]].append({
                "modifier_id": node["modifier_id"],
                "modifier_type": node["modifier_type"],
                "city_state": node.get("city_state"),
            })
    return dict(out)


def _zero_shipped(value) -> bool:
    """True when a numeric cell's shipped value is zero.

    A zero-valued cell cannot change under any multiplier, so it needs no
    ownership decision: it is recorded as excluded so the decision list holds
    only real decisions.
    """
    if not _is_numeric(value):
        return False
    try:
        return float(value) == 0.0
    except (TypeError, ValueError):
        return False


def improvement_side_path(db, improvement_type: str,
                          granting: list[dict]) -> dict:
    """Full side-path inventory for one unlocked improvement."""
    cells: list[dict] = []
    structural = []
    selectors = []

    columns = [c[1] for c in db.execute(
        f'PRAGMA table_info("Improvements")')]
    base = db.execute("SELECT * FROM Improvements WHERE ImprovementType=?",
                      (improvement_type,)).fetchone()
    base = dict(base) if base else {}

    for col in columns:
        if col == "ImprovementType":
            continue
        value = base.get(col)
        if col in IMPROVEMENT_SELECTOR_COLUMNS:
            selectors.append({"column": col, "value": value,
                              "disposition": "EXCLUDED",
                              "family": "SELECTOR",
                              "reason": "selector/type/reference column"})
            continue
        if value is None:
            structural.append({"column": col, "value": None,
                               "disposition": "EXCLUDED",
                               "family": "CONFIG",
                               "reason": "absence is the shipped default"})
            continue
        if col in IMPROVEMENT_STRUCTURAL_COLUMNS:
            structural.append({"column": col, "value": value,
                               "disposition": "EXCLUDED",
                               "family": "BOOLEAN_UNLOCK",
                               "reason": "0/1 structural or placement flag"})
            continue
        if col in IMPROVEMENT_COLUMN_RULES:
            fam, disp, reason = IMPROVEMENT_COLUMN_RULES[col]
            if disp != "EXCLUDED" and _zero_shipped(value):
                cells.append({
                    "cell": f"Improvements.{col}", "value": value,
                    "family": fam, "disposition": "EXCLUDED",
                    "reason": ("shipped value is 0, so no multiplier can "
                               "change it; the column-level ownership "
                               "question is recorded once per improvement "
                               "family rather than per zero cell"),
                    "provenance": {"source": "official runtime DB",
                                   "table": "Improvements"}})
                continue
            cells.append({"cell": f"Improvements.{col}", "value": value,
                          "family": fam, "disposition": disp,
                          "reason": reason,
                          "provenance": {"source": "official runtime DB",
                                         "table": "Improvements"}})
            continue
        # Any other numeric column: recorded structurally, never assumed.
        if _is_numeric(value):
            structural.append({"column": col, "value": value,
                               "disposition": "EXCLUDED",
                               "family": "CONFIG",
                               "reason": "numeric column with no curated "
                                         "magnitude rule (structural)"})
        else:
            selectors.append({"column": col, "value": value,
                              "disposition": "EXCLUDED",
                              "family": "SELECTOR",
                              "reason": "selector/type/reference column"})

    # YieldChanges
    for r in db.execute(
            "SELECT YieldType, YieldChange FROM Improvement_YieldChanges "
            "WHERE ImprovementType=? ORDER BY YieldType",
            (improvement_type,)):
        fam, disp, reason = SIDE_PATH_MAGNITUDE_RULES["YieldChange"]
        if _zero_shipped(r["YieldChange"]):
            cells.append({
                "cell": f"Improvement_YieldChanges.{r['YieldType']}",
                "value": r["YieldChange"], "family": fam,
                "disposition": "EXCLUDED",
                "reason": ("shipped value is 0, so no multiplier can change "
                           "it"),
                "provenance": {"source": "official runtime DB",
                               "table": "Improvement_YieldChanges"}})
            continue
        cells.append({"cell": f"Improvement_YieldChanges.{r['YieldType']}",
                      "value": r["YieldChange"], "family": fam,
                      "disposition": disp, "reason": reason,
                      "provenance": {"source": "official runtime DB",
                                     "table": "Improvement_YieldChanges"}})

    # Adjacencies -> Adjacency_YieldChanges (referenced definitions)
    for r in db.execute(
            "SELECT YieldChangeId FROM Improvement_Adjacencies "
            "WHERE ImprovementType=? ORDER BY YieldChangeId",
            (improvement_type,)):
        yid = r["YieldChangeId"]
        yc = db.execute("SELECT * FROM Adjacency_YieldChanges WHERE ID=?",
                        (yid,)).fetchone()
        if yc is None:
            continue
        yc = dict(yc)
        fam, disp, reason = SIDE_PATH_MAGNITUDE_RULES["YieldChange"]
        if _zero_shipped(yc["YieldChange"]):
            cells.append({
                "cell": f"Adjacency_YieldChanges.{yid}.YieldChange",
                "value": yc["YieldChange"], "family": fam,
                "disposition": "EXCLUDED",
                "reason": "shipped value is 0, so no multiplier can change it",
                "provenance": {"source": "official runtime DB",
                               "table": "Adjacency_YieldChanges",
                               "via": "Improvement_Adjacencies"}})
        else:
            cells.append({"cell": f"Adjacency_YieldChanges.{yid}.YieldChange",
                          "value": yc["YieldChange"], "family": fam,
                          "disposition": disp,
                          "reason": reason + " (adjacency version)",
                          "provenance": {"source": "official runtime DB",
                                         "table": "Adjacency_YieldChanges",
                                         "via": "Improvement_Adjacencies"}})
        cells.append({
            "cell": f"Adjacency_YieldChanges.{yid}.TilesRequired",
            "value": yc["TilesRequired"],
            "family": SIDE_PATH_MAGNITUDE_RULES["TilesRequired__adjacency"][0],
            "disposition": SIDE_PATH_MAGNITUDE_RULES["TilesRequired__adjacency"][1],
            "reason": SIDE_PATH_MAGNITUDE_RULES["TilesRequired__adjacency"][2],
            "provenance": {"source": "official runtime DB",
                           "table": "Adjacency_YieldChanges"}})

    # Tourism
    for r in db.execute(
            "SELECT TourismSource, ScalingFactor, PrereqTech FROM "
            "Improvement_Tourism WHERE ImprovementType=? ORDER BY TourismSource",
            (improvement_type,)):
        fam, disp, reason = SIDE_PATH_MAGNITUDE_RULES["ScalingFactor"]
        cells.append({"cell": "Improvement_Tourism.ScalingFactor",
                      "value": r["ScalingFactor"], "family": fam,
                      "disposition": disp, "reason": reason,
                      "provenance": {"source": "official runtime DB",
                                     "table": "Improvement_Tourism"}})
        selectors.append({"column": "TourismSource",
                          "value": r["TourismSource"],
                          "disposition": "EXCLUDED", "family": "SELECTOR",
                          "reason": "tourism source selector"})

    # ImprovementModifiers -> modifier definitions
    modifiers = []
    for r in db.execute(
            "SELECT ModifierID FROM ImprovementModifiers WHERE "
            "ImprovementType=? ORDER BY ModifierID", (improvement_type,)):
        mid = r["ModifierID"]
        m = db.execute("SELECT * FROM Modifiers WHERE ModifierId=?",
                       (mid,)).fetchone()
        if m is None:
            continue
        m = dict(m)
        eff = _effect_for(db, m["ModifierType"])
        modifiers.append({"modifier_id": mid,
                          "modifier_type": m["ModifierType"],
                          "effect_type": eff["EffectType"],
                          "subject_requirement_set_id":
                              m["SubjectRequirementSetId"],
                          "subject_requirements":
                              requirement_set_requirements(
                                  db, m["SubjectRequirementSetId"])})
        for arg in _modifier_arguments(db, mid):
            cls = classify_side_path_argument(eff["EffectType"], arg["Name"],
                                             arg["Value"])
            cells.append({
                "cell": f"ImprovementModifiers.{mid}.{arg['Name']}",
                "value": arg["Value"], "family": cls["family"],
                "disposition": cls["disposition"],
                "reason": cls["reason"],
                "provenance": {"source": "official runtime DB",
                               "table": "ImprovementModifiers"}})

    # Structural tables for this improvement
    structural_tables = {
        "Improvement_ValidFeatures": "FeatureType",
        "Improvement_ValidTerrains": "TerrainType",
        "Improvement_InvalidAdjacentFeatures": "FeatureType",
        "Improvement_ValidResources": "ResourceType",
        "Improvement_ValidAdjacentTerrains": "TerrainType",
        "Improvement_ValidAdjacentResources": "ResourceType",
        "Improvement_ValidBuildUnits": "UnitType",
    }
    other_tables = []
    for table, col in structural_tables.items():
        if not _table_exists(db, table):
            continue
        rows = [dict(r) for r in db.execute(
            f'SELECT * FROM "{table}" WHERE ImprovementType=?',
            (improvement_type,))]
        if rows:
            other_tables.append({"table": table, "rows": len(rows),
                                 "columns": sorted({c for r in rows for c in r
                                                    if c != "ImprovementType"}),
                                 "disposition": "EXCLUDED",
                                 "family": "SELECTOR",
                                 "reason": "valid-terrain/feature/resource/"
                                           "build-unit selectors or build "
                                           "charges: structural, never "
                                           "magnitudes"})
    for table in ("Boosts", "GoodyHuts",
                  "RandomEvent_Improvement_Placements",
                  "RandomEvent_PillagedImprovements"):
        if not _table_exists(db, table):
            continue
        rows = [dict(r) for r in db.execute(
            f'SELECT * FROM "{table}" WHERE ImprovementType=?',
            (improvement_type,))]
        if rows:
            other_tables.append({"table": table, "rows": len(rows),
                                 "columns": sorted({c for r in rows for c in r
                                                    if c != "ImprovementType"}),
                                 "disposition": "EXCLUDED",
                                 "family": "CONFIG",
                                 "reason": "unrelated game-systems reference "
                                           "to the improvement (boost, goody "
                                           "hut, random event); not part of "
                                           "the Suzerain bonus"})

    return {"improvement_type": improvement_type, "granted_by": granting,
            "cells": cells, "structural_columns": structural,
            "selector_columns": selectors,
            "attached_modifiers": modifiers,
            "other_tables": other_tables,
            "owning_trait": base.get("TraitType")}

# --------------------------------------------------------------------------
# Side paths: unique units and granted abilities
# --------------------------------------------------------------------------
# Direct Units columns: intrinsic unit definition, NOT owned by the Suzerain
# multiplier by default. Only a magnitude whose own requirement proves it is
# part of the Suzerain bonus itself may be claimed.
UNIT_INTRINSIC_RULE = (
    "intrinsic unit definition (Combat / Cost / BaseMoves / ...): the "
    "unlock is a capability, so the unit's own base stats are NOT claimed by "
    "the Suzerain multiplier")


def discover_unit_unlocks(graph: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for node in graph["definitions"].values():
        if node["effect_type"] != "EFFECT_ADJUST_PLAYER_VALID_UNIT_BUILD":
            continue
        for arg in node["arguments"]:
            if arg["Name"] != "UnitType":
                continue
            out[arg["Value"]].append({
                "modifier_id": node["modifier_id"],
                "modifier_type": node["modifier_type"],
            })
    return dict(out)


def _table_exists(db, table: str) -> bool:
    row = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND "
                     "name=?", (table,)).fetchone()
    return row is not None


def _table_has_column(db, table: str, column: str) -> bool:
    return any(c[1] == column for c in db.execute(
        f'PRAGMA table_info("{table}")'))


def unit_side_path(db, unit_type: str, granting: list[dict]) -> dict:
    """Inventory the granted unique unit's direct data and modifier graph."""
    base = db.execute("SELECT * FROM Units WHERE UnitType=?",
                      (unit_type,)).fetchone()
    base = dict(base) if base else {}

    columns = [c[1] for c in db.execute('PRAGMA table_info("Units")')]
    direct: list[dict] = []
    for col in columns:
        if col == "UnitType":
            continue
        value = base.get(col)
        if value is None:
            continue
        if _is_numeric(value) and _zero_shipped(value) and \
                col not in ("Combat", "Cost", "BaseMoves", "BaseSightRange"):
            # zero-valued intrinsic stat: nothing to scale and no decision
            continue
        if _is_numeric(value):
            direct.append({"cell": f"Units.{col}", "value": value,
                           "family": "FLAT_AMOUNT",
                           "disposition": "EXCLUDED",
                           "reason": UNIT_INTRINSIC_RULE,
                           "provenance": {"source": "official runtime DB",
                                          "table": "Units"}})
        else:
            direct.append({"cell": f"Units.{col}", "value": value,
                           "family": "SELECTOR",
                           "disposition": "EXCLUDED",
                           "reason": "intrinsic unit selector/definition",
                           "provenance": {"source": "official runtime DB",
                                          "table": "Units"}})

    # Modifier graph attached to the unit's promotion class / abilities.
    modifiers: list[dict] = []
    promotion_class = base.get("PromotionClass")
    if promotion_class:
        for pm in db.execute(
                """SELECT pm.UnitPromotionType, up.Level, up.Column, pm.ModifierId
                   FROM UnitPromotionModifiers pm
                   JOIN UnitPromotions up ON up.UnitPromotionType = pm.UnitPromotionType
                   WHERE up.PromotionClass=?
                   ORDER BY pm.UnitPromotionType""", (promotion_class,)):
            m = db.execute("SELECT * FROM Modifiers WHERE ModifierId=?",
                           (pm["ModifierId"],)).fetchone()
            if m is None:
                continue
            m = dict(m)
            eff = _effect_for(db, m["ModifierType"])
            reqs = requirement_set_requirements(db,
                                                 m["SubjectRequirementSetId"])
            is_suz_owned = any(
                r["RequirementType"] == "REQUIREMENT_PLAYER_IS_SUZERAIN_OF_X"
                for r in reqs)
            for arg in _modifier_arguments(db, pm["ModifierId"]):
                cls = classify_side_path_argument(eff["EffectType"],
                                                  arg["Name"], arg["Value"])
                note = ("unit promotion attached to the granted unit; "
                        "intrinsic to the unit, not claimed by the Suzerain "
                        "multiplier")
                if is_suz_owned:
                    note = ("STRONGEST Suzerain-side-path candidate: this "
                            "promotion's own requirement "
                            f"({m['SubjectRequirementSetId']}) proves it only "
                            "applies while the player is Lahore's Suzerain, "
                            "so the magnitude is gated by Suzerain status "
                            "itself")
                modifiers.append({
                    "modifier_id": pm["ModifierId"],
                    "promotion": pm["UnitPromotionType"],
                    "promotion_level": pm["Level"],
                    "promotion_column": pm["Column"],
                    "modifier_type": m["ModifierType"],
                    "effect_type": eff["EffectType"],
                    "subject_requirement_set_id": m["SubjectRequirementSetId"],
                    "subject_requirements": reqs,
                    "suzerain_gated": is_suz_owned,
                    "argument_name": arg["Name"],
                    "argument_value": arg["Value"],
                    "family": cls["family"],
                    "disposition": cls["disposition"],
                    "reason": note,
                    "provenance": {"source": "official runtime DB",
                                   "table": "UnitPromotionModifiers"},
                })

    # Unit-ability progression attached through shared class tags
    # (e.g. the Nihang's barracks/armory/academy strength): discovered
    # mechanically as Unit TypeTags -> matching UnitAbility TypeTags ->
    # UnitAbilityModifiers -> Modifiers/ModifierArguments, with the
    # BuildingModifiers grant provenance retained. No name-prefix filter is
    # used anywhere: the relationship is the shared Tag. Intrinsic unit
    # scaling, not Suzerain-owned.
    ability_modifiers: list[dict] = []
    unit_tags: set[str] = set()
    if _table_exists(db, "TypeTags"):
        unit_tags = {r[0] for r in db.execute(
            "SELECT Tag FROM TypeTags WHERE Type=?", (unit_type,))}
    tagged_abilities: list[str] = []
    own_tags: set[str] = set()
    if unit_tags and _table_exists(db, "UnitAbilities"):
        abilities_in_db = {r[0] for r in db.execute(
            "SELECT UnitAbilityType FROM UnitAbilities")}
        # Narrow to the unit's OWN class tags: a tag identifies this unit's
        # progression only when no OTHER unit carries it. Generic tags such
        # as CLASS_MELEE or CLASS_ALL_ERAS are shared by many units and must
        # not pull the whole world into the side path.
        unit_types_in_db: set[str] = set()
        if _table_exists(db, "Units"):
            unit_types_in_db = {r[0] for r in db.execute(
                "SELECT UnitType FROM Units")}
        for tag in sorted(unit_tags):
            carriers = {r[0] for r in db.execute(
                "SELECT Type FROM TypeTags WHERE Tag=?", (tag,))}
            unit_carriers = carriers & unit_types_in_db
            if unit_carriers <= {unit_type}:
                own_tags.add(tag)
        placeholders = ",".join("?" * len(own_tags)) if own_tags else ""
        if own_tags:
            for (t,) in db.execute(
                    "SELECT DISTINCT Type FROM TypeTags WHERE Tag IN "
                    f"({placeholders})", tuple(sorted(own_tags))):
                if t in abilities_in_db and t != unit_type:
                    tagged_abilities.append(t)
            tagged_abilities.sort()
    # Grant provenance: which grant modifiers (and buildings) hand out each
    # tagged ability. A grant modifier carries AbilityType=<ability>; a
    # BuildingModifiers row attaches that grant modifier to a building.
    ability_grant_provenance: dict[str, dict] = {}
    if tagged_abilities and _table_exists(db, "ModifierArguments"):
        for ab in tagged_abilities:
            grants = [dict(r) for r in db.execute(
                "SELECT ModifierId FROM ModifierArguments "
                "WHERE Name='AbilityType' AND Value=? "
                "ORDER BY ModifierId", (ab,))]
            buildings: list[dict] = []
            if grants and _table_exists(db, "BuildingModifiers"):
                for g in grants:
                    for b in db.execute(
                            "SELECT BuildingType FROM BuildingModifiers "
                            "WHERE ModifierId=? ORDER BY BuildingType",
                            (g["ModifierId"],)):
                        buildings.append({"building": b[0],
                                          "grant_modifier": g["ModifierId"]})
            ability_grant_provenance[ab] = {
                "grant_modifiers": [g["ModifierId"] for g in grants],
                "buildings": buildings,
            }
    if tagged_abilities and _table_exists(db, "UnitAbilityModifiers"):
        for ab in tagged_abilities:
            for uam in db.execute(
                    "SELECT ModifierId FROM UnitAbilityModifiers "
                    "WHERE UnitAbilityType=? ORDER BY ModifierId", (ab,)):
                mid = uam["ModifierId"]
                m = db.execute("SELECT * FROM Modifiers WHERE ModifierId=?",
                               (mid,)).fetchone()
                if m is None:
                    continue
                m = dict(m)
                eff = _effect_for(db, m["ModifierType"])
                for a in _modifier_arguments(db, mid):
                    if a["Name"] == "AbilityType":
                        continue
                    cls = classify_side_path_argument(
                        eff["EffectType"], a["Name"], a["Value"])
                    prov = dict(ability_grant_provenance.get(ab, {}))
                    ability_modifiers.append({
                        "modifier_id": mid,
                        "unit_ability": ab,
                        "modifier_type": m["ModifierType"],
                        "effect_type": eff["EffectType"],
                        "argument_name": a["Name"],
                        "argument_value": a["Value"],
                        "family": cls["family"],
                        "disposition": cls["disposition"],
                        "reason": (cls["reason"] +
                                   " (unit-ability progression attached "
                                   "through the shared class tag; intrinsic "
                                   "to the unlocked unit)"),
                        "provenance": {"source": "official runtime DB",
                                       "table": "UnitAbilityModifiers",
                                       "via": "TypeTags",
                                       "unit_tags": sorted(unit_tags),
                                       "grant": prov}})

    other_tables = []
    for table in ("UnitReplaces", "UnitUpgrades", "TypeTags",
                  "UnitPromotions"):
        if not _table_exists(db, table):
            continue
        if not _table_has_column(db, table, "UnitType") and \
                table != "UnitPromotionClasses":
            if table == "UnitPromotions":
                rows = [dict(r) for r in db.execute(
                    "SELECT * FROM UnitPromotions WHERE PromotionClass=?",
                    (promotion_class,))] if promotion_class else []
            else:
                continue
        else:
            rows = [dict(r) for r in db.execute(
                f'SELECT * FROM "{table}" WHERE UnitType=?', (unit_type,))]
        if rows:
            other_tables.append({"table": table, "rows": len(rows),
                                 "disposition": "EXCLUDED",
                                 "family": "SELECTOR",
                                 "reason": "unit selectors / promotion "
                                           "definitions; structural"})

    return {"unit_type": unit_type, "granted_by": granting,
            "promotion_class": promotion_class,
            "unit_tags": sorted(unit_tags),
            "unit_own_tags": sorted(own_tags),
            "tagged_abilities": tagged_abilities,
            "ability_grant_provenance": ability_grant_provenance,
            "direct_cells": direct, "promotion_modifiers": modifiers,
            "ability_modifiers": ability_modifiers,
            "other_tables": other_tables}


def discover_ability_grants(graph: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for node in graph["definitions"].values():
        if node["effect_type"] != "EFFECT_GRANT_ABILITY":
            continue
        for arg in node["arguments"]:
            if arg["Name"] != "AbilityType":
                continue
            out[arg["Value"]].append({
                "modifier_id": node["modifier_id"],
                "modifier_type": node["modifier_type"],
            })
    return dict(out)


def ability_side_path(db, ability_type: str, granting: list[dict]) -> dict:
    """Inventory a granted ability's own modifier (reached outside the graph)."""
    if not _table_exists(db, "UnitAbilityModifiers"):
        return {"ability_type": ability_type, "ability": None,
                "granted_by": granting, "modifiers": []}
    rows = [dict(r) for r in db.execute(
        "SELECT * FROM UnitAbilityModifiers WHERE UnitAbilityType=?",
        (ability_type,))]
    ability_def = db.execute("SELECT * FROM UnitAbilities WHERE "
                             "UnitAbilityType=?", (ability_type,)).fetchone()
    modifiers = []
    for row in rows:
        m = db.execute("SELECT * FROM Modifiers WHERE ModifierId=?",
                       (row["ModifierId"],)).fetchone()
        if m is None:
            continue
        m = dict(m)
        eff = _effect_for(db, m["ModifierType"])
        for a in _modifier_arguments(db, row["ModifierId"]):
            cls = classify_side_path_argument(eff["EffectType"], a["Name"],
                                              a["Value"])
            modifiers.append({
                "modifier_id": row["ModifierId"],
                "modifier_type": m["ModifierType"],
                "effect_type": eff["EffectType"],
                "argument_name": a["Name"], "argument_value": a["Value"],
                "family": cls["family"], "disposition": cls["disposition"],
                "reason": ("reached only through the granted ability, not "
                           "through the Suzerain modifier graph: "
                           + cls["reason"]),
                "provenance": {"source": "official runtime DB",
                               "table": "UnitAbilityModifiers",
                               "via": "UnitAbilities"}})
    return {"ability_type": ability_type,
            "ability": dict(ability_def) if ability_def else None,
            "granted_by": granting, "modifiers": modifiers}

# --------------------------------------------------------------------------
# Legacy x10 comparison (historical evidence, never certification)
# --------------------------------------------------------------------------
def legacy_comparison(coverage_csv: str | Path, graph: dict,
                      rows: list[dict]) -> dict:
    """Compare the audited graph with `data/local/trait_coverage.csv`.

    The CSV is historical evidence from the legacy x10 Suzerain mod: useful to
    show which official roots the old mod covered, which it missed, and which
    obsolete/orphan roots it touched. It is NOT authoritative scope and is
    never certification evidence.
    """
    path = Path(coverage_csv)
    if not path.is_file():
        return {"available": False,
                "note": f"legacy coverage file not present: {path}"}
    with open(path, encoding="utf-8", newline="") as fh:
        csv_rows = [r for r in csv.DictReader(fh)
                    if r.get("module") == "SUZERAIN"]
    if not csv_rows:
        return {"available": False,
                "note": "no SUZERAIN rows found in the legacy coverage file"}
    has_civ_column = "civilization" in csv_rows[0]

    active_roots = {r["ModifierId"] for r in graph["roots"]}
    by_root: dict[str, list[dict]] = defaultdict(list)
    for r in csv_rows:
        by_root[r["modifier_id"]].append(r)

    active_status = Counter()
    missing_roots = []
    for root in sorted(active_roots):
        entries = by_root.get(root, [])
        if not entries:
            missing_roots.append(root)
            active_status["ABSENT"] += 1
            continue
        active_status[entries[0]["row_status"]] += 1
        if entries[0]["row_status"] != "COMPLETE":
            missing_roots.append(root)
    obsolete = sorted(set(by_root) - active_roots)

    # The legacy CSV records one row per (root, ModifierId) edge, so its
    # descendants are the nested definitions. Classify those nested numeric
    # arguments against this audit's dispositions.
    nested_of_root = {
        r["ModifierId"]: [e["to"] for e in graph["edges"]
                          if e["from"] == r["ModifierId"]]
        for r in graph["roots"]}
    nested_of_root.update({
        r["ModifierId"]: [e["to"] for e in graph["edges"]
                          if e["from"] == r["ModifierId"]]
        for r in graph["not_gated_roots"]})

    descendants = []
    for root_id in sorted(active_roots):
        csv_entries = by_root.get(root_id) or []
        legacy_status = (csv_entries[0]["row_status"] if csv_entries
                          else "ABSENT")
        for nested in nested_of_root.get(root_id, []):
            for row in rows:
                if row["modifier_id"] != nested or not row["numeric"]:
                    continue
                descendants.append({
                    "root_modifier_id": root_id,
                    "nested_modifier_id": nested,
                    "city_state": row["city_state"],
                    "modifier_id": row["modifier_id"],
                    "argument_name": row["argument_name"],
                    "argument_value": row["argument_value"],
                    "legacy_row_status": legacy_status,
                    "audit_disposition": row["disposition"],
                    "audit_family": row["family"],
                })
    descendants.sort(key=lambda d: (d["nested_modifier_id"],
                                    d["argument_name"]))
    covered = [d for d in descendants
               if d["legacy_row_status"] == "COMPLETE"]
    uncovered = [d for d in descendants
                 if d["legacy_row_status"] != "COMPLETE"]
    blanket_correct = [d for d in covered
                      if d["audit_disposition"] == "CERTIFIED_CANDIDATE"]
    blanket_questionable = [d for d in covered
                            if d["audit_disposition"] == "DECISION_REQUIRED"]
    blanket_excluded = [d for d in covered
                        if d["audit_disposition"] == "EXCLUDED"]
    uncovered_review = [d for d in uncovered
                        if d["audit_disposition"] == "CERTIFIED_CANDIDATE"]

    return {
        "available": True,
        "file": str(path),
        "sha256": _file_sha256(path),
        "total_suzerain_rows": len(csv_rows),
        "distinct_modifier_ids": len(by_root),
        "civilizations": sorted({r["civilization"] for r in csv_rows
                                 if r.get("civilization")}) if has_civ_column
        else [],
        "row_status_counts": dict(sorted(Counter(
            r["row_status"] for r in csv_rows).items())),
        "active_roots_in_legacy_csv": len(active_roots & set(by_root)),
        "active_roots_multiplied_by_legacy_mod":
            sum(1 for r in active_roots
                if by_root.get(r) and by_root[r][0]["row_status"] == "COMPLETE"),
        "active_roots_not_multiplied": missing_roots,
        "active_roots_row_status": dict(sorted(active_status.items())),
        "obsolete_or_orphan_roots": obsolete,
        "descendants_multiplied": {
            "total_active_descendants": len(descendants),
            "covered_by_legacy_mod": len(covered),
            "uncovered_by_legacy_mod": len(uncovered),
            "uncovered_detail": uncovered,
            "covered_audit_certified_candidate": len(blanket_correct),
            "covered_audit_decision_required": len(blanket_questionable),
            "covered_audit_excluded": len(blanket_excluded),
            "legacy_row_status_counts": dict(sorted(Counter(
                d["legacy_row_status"] for d in descendants).items())),
            "meaning": ("every numeric descendant of the active roots is "
                        "listed. covered = the legacy mod's SQL reached the "
                        "root and multiplied it; uncovered = it never reached "
                        "it (MISSING) or the root is absent from the legacy "
                        "file (ABSENT), so the bonus stayed at the official "
                        "value. 'questionable' rows are ones the legacy x10 "
                        "multiplied but this audit refuses"),
            "questionable_detail": blanket_questionable,
            "excluded_detail": blanket_excluded,
        },
        "descendant_detail": descendants,
        "note": ("historical evidence only; the legacy mod's blanket "
                 "SET Value = Value * 10 is never treated as proof that a row "
                 "is semantically correct"),
    }


# --------------------------------------------------------------------------
# Production registry overlap
# --------------------------------------------------------------------------
def registry_overlap(rows: list[dict], root=".") -> dict:
    """Exact overlap of the audited numeric graph with the production registry.

    The production registry is the authoritative shipped artifact
    (`build/X10ProductionRegistry.inc`); a non-zero overlap would mean Phase 5B
    must negotiate shared ownership rather than claim a row.
    """
    inc = Path(root) / "build" / "X10ProductionRegistry.inc"
    if not inc.is_file():
        return {"available": False,
                "note": f"production registry not present: {inc}"}
    text = inc.read_text(encoding="utf-8")
    registered = set()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            first = line[1:].split(",", 1)[0]
            registered.add(first.strip().strip('"'))
    audited = {r["modifier_id"] for r in rows}
    overlap = sorted(audited & registered)
    audited_args = {(r["modifier_id"], r["argument_name"]) for r in rows
                    if r["numeric"]}
    return {"available": True, "file": str(inc), "sha256": _file_sha256(inc),
            "registered_entries": len(registered),
            "audited_modifier_ids": len(audited),
            "overlapping_modifier_ids": overlap,
            "overlapping_pairs": sorted(audited_args & registered) and
            sorted(p for p in ((r["modifier_id"], r["argument_name"])
                               for r in rows if r["numeric"])
                   if p[0] in registered),
            "count": len(overlap),
            "proposed_owner_bit": PROPOSED_SUZERAIN_MODULE_BIT,
            "proposed_next_free_bit": PROPOSED_NEXT_MODULE_BIT_AFTER_SUZERAIN,
            "note": ("a non-zero count means shared ownership must be "
                     "resolved before Phase 5B claims any row")}


def _file_sha256(path) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Audit assembly
# --------------------------------------------------------------------------
def build_audit(db_path: str | Path,
                coverage_csv: str | Path | None = None,
                game_root: str | Path | None = None,
                root: str | Path | None = None,
                sem_floor_path: str | Path | None = None) -> dict:
    """Full Phase 5A audit. Reads the official DB copy read-only."""
    con = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    db = con
    try:
        active = discover_city_states(db)
        active_leaders = {r["LeaderType"] for r in active}
        orphans = discover_orphan_minor_leaders(db, active_leaders)

        graph = build_graph(db, active)
        rows = build_rows(db, graph)

        # ---- side paths
        improvements = discover_improvement_unlocks(graph)
        unit_unlocks = discover_unit_unlocks(graph)
        ability_grants = discover_ability_grants(graph)
        improvement_paths = {k: improvement_side_path(db, k, v)
                             for k, v in sorted(improvements.items())}
        unit_paths = {k: unit_side_path(db, k, v)
                      for k, v in sorted(unit_unlocks.items())}
        ability_paths = {k: ability_side_path(db, k, v)
                         for k, v in sorted(ability_grants.items())}

        # granted resources/objects
        granted: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            if row["argument_name"] == "ResourceType":
                granted[row["argument_value"]].append({
                    "modifier_id": row["modifier_id"],
                    "effect_type": row["effect_type"],
                    "amount_argument": "Amount",
                    "amount": next((r["argument_value"] for r in rows
                                    if r["modifier_id"] == row["modifier_id"]
                                    and r["argument_name"] == "Amount"), None),
                    "disposition": row["disposition"],
                })
        grant_notes = {
            "note": ("only the GRANT QUANTITY is audited as a candidate; the "
                     "intrinsic properties of a granted resource/object are "
                     "never multiplied just because a city-state grants it"),
            "objects": sorted(granted),
        }

        # ---- counts
        numeric_rows = [r for r in rows if r["numeric"]]
        counts = {
            "active_city_states": len({r["CivilizationType"] for r in active}),
            "active_civilization_rows": len(active),
            "active_minor_leaders": len(active_leaders),
            "active_minor_traits": len({r["TraitType"] for r in active}),
            "inactive_orphan_minor_leaders": len(orphans),
            "minor_leaders_in_db": len({r["LeaderType"] for r in orphans}
                                       | active_leaders),
            "gate_roots": len(graph["roots"]),
            "gate_root_effect_types": dict(sorted(Counter(
                r["ModifierType"] for r in graph["roots"]).items())),
            "gate_requirement_sets": dict(sorted(Counter(
                r["gate_set"] for r in graph["roots"]).items())),
            "flagged_not_gated_roots": len(graph["not_gated_roots"]),
            "reachable_definitions": len(graph["definitions"]),
            "root_definitions": len(graph["roots"]),
            "nested_definitions": len(graph["definitions"])
            - len({r["ModifierId"] for r in graph["roots"]}),
            "modifier_to_modifier_edges": len(graph["edges"]),
            "cycles": len(graph["cycles"]),
            "max_depth": max((d["depth"] for d in
                              graph["definitions"].values()), default=0),
            "reachable_arguments": len(rows),
            "numeric_arguments": len(numeric_rows),
            "nonnumeric_arguments": len(rows) - len(numeric_rows),
            "definitions_with_numeric_arguments": len(
                {r["modifier_id"] for r in numeric_rows}),
            "side_path_improvements": len(improvement_paths),
            "side_path_units": len(unit_paths),
            "side_path_abilities": len(ability_paths),
        }

        def disposition_note(r: dict) -> str:
            return r["disposition"]

        dispositions = {
            "reachable_rows": dict(sorted(Counter(
                r["disposition"] for r in rows).items())),
            "numeric_rows": dict(sorted(Counter(
                r["disposition"] for r in numeric_rows).items())),
            "side_path_improvement_cells": dict(sorted(Counter(
                c["disposition"] for p in improvement_paths.values()
                for c in p["cells"]).items())),
            "side_path_unit_cells": dict(sorted(Counter(
                c["disposition"] for p in unit_paths.values()
                for c in p["direct_cells"]).items())),
            "side_path_unit_modifier_cells": dict(sorted(Counter(
                c["disposition"] for p in unit_paths.values()
                for c in p["promotion_modifiers"]).items())),
            "side_path_unit_ability_cells": dict(sorted(Counter(
                c["disposition"] for p in unit_paths.values()
                for c in p["ability_modifiers"]).items())),
            "side_path_ability_cells": dict(sorted(Counter(
                c["disposition"] for p in ability_paths.values()
                for c in p["modifiers"]).items())),
        }
        # Aggregate direct/side-path totals for the report.
        side_cells = ([c for p in improvement_paths.values() for c in p["cells"]]
                      + [c for p in unit_paths.values()
                         for c in p["direct_cells"]]
                      + [c for p in unit_paths.values()
                         for c in p["promotion_modifiers"]]
                      + [c for p in unit_paths.values()
                         for c in p["ability_modifiers"]]
                      + [c for p in ability_paths.values()
                         for c in p["modifiers"]])
        dispositions["direct_side_path_cells"] = dict(sorted(Counter(
            c["disposition"] for c in side_cells).items()))
        counts["side_path_cells"] = len(side_cells)

        family_summary: dict[str, dict] = {}
        for r in rows:
            fam = r["family"]
            entry = family_summary.setdefault(
                fam, {"candidate": 0, "excluded": 0, "decision_required": 0,
                      "examples": []})
            key = ("candidate" if r["disposition"] == "CERTIFIED_CANDIDATE"
                   else "excluded" if r["disposition"] == "EXCLUDED"
                   else "decision_required")
            entry[key] += 1
            if len(entry["examples"]) < 4 and r["numeric"]:
                entry["examples"].append(f"{r['modifier_id']}:"
                                         f"{r['argument_name']}="
                                         f"{r['argument_value']}")

        per_city_state: dict[str, dict] = {}
        for r in rows:
            cs = r["city_state"]
            entry = per_city_state.setdefault(
                cs, {"trait": r["trait_type"],
                     "candidate": 0, "excluded": 0, "decision_required": 0,
                     "roots": set()})
            entry["roots"].add(r["root_modifier_id"])
            key = ("candidate" if r["disposition"] == "CERTIFIED_CANDIDATE"
                   else "excluded" if r["disposition"] == "EXCLUDED"
                   else "decision_required")
            entry[key] += 1
        for cs, entry in per_city_state.items():
            entry["roots"] = sorted(entry["roots"])

        proposed = {}
        for r in rows:
            if r["numeric"] and r["disposition"] == "CERTIFIED_CANDIDATE":
                proposed.setdefault((r["modifier_id"], r["argument_name"]), r)

        overlap = registry_overlap(rows, root=root or ".")
        comparison = (legacy_comparison(coverage_csv, graph, rows)
                      if coverage_csv else {"available": False})

        floor = load_floor_for_consistency(sem_floor_path, root=root or ".")
        if floor is None:
            floor_consistency: dict = {
                "available": False,
                "note": ("effect-semantic floor not present: consistency "
                         "check skipped (CI-safe); pass sem_floor_path to "
                         "enable it"),
            }
        else:
            report = check_side_path_floor_consistency(
                side_path_cells_with_tuples({
                    "side_paths": {
                        "improvements": improvement_paths,
                        "units": unit_paths,
                        "abilities": ability_paths,
                    }}), floor)
            floor_consistency = {"available": True, **report}

        return {
            "audit": ("Phase 5A closed-world City-State / Suzerain semantic "
                      "audit (audit only; no production registry rows)"),
            "proposed_owner_bit": PROPOSED_SUZERAIN_MODULE_BIT,
            "proposed_next_bit_after": PROPOSED_NEXT_MODULE_BIT_AFTER_SUZERAIN,
            "db": {"path": str(db_path),
                   "sha256": _file_sha256(db_path),
                   "tables": db.execute(
                       "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                   ).fetchone()[0]},
            "game_root": str(game_root) if game_root else None,
            "counts": counts,
            "disposition_summary": dispositions,
            "family_summary": dict(sorted(family_summary.items())),
            "active_city_states": active,
            "inactive_orphan_minor_leaders": orphans,
            "not_suzerain_gated_roots": graph["not_gated_roots"],
            "graph": {
                "roots": [{k: v for k, v in r.items()} for r in
                          graph["roots"]],
                "definitions": {k: {kk: vv for kk, vv in v.items()
                                    if kk != "arguments"}
                                for k, v in graph["definitions"].items()},
                "edges": graph["edges"],
                "cycles": graph["cycles"],
            },
            "rows": rows,
            "per_city_state": per_city_state,
            "proposed_candidates": [
                {"modifier_id": k[0], "argument": k[1],
                 "value": v["argument_value"],
                 "family": v["family"],
                 "city_state": v["city_state"],
                 "effect_type": v["effect_type"]}
                for k, v in sorted(proposed.items())],
            "side_paths": {
                "improvements": improvement_paths,
                "units": unit_paths,
                "abilities": ability_paths,
                "granted_objects": grant_notes,
            },
            "registry_overlap": overlap,
            "legacy_comparison": comparison,
            "side_path_floor_consistency": floor_consistency,
        }
    finally:
        con.close()

# --------------------------------------------------------------------------
# Writers
# --------------------------------------------------------------------------
def write_manifest(audit: dict, out) -> None:
    import yaml
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Phase 5A Suzerain audit manifest (machine-generated, reviewed input)\n"
                 "# Generated by `python -m civ6x10 audit-suzerains`.\n"
                 "# AUDIT ONLY: Phase 5B consumes this; nothing here is production.\n")
        yaml.safe_dump(audit, fh, sort_keys=True, allow_unicode=True,
                       width=120, default_flow_style=False)


def write_inventory_csv(rows: list[dict], out) -> None:
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    fields = ["row_id", "city_state", "leader", "trait_type",
              "root_modifier_id", "root_gate_set", "is_root", "reached_via",
              "depth", "modifier_id", "modifier_type", "effect_type",
              "collection_type", "owner_requirement_set_id",
              "subject_requirement_set_id", "subject_requirement_types",
              "argument_name", "argument_type", "argument_value", "numeric",
              "family", "disposition", "reason", "engine_integral"]
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            d = dict(r)
            d["subject_requirement_types"] = ";".join(
                sorted({x["RequirementType"] for x in r["subject_requirements"]}))
            w.writerow(d)


def write_graph_json(audit: dict, out) -> None:
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "counts": audit["counts"],
        "edges": audit["graph"]["edges"],
        "cycles": audit["graph"]["cycles"],
        "roots": [{"ModifierId": r["ModifierId"],
                   "TraitType": r["trait_type"],
                   "CityState": r["city_state"],
                   "GateSet": r["gate_set"]} for r in
                  audit["graph"]["roots"]],
        "not_gated_roots": [{"ModifierId": r["ModifierId"],
                             "TraitType": r["trait_type"],
                             "CityState": r["city_state"],
                             "Reason": r["flag"]} for r in
                            audit["not_suzerain_gated_roots"]],
        "side_paths": {
            "improvements": sorted(audit["side_paths"]["improvements"]),
            "units": sorted(audit["side_paths"]["units"]),
            "abilities": sorted(audit["side_paths"]["abilities"]),
            "objects": audit["side_paths"]["granted_objects"]["objects"],
        },
    }, indent=1, sort_keys=True), encoding="utf-8")


def summarize(audit: dict) -> dict:
    """Compact console/report summary."""
    c = audit["counts"]
    d = audit["disposition_summary"]
    families = {k: {"candidate": v["candidate"],
                    "excluded": v["excluded"],
                    "decision_required": v["decision_required"]}
                for k, v in audit["family_summary"].items()}
    lc = audit["legacy_comparison"]
    dm = lc.get("descendants_multiplied") or {}
    return {
        "counts": c,
        "dispositions": d,
        "family_summary": families,
        "proposed_candidates": len(audit["proposed_candidates"]),
        "registry_overlap": {
            "count": audit["registry_overlap"].get("count"),
            "modifier_ids": audit["registry_overlap"].get(
                "overlapping_modifier_ids", []),
        },
        "legacy": {
            "available": lc.get("available"),
            "total_suzerain_rows": lc.get(
                "total_suzerain_rows"),
            "row_status_counts": lc.get("row_status_counts"),
            "active_roots_in_legacy_csv": lc.get("active_roots_in_legacy_csv"),
            "active_roots_multiplied_by_legacy_mod": lc.get(
                "active_roots_multiplied_by_legacy_mod"),
            "active_roots_not_multiplied": lc.get(
                "active_roots_not_multiplied"),
            "obsolete_or_orphan_roots": lc.get(
                "obsolete_or_orphan_roots"),
            "descendants": {
                "total": dm.get("total_active_descendants"),
                "covered_by_legacy_mod": dm.get("covered_by_legacy_mod"),
                "uncovered_by_legacy_mod": dm.get("uncovered_by_legacy_mod"),
                "covered_audit_certified_candidate":
                    dm.get("covered_audit_certified_candidate"),
                "covered_audit_decision_required":
                    dm.get("covered_audit_decision_required"),
                "covered_audit_excluded": dm.get("covered_audit_excluded"),
            },
        },
        "side_path_floor_consistency": {
            k: v for k, v in
            audit.get("side_path_floor_consistency", {}).items()
            if k != "details"
        },
    }
