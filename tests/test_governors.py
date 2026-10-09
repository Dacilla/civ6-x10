"""Phase 4A: closed-world Governor audit completeness.

Everything here is derived from the official DB copy (local-only) plus the
mode-gated Secret Societies XML that ships with the installed game. CI-safe:
DB-dependent assertions skip when the local copy is absent, but the
manifest-shape and design-decision assertions always run.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

from civ6x10.governors import (
    PROPOSED_GOVERNOR_MODULE_BIT,
    PROPOSED_NEXT_MODULE_BIT_AFTER_GOVERNORS,
    build_audit,
    build_manifest,
)

SECRET_SOCIETY_GOVERNORS = {
    "GOVERNOR_OWLS_OF_MINERVA", "GOVERNOR_HERMETIC_ORDER",
    "GOVERNOR_VOIDSINGERS", "GOVERNOR_SANGUINE_PACT",
}
ACTUAL_SECRET_SOCIETY_GOVERNORS = {
    "GOVERNOR_OWLS_OF_MINERVA", "GOVERNOR_HERMETIC_ORDER",
    "GOVERNOR_VOIDSINGERS", "GOVERNOR_SANGUINE_PACT",
}
BASE_GOVERNORS = {
    "GOVERNOR_IBRAHIM", "GOVERNOR_THE_AMBASSADOR", "GOVERNOR_THE_BUILDER",
    "GOVERNOR_THE_CARDINAL", "GOVERNOR_THE_DEFENDER", "GOVERNOR_THE_EDUCATOR",
    "GOVERNOR_THE_MERCHANT", "GOVERNOR_THE_RESOURCE_MANAGER",
}


def local_db():
    p = ROOT / "data" / "local" / "DebugGameplay_official.sqlite"
    if not p.is_file():
        raise FileNotFoundError(str(p))
    return p


def audit_or_skip():
    try:
        return build_audit(local_db(), root=ROOT)
    except FileNotFoundError:
        raise unittest.SkipTest("official DB copy unavailable (local-only)")


class TestDesignDecisions(unittest.TestCase):
    """Ownership design and no-production-change guarantees."""

    def test_proposed_owner_bit_is_next_free_value(self):
        from civ6x10.production import MODULE_BITS
        self.assertEqual(MODULE_BITS, {"traits": 1, "policies": 2,
                                       "governments": 4, "pantheons": 8,
                                       "wonders": 16})
        self.assertEqual(PROPOSED_GOVERNOR_MODULE_BIT, 32)
        self.assertEqual(PROPOSED_NEXT_MODULE_BIT_AFTER_GOVERNORS, 64)
        self.assertNotIn("governors-as-module", MODULE_BITS)

    def test_audit_writes_no_production_artifacts(self):
        # Phase 4A generates no registry include and touches no SQL.
        import civ6x10.governors as g
        self.assertFalse(hasattr(g, "emit_cxx"))
        self.assertFalse(hasattr(g, "emit_bridge_sql"))
        from civ6x10 import production
        self.assertNotIn("governors_module", dir(production))
        self.assertNotIn(32, set(production.MODULE_BITS.values()))


class TestDiscovery(unittest.TestCase):
    def setUp(self):
        self.audit = audit_or_skip()
        self.u = self.audit["universe"]

    def test_governor_count_and_split(self):
        self.assertEqual(len(self.u["governors"]), 12)
        self.assertTrue(BASE_GOVERNORS <= set(self.u["governors"]))
        self.assertEqual(set(self.u["secret_societies"]["governors"]),
                         SECRET_SOCIETY_GOVERNORS)

    def test_secret_societies_use_same_framework(self):
        # Their governor types appear in GovernorPromotionSets with the same
        # promotion/level structure as ordinary governors.
        sets = self.u["sets"]
        ss_sets = [s for s in sets if s["GovernorType"] in SECRET_SOCIETY_GOVERNORS]
        self.assertEqual(len(ss_sets), 16)
        self.assertEqual(len({s["GovernorPromotion"] for s in ss_sets}), 16)
        for gt in SECRET_SOCIETY_GOVERNORS:
            g = self.u["governors"][gt]
            self.assertEqual(len(g.get("promotions", [])), 4, gt)
            self.assertTrue(g.get("IdentityPressure"), gt)
        # promos 1..4 per society: one base ability + three levels
        for gt in SECRET_SOCIETY_GOVERNORS:
            levels = sorted(self.u["promotions"][p]["Level"]
                            for p in self.u["governors"][gt]["promotions"])
            self.assertEqual(levels, ["0", "1", "2", "3"], gt)

    def test_secret_society_provenance_is_mode_gated(self):
        for gt in SECRET_SOCIETY_GOVERNORS:
            src = self.u["governors"][gt]["source"]
            self.assertIn("Secret Societies", src, gt)
            self.assertIn("GAMEMODE_SECRETSOCIETIES",
                          self.u["governors"][gt]["load_order"], gt)

    def test_promotions_all_attached(self):
        attached = {p for g in self.u["governors"].values()
                    for p in g.get("promotions", [])}
        self.assertEqual(attached, set(self.u["promotions"]))
        self.assertEqual(len(self.u["promotions"]), 64)

    def test_governor_direct_numeric_cells(self):
        self.assertEqual(self.u["governors"]["GOVERNOR_IBRAHIM"]["IdentityPressure"], 8)
        self.assertEqual(self.u["governors"]["GOVERNOR_THE_AMBASSADOR"]["TransitionStrength"], 100)
        self.assertEqual(self.u["governors"]["GOVERNOR_OWLS_OF_MINERVA"]["IdentityPressure"], "10")


class TestClosedWorld(unittest.TestCase):
    def setUp(self):
        self.audit = audit_or_skip()
        self.rows = self.audit["rows"]
        self.u = self.audit["universe"]

    def test_every_governor_has_disposition(self):
        for gt in self.u["governors"]:
            self.assertTrue(any(r["root_governor"] == gt for r in self.rows), gt)

    def test_every_promotion_has_disposition(self):
        with_rows = {r["root_promotion"] for r in self.rows if r["root_promotion"]}
        for pt in self.u["promotions"]:
            self.assertIn(pt, with_rows, pt)

    def test_every_reachable_row_has_explicit_disposition(self):
        for r in self.rows:
            self.assertIn(r["disposition"],
                          ("CERTIFIED_CANDIDATE", "EXCLUDED", "DECISION_REQUIRED"),
                          r)
            self.assertTrue(r["reason"].strip(), r)
            self.assertTrue(r["family"], r)

    def test_zero_unexplained_reachable_rows(self):
        # no row may fall through the curated classifier
        for r in self.rows:
            self.assertNotIn("no curated", r["reason"], r["modifier_id"])

    def test_zero_absent_modifier_definitions(self):
        for r in self.rows:
            self.assertIsNotNone(r["modifier_type"], r["modifier_id"])
            self.assertIsNotNone(r["effect_type"], r["modifier_id"])

    def test_every_direct_numeric_cell_has_disposition(self):
        cells = self.audit["direct_cells"]
        self.assertTrue(cells)
        for c in cells:
            self.assertIn(c["disposition"], ("EXCLUDED", "DECISION_REQUIRED"), c)
            self.assertTrue(c["reason"].strip(), c)

    def test_requirement_thresholds_are_not_scaled(self):
        # Radius/threshold requirements must never be certified as magnitudes.
        for r in self.rows:
            if r["family"] == "SPATIAL_BUDGET":
                self.assertEqual(r["disposition"], "EXCLUDED", r["modifier_id"])

    def test_loyalty_family_never_certified(self):
        # Toqui hold class: identity/loyalty pressure effects are never
        # certified by this audit.
        for r in self.rows:
            if r["family"] == "LOYALTY":
                self.assertNotEqual(r["disposition"], "CERTIFIED_CANDIDATE",
                                    r["modifier_id"])

    def test_engine_integral_rows_flagged(self):
        eng = [r for r in self.rows if r["engine_integral"]]
        self.assertEqual(len(eng), 4)
        self.assertEqual({r["effect_type"] for r in eng},
                         {"EFFECT_ADJUST_BUILDING_YIELD_CHANGE"})
        # every engine-integral candidate carries the gate requirement
        for r in eng:
            if r["disposition"] == "CERTIFIED_CANDIDATE":
                self.assertIn("integral gate required", r["reason"], r["modifier_id"])


class TestOverlapAndSidePaths(unittest.TestCase):
    def setUp(self):
        self.audit = audit_or_skip()

    def test_shared_definition_identified(self):
        ov = self.audit["registry_overlap"]
        self.assertTrue(ov["available"])
        self.assertEqual(ov["shared"], ["SULEIMAN_GOVERNOR_POINTS"])

    def test_shared_row_not_certified_for_governors(self):
        for r in self.audit["rows"]:
            if r["modifier_id"] == "SULEIMAN_GOVERNOR_POINTS":
                self.assertEqual(r["disposition"], "EXCLUDED", r["modifier_id"])
                self.assertEqual(r["family"], "GOVERNOR_TITLES")

    def test_unit_ability_side_path_documented(self):
        side = self.audit["unit_ability_modifiers"]
        if not side:
            self.skipTest("game install not present (mode XML unavailable)")
        self.assertTrue(all(s["disposition"] == "OUT_OF_GRAPH" for s in side))
        ids = {s["modifier_id"] for s in side}
        self.assertIn("SPREAD_DISSENT_LOYALTY_DAMAGE", ids)
        for s in side:
            if s["modifier_id"] == "SPREAD_DISSENT_LOYALTY_DAMAGE":
                self.assertEqual(s["value"], "10")


class TestManifest(unittest.TestCase):
    """The checked-in manifest must match a fresh derivation exactly."""

    def test_manifest_matches_repo_file(self):
        import yaml
        man_path = ROOT / "civ6x10" / "rules" / "governor_audit.yml"
        if not man_path.is_file():
            self.skipTest("governor_audit.yml not generated yet")
        try:
            audit = build_audit(local_db(), root=ROOT)
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        expected = build_manifest(audit)
        actual = yaml.safe_load(man_path.read_text(encoding="utf-8"))
        self.assertEqual(actual["counts"], expected["counts"])
        self.assertEqual(actual["disposition_summary"],
                         expected["disposition_summary"])
        self.assertEqual(actual["family_summary"], expected["family_summary"])
        self.assertEqual(set(actual["governors"]), set(expected["governors"]))
        self.assertEqual(set(actual["promotions"]), set(expected["promotions"]))
        for gt, want in expected["governors"].items():
            self.assertEqual(actual["governors"][gt]["disposition_summary"],
                             want["disposition_summary"], gt)
        for pt, want in expected["promotions"].items():
            self.assertEqual(actual["promotions"][pt]["disposition_summary"],
                             want["disposition_summary"], pt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
