"""Phase 6A.3: gate-fix verification + full Phase-6B certification dry run.

The focused tests are CI-safe (synthetic floor rows + checked-in rules).
The complete dry run needs local manifests/floor/registry and skips cleanly
without them.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

COMPLETION = ("EFFECT_GRANT_CITY_YIELD_PERCENT_BUILDING_CREATED_COST",
              "BuildingProductionPercent")
VATICAN = ("EFFECT_GRANT_PLAYER_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED",
           "Amount")


def grant_object_floor():
    return {"semantic_family": "GRANT_OBJECT", "confidence": "AUTO_PATTERN"}


def manifest_row(mt, et, arg, official, family):
    return {"modifier_id": "MID_X", "modifier_type": mt, "effect_type": et,
            "argument_name": arg, "official_value": official,
            "semantic_family": family,
            "transformation": "canonical_x10_multiply", "status": "ok"}


class TestGrantObjectFailureReproduced(unittest.TestCase):
    """The Phase-6A.2 mixed_overrides proposal cannot work: the gate only
    consults mixed_overrides for MIXED_VALUE_DOMAIN floors, while these
    tuples sit on GRANT_OBJECT. Demonstrated against the CURRENT gate."""

    def test_three_rows_excluded_without_fix(self):
        from civ6x10.certification import certify_row, load_rules
        import copy
        # the pre-fix gate: no strong-family mechanism at all (plus the
        # unworkable mixed_overrides proposal present, to prove it cannot
        # help GRANT_OBJECT rows)
        rules = copy.deepcopy(load_rules())
        rules.pop("strong_family_overrides", None)
        rules.setdefault("mixed_overrides", []).append(
            {"effect": COMPLETION[0], "argument": COMPLETION[1],
             "kind": "ADDITIVE", "rationale": "6A.2 proposal (unworkable)"})
        cases = [
            ("MODIFIER_SINGLE_CITY_GRANT_YIELD_PER_BUILDING_COST",
             COMPLETION[0], COMPLETION[1], "25", "PERCENT_BONUS"),
            ("MODIFIER_PLAYER_CITIES_GRANT_YIELD_PER_BUILDING_COST",
             COMPLETION[0], COMPLETION[1], "10", "PERCENT_BONUS"),
            ("MODIFIER_PLAYER_GRANT_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED",
             VATICAN[0], VATICAN[1], "400", "LOYALTY"),
        ]
        for mt, et, arg, val, fam in cases:
            c = certify_row(manifest_row(mt, et, arg, val, fam),
                            grant_object_floor(), rules)
            self.assertFalse(c["certified"], (et, arg))
            self.assertEqual(c["resolution"], "excluded:grant-object",
                             (et, arg))


class TestStrongFamilyOverride(unittest.TestCase):
    def test_completion_certifies_with_fix(self):
        from civ6x10.certification import certify_row, load_rules
        rules = load_rules()
        for mt, val in (("MODIFIER_SINGLE_CITY_GRANT_YIELD_PER_BUILDING_COST",
                         "25"),
                        ("MODIFIER_PLAYER_CITIES_GRANT_YIELD_PER_BUILDING_COST",
                         "10")):
            c = certify_row(
                manifest_row(mt, COMPLETION[0], COMPLETION[1], val,
                             "PERCENT_BONUS"),
                grant_object_floor(), rules)
            self.assertTrue(c["certified"], (mt, c))
            self.assertEqual(c["kind"], "ADDITIVE")
            self.assertFalse(c["count_like"])
            self.assertEqual(
                c["source"],
                "curated-effect:strong-family:"
                "EFFECT_GRANT_CITY_YIELD_PERCENT_BUILDING_CREATED_COST")

    def test_vatican_certifies_with_fix(self):
        from civ6x10.certification import certify_row, load_rules
        rules = load_rules()
        c = certify_row(
            manifest_row(
                "MODIFIER_PLAYER_GRANT_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED",
                VATICAN[0], VATICAN[1], "400", "LOYALTY"),
            grant_object_floor(), rules)
        self.assertTrue(c["certified"], c)
        self.assertEqual(c["kind"], "ADDITIVE")
        self.assertFalse(c["count_like"])

    def test_floor_drift_fails_closed(self):
        from civ6x10.certification import certify_row, load_rules
        rules = load_rules()
        drift = {"semantic_family": "MAGNITUDE_UNCLASSIFIED",
                 "confidence": "NEEDS_REVIEW"}
        c = certify_row(
            manifest_row("MODIFIER_SINGLE_CITY_GRANT_YIELD_PER_BUILDING_COST",
                         COMPLETION[0], COMPLETION[1], "25", "PERCENT_BONUS"),
            drift, rules)
        self.assertFalse(c["certified"])
        self.assertIn("strong-override-floor-drift", c["resolution"])

    def test_proposed_family_mismatch_fails_closed(self):
        from civ6x10.certification import certify_row, load_rules
        rules = load_rules()
        c = certify_row(
            manifest_row("MODIFIER_SINGLE_CITY_GRANT_YIELD_PER_BUILDING_COST",
                         COMPLETION[0], COMPLETION[1], "25", "FLAT_YIELD"),
            grant_object_floor(), rules)
        self.assertFalse(c["certified"])
        self.assertIn("strong-override-family-mismatch", c["resolution"])

    def test_selector_sibling_remains_excluded(self):
        from civ6x10.certification import certify_row, load_rules
        rules = load_rules()
        for arg in ("YieldType", "IncludeWonder"):
            c = certify_row(
                manifest_row(
                    "MODIFIER_SINGLE_CITY_GRANT_YIELD_PER_BUILDING_COST",
                    COMPLETION[0], arg, "0", "SELECTOR"
                    if arg == "YieldType" else "BOOLEAN_UNLOCK"),
                grant_object_floor(), rules)
            self.assertFalse(c["certified"], arg)

    def test_override_hits_are_exactly_reviewed_rows(self):
        # Phase 6B + 8B: every strong-family override tuple matches only
        # status-ok reviewed rows; Ramses corroborators stay undecided and
        # no undecided row shares a tuple (fail-closed ledger proves it).
        # The table grows by review (6B: 2 tuples; 8B: grants, spatial
        # budgets, post-combat percents, tourism factor), never by widening.
        from civ6x10.bridge import collect_registry_rows
        from civ6x10.certification import load_rules
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        try:
            rows = collect_registry_rows(root)
        except FileNotFoundError:
            self.skipTest("local-only registry inputs unavailable")
        rules = load_rules()
        table = {(e["effect"], e["argument"]) for e in
                 rules.get("strong_family_overrides") or []}
        # 2 (6B) + 33 reviewed 8B tuples (grants, spatial budgets,
        # post-combat percents, tourism factor, air slots, papal
        # pressure, yield bursts).
        self.assertEqual(len(table), 35)
        hits = sorted((r["modifier_id"], r["argument_name"]) for r in rows
                      if (r.get("effect_type"), r.get("argument_name"))
                      in table and r.get("status") == "ok")
        # The 6B core is still present; the 8B growth is reviewed per-tuple
        # in the rules file (each entry carries its own rationale).
        for key in (
                ("CARDINAL_CITADEL_OF_GOD_FAITH_FINISH_BUILDINGS",
                 "BuildingProductionPercent"),
                ("MINOR_CIV_AYUTTHAYA_CULTURE_COMPLETE_BUILDING",
                 "BuildingProductionPercent"),
                ("MINOR_CIV_VATICAN_CITY_GREAT_PERSON_RELIGIOUS_PRESSURE",
                 "Amount"),
                ("PYRAMID_GRANT_BUILDERS", "Amount"),
                ("JEBELBARKAL_GRANT_FOUR_IRON_PER_TURN", "Amount"),
                ("TRAIT_LEADER_FAITH_KILLS", "PercentDefeatedStrength")):
            self.assertIn(key, hits, key)
        undecided = [(r["modifier_id"], r["argument_name"]) for r in rows
                     if (r.get("effect_type"), r.get("argument_name"))
                     in table and r.get("status") != "ok"]
        # Undecided rows sharing a tuple are sibling selectors (UnitType,
        # ResourceType, ...), never magnitudes: they stay out via the
        # status gate while the Amount rows certify.
        for mid, arg in undecided:
            self.assertNotEqual(arg, "Amount", (mid, arg))
            self.assertNotEqual(arg, "PercentDefeatedStrength", (mid, arg))

    def test_unrelated_grant_object_rows_remain_excluded(self):
        from civ6x10.certification import certify_row, load_rules
        rules = load_rules()
        c = certify_row(
            manifest_row("MODIFIER_PLAYER_ADJUST_NATURAL_WONDER_RELIC",
                         "EFFECT_ADJUST_NATURAL_WONDER_RELIC",
                         "Amount", "1", "GRANT_OBJECT"),
            grant_object_floor(), rules)
        self.assertFalse(c["certified"])
        self.assertEqual(c["resolution"], "excluded:grant-object")

    def test_excluded_effects_keep_precedence(self):
        import copy
        from civ6x10.certification import certify_row, load_rules
        rules = load_rules()
        # baseline: the completion tuple is not deliberately excluded
        c = certify_row(
            manifest_row("MODIFIER_SINGLE_CITY_GRANT_YIELD_PER_BUILDING_COST",
                         COMPLETION[0], COMPLETION[1], "25", "PERCENT_BONUS"),
            grant_object_floor(), rules)
        self.assertTrue(c["certified"])
        # if the effect were ever deliberately excluded, the exclusion wins
        # over the strong-family override (ordering guarantee)
        blocked = copy.deepcopy(rules)
        blocked.setdefault("excluded_effects", []).append(
            {"effect": COMPLETION[0], "rationale": "synthetic hold"})
        c = certify_row(
            manifest_row("MODIFIER_SINGLE_CITY_GRANT_YIELD_PER_BUILDING_COST",
                         COMPLETION[0], COMPLETION[1], "25", "PERCENT_BONUS"),
            grant_object_floor(), blocked)
        self.assertFalse(c["certified"])
        self.assertEqual(c["resolution"], "excluded:curated-effect")


if __name__ == "__main__":
    unittest.main(verbosity=2)
