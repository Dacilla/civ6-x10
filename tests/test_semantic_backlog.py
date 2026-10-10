"""Phase 6A: unified semantic-backlog research tests.

CI-safe by construction: the backlog builder reads only the checked-in
audit YAMLs (synthetic fixtures for rule tests); no private Firaxis data.
Production-unchanged guards skip cleanly when local build artifacts are
absent.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

from civ6x10.backlog import (
    NEEDS_LIVE_PROBE,
    NEEDS_PRODUCT_DECISION,
    RESOLVED_CANDIDATE,
    RESOLVED_CANDIDATE_COUNT_LIKE,
    RESOLVED_EXCLUDED,
    STILL_SEMANTICALLY_UNRESOLVED,
    build_backlog,
)

GOV_AUDIT = ROOT / "civ6x10" / "rules" / "governor_audit.yml"
SUZ_AUDIT = ROOT / "civ6x10" / "rules" / "suzerain_audit.yml"
BACKLOG = ROOT / "civ6x10" / "rules" / "semantic_backlog.yml"


def backlog_or_skip():
    if not (GOV_AUDIT.is_file() and SUZ_AUDIT.is_file()):
        raise unittest.SkipTest("checked-in audits unavailable")
    return build_backlog(GOV_AUDIT, SUZ_AUDIT)


class TestBacklogImport(unittest.TestCase):
    def test_exact_imported_counts(self):
        b = backlog_or_skip()
        self.assertEqual(b["counts"]["imported_governor_reachable"], 29)
        self.assertEqual(b["counts"]["imported_governor_direct"], 24)
        self.assertEqual(b["counts"]["imported_suzerain_main"], 21)
        self.assertEqual(b["counts"]["imported_suzerain_side"], 68)
        self.assertEqual(b["counts"]["imported_total"], 142)

    def test_no_row_disappears(self):
        b = backlog_or_skip()
        self.assertEqual(len(b["rows"]), 142)
        total = sum(b["by_resolution"].values())
        self.assertEqual(total, 142)
        for r in b["rows"]:
            self.assertTrue(r["resolution"])
            self.assertTrue(r["group"])
            self.assertTrue(r["resolution_rationale"])

    def test_resolution_totals(self):
        b = backlog_or_skip()
        d = b["by_resolution"]
        self.assertEqual(d[RESOLVED_CANDIDATE], 10)
        self.assertEqual(d[RESOLVED_CANDIDATE_COUNT_LIKE], 22)
        self.assertEqual(d[RESOLVED_EXCLUDED], 25)
        self.assertEqual(d[NEEDS_LIVE_PROBE], 6)
        self.assertEqual(d[NEEDS_PRODUCT_DECISION], 58)
        self.assertEqual(d[STILL_SEMANTICALLY_UNRESOLVED], 21)

    def test_checked_in_backlog_reproduces(self):
        import yaml
        if not BACKLOG.is_file():
            self.skipTest("checked-in backlog unavailable")
        on_disk = yaml.safe_load(BACKLOG.read_text(encoding="utf-8"))
        fresh = backlog_or_skip()
        self.assertEqual(fresh["counts"], on_disk["counts"])
        self.assertEqual(fresh["by_resolution"], on_disk["by_resolution"])
        self.assertEqual(fresh["proposed_candidates"],
                         on_disk["proposed_candidates"])


class TestCrossModuleCountLike(unittest.TestCase):
    """Whole-unit quantities share one rule across modules."""

    def _row(self, mid, fam, cl):
        b = backlog_or_skip()
        matches = [c for c in b["proposed_candidates"]
                   if c["modifier_id"] == mid]
        self.assertEqual(len(matches), 1, mid)
        self.assertEqual(matches[0]["family"], fam, mid)
        self.assertEqual(matches[0]["count_like"], cl, mid)
        self.assertEqual(matches[0]["kind"], "ADDITIVE", mid)
        self.assertEqual(matches[0]["transform"], "canonical_x10_multiply",
                         mid)
        return matches[0]

    def test_governor_and_suzerain_quantities_share_family(self):
        for mid in ("GUILDMASTER_ADDITIONAL_BUILDER_CHARGES_UNIT_MODIFIER",
                    "CARDINAL_PATRON_SAINT_PROMOTION",
                    "MINOR_CIV_CARDIFF_POWER_LIGHTHOUSE",
                    "MINOR_CIV_HATTUSA_COAL_RESOURCE_XP2",
                    "MINOR_CIV_ZANZIBAR_CINNAMON_RESOURCE_BONUS"):
            self._row(mid, "FLAT_AMOUNT", True)

    def test_all_22_count_like(self):
        b = backlog_or_skip()
        cl = [c for c in b["proposed_candidates"] if c["count_like"]]
        self.assertEqual(len(cl), 22)
        self.assertTrue(all(c["kind"] == "ADDITIVE" for c in cl))
        # every official is 1/2/3: all refuse at stored FLOAT32 k=7.3
        from civ6x10 import transforms as T
        kf = T.stored_float32(7.3)
        for c in cl:
            self.assertFalse(
                T.count_like_applies(float(c["value"]), kf), c["modifier_id"])
            self.assertTrue(
                T.count_like_applies(float(c["value"]), 10.0),
                c["modifier_id"])


class TestVallettaDiscount(unittest.TestCase):
    def test_valletta_resolved_discount(self):
        b = backlog_or_skip()
        rows = [c for c in b["proposed_candidates"]
                if "VALLETTA" in (c["modifier_id"] or "")]
        self.assertEqual(len(rows), 3)
        for c in rows:
            self.assertEqual(c["family"], "PERCENT_DISCOUNT")
            self.assertEqual(c["kind"], "DISCOUNT")
            self.assertEqual(c["transform"], "compound_discount")
            self.assertEqual(c["value"], "50")
            self.assertFalse(c["count_like"])
        # never linear: 50 x 10 is not a discount
        from civ6x10.transforms import compound_discount_for_multiplier as d
        self.assertAlmostEqual(d(50.0, 10.0), 99.9023, places=3)
        self.assertAlmostEqual(d(50.0, 7.3), 99.3654, places=3)


class TestCompletionPercent(unittest.TestCase):
    def test_citadel_and_ayutthaya_share_rule(self):
        b = backlog_or_skip()
        rows = {c["modifier_id"]: c for c in b["proposed_candidates"]
                if c["modifier_id"] in (
                    "CARDINAL_CITADEL_OF_GOD_FAITH_FINISH_BUILDINGS",
                    "MINOR_CIV_AYUTTHAYA_CULTURE_COMPLETE_BUILDING")}
        self.assertEqual(len(rows), 2)
        for mid, c in rows.items():
            self.assertEqual(c["family"], "PERCENT_BONUS", mid)
            self.assertEqual(c["kind"], "ADDITIVE", mid)
            self.assertEqual(c["argument"], "BuildingProductionPercent", mid)
        self.assertEqual(rows[
            "CARDINAL_CITADEL_OF_GOD_FAITH_FINISH_BUILDINGS"]["owner"],
            "governors")
        self.assertEqual(rows[
            "MINOR_CIV_AYUTTHAYA_CULTURE_COMPLETE_BUILDING"]["owner"],
            "suzerain")
        # IncludeWonder never rides along
        for r in b["rows"]:
            if r["modifier_id"] in rows and r["argument"] == "IncludeWonder":
                self.fail("IncludeWonder must not be a candidate")


class TestNegativeCombatUnshippable(unittest.TestCase):
    def test_negative_has_no_valid_transform(self):
        import math
        for k in (7.3, 10.0):
            inner = k * (math.exp(-5.0 / 25.0) - 1) + 1
            self.assertLessEqual(inner, 0.0)
            with self.assertRaises(ValueError):
                from civ6x10.transforms import combat_bonus_for_multiplier
                combat_bonus_for_multiplier(-5.0, k)

    def test_negative_resolved_excluded_permanently(self):
        b = backlog_or_skip()
        rows = [r for r in b["rows"]
                if r["modifier_id"] ==
                "SECRET_SOCIETY_INTIMIDATE_ADJACENT_ENEMIES_MODIFIER"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["resolution"], RESOLVED_EXCLUDED)
        self.assertIn("UNSUPPORTED_TRANSFORM",
                      rows[0]["resolution_rationale"])


class TestLahoreOwnership(unittest.TestCase):
    def test_suzerain_gated_plus10_is_candidate(self):
        b = backlog_or_skip()
        rows = [c for c in b["proposed_candidates"]
                if c["modifier_id"] == "NIHANG_SUZERAIN_COMBAT_BONUS"]
        self.assertEqual(len(rows), 1)
        c = rows[0]
        self.assertEqual(c["family"], "COMBAT_STRENGTH_BONUS")
        self.assertEqual(c["kind"], "COMBAT")
        self.assertEqual(c["owner"], "suzerain")

    def test_intrinsic_progression_stays_out(self):
        b = backlog_or_skip()
        by_id = {}
        for r in b["rows"]:
            by_id.setdefault(r["modifier_id"], r)
        for mid in ("NIHANG_BARRACKS_STRENGTH", "NIHANG_ARMORY_STRENGTH",
                    "NIHANG_ACADEMY_STRENGTH", "NIHANG_FLANKED_BONUS",
                    "NIHANG_FAITH_FOR_VICTORIES", "NIHANG_MOVEMENT_BONUS"):
            self.assertEqual(by_id[mid]["resolution"], RESOLVED_EXCLUDED,
                             mid)


class TestTransitionStrength(unittest.TestCase):
    def test_all_twelve_excluded_structural(self):
        b = backlog_or_skip()
        rows = [r for r in b["rows"]
                if r["source_kind"] == "direct"
                and r["argument"] == "value"
                and r["root_detail"] == "TransitionStrength"]
        self.assertEqual(len(rows), 12)
        for r in rows:
            self.assertEqual(r["resolution"], RESOLVED_EXCLUDED)


class TestProductionUnchanged(unittest.TestCase):
    def test_registry_digest_unchanged(self):
        import hashlib
        p = ROOT / "build" / "X10ProductionRegistry.inc"
        if not p.is_file():
            self.skipTest("local production registry unavailable")
        self.assertEqual(
            hashlib.sha256(p.read_bytes()).hexdigest(),
            "6468bcbc6760e8753d8bca3086e9dfe6b267e39be9004b31312d1d9c50556c55")

    def test_manifests_unchanged(self):
        import hashlib
        for name, want in (
                ("governors.yml",
                 "c864361c744ee459aa2e13acb279dc2ff44597acc67d9608bcd1f7ef7428b467"),
                ("suzerain.yml",
                 "d4d2e007d8a97793b50b8e4228c8b639bd41b385039de8f6e5bb065ad6234957")):
            p = ROOT / "manifests" / name
            if not p.is_file():
                self.skipTest(f"local manifest {name} unavailable")
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),
                             want, name)

    def test_bits_modules_and_dll_untouched(self):
        from civ6x10.production import MODULE_BITS
        self.assertEqual(MODULE_BITS, {"traits": 1, "policies": 2,
                                       "governments": 4, "pantheons": 8,
                                       "wonders": 16, "governors": 32,
                                       "suzerain": 64})
        from civ6x10.bridge import REGISTRY_MODULES
        self.assertEqual(tuple(REGISTRY_MODULES),
                         ("traits", "policies", "governments", "pantheons",
                          "wonders", "governors", "suzerain"))
        import hashlib
        p = ROOT / "spike" / "EXPECTED_DLL_SHA256.txt"
        if p.is_file():
            self.assertEqual(p.read_text(encoding="utf-8").strip(),
                             "b6862b28d86aa67d20cd6ffecd1588cfc2e528dbb75d484cb8c4e52a387fb20d")


if __name__ == "__main__":
    unittest.main(verbosity=2)
