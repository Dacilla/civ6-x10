"""Phase 5A: closed-world City-State / Suzerain audit.

CI-safe by construction - nothing here needs the proprietary game data:

1. **Synthetic fixture tests** - a minimal fake Civ VI SQLite tree exercises
   active discovery, orphan accounting, graph traversal, cycle safety,
   dispositions, and the improvement/unit/ability side paths.
2. **Checked-in manifest invariants** - structural invariants of
   `civ6x10/rules/suzerain_audit.yml` that hold without any local data.
3. **Audit-only guarantees** - the phase provably leaves the production
   registry, the CE fork, and the native/controller files untouched.
"""
from __future__ import annotations

import csv
import os
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

from civ6x10 import suzerain
from civ6x10.suzerain import (
    PROPOSED_NEXT_MODULE_BIT_AFTER_SUZERAIN,
    PROPOSED_SUZERAIN_MODULE_BIT,
    build_audit,
    classify_argument,
    classify_side_path_argument,
)

CIVILIZATION_LEVEL_CITY_STATE = "CIVILIZATION_LEVEL_CITY_STATE"

# ---------------------------------------------------------------------------
# Schema: the real Civ VI columns this module reads. A superset of what the
# fixture populates keeps PRAGMA-driven discovery identical to production.
# ---------------------------------------------------------------------------
SCHEMA = {
    "Civilizations": ["CivilizationType", "Name", "Description", "Adjective",
                      "StartingCivilizationLevelType"],
    "CivilizationLeaders": ["LeaderType", "CivilizationType", "CapitalName"],
    "Leaders": ["LeaderType", "Name"],
    "Leaders_XP2": ["LeaderType", "OceanStart", "MinorCivBonusType"],
    "LeaderTraits": ["LeaderType", "TraitType"],
    "Traits": ["TraitType", "Name", "InternalOnly"],
    "MinorCivBonuses": ["MinorCivBonusType", "Name"],
    "TraitModifiers": ["TraitType", "ModifierId"],
    "Modifiers": ["ModifierId", "ModifierType", "RunOnce", "NewOnly",
                  "Permanent", "Repeatable", "OwnerRequirementSetId",
                  "SubjectRequirementSetId"],
    "ModifierArguments": ["ModifierId", "Name", "Type", "Value", "Extra",
                          "SecondExtra"],
    "DynamicModifiers": ["ModifierType", "CollectionType", "EffectType"],
    "RequirementSets": ["RequirementSetId", "RequirementSetType"],
    "RequirementSetRequirements": ["RequirementSetId", "RequirementId"],
    "Requirements": ["RequirementId", "RequirementType", "Likeliness",
                     "Impact", "Inverse", "Reverse", "Persistent",
                     "ProgressWeight", "Triggered"],
    "RequirementArguments": ["RequirementId", "Name", "Type", "Value", "Extra",
                             "SecondExtra"],
    "Improvements": ["ImprovementType", "Name", "BarbarianCamp", "PrereqTech",
                     "PrereqCivic", "Buildable", "PlunderType",
                     "PlunderAmount", "Goody", "Housing", "TilesRequired",
                     "SameAdjacentValid", "OnePerCity", "GrantFortification",
                     "Appeal", "ReligiousUnitHealRate", "DefenseModifier",
                     "Workable", "Removable", "Capturable", "TraitType",
                     "YieldFromAppealPercent", "Domain", "DispersalGold",
                     "TilesPerGoody", "GoodyRange", "AirSlots", "WeaponSlots",
                     "MinimumAppeal", "MovementChange",
                     "ValidAdjacentTerrainAmount", "YieldFromAppeal"],
    "Improvement_YieldChanges": ["ImprovementType", "YieldType",
                                 "YieldChange"],
    "Improvement_Adjacencies": ["ImprovementType", "YieldChangeId"],
    "Adjacency_YieldChanges": ["ID", "YieldType", "YieldChange",
                               "TilesRequired"],
    "Improvement_Tourism": ["ImprovementType", "TourismSource", "PrereqCivic",
                            "PrereqTech", "ScalingFactor"],
    "ImprovementModifiers": ["ImprovementType", "ModifierID"],
    "Improvement_ValidTerrains": ["ImprovementType", "TerrainType"],
    "Improvement_ValidBuildUnits": ["ImprovementType", "UnitType",
                                    "ConsumesCharge", "ValidRepairOnly"],
    "Units": ["UnitType", "Name", "Combat", "Cost", "BaseMoves", "BaseSightRange",
              "Domain", "FormationClass", "CostProgressionParam1",
              "PromotionClass", "CanTrain", "TraitType", "Description",
              "PopulationCost", "RangedCombat", "Range"],
    "UnitPromotionClasses": ["PromotionClassType", "Name"],
    "UnitPromotions": ["UnitPromotionType", "Name", "Description", "Level",
                       "Specialization", "PromotionClass", "Column"],
    "UnitPromotionModifiers": ["UnitPromotionType", "ModifierId"],
    "UnitAbilityModifiers": ["UnitAbilityType", "ModifierId"],
    "UnitAbilities": ["UnitAbilityType", "Name", "Description", "Inactive",
                      "ShowFloatTextWhenEarned", "Permanent"],
}

REQ_SETS = {
    "PLAYER_IS_SUZERAIN": [("REQUIRES_PLAYER_IS_SUZERAIN",
                            "REQUIREMENT_PLAYER_IS_SUZERAIN", None, None),
                           ("REQUIRES_PLAYER_IS_SUZERAIN_BONUS_ENABLED",
                            "REQUIREMENT_PLAYER_IS_SUZERAIN_BONUS_ENABLED",
                            None, None)],
    "PLAYER_IS_SUZERAIN_ALLY_LEVEL_1": [
        ("REQUIRES_PLAYER_IS_SUZERAIN", "REQUIREMENT_PLAYER_IS_SUZERAIN",
         None, None),
        ("REQUIRES_ALLY_LEVEL_1",
         "REQUIREMENT_PLAYER_HAS_ACTIVE_ALLIANCE_OF_AT_LEAST_LEVEL",
         "Level", "1")],
    "PLAYER_IS_SUZERAIN_ALLY_LEVEL_2": [
        ("REQUIRES_PLAYER_IS_SUZERAIN", "REQUIREMENT_PLAYER_IS_SUZERAIN",
         None, None),
        ("REQUIRES_ALLY_LEVEL_2",
         "REQUIREMENT_PLAYER_HAS_ACTIVE_ALLIANCE_OF_AT_LEAST_LEVEL",
         "Level", "2")],
    "PLAYER_IS_SUZERAIN_ALLY_LEVEL_3": [
        ("REQUIRES_PLAYER_IS_SUZERAIN", "REQUIREMENT_PLAYER_IS_SUZERAIN",
         None, None),
        ("REQUIRES_ALLY_LEVEL_3",
         "REQUIREMENT_PLAYER_HAS_ACTIVE_ALLIANCE_OF_AT_LEAST_LEVEL",
         "Level", "3")],
    # a set that is NOT Suzerain-gated (envoy tier bonus)
    "PLAYER_IS_MAJOR": [("REQUIRES_PLAYER_IS_MAJOR",
                         "REQUIREMENT_PLAYER_IS_MAJOR", None, None)],
    # a filter on the subject, never a magnitude
    "BUILDING_IS_LIBRARY": [("REQUIRES_CITY_HAS_LIBRARY",
                             "REQUIREMENT_CITY_HAS_BUILDING",
                             "BuildingType", "BUILDING_LIBRARY")],
    "PLAYER_HAS_LAHORE_SUZERAIN_REQUIREMENTS": [
        ("REQUIRES_PLAYER_IS_SUZERAIN_OF_LAHORE",
         "REQUIREMENT_PLAYER_IS_SUZERAIN_OF_X", "LeaderType",
         "LEADER_MINOR_CIV_LAHORE")],
    "UNIT_IS_FLANKED_REQUIREMENTS": [
        ("REQUIRES_UNIT_IS_FLANKED", "REQUIREMENT_UNIT_IS_FLANKED",
         None, None)],
}


def build_fixture_db(path) -> None:
    con = sqlite3.connect(str(path))
    try:
        for table, columns in SCHEMA.items():
            con.execute(f'CREATE TABLE "{table}" ({", ".join(columns)})')

        def ins(table, **row):
            cols = SCHEMA[table]
            con.execute(
                f'INSERT INTO "{table}" ({", ".join(cols)}) '
                f'VALUES ({", ".join("?" * len(cols))})',
                tuple(row.get(c) for c in cols))

        for set_id, reqs in REQ_SETS.items():
            ins("RequirementSets", RequirementSetId=set_id,
                RequirementSetType="REQUIREMENTSET_TEST_ALL")
            for rid, rtype, name, value in reqs:
                ins("Requirements", RequirementId=rid, RequirementType=rtype,
                    Inverse=0)
                if name:
                    ins("RequirementArguments", RequirementId=rid, Name=name,
                        Type="ARGTYPE_IDENTITY", Value=value)
                ins("RequirementSetRequirements", RequirementSetId=set_id,
                    RequirementId=rid)

        ins("DynamicModifiers",
            ModifierType="MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER",
            CollectionType="COLLECTION_OWNER",
            EffectType="EFFECT_ATTACH_MODIFIER")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_CITY_ADJUST_CITIZEN_GOLD_PER_TURN",
            CollectionType="COLLECTION_OWNER",
            EffectType="EFFECT_ADJUST_CITY_GOLD_FROM_CITIZENS")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_ADJUST_YIELD_MODIFIER_PER_EARNED_GREAT_PERSON",
            CollectionType="COLLECTION_OWNER",
            EffectType="EFFECT_ADJUST_PLAYER_YIELD_MODIFIER_PER_EARNED_GREAT_PERSON")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_ADJUST_VALID_IMPROVEMENT",
            CollectionType="COLLECTION_OWNER",
            EffectType="EFFECT_ADJUST_PLAYER_VALID_IMPROVEMENT")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_ADJUST_VALID_UNIT_BUILD",
            CollectionType="COLLECTION_OWNER",
            EffectType="EFFECT_ADJUST_PLAYER_VALID_UNIT_BUILD")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_UNITS_GRANT_ABILITY",
            CollectionType="COLLECTION_PLAYER_UNITS",
            EffectType="EFFECT_GRANT_ABILITY")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_CITIES_ADJUST_UNITS_PURCHASE_COST",
            CollectionType="COLLECTION_PLAYER_CITIES",
            EffectType="EFFECT_ADJUST_ALL_UNITS_PURCHASE_COST")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_DISTRICTS_ADJUST_YIELD_MODIFIER",
            CollectionType="COLLECTION_PLAYER_DISTRICTS",
            EffectType="EFFECT_ADJUST_DISTRICT_YIELD_MODIFIER")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_SINGLE_PLOT_ADJUST_PLOT_YIELDS",
            CollectionType="COLLECTION_PLAYER_PLOT_YIELDS",
            EffectType="EFFECT_ADJUST_PLOT_YIELD")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_CITIES_ADJUST_IDENTITY_PER_TURN",
            CollectionType="COLLECTION_PLAYER_CITIES",
            EffectType="EFFECT_ADJUST_CITY_IDENTITY_PER_TURN")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH",
            CollectionType="COLLECTION_PLAYER_UNITS",
            EffectType="EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_GRANT_CITIES_FRESHWATER_HOUSING_BONUS",
            CollectionType="COLLECTION_OWNER",
            EffectType="EFFECT_ADJUST_CITIES_FRESHWATER_HOUSING_BONUS")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_ADJUST_FREE_RESOURCE_IMPORT",
            CollectionType="COLLECTION_OWNER",
            EffectType="EFFECT_ADJUST_PLAYER_FREE_RESOURCE_IMPORT")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_ADJUST_UNITS_GREAT_PEOPLE_POINTS_PER_KILL_BY_DEFEATED_STRENGTH",
            CollectionType="COLLECTION_PLAYER_UNITS",
            EffectType="EFFECT_ADJUST_GREAT_PEOPLE_POINTS_PER_KILL_BY_DEFEATED_STRENGTH")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_UNIT_ADJUST_MOVEMENT",
            CollectionType="COLLECTION_PLAYER_UNITS",
            EffectType="EFFECT_ADJUST_UNIT_MOVEMENT")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_UNIT_ADJUST_NO_REDUCTION_DAMAGE",
            CollectionType="COLLECTION_PLAYER_UNITS",
            EffectType="EFFECT_ADJUST_UNIT_NO_REDUCTION_DAMAGE")
        ins("DynamicModifiers",
            ModifierType="MODIFIER_PLAYER_UNIT_ADJUST_TRADE_ROUTE_PLUNDER_IMMUNITY",
            CollectionType="COLLECTION_PLAYER_UNITS",
            EffectType="EFFECT_ADJUST_UNIT_TRADE_ROUTE_PLUNDER_IMMUNITY")

        # --- bonuses (only for the localized-name lookup) ---------------
        for b in ("MINOR_CIV_BONUS_MILITARISTIC", "MINOR_CIV_BONUS_SCIENCE",
                  "MINOR_CIV_BONUS_TRADE"):
            ins("MinorCivBonuses", MinorCivBonusType=b, Name="LOC_BONUS")

        # --- two ACTIVE city-states + one orphan ------------------------
        ins("Traits", TraitType="MINOR_CIV_ANTIOCH_TRAIT",
            Name="LOC_LEADER_TRAIT_ANTIOCH_NAME", InternalOnly=0)
        ins("Traits", TraitType="MINOR_CIV_VILNIUS_TRAIT",
            Name="LOC_LEADER_TRAIT_VILNIUS_NAME", InternalOnly=0)
        ins("Traits", TraitType="MINOR_CIV_LAHORE_TRAIT",
            Name="LOC_LEADER_TRAIT_LAHORE_NAME", InternalOnly=0)
        ins("Traits", TraitType="MINOR_CIV_TRADE_TRAIT",
            Name="LOC_MINOR_CIV_TRADE_TRAIT_NAME", InternalOnly=0)
        ins("Traits", TraitType="MINOR_CIV_CARTHAGE_TRAIT",
            Name="LOC_LEADER_TRAIT_CARTHAGE_NAME", InternalOnly=0)
        ins("Traits", TraitType="MINOR_CIV_WOLIN_TRAIT",
            Name="LOC_LEADER_TRAIT_WOLIN_NAME", InternalOnly=0)
        ins("Traits", TraitType="MINOR_CIV_ZANZIBAR_TRAIT",
            Name="LOC_LEADER_TRAIT_ZANZIBAR_NAME", InternalOnly=0)

        ins("Civilizations", CivilizationType="CIVILIZATION_ANTIOCH",
            Name="Antioch", Description="d", Adjective="st",
            StartingCivilizationLevelType=CIVILIZATION_LEVEL_CITY_STATE)
        ins("Civilizations", CivilizationType="CIVILIZATION_VILNIUS",
            Name="Vilnius", Description="d", Adjective="st",
            StartingCivilizationLevelType=CIVILIZATION_LEVEL_CITY_STATE)
        ins("Civilizations", CivilizationType="CIVILIZATION_LAHORE",
            Name="Lahore", Description="d", Adjective="st",
            StartingCivilizationLevelType=CIVILIZATION_LEVEL_CITY_STATE)
        ins("Civilizations", CivilizationType="CIVILIZATION_WOLIN",
            Name="Wolin", Description="d", Adjective="st",
            StartingCivilizationLevelType=CIVILIZATION_LEVEL_CITY_STATE)
        ins("Civilizations", CivilizationType="CIVILIZATION_ZANZIBAR",
            Name="Zanzibar", Description="d", Adjective="st",
            StartingCivilizationLevelType=CIVILIZATION_LEVEL_CITY_STATE)
        # a full civ, so membership cannot be decided from a name
        ins("Civilizations", CivilizationType="CIVILIZATION_ROME",
            Name="Rome", Description="d", Adjective="st",
            StartingCivilizationLevelType="CIVILIZATION_LEVEL_FULL_CIV")

        for leader, civ, bonus in (
                ("LEADER_MINOR_CIV_ANTIOCH", "CIVILIZATION_ANTIOCH",
                 "MINOR_CIV_BONUS_TRADE"),
                ("LEADER_MINOR_CIV_VILNIUS", "CIVILIZATION_VILNIUS",
                 "MINOR_CIV_BONUS_CULTURALISH"),
                ("LEADER_MINOR_CIV_LAHORE", "CIVILIZATION_LAHORE",
                 "MINOR_CIV_BONUS_MILITARISTIC"),
                ("LEADER_MINOR_CIV_WOLIN", "CIVILIZATION_WOLIN",
                 "MINOR_CIV_BONUS_MILITARISTIC"),
                ("LEADER_MINOR_CIV_ZANZIBAR", "CIVILIZATION_ZANZIBAR",
                 "MINOR_CIV_BONUS_TRADE")):
            ins("Leaders", LeaderType=leader, Name="LOC_LEADER")
            ins("Leaders_XP2", LeaderType=leader, OceanStart=0,
                MinorCivBonusType=bonus)
            ins("CivilizationLeaders", LeaderType=leader,
                CivilizationType=civ, CapitalName="LOC_CAPITAL")

        # the orphan: a minor leader with NO CivilizationLeaders mapping
        ins("Leaders", LeaderType="LEADER_MINOR_CIV_CARTHAGE",
            Name="LOC_LEADER_CARTHAGE")
        ins("Leaders_XP2", LeaderType="LEADER_MINOR_CIV_CARTHAGE",
            OceanStart=0, MinorCivBonusType="MINOR_CIV_BONUS_MILITARISTIC")

        ins("Leaders", LeaderType="LEADER_MAJOR_ROME", Name="LOC_LEADER_ROME")
        ins("CivilizationLeaders", LeaderType="LEADER_MAJOR_ROME",
            CivilizationType="CIVILIZATION_ROME", CapitalName="LOC_CAPITAL")

        ins("LeaderTraits", LeaderType="LEADER_MINOR_CIV_ANTIOCH",
            TraitType="MINOR_CIV_ANTIOCH_TRAIT")
        ins("LeaderTraits", LeaderType="LEADER_MINOR_CIV_VILNIUS",
            TraitType="MINOR_CIV_VILNIUS_TRAIT")
        ins("LeaderTraits", LeaderType="LEADER_MINOR_CIV_LAHORE",
            TraitType="MINOR_CIV_LAHORE_TRAIT")
        ins("LeaderTraits", LeaderType="LEADER_MINOR_CIV_CARTHAGE",
            TraitType="MINOR_CIV_CARTHAGE_TRAIT")
        # the orphan's leader ALSO carries the generic envoy-tier trait
        ins("LeaderTraits", LeaderType="LEADER_MINOR_CIV_WOLIN",
            TraitType="MINOR_CIV_WOLIN_TRAIT")
        ins("LeaderTraits", LeaderType="LEADER_MINOR_CIV_ZANZIBAR",
            TraitType="MINOR_CIV_ZANZIBAR_TRAIT")
        ins("LeaderTraits", LeaderType="LEADER_MINOR_CIV_ANTIOCH",
            TraitType="MINOR_CIV_TRADE_TRAIT")

        # --- modifiers --------------------------------------------------
        def mod(mid, mtype, subj=None, owner=None):
            ins("Modifiers", ModifierId=mid, ModifierType=mtype, RunOnce=0,
                NewOnly=0, Permanent=0, Repeatable=0,
                OwnerRequirementSetId=owner, SubjectRequirementSetId=subj)

        def arg(mid, name, value):
            ins("ModifierArguments", ModifierId=mid, Name=name,
                Type="ARGTYPE_IDENTITY", Value=value)

        # Antioch: root -> nested numeric gold
        mod("MINOR_CIV_ANTIOCH_ROOT", "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER",
            subj="PLAYER_IS_SUZERAIN")
        arg("MINOR_CIV_ANTIOCH_ROOT", "ModifierId", "MINOR_CIV_ANTIOCH_GOLD")
        mod("MINOR_CIV_ANTIOCH_GOLD",
            "MODIFIER_CITY_ADJUST_CITIZEN_GOLD_PER_TURN", "PLAYER_IS_MAJOR")
        arg("MINOR_CIV_ANTIOCH_GOLD", "Amount", "1")
        arg("MINOR_CIV_ANTIOCH_GOLD", "YieldType", "YIELD_GOLD")
        ins("TraitModifiers", TraitType="MINOR_CIV_ANTIOCH_TRAIT",
            ModifierId="MINOR_CIV_ANTIOCH_ROOT")

        # Vilnius-style: three alternate Suzerain gate sets
        for level in (1, 2, 3):
            mod(f"MINOR_CIV_VILNIUS_ROOT_{level}",
                "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER",
                subj=f"PLAYER_IS_SUZERAIN_ALLY_LEVEL_{level}")
            arg(f"MINOR_CIV_VILNIUS_ROOT_{level}", "ModifierId",
                f"MINOR_CIV_VILNIUS_NESTED_{level}")
            mod(f"MINOR_CIV_VILNIUS_NESTED_{level}",
                "MODIFIER_PLAYER_DISTRICTS_ADJUST_YIELD_MODIFIER",
                subj="DISTRICT_IS_THEATER")
            arg(f"MINOR_CIV_VILNIUS_NESTED_{level}", "Amount", "50")
            arg(f"MINOR_CIV_VILNIUS_NESTED_{level}", "YieldType",
                "YIELD_CULTURE")
            ins("TraitModifiers", TraitType="MINOR_CIV_VILNIUS_TRAIT",
                ModifierId=f"MINOR_CIV_VILNIUS_ROOT_{level}")

        # Lahore: unit unlock + improvement unlock + capability + count-like
        mod("MINOR_CIV_LAHORE_ROOT_UNIT",
            "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER",
            subj="PLAYER_IS_SUZERAIN")
        arg("MINOR_CIV_LAHORE_ROOT_UNIT", "ModifierId",
            "MINOR_CIV_LAHORE_UNIT")
        mod("MINOR_CIV_LAHORE_UNIT",
            "MODIFIER_PLAYER_ADJUST_VALID_UNIT_BUILD")
        arg("MINOR_CIV_LAHORE_UNIT", "UnitType", "UNIT_LAHORE_NIHANG")
        ins("TraitModifiers", TraitType="MINOR_CIV_LAHORE_TRAIT",
            ModifierId="MINOR_CIV_LAHORE_ROOT_UNIT")

        mod("MINOR_CIV_LAHORE_ROOT_IMPROVEMENT",
            "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER",
            subj="PLAYER_IS_SUZERAIN")
        arg("MINOR_CIV_LAHORE_ROOT_IMPROVEMENT", "ModifierId",
            "MINOR_CIV_LAHORE_IMPROVEMENT")
        mod("MINOR_CIV_LAHORE_IMPROVEMENT",
            "MODIFIER_PLAYER_ADJUST_VALID_IMPROVEMENT")
        arg("MINOR_CIV_LAHORE_IMPROVEMENT", "ImprovementType",
            "IMPROVEMENT_MOAI")
        ins("TraitModifiers", TraitType="MINOR_CIV_LAHORE_TRAIT",
            ModifierId="MINOR_CIV_LAHORE_ROOT_IMPROVEMENT")

        mod("MINOR_CIV_LAHORE_ROOT_ABILITY",
            "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER",
            subj="PLAYER_IS_SUZERAIN")
        arg("MINOR_CIV_LAHORE_ROOT_ABILITY", "ModifierId",
            "MINOR_CIV_LAHORE_ABILITY")
        mod("MINOR_CIV_LAHORE_ABILITY",
            "MODIFIER_PLAYER_UNITS_GRANT_ABILITY", subj="UNIT_IS_TRADER")
        arg("MINOR_CIV_LAHORE_ABILITY", "AbilityType",
            "ABILITY_TRADE_ROUTE_PLUNDER_IMMUNITY_SEA")
        ins("TraitModifiers", TraitType="MINOR_CIV_LAHORE_TRAIT",
            ModifierId="MINOR_CIV_LAHORE_ROOT_ABILITY")

        mod("MINOR_CIV_LAHORE_ROOT_HOUSING",
            "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER",
            subj="PLAYER_IS_SUZERAIN")
        arg("MINOR_CIV_LAHORE_ROOT_HOUSING", "ModifierId",
            "MINOR_CIV_LAHORE_HOUSING")
        mod("MINOR_CIV_LAHORE_HOUSING",
            "MODIFIER_PLAYER_GRANT_CITIES_FRESHWATER_HOUSING_BONUS")
        arg("MINOR_CIV_LAHORE_HOUSING", "HasBonus", "1")
        ins("TraitModifiers", TraitType="MINOR_CIV_LAHORE_TRAIT",
            ModifierId="MINOR_CIV_LAHORE_ROOT_HOUSING")

        # a CYCLE: A -> B -> A
        mod("CYCLE_A", "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER",
            subj="PLAYER_IS_SUZERAIN")
        arg("CYCLE_A", "ModifierId", "CYCLE_B")
        mod("CYCLE_B", "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER")
        arg("CYCLE_B", "ModifierId", "CYCLE_A")
        ins("TraitModifiers", TraitType="MINOR_CIV_ANTIOCH_TRAIT",
            ModifierId="CYCLE_A")

        # an active minor-civ trait root that is NOT Suzerain-gated
        mod("MINOR_CIV_ANTIOCH_ROOT_NOT_GATED",
            "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER", subj="PLAYER_IS_MAJOR")
        arg("MINOR_CIV_ANTIOCH_ROOT_NOT_GATED", "ModifierId",
            "MINOR_CIV_ANTIOCH_GOLD")
        ins("TraitModifiers", TraitType="MINOR_CIV_ANTIOCH_TRAIT",
            ModifierId="MINOR_CIV_ANTIOCH_ROOT_NOT_GATED")

        # the generic envoy-tier trait, carried by an active minor leader but
        # NOT a minor-civ trait root of the audited scope
        mod("MINOR_CIV_TRADE_TYPE_ROOT",
            "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER", subj="PLAYER_IS_MAJOR")
        arg("MINOR_CIV_TRADE_TYPE_ROOT", "ModifierId",
            "MINOR_CIV_TRADE_TYPE_NESTED")
        mod("MINOR_CIV_TRADE_TYPE_NESTED",
            "MODIFIER_CITY_ADJUST_CITIZEN_GOLD_PER_TURN")
        arg("MINOR_CIV_TRADE_TYPE_NESTED", "Amount", "3")
        ins("TraitModifiers", TraitType="MINOR_CIV_TRADE_TRAIT",
            ModifierId="MINOR_CIV_TRADE_TYPE_ROOT")
        # ...and the orphan's trait root
        mod("MINOR_CIV_CARTHAGE_ROOT", "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER",
            subj="PLAYER_IS_SUZERAIN")
        arg("MINOR_CIV_CARTHAGE_ROOT", "ModifierId", "MINOR_CIV_CARTHAGE_GOLD")
        mod("MINOR_CIV_CARTHAGE_GOLD",
            "MODIFIER_CITY_ADJUST_CITIZEN_GOLD_PER_TURN")
        arg("MINOR_CIV_CARTHAGE_GOLD", "Amount", "9")
        ins("TraitModifiers", TraitType="MINOR_CIV_CARTHAGE_TRAIT",
            ModifierId="MINOR_CIV_CARTHAGE_ROOT")

        # --- unique improvement side path -------------------------------
        ins("Improvements", ImprovementType="IMPROVEMENT_MOAI",
            Name="LOC_IMPROVEMENT_MOAI_NAME", BarbarianCamp=0, Buildable=1,
            PrereqTech=None, PrereqCivic=None, PlunderType="PLUNDER_FAITH",
            PlunderAmount=25, Goody=0, Housing=0, TilesRequired=1,
            SameAdjacentValid=1, OnePerCity=0, GrantFortification=0, Appeal=1,
            ReligiousUnitHealRate=0, DefenseModifier=0, Workable=1,
            Removable=1, Capturable=1, TraitType="MINOR_CIV_VILNIUS_TRAIT",
            YieldFromAppealPercent=100, Domain="DOMAIN_LAND",
            DispersalGold=0, TilesPerGoody=None, GoodyRange=None, AirSlots=0,
            WeaponSlots=0, MinimumAppeal=None, MovementChange=0,
            ValidAdjacentTerrainAmount=0, YieldFromAppeal=None)
        ins("Improvement_YieldChanges", ImprovementType="IMPROVEMENT_MOAI",
            YieldType="YIELD_CULTURE", YieldChange=1)
        ins("Improvement_Adjacencies", ImprovementType="IMPROVEMENT_MOAI",
            YieldChangeId="MOAI_COASTADJACENCY_CULTURE")
        ins("Adjacency_YieldChanges", ID="MOAI_COASTADJACENCY_CULTURE",
            YieldType="YIELD_CULTURE", YieldChange=2, TilesRequired=1)
        ins("Improvement_Tourism", ImprovementType="IMPROVEMENT_MOAI",
            TourismSource="TOURISMSOURCE_CULTURE", PrereqCivic=None,
            PrereqTech="TECH_FLIGHT", ScalingFactor=100)
        ins("Improvement_ValidTerrains", ImprovementType="IMPROVEMENT_MOAI",
            TerrainType="TERRAIN_COAST")
        ins("Improvement_ValidBuildUnits", ImprovementType="IMPROVEMENT_MOAI",
            UnitType="UNIT_BUILDER", ConsumesCharge=1, ValidRepairOnly=0)
        # improvement modifier with a numeric amount (never a candidate)
        mod("MOAI_COASTADJACENCY_CULTURE",
            "MODIFIER_SINGLE_PLOT_ADJUST_PLOT_YIELDS",
            subj="PLOT_IS_OR_ADJACENT_TO_COAST")
        arg("MOAI_COASTADJACENCY_CULTURE", "Amount", "2")
        arg("MOAI_COASTADJACENCY_CULTURE", "YieldType", "YIELD_CULTURE")
        ins("ImprovementModifiers", ImprovementType="IMPROVEMENT_MOAI",
            ModifierID="MOAI_COASTADJACENCY_CULTURE")

        # --- unique unit side path --------------------------------------
        ins("Units", UnitType="UNIT_LAHORE_NIHANG", Name="LOC_NIHANG",
            Combat=25, Cost=100, BaseMoves=2, BaseSightRange=2,
            Domain="DOMAIN_LAND", FormationClass="FORMATION_CLASS_LAND_COMBAT",
            CostProgressionParam1=400, PromotionClass="PROMOTION_CLASS_NIHANG",
            CanTrain=1, TraitType="MINOR_CIV_LAHORE_TRAIT",
            Description="LOC_NIHANG_DESC", PopulationCost=None,
            RangedCombat=0, Range=0)
        ins("UnitPromotionClasses", PromotionClassType="PROMOTION_CLASS_NIHANG",
            Name="LOC_NIHANG_CLASS")
        for promo, level, col in (("PROMOTION_NIHANG_FLANKED_BONUS", 1, 1),
                                   ("PROMOTION_NIHANG_MOVEMENT_BONUS", 2, 1),
                                   ("PROMOTION_NIHANG_SUZERAIN_COMBAT_BONUS",
                                    3, 2)):
            ins("UnitPromotions", UnitPromotionType=promo, Name="LOC_P",
                Description="LOC_PD", Level=level, Specialization=None,
                PromotionClass="PROMOTION_CLASS_NIHANG", Column=col)
        mod("NIHANG_FLANKED_BONUS", "MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH",
            subj="UNIT_IS_FLANKED_REQUIREMENTS")
        arg("NIHANG_FLANKED_BONUS", "Amount", "7")
        mod("NIHANG_MOVEMENT_BONUS", "MODIFIER_PLAYER_UNIT_ADJUST_MOVEMENT")
        arg("NIHANG_MOVEMENT_BONUS", "Amount", "1")
        mod("NIHANG_SUZERAIN_COMBAT_BONUS",
            "MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH",
            subj="PLAYER_HAS_LAHORE_SUZERAIN_REQUIREMENTS")
        arg("NIHANG_SUZERAIN_COMBAT_BONUS", "Amount", "10")
        for promo, mid in (("PROMOTION_NIHANG_FLANKED_BONUS",
                            "NIHANG_FLANKED_BONUS"),
                           ("PROMOTION_NIHANG_MOVEMENT_BONUS",
                            "NIHANG_MOVEMENT_BONUS"),
                           ("PROMOTION_NIHANG_SUZERAIN_COMBAT_BONUS",
                            "NIHANG_SUZERAIN_COMBAT_BONUS")):
            ins("UnitPromotionModifiers", UnitPromotionType=promo,
                ModifierId=mid)

        # --- granted ability side path ----------------------------------
        ins("UnitAbilities",
            UnitAbilityType="ABILITY_TRADE_ROUTE_PLUNDER_IMMUNITY_SEA",
            Name="LOC_AB", Description="LOC_ABD", Inactive=1,
            ShowFloatTextWhenEarned=0, Permanent=1)
        mod("TRADE_ROUTE_PLUNDER_IMMUNITY_SEA",
            "MODIFIER_PLAYER_UNIT_ADJUST_TRADE_ROUTE_PLUNDER_IMMUNITY")
        arg("TRADE_ROUTE_PLUNDER_IMMUNITY_SEA", "DomainType", "DOMAIN_SEA")
        mod("WOLIN_GREAT_GENERAL_POINTS",
            "MODIFIER_PLAYER_ADJUST_UNITS_GREAT_PEOPLE_POINTS_PER_KILL_BY_DEFEATED_STRENGTH")
        arg("WOLIN_GREAT_GENERAL_POINTS", "Amount", "25")
        arg("WOLIN_GREAT_GENERAL_POINTS", "GreatPersonClassType",
            "GREAT_PERSON_CLASS_GENERAL")
        ins("UnitAbilityModifiers",
            UnitAbilityType="ABILITY_TRADE_ROUTE_PLUNDER_IMMUNITY_SEA",
            ModifierId="TRADE_ROUTE_PLUNDER_IMMUNITY_SEA")
        ins("UnitAbilityModifiers", UnitAbilityType="ABILITY_WOLIN_LAND_UNITS",
            ModifierId="WOLIN_GREAT_GENERAL_POINTS")
        # Wolin ability is granted through its own trait root so the side
        # path is reachable but the ability is not an improvement/unit unlock
        mod("MINOR_CIV_WOLIN_ROOT", "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER",
            subj="PLAYER_IS_SUZERAIN")
        arg("MINOR_CIV_WOLIN_ROOT", "ModifierId", "MINOR_CIV_WOLIN_ABILITY")
        mod("MINOR_CIV_WOLIN_ABILITY",
            "MODIFIER_PLAYER_UNITS_GRANT_ABILITY")
        arg("MINOR_CIV_WOLIN_ABILITY", "AbilityType",
            "ABILITY_WOLIN_LAND_UNITS")
        ins("TraitModifiers", TraitType="MINOR_CIV_WOLIN_TRAIT",
            ModifierId="MINOR_CIV_WOLIN_ROOT")

        # Zanzibar grants a luxury resource: quantity is auditable, the
        # resource's intrinsic properties are not claimed
        mod("MINOR_CIV_ZANZIBAR_ROOT", "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER",
            subj="PLAYER_IS_SUZERAIN")
        arg("MINOR_CIV_ZANZIBAR_ROOT", "ModifierId",
            "MINOR_CIV_ZANZIBAR_CINNAMON")
        mod("MINOR_CIV_ZANZIBAR_CINNAMON",
            "MODIFIER_PLAYER_ADJUST_FREE_RESOURCE_IMPORT")
        arg("MINOR_CIV_ZANZIBAR_CINNAMON", "Amount", "1")
        arg("MINOR_CIV_ZANZIBAR_CINNAMON", "ResourceType",
            "RESOURCE_CINNAMON")
        ins("TraitModifiers", TraitType="MINOR_CIV_ZANZIBAR_TRAIT",
            ModifierId="MINOR_CIV_ZANZIBAR_ROOT")

        ins("Improvements", ImprovementType="IMPROVEMENT_BATEY",
            Name="LOC_IMPROVEMENT_BATEY_NAME", BarbarianCamp=0, Buildable=1,
            PrereqTech=None, PrereqCivic=None, PlunderType="PLUNDER_FAITH",
            PlunderAmount=25, Goody=0, Housing=0, TilesRequired=1,
            SameAdjacentValid=0, OnePerCity=0, GrantFortification=0, Appeal=0,
            ReligiousUnitHealRate=0, DefenseModifier=0, Workable=1,
            Removable=1, Capturable=1, TraitType="MINOR_CIV_CAGUANA_TRAIT",
            YieldFromAppealPercent=100, Domain="DOMAIN_LAND",
            DispersalGold=0, TilesPerGoody=None, GoodyRange=None, AirSlots=0,
            WeaponSlots=0, MinimumAppeal=None, MovementChange=0,
            ValidAdjacentTerrainAmount=0, YieldFromAppeal=None)
        ins("Improvement_YieldChanges", ImprovementType="IMPROVEMENT_BATEY",
            YieldType="YIELD_CULTURE", YieldChange=1)
        con.commit()
    finally:
        con.close()


FIXTURE_PROMOTION = """<?xml version="1.0" encoding="utf-8"?>
<GameInfo></GameInfo>
"""


class SuzerainAuditTest(unittest.TestCase):
    """Phase 5A synthetic-fixture suite (no proprietary data required)."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls._td = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls._td.name) / "fixture.sqlite"
        build_fixture_db(cls.db_path)
        cls.csv_path = Path(cls._td.name) / "legacy_trait_coverage.csv"
        cls._write_legacy_csv(cls.csv_path)
        cls.audit = build_audit(str(cls.db_path),
                                coverage_csv=str(cls.csv_path))

    @classmethod
    def tearDownClass(cls):
        cls._td.cleanup()

    @staticmethod
    def _write_legacy_csv(path):
        rows = [
            # active root the legacy mod reached
            ["civ", "leader", "trait_type", "source_kind", "module",
             "modifier_id", "modifier_type", "argument_name",
             "argument_value", "row_status", "evidence"],
            ["Antioch", "Antioch", "MINOR_CIV_ANTIOCH_TRAIT", "expansion",
             "SUZERAIN", "MINOR_CIV_ANTIOCH_ROOT",
             "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER", "ModifierId",
             "MINOR_CIV_ANTIOCH_GOLD", "COMPLETE", "reached"],
            # active roots the legacy mod missed
            ["Vilnius", "Vilnius", "MINOR_CIV_VILNIUS_TRAIT", "expansion",
             "SUZERAIN", "MINOR_CIV_VILNIUS_ROOT_1",
             "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER", "ModifierId",
             "MINOR_CIV_VILNIUS_NESTED_1", "MISSING", "not reached"],
            # an orphan/historical root the legacy mod still touched
            ["Carthage", "Carthage", "MINOR_CIV_CARTHAGE_TRAIT",
             "base_game", "SUZERAIN", "MINOR_CIV_CARTHAGE_ROOT",
             "MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER", "ModifierId",
             "MINOR_CIV_CARTHAGE_GOLD", "COMPLETE", "reached"],
            # a non-Suzerain module row that must be ignored
            ["Rome", "Rome", "TRAIT_ROME_SOMETHING", "base_game", "TRAITS",
             "SOME_OTHER_ROOT", "MODIFIER_X", "Amount", "5", "COMPLETE", ""],
        ]
        with open(path, "w", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerows(rows)

    # -- 1. active City-State discovery requires actual mapping -----------
    def test_active_discovery_requires_civilization_mapping(self):
        civs = {r["CivilizationType"] for r in
                self.audit["active_city_states"]}
        self.assertEqual(civs, {"CIVILIZATION_ANTIOCH", "CIVILIZATION_VILNIUS",
                                "CIVILIZATION_LAHORE", "CIVILIZATION_WOLIN",
                                "CIVILIZATION_ZANZIBAR"})
        # a full civ with a leader is not a city-state
        self.assertNotIn("CIVILIZATION_ROME", civs)
        names = {r["LeaderType"] for r in self.audit["active_city_states"]}
        # all LEADER_MINOR_CIV_% rows would be 4 in the DB, but only the 3
        # mapped ones are active
        self.assertEqual(names, {"LEADER_MINOR_CIV_ANTIOCH",
                                 "LEADER_MINOR_CIV_VILNIUS",
                                 "LEADER_MINOR_CIV_LAHORE",
                                 "LEADER_MINOR_CIV_WOLIN",
                                 "LEADER_MINOR_CIV_ZANZIBAR"})
        # localized-name key recorded, not invented
        antioch = [r for r in self.audit["active_city_states"]
                   if r["CivilizationType"] == "CIVILIZATION_ANTIOCH"][0]
        self.assertEqual(antioch["trait_name"],
                         "LOC_LEADER_TRAIT_ANTIOCH_NAME")
        self.assertEqual(antioch["MinorCivBonusType"], "MINOR_CIV_BONUS_TRADE")
        self.assertTrue(antioch["provenance"]["chain"].startswith(
            "Civilizations.StartingCivilizationLevelType="))

    # -- 2. orphans are accounted but never roots -------------------------
    def test_orphan_minor_leaders_accounted_but_not_active(self):
        orphans = self.audit["inactive_orphan_minor_leaders"]
        self.assertEqual(len(orphans), 1)
        o = orphans[0]
        self.assertEqual(o["LeaderType"], "LEADER_MINOR_CIV_CARTHAGE")
        self.assertEqual(o["status"], "inactive_orphan")
        self.assertEqual(o["traits"], ["MINOR_CIV_CARTHAGE_TRAIT"])
        # the orphan's own Suzerain root must NOT be in the audited graph
        root_ids = {r["ModifierId"] for r in self.audit["graph"]["roots"]}
        self.assertNotIn("MINOR_CIV_CARTHAGE_ROOT", root_ids)
        row_ids = {r["modifier_id"] for r in self.audit["rows"]}
        self.assertNotIn("MINOR_CIV_CARTHAGE_GOLD", row_ids)

    # -- 3/4. leader -> trait -> wrapper -> nested numeric modifier -------
    def test_full_chain_from_active_leader_to_nested_numeric(self):
        gold = [r for r in self.audit["rows"]
                if r["modifier_id"] == "MINOR_CIV_ANTIOCH_GOLD"
                and r["argument_name"] == "Amount"]
        self.assertEqual(len(gold), 1)
        r = gold[0]
        self.assertEqual(r["city_state"], "CIVILIZATION_ANTIOCH")
        self.assertEqual(r["trait_type"], "MINOR_CIV_ANTIOCH_TRAIT")
        self.assertEqual(r["root_modifier_id"], "MINOR_CIV_ANTIOCH_ROOT")
        self.assertEqual(r["root_gate_set"], "PLAYER_IS_SUZERAIN")
        self.assertEqual(r["effect_type"],
                         "EFFECT_ADJUST_CITY_GOLD_FROM_CITIZENS")
        self.assertEqual(r["argument_value"], "1")
        self.assertEqual(r["family"], "GOLD")
        self.assertEqual(r["disposition"], "CERTIFIED_CANDIDATE")
        # the ModifierId traversal argument is a selector, excluded
        wrapper = [x for x in self.audit["rows"]
                   if x["modifier_id"] == "MINOR_CIV_ANTIOCH_ROOT"
                   and x["argument_name"] == "ModifierId"]
        self.assertEqual(len(wrapper), 1)
        self.assertEqual(wrapper[0]["family"], "SELECTOR")
        self.assertEqual(wrapper[0]["disposition"], "EXCLUDED")

    # -- 4b. recursive + cycle-safe ---------------------------------------
    def test_traversal_recursive_and_cycle_safe(self):
        self.assertGreaterEqual(self.audit["counts"]["max_depth"], 1)
        self.assertTrue(self.audit["counts"]["cycles"] >= 1,
                        "the CYCLE_A <-> CYCLE_B fixture must be detected")
        cyc = self.audit["graph"]["cycles"]
        self.assertTrue(any(c["from"] == "CYCLE_A" and c["to"] == "CYCLE_B"
                            or c["from"] == "CYCLE_B" and c["to"] == "CYCLE_A"
                            for c in cyc))
        # traversal terminates and every edge target is a real definition
        defined = set(self.audit["graph"]["definitions"])
        for e in self.audit["graph"]["edges"]:
            self.assertIn(e["from"], defined)
            self.assertIn(e["to"], defined)

    # -- 5. the Vilnius-style alternate gates stay in scope ---------------
    def test_alternate_suzerain_requirement_sets_stay_in_scope(self):
        gates = self.audit["counts"]["gate_requirement_sets"]
        for level in (1, 2, 3):
            self.assertEqual(
                gates.get(f"PLAYER_IS_SUZERAIN_ALLY_LEVEL_{level}"), 1)
        roots = {r["ModifierId"] for r in self.audit["graph"]["roots"]}
        for level in (1, 2, 3):
            self.assertIn(f"MINOR_CIV_VILNIUS_ROOT_{level}", roots)
        nested = [r for r in self.audit["rows"]
                  if r["modifier_id"] == "MINOR_CIV_VILNIUS_NESTED_2"]
        self.assertEqual(len(nested), 2)
        amounts = [r for r in nested if r["argument_name"] == "Amount"]
        self.assertEqual(amounts[0]["disposition"], "CERTIFIED_CANDIDATE")
        self.assertEqual(amounts[0]["root_gate_set"],
                         "PLAYER_IS_SUZERAIN_ALLY_LEVEL_2")

    def test_non_suzerain_gated_root_is_flagged_not_broadened(self):
        flagged = self.audit["not_suzerain_gated_roots"]
        ids = {r["ModifierId"] for r in flagged}
        self.assertIn("MINOR_CIV_ANTIOCH_ROOT_NOT_GATED", ids)
        self.assertTrue(any("NOT" in r["flag"] or "not" in r["flag"]
                            for r in flagged))
        # and the flagged root is not treated as an audited root
        roots = {r["ModifierId"] for r in self.audit["graph"]["roots"]}
        self.assertNotIn("MINOR_CIV_ANTIOCH_ROOT_NOT_GATED", roots)

    # -- 6. generic envoy-tier bonuses are not swept in -------------------
    def test_generic_envoy_tier_trait_not_swept_in(self):
        ids = {r["modifier_id"] for r in self.audit["rows"]}
        # the trade type trait root is not Suzerain-gated and belongs to a
        # trait outside the audited minor-civ trait roots
        self.assertNotIn("MINOR_CIV_TRADE_TYPE_NESTED", ids)
        roots = {r["ModifierId"] for r in self.audit["graph"]["roots"]}
        self.assertNotIn("MINOR_CIV_TRADE_TYPE_ROOT", roots)

    # -- 7. selectors and capabilities are excluded -----------------------
    def test_selectors_and_capabilities_excluded(self):
        rows = {(r["modifier_id"], r["argument_name"]): r
                for r in self.audit["rows"]}
        for key in [("MINOR_CIV_LAHORE_UNIT", "UnitType"),
                    ("MINOR_CIV_LAHORE_IMPROVEMENT", "ImprovementType"),
                    ("MINOR_CIV_LAHORE_ABILITY", "AbilityType"),
                    ("MINOR_CIV_LAHORE_HOUSING", "HasBonus"),
                    ("MINOR_CIV_ANTIOCH_GOLD", "YieldType")]:
            self.assertIn(key, rows)
            self.assertEqual(rows[key]["disposition"], "EXCLUDED")
        self.assertEqual(rows[("MINOR_CIV_LAHORE_UNIT", "UnitType")]["family"],
                         "SELECTOR")
        self.assertEqual(
            rows[("MINOR_CIV_LAHORE_HOUSING", "HasBonus")]["family"],
            "BOOLEAN_UNLOCK")

    # -- 8. unique-improvement unlock -> side-path inventory ---------------
    def test_improvement_unlock_produces_side_path_inventory(self):
        imps = self.audit["side_paths"]["improvements"]
        # Batey is deliberately NOT unlocked by any trait: only the
        # mechanically discovered IMPROVEMENT_MOAI appears
        self.assertEqual(sorted(imps), ["IMPROVEMENT_MOAI"])
        moai = imps["IMPROVEMENT_MOAI"]
        self.assertTrue(moai["granted_by"])
        self.assertEqual(moai["owning_trait"], "MINOR_CIV_VILNIUS_TRAIT")
        cells = {c["cell"]: c for c in moai["cells"]}
        # direct numeric cells accounted
        self.assertIn("Improvements.Appeal", cells)
        self.assertIn("Improvements.Housing", cells)
        self.assertIn("Improvement_YieldChanges.YIELD_CULTURE", cells)
        # adjacency yield referenced through Improvement_Adjacencies
        self.assertIn("Adjacency_YieldChanges.MOAI_COASTADJACENCY_CULTURE."
                      "YieldChange", cells)
        # tourism factor preserved as a decision, never multiplied blindly
        self.assertEqual(cells["Improvement_Tourism.ScalingFactor"]
                         ["disposition"], "DECISION_REQUIRED")
        # attached modifier amount is NOT automatically a candidate
        amt = cells["ImprovementModifiers.MOAI_COASTADJACENCY_CULTURE.Amount"]
        self.assertEqual(amt["disposition"], "DECISION_REQUIRED")
        self.assertEqual(amt["family"], "FLAT_YIELD")
        # the adjacency magnitude is a decision, never a silent candidate
        self.assertEqual(
            cells["Adjacency_YieldChanges.MOAI_COASTADJACENCY_CULTURE."
                  "YieldChange"]["disposition"], "DECISION_REQUIRED")
        self.assertEqual(
            cells["Adjacency_YieldChanges.MOAI_COASTADJACENCY_CULTURE."
                  "TilesRequired"]["disposition"], "EXCLUDED")
        # base yield of the unlocked improvement is an ownership decision
        self.assertEqual(cells["Improvement_YieldChanges.YIELD_CULTURE"]
                         ["disposition"], "DECISION_REQUIRED")
        # the attached modifier's selector argument is excluded
        sel = cells["ImprovementModifiers.MOAI_COASTADJACENCY_CULTURE."
                    "YieldType"]
        self.assertEqual(sel["disposition"], "EXCLUDED")
        # plunder belongs to the attacker, not the bonus
        self.assertEqual(cells["Improvements.PlunderAmount"]
                        ["disposition"], "EXCLUDED")
        # structural and selector columns are accounted
        self.assertTrue(moai["structural_columns"])
        self.assertTrue(moai["selector_columns"])
        self.assertTrue(any(t["table"] == "Improvement_ValidTerrains"
                            for t in moai["other_tables"]))
        # closed-world accounting: every numeric Improvement column must be
        # present in exactly one of cells / structural / selector
        con = sqlite3.connect(str(self.db_path))
        try:
            cols = [c[1] for c in con.execute(
                'PRAGMA table_info("Improvements")')]
        finally:
            con.close()
        # TourismSource comes from Improvement_Tourism, not Improvements
        selectors_only = {s["column"] for s in moai["selector_columns"]
                          if s["column"] != "TourismSource"}
        accounted = ({c["cell"].split(".", 1)[1] for c in moai["cells"]
                      if c["cell"].startswith("Improvements.")}
                     | {s["column"] for s in moai["structural_columns"]}
                     | selectors_only)
        self.assertEqual(set(cols) - {"ImprovementType"}, accounted)

    def test_improvement_numeric_cells_never_auto_certified(self):
        for imp, path in self.audit["side_paths"]["improvements"].items():
            for c in path["cells"]:
                self.assertNotEqual(c["disposition"], "CERTIFIED_CANDIDATE",
                                    f"{imp}:{c['cell']} must not be a "
                                    "candidate on the side path")

    def test_zero_shipped_cells_need_no_decision(self):
        for imp, path in self.audit["side_paths"]["improvements"].items():
            for c in path["cells"]:
                if c["cell"].startswith("Improvements.") and \
                        str(c["value"]) in ("0", "0.0"):
                    self.assertEqual(c["disposition"], "EXCLUDED",
                                     f"{imp}:{c['cell']} is a zero cell")

    # -- 10. granted unique unit is accounted, not claimed -----------------
    def test_granted_unit_accounted_but_not_claimed(self):
        units = self.audit["side_paths"]["units"]
        self.assertEqual(sorted(units), ["UNIT_LAHORE_NIHANG"])
        nihang = units["UNIT_LAHORE_NIHANG"]
        direct = {c["cell"]: c for c in nihang["direct_cells"]}
        self.assertIn("Units.Combat", direct)
        self.assertIn("Units.Cost", direct)
        numeric_cells = [c for c in nihang["direct_cells"]
                         if c["cell"] in ("Units.Combat", "Units.Cost",
                                          "Units.BaseMoves")]
        for c in numeric_cells:
            self.assertEqual(c["disposition"], "EXCLUDED")
            self.assertIn("intrinsic unit definition", c["reason"])
        for c in nihang["direct_cells"]:
            self.assertEqual(c["disposition"], "EXCLUDED")
        # the Suzerain-gated promotion is flagged, not silently claimed
        suz = [m for m in nihang["promotion_modifiers"]
               if m["promotion"] ==
               "PROMOTION_NIHANG_SUZERAIN_COMBAT_BONUS"]
        self.assertEqual(len(suz), 1)
        self.assertTrue(suz[0]["suzerain_gated"])
        self.assertEqual(suz[0]["disposition"], "DECISION_REQUIRED")
        self.assertIn("LAHORE_SUZERAIN", suz[0]["subject_requirement_set_id"])
        self.assertEqual(suz[0]["argument_value"], "10")
        # intrinsic promotions are also decisions, not claims
        flank = [m for m in nihang["promotion_modifiers"]
                 if m["promotion"] == "PROMOTION_NIHANG_FLANKED_BONUS"]
        self.assertEqual(flank[0]["disposition"], "DECISION_REQUIRED")
        self.assertFalse(flank[0]["suzerain_gated"])

    # -- 8c. granted abilities -------------------------------------------
    def test_granted_ability_side_path(self):
        abilities = self.audit["side_paths"]["abilities"]
        self.assertIn("ABILITY_TRADE_ROUTE_PLUNDER_IMMUNITY_SEA", abilities)
        self.assertIn("ABILITY_WOLIN_LAND_UNITS", abilities)
        wolin = abilities["ABILITY_WOLIN_LAND_UNITS"]["modifiers"]
        amt = [m for m in wolin if m["argument_name"] == "Amount"]
        self.assertEqual(len(amt), 1)
        self.assertEqual(amt[0]["disposition"], "DECISION_REQUIRED")
        self.assertEqual(amt[0]["family"], "GREAT_PERSON_POINTS")
        # the immunity ability is a capability with no magnitude
        immunity = abilities[
            "ABILITY_TRADE_ROUTE_PLUNDER_IMMUNITY_SEA"]["modifiers"]
        self.assertEqual(len(immunity), 1)
        self.assertEqual(immunity[0]["disposition"], "EXCLUDED")

    def test_granted_objects_separate_quantity_from_intrinsic(self):
        objs = self.audit["side_paths"]["granted_objects"]
        self.assertIn("RESOURCE_CINNAMON", objs["objects"])
        note = objs["note"]
        self.assertIn("GRANT QUANTITY", note)
        self.assertIn("never multiplied", note)

    # -- legacy comparison ------------------------------------------------
    def test_legacy_comparison_historical_only(self):
        lc = self.audit["legacy_comparison"]
        self.assertTrue(lc["available"])
        # only SUZERAIN rows counted (the TRAITS row is ignored)
        self.assertEqual(lc["total_suzerain_rows"], 3)
        self.assertEqual(lc["active_roots_in_legacy_csv"], 2)
        self.assertEqual(lc["active_roots_multiplied_by_legacy_mod"], 1)
        # the Vilnius root IS in the CSV but was never multiplied (MISSING);
        # every other active root is absent from the CSV entirely
        self.assertIn("MINOR_CIV_VILNIUS_ROOT_1",
                      lc["active_roots_not_multiplied"])
        self.assertNotIn("MINOR_CIV_CARTHAGE_ROOT",
                         lc["active_roots_not_multiplied"])
        self.assertEqual(lc["obsolete_or_orphan_roots"],
                         ["MINOR_CIV_CARTHAGE_ROOT"])
        dm = lc["descendants_multiplied"]
        # the legacy mod covered the Antioch root and missed the Vilnius one
        # (the other active roots are absent from the legacy file entirely)
        self.assertEqual(dm["covered_by_legacy_mod"], 1)
        self.assertEqual(dm["covered_audit_certified_candidate"], 1)
        # Vilnius's +50% district culture was never multiplied by the legacy mod
        uncovered = [d["nested_modifier_id"] for d in dm["uncovered_detail"]]
        self.assertIn("MINOR_CIV_VILNIUS_NESTED_1", uncovered)
        self.assertEqual(set(dm["legacy_row_status_counts"]),
                         {"COMPLETE", "MISSING", "ABSENT"})
        self.assertEqual(dm["covered_audit_certified_candidate"], 1)
        self.assertIn("never treated as proof", lc["note"])

    # -- closed world ----------------------------------------------------
    def test_every_reachable_argument_has_a_disposition(self):
        self.assertEqual(len(self.audit["rows"]),
                         self.audit["counts"]["reachable_arguments"])
        for r in self.audit["rows"]:
            self.assertIn(r["disposition"],
                          ("CERTIFIED_CANDIDATE", "DECISION_REQUIRED",
                           "EXCLUDED"))
            self.assertTrue(r["reason"])
            self.assertTrue(r["family"])
        total = sum(self.audit["disposition_summary"]
                    ["reachable_rows"].values())
        self.assertEqual(total, len(self.audit["rows"]))

    def test_proposed_candidates_are_exactly_the_certified_numeric_rows(self):
        expected = {(r["modifier_id"], r["argument_name"])
                    for r in self.audit["rows"]
                    if r["numeric"]
                    and r["disposition"] == "CERTIFIED_CANDIDATE"}
        got = {(c["modifier_id"], c["argument"]) for c in
               self.audit["proposed_candidates"]}
        self.assertEqual(expected, got)
        self.assertTrue(got)

    # -- ownership design (report only) ----------------------------------
    def test_proposed_owner_bit_is_reported_not_implemented(self):
        self.assertEqual(self.audit["proposed_owner_bit"], 64)
        self.assertEqual(PROPOSED_SUZERAIN_MODULE_BIT, 64)
        self.assertEqual(PROPOSED_NEXT_MODULE_BIT_AFTER_SUZERAIN, 128)
        from civ6x10 import production
        self.assertNotIn("suzerain", production.MODULE_BITS)
        self.assertNotIn(64, set(production.MODULE_BITS.values()))
        from civ6x10.governors import PROPOSED_GOVERNOR_MODULE_BIT
        self.assertEqual(production.MODULE_BITS.get("governors"), 32)
        self.assertEqual(PROPOSED_GOVERNOR_MODULE_BIT, 32)

    # -- 11. deterministic output ----------------------------------------
    def test_deterministic_output(self):
        again = build_audit(str(self.db_path),
                            coverage_csv=str(self.csv_path))
        a = _stable(self.audit)
        b = _stable(again)
        self.assertEqual(a, b)

    # -- 12. audit-only: registry untouched ------------------------------
    def test_audit_only_leaves_production_registry_unchanged(self):
        before = _registry_digest()
        # re-run the whole audit
        build_audit(str(self.db_path), coverage_csv=str(self.csv_path))
        self.assertEqual(before, _registry_digest())
        # and the audit never claims a production row (when a registry exists)
        ov = self.audit["registry_overlap"]
        if ov.get("available"):
            self.assertEqual(ov["count"], 0)

    def test_no_manifests_suzerain_file(self):
        self.assertFalse((ROOT / "manifests" / "suzerain.yml").exists(),
                         "Phase 5A must not create a production manifest")

    # -- 13. no CE/native/controller modification -------------------------
    def test_no_ce_native_or_controller_modification(self):
        # the audit module must not import or touch native sources
        src = Path(suzerain.__file__).read_text(encoding="utf-8")
        for banned in ("GameCore", "s_modEnabled", "X10_MODULE_SUZERAIN",
                       "Mods\\\\X10"):
            self.assertNotIn(banned, src)
        # the controller config must not carry a suzerain bit yet
        cfg = ROOT / "controller" / "X10" / "Config" / "X10Config.sql"
        text = cfg.read_text(encoding="utf-8")
        self.assertIn("32=governors", text)
        self.assertNotIn("64", text)


def _stable(obj):
    """Hashable, order-insensitive view of an audit for determinism checks."""
    import json
    return json.dumps(obj, sort_keys=True, default=str)


def _registry_digest():
    import hashlib
    p = ROOT / "build" / "X10ProductionRegistry.inc"
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()

# ---------------------------------------------------------------------------
# Checked-in manifest invariants (no local data required)
# ---------------------------------------------------------------------------
AUDIT_PATH = ROOT / "civ6x10" / "rules" / "suzerain_audit.yml"


@unittest.skipUnless(AUDIT_PATH.is_file(),
                     "checked-in audit manifest unavailable")
class SuzerainAuditManifestInvariantsTest(unittest.TestCase):
    """Structural invariants of the checked-in Phase 5A audit manifest."""

    @classmethod
    def setUpClass(cls):
        import yaml
        with open(AUDIT_PATH, encoding="utf-8") as fh:
            cls.audit = yaml.safe_load(fh)

    def test_manifest_declares_audit_only(self):
        self.assertIn("audit only", self.audit["audit"].lower())
        self.assertEqual(self.audit["proposed_owner_bit"], 64)
        self.assertEqual(self.audit["proposed_next_bit_after"], 128)

    def test_manifest_records_all_required_sections(self):
        for key in ("active_city_states", "inactive_orphan_minor_leaders",
                    "counts", "disposition_summary", "family_summary",
                    "graph", "rows", "per_city_state", "proposed_candidates",
                    "side_paths", "registry_overlap", "legacy_comparison"):
            self.assertIn(key, self.audit)

    def test_manifest_graph_is_closed_world(self):
        c = self.audit["counts"]
        self.assertEqual(c["reachable_arguments"],
                         c["numeric_arguments"] + c["nonnumeric_arguments"])
        total = sum(self.audit["disposition_summary"]
                    ["reachable_rows"].values())
        self.assertEqual(total, c["reachable_arguments"])
        self.assertGreaterEqual(c["active_city_states"], 1)
        self.assertGreaterEqual(c["gate_roots"], 1)

    def test_manifest_has_no_production_rows(self):
        # the audit is a reviewed input, never a production manifest
        self.assertNotIn("governors", self.audit.get("counts", {}))
        for row in self.audit["rows"]:
            self.assertIn(row["disposition"],
                          ("CERTIFIED_CANDIDATE", "DECISION_REQUIRED",
                           "EXCLUDED"))
        # every proposed candidate is a numeric certified row
        certified = {(r["modifier_id"], r["argument_name"])
                     for r in self.audit["rows"]
                     if r["numeric"]
                     and r["disposition"] == "CERTIFIED_CANDIDATE"}
        self.assertEqual(certified, {(c["modifier_id"], c["argument"])
                                     for c in self.audit[
                                         "proposed_candidates"]})

    def test_manifest_registry_overlap_is_zero(self):
        ov = self.audit["registry_overlap"]
        if ov.get("available"):
            self.assertEqual(ov["count"], 0, "Phase 5A must not claim a "
                                             "production row")


# ---------------------------------------------------------------------------
# Real integration (local private data; skips whole-module when absent)
# ---------------------------------------------------------------------------
def _local_db():
    return ROOT / "data" / "local" / "DebugGameplay_official.sqlite"


@unittest.skipUnless(
    _local_db().is_file(),
    "official DB copy unavailable (local-only)")
class SuzerainAuditRealIntegrationTest(unittest.TestCase):
    """Full derivation against the local official DB copy.

    Skipped as a whole module when the private copy is absent so CI never
    compares a partial derivation.
    """

    @classmethod
    def setUpClass(cls):
        cls.audit = build_audit(
            str(_local_db()),
            coverage_csv=str(ROOT / "data" / "local" / "trait_coverage.csv"))

    def test_real_counts(self):
        c = self.audit["counts"]
        # authoritative active membership
        self.assertEqual(c["active_city_states"], 48)
        self.assertEqual(c["active_minor_leaders"], 48)
        self.assertEqual(c["active_minor_traits"], 48)
        self.assertEqual(c["inactive_orphan_minor_leaders"], 2)
        # the two orphan historical definitions
        orphans = sorted(o["LeaderType"] for o in
                        self.audit["inactive_orphan_minor_leaders"])
        self.assertEqual(orphans, ["LEADER_MINOR_CIV_CARTHAGE",
                                   "LEADER_MINOR_CIV_STOCKHOLM"])
        # graph
        self.assertEqual(c["gate_roots"], 91)
        self.assertEqual(c["reachable_definitions"], 182)
        self.assertEqual(c["modifier_to_modifier_edges"], 91)
        self.assertEqual(c["numeric_arguments"], 74)
        self.assertEqual(c["definitions_with_numeric_arguments"], 73)
        self.assertEqual(c["cycles"], 0)
        self.assertEqual(c["modifier_to_modifier_edges"],
                         c["nested_definitions"])
        # the three Vilnius-style alternate gates
        gates = c["gate_requirement_sets"]
        self.assertEqual(gates["PLAYER_IS_SUZERAIN"], 88)
        for level in (1, 2, 3):
            self.assertEqual(gates[f"PLAYER_IS_SUZERAIN_ALLY_LEVEL_{level}"], 1)
        # all roots are MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER
        self.assertEqual(c["gate_root_effect_types"],
                         {"MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER": 91})
        # side paths
        self.assertEqual(c["side_path_improvements"], 9)
        self.assertEqual(c["side_path_units"], 1)
        self.assertEqual(c["side_path_abilities"], 3)

    def test_real_side_path_contents(self):
        imps = sorted(self.audit["side_paths"]["improvements"])
        self.assertEqual(imps, [
            "IMPROVEMENT_ALCAZAR", "IMPROVEMENT_BATEY",
            "IMPROVEMENT_COLOSSAL_HEAD", "IMPROVEMENT_MAHAVIHARA",
            "IMPROVEMENT_MOAI", "IMPROVEMENT_MONASTERY",
            "IMPROVEMENT_MOUND", "IMPROVEMENT_NAZCA_LINE",
            "IMPROVEMENT_TRADING_DOME"])
        self.assertEqual(sorted(self.audit["side_paths"]["units"]),
                         ["UNIT_LAHORE_NIHANG"])
        # the Zanzibar/Hattusa granted resources
        objs = self.audit["side_paths"]["granted_objects"]["objects"]
        for r in ("RESOURCE_CINNAMON", "RESOURCE_CLOVES",
                  "RESOURCE_ALUMINUM", "RESOURCE_URANIUM"):
            self.assertIn(r, objs)

    def test_real_registry_overlap_is_zero(self):
        self.assertEqual(self.audit["registry_overlap"]["count"], 0)

    def test_real_legacy_comparison(self):
        lc = self.audit["legacy_comparison"]
        self.assertTrue(lc["available"])
        self.assertEqual(lc["total_suzerain_rows"], 103)
        self.assertEqual(lc["active_roots_in_legacy_csv"], 91)
        self.assertEqual(lc["active_roots_multiplied_by_legacy_mod"], 73)
        self.assertEqual(len(lc["active_roots_not_multiplied"]), 18)
        # the legacy mod also multiplied obsolete orphan roots
        obsolete = lc["obsolete_or_orphan_roots"]
        self.assertEqual(len(obsolete), 12)
        self.assertTrue(all(r.startswith("MINOR_CIV_CARTHAGE_")
                            or r.startswith("MINOR_CIV_STOCKHOLM_")
                            for r in obsolete))
        dm = lc["descendants_multiplied"]
        self.assertEqual(dm["total_active_descendants"], 74)
        self.assertEqual(dm["covered_by_legacy_mod"], 68)
        self.assertEqual(dm["uncovered_by_legacy_mod"], 6)


if __name__ == "__main__":
    unittest.main()
