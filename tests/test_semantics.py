"""Semantic certification regressions: the gate, not heuristics, admits rows.

CI-safe tests use synthetic floors; local-only tests scan the full certified
registry (manifests + data/local floor, both gitignored).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

from civ6x10 import semantics as S
from civ6x10.certification import certify_row, load_rules
from civ6x10.production import build_production_registry


def manifest_row(modifier_type, effect_type, arg, official="5",
                 family="FLAT_AMOUNT", transform="canonical_x10_multiply",
                 status="ok", mid="M_X"):
    return {"object_id": "O", "modifier_id": mid, "modifier_type": modifier_type,
            "effect_type": effect_type, "argument_name": arg,
            "official_value": official, "semantic_family": family,
            "transformation": transform, "generated_value": "", "status": status,
            "confidence": "auto_rule", "module": "traits"}


def floor_row(modifier_type, effect_type, arg, family,
              transform="CANONICAL_X10_MULTIPLY"):
    return {"modifier_type": modifier_type, "effect_type": effect_type,
            "argument_name": arg, "semantic_family": family,
            "transformation_family": transform, "confidence": "AUTO_PATTERN"}


def load_manifests():
    import yaml
    rows = []
    for module in ("traits", "policies", "governments"):
        man = yaml.safe_load(
            open(ROOT / "manifests" / f"{module}.yml", encoding="utf-8"))
        for r in man[module]:
            r = dict(r)
            r["module"] = module
            rows.append(r)
    return rows


def load_floor():
    import csv
    with open(ROOT / "data" / "local" / "effect_semantics.csv",
              encoding="utf-8", newline="") as fh:
        return {(r["modifier_type"], r["effect_type"], r["argument_name"]): r
                for r in csv.DictReader(fh)}


class TestNoCertifiedHeuristics(unittest.TestCase):
    def test_no_generic_amount_fallback_produces_certified_status(self):
        # Every infer_family output is auto_rule or needs_human: heuristics
        # never claim certification.
        for args in [("M", "E", "Amount", ["5"]),
                     ("M", "EFFECT_X", "Value", ["3"]),
                     ("M", "E", "YieldChange", ["2"]),
                     ("M", "E_DISCOUNT_X", "Percent", ["-20"]),
                     ("M", "EFFECT_COMBAT_STRENGTH_X", "Amount", ["5"]),
                     ("M", "E", "TurnsActive", ["10"]),
                     ("M", "E", "YieldType", ["YIELD_GOLD"])]:
            fam, tr, conf = S.infer_family(*args)
            self.assertIn(conf, ("auto_rule", "needs_human"), args)
            self.assertNotIn(conf, ("reviewed", "certified"), args)

    def test_uncertified_claims_fail_closed(self):
        rules = load_rules()
        # COMBAT claim on an effect nobody curated, with a silent floor:
        # conflict, never certified.
        # Plain magnitudes certify by category under a silent floor.
        c = certify_row(
            manifest_row("M1", "EFFECT_ADJUST_UNIT_PRODUCTION",
                         "Amount", family="FLAT_AMOUNT"),
            floor_row("M1", "EFFECT_ADJUST_UNIT_PRODUCTION", "Amount",
                      "MAGNITUDE_UNCLASSIFIED"), rules)
        self.assertTrue(c["certified"])
        self.assertEqual(c["resolution"], "certified")
        self.assertEqual(c["source"], "category:FLAT_AMOUNT")
        c = certify_row(
            manifest_row("M1", "EFFECT_ADJUST_UNIT_PRODUCTION",
                         "Amount", family="COMBAT_STRENGTH_BONUS",
                         transform="canonical_combat_bonus"),
            floor_row("M1", "EFFECT_ADJUST_UNIT_PRODUCTION", "Amount",
                      "MAGNITUDE_UNCLASSIFIED"), rules)
        self.assertFalse(c["certified"])
        self.assertTrue(c["resolution"].startswith("conflict:"))
        c = certify_row(
            manifest_row("M1", "EFFECT_ADJUST_UNIT_BARBARIAN_COMBAT",
                         "Amount", family="FLAT_AMOUNT"),
            floor_row("M1", "EFFECT_ADJUST_UNIT_BARBARIAN_COMBAT", "Amount",
                      "MAGNITUDE_UNCLASSIFIED"), rules)
        self.assertTrue(c["certified"])
        self.assertEqual(c["kind"], "COMBAT")
        self.assertTrue(c["source"].startswith("override:combat-points:"))
        # Grant rows never certify as additive.
        c = certify_row(
            manifest_row("MODIFIER_PLAYER_GRANT_SPY", "EFFECT_GRANT_SPY",
                         "Amount", official="1"),
            floor_row("MODIFIER_PLAYER_GRANT_SPY", "EFFECT_GRANT_SPY",
                      "Amount", "GRANT_OBJECT", "CANONICAL_REPEAT"), rules)
        self.assertFalse(c["certified"])
        self.assertEqual(c["resolution"], "excluded:grant-object")


class TestFullRegistrySemantics(unittest.TestCase):
    def _entries(self):
        try:
            rows = load_manifests()
            floor = load_floor()
        except FileNotFoundError:
            self.skipTest("manifests/floor unavailable (local-only)")
        return build_production_registry(rows, sem_floor=floor)

    def test_zero_unresolved_semantic_conflicts(self):
        entries, report = self._entries()
        self.assertEqual(report["unresolved_conflicts"], [])
        for c in report["conflict_ledger"]:
            self.assertFalse(c["resolution"].startswith("conflict:"), c)

    def test_grant_object_cannot_emit_additive(self):
        entries, _ = self._entries()
        rows = { (r["modifier_id"], r["argument_name"]): r
                 for r in load_manifests() }
        floor = load_floor()
        for e in entries:
            r = rows[(e["modifier_id"], e["argument"])]
            s = floor[(r["modifier_type"], r["effect_type"],
                       r["argument_name"])]
            self.assertNotEqual(s["semantic_family"], "GRANT_OBJECT",
                                e["modifier_id"])
            # Curated grant-like exclusions stay out entirely.
            self.assertNotIn(r["effect_type"], (
                "EFFECT_ADJUST_EXTRA_UNIT_COPY",
                "EFFECT_ADJUST_EXTRA_UNIT_COPY_TAG",
                "EFFECT_ADJUST_PLAYER_ADJUST_ENVOYS_NON_SPECIALTY",
                "EFFECT_ADJUST_PLAYER_SPECIFIC_DISTRICT_GRANT_ENVOYS",
                "EFFECT_ADJUST_DUPLICATE_FIRST_INFLUENCE_TOKEN",
                "EFFECT_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_RIVAL_GOVERNMENT",
                "EFFECT_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_SAME_RELIGION",
                "EFFECT_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_TRADE_ROUTE_TO",
                "EFFECT_ADJUST_UNIT_GRANT_EXPERIENCE",
                "EFFECT_ADJUST_FREE_CIVIC_BOOST_FIRST_TRADING_POST_EACH_CIV",
                "EFFECT_ADJUST_FREE_TECH_BOOST_FIRST_TRADING_POST_EACH_CIV",
                "EFFECT_ADJUST_FREE_CIVIC_BOOST_WONDER_ERA",
                "EFFECT_ADJUST_FREE_TECH_BOOST_WONDER_ERA"), e["modifier_id"])

    def test_spatial_budget_cannot_enter_without_override(self):
        entries, _ = self._entries()
        rows = {(r["modifier_id"], r["argument_name"]): r
                for r in load_manifests()}
        floor = load_floor()
        for e in entries:
            r = rows[(e["modifier_id"], e["argument"])]
            s = floor[(r["modifier_type"], r["effect_type"],
                       r["argument_name"])]
            self.assertNotEqual(s["semantic_family"], "SPATIAL_BUDGET",
                                e["modifier_id"])

    def test_decision_required_families_cannot_enter(self):
        entries, _ = self._entries()
        rows = {(r["modifier_id"], r["argument_name"]): r
                for r in load_manifests()}
        floor = load_floor()
        banned = {"UNKNOWN", "BOOLEAN_UNLOCK", "MULTIPLICATIVE_FACTOR",
                  "COUNT_OR_DURATION", "MIXED_VALUE_DOMAIN",
                  "DEFEATED_STRENGTH_SCALING"}
        for e in entries:
            r = rows[(e["modifier_id"], e["argument"])]
            s = floor[(r["modifier_type"], r["effect_type"],
                       r["argument_name"])]
            if s["semantic_family"] in banned:
                # MIXED rows enter only via an explicit curated override.
                self.assertEqual(s["semantic_family"], "MIXED_VALUE_DOMAIN", e)
                self.assertTrue(
                    e["cert_source"].startswith("override:mixed:"), e)

    def test_known_discount_effects_emit_discount(self):
        entries, _ = self._entries()
        by_id = {}
        for e in entries:
            by_id.setdefault(e["modifier_id"], []).append(e)
        for mid in ("TRAIT_LEVY_DISCOUNT", "HARALD_LEVY_DISCOUNT",
                    "LEVY_UNITUPGRADEDISCOUNT",
                    "PROFESSIONAL_ARMY_UNITUPGRADEDISCOUNT",
                    "PROFESSIONAL_ARMY_UPGRADE_RESOURCE_DISCOUNT",
                    "HARALD_MAINTENANCE_DISCOUNT",
                    "CONSCRIPTION_UNITMAINTENANCEDISCOUNT",
                    "LEVEEENMASSE_UNITMAINTENANCEDISCOUNT",
                    "FLOWER_POWER_ROCKBAND_DISCOUNT",
                    "SUNDIATA_KEITA_PURCHASE_GREAT_PEOPLE",
                    "SECONDSTRIKE_MAINTENANCEWMDS"):
            self.assertIn(mid, by_id, mid)
            for e in by_id[mid]:
                self.assertEqual(e["kind"], "DISCOUNT", (mid, e))

    def test_known_strength_effects_emit_combat_where_certified(self):
        entries, _ = self._entries()
        by_id = {}
        for e in entries:
            by_id.setdefault(e["modifier_id"], []).append(e)
        for mid in ("DISCIPLINE_BARBARIANCOMBAT", "TRAIT_CAESAR_BARB_COMBAT",
                    "TRAIT_EACH_DIPLO_VISIBILITY_COMBAT_MODIFIER",
                    "TRAIT_TERRITORIAL_WAR_COMBAT",
                    "TRAIT_LAND_CORPS_COMBAT_STRENGTH",
                    "TRAIT_LAND_ARMIES_COMBAT_STRENGTH",
                    "TRAIT_TOQUI_COMBAT_BONUS_VS_GOLDEN_AGE_CIV"):
            self.assertIn(mid, by_id, mid)
            amounts = [e for e in by_id[mid] if e["argument"] == "Amount"]
            self.assertTrue(amounts, mid)
            for e in amounts:
                self.assertEqual(e["kind"], "COMBAT", (mid, e))
        # Damage-reduction is NOT strength points: excluded, not combat.
        self.assertNotIn("NATIONALIDENTITY_REDUCESTRENGTHREDUCTIONFORDAMAGE",
                         by_id)

    def test_count_like_or_excluded_for_discrete_effects(self):
        entries, _ = self._entries()
        by_key = {(e["modifier_id"], e["argument"]): e for e in entries}
        for key in (("PUBLICWORKS_BUILDERCHARGES", "Amount"),
                    ("TRAIT_MISSIONARY_SPREADS", "Amount"),
                    ("SUNDIATA_KEITA_MARKET_GREAT_WRITING_SLOTS", "Amount"),
                    ("TRAIT_EXTRA_PALACE_SLOTS", "Amount"),
                    ("POPULATION_PRESETTLEMENT", "Amount"),
                    ("INQUISITION_REDUCE_START_CHARGES", "Amount"),
                    ("TRAIT_ALLOW_QUESTS_IN_GOLDEN_AGE", "Amount"),
                    ("ELIZABETH_TRADE_ROUTES_MODIFIER", "Amount"),
                    ("TRAIT_ADJUST_LIGHTHOUSE_STOCKPILE_CAP", "Amount"),
                    ("FRESCOES_ARTIST_ARTMUSEUM", "Amount"),
                    ("TRAIT_ALLIANCE_POINTS_FROM_COMMON_FOE", "Amount"),
                    ("NUCLEARESPIONAGE_EXTRABOOSTS", "Amount"),
                    ("TRAIT_INCREASED_TILES", "Amount"),
                    ("TRAIT_EXTRA_DISTRICT_EACH_CITY", "Amount")):
            self.assertIn(key, by_key, key)
            self.assertTrue(by_key[key]["count_like"], key)
        # Free units/spies/buildings never enter at all.
        for mid in ("BUILDER_PRESETTLEMENT", "WU_ZETIAN_FREE_SPY",
                    "UNIQUE_LEADER_ADD_SPY_CAPACITY",
                    "TRAIT_ADJUST_NON_CAPITAL_FREE_CHEAPEST_BUILDING",
                    "LEVY_MILITARY_TWO_FREE_ENVOYS",
                    "TRAIT_FREE_ENVOY_WHEN_DISTRICT_MADE",
                    "TRAIT_EXTRASAKAHORSEARCHER",
                    "GOLDEN_AGE_TRADE_ROUTE"):
            self.assertNotIn(mid, {e["modifier_id"] for e in entries}, mid)

    def test_auto_theme_thresholds_excluded(self):
        entries, _ = self._entries()
        ids = {e["modifier_id"] for e in entries}
        self.assertNotIn("AUTO_THEME_AT_LEAST_2_SLOTS", ids)
        self.assertNotIn("AUTO_THEME_AT_LEAST_3_SLOTS", ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
