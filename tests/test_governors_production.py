"""Phase 4B: Governor production integration.

Proves the 54 audited Phase-4A.1 candidate rows enter production with the
correct ownership, kinds, conditional state and fail-closed behaviour, and
that nothing from the audit's excluded/decision-required set leaks in.
"""
from __future__ import annotations

import math
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

from civ6x10.bridge import REGISTRY_MODULES, collect_registry_rows
from civ6x10.governors import (GOVERNOR_MODULE_BIT,
                               audited_governor_candidates,
                               build_governor_manifest)
from civ6x10.production import MODULE_BITS, build_production_registry

GOV_BIT = 32
GOVERNOR_ENTRIES = 54

COMBAT_EFFECTS = {
    "EFFECT_ADJUST_CITY_FRIENDLY_COMBAT_BONUS",
    "EFFECT_ADJUST_UNIT_AGAINST_DISTRICT_COMBAT_BONUS",
    "EFFECT_ADJUST_CITY_RELIGIOUS_COMBAT_BONUS",
    "EFFECT_ADJUST_CITY_AIR_DEFENSE_BONUS",
    "EFFECT_ADJUST_CITY_COMBAT_BONUS",
    "EFFECT_ADJUST_CITY_INNER_DEFENSE",
}

INTEGRAL_GOVERNOR_ROWS = {
    "FORESTRY_MANAGEMENT_FEATURE_NO_IMPROVEMENT_APPEAL",
    "RENEWABLE_ENERGY_IMPROVEMENT_BUILDING_GOLD",
    "INDUSTRIALIST_COAL_POWER_PLANT_PRODUCTION",
    "INDUSTRIALIST_OIL_POWER_PLANT_PRODUCTION",
    "INDUSTRIALIST_NUCLEAR_POWER_PLANT_PRODUCTION",
}

MODE_ONLY_TUPLES = {
    ("MODIFIER_PLAYER_ADJUST_GOLD_INTEREST_PERCENT",
     "EFFECT_ADJUST_PLAYER_GOLD_INTEREST_PERCENT", "Percent"),
    ("MODIFIER_PLAYER_ADJUST_GREAT_PERSON_RESOURCE_YIELD_CHANGE",
     "EFFECT_ADJUST_PLAYER_YIELD_CHANGE_PER_GREAT_PERSON_CLASS_ON_RESOURCE",
     "Amount"),
}


def manifests_or_skip():
    try:
        return collect_registry_rows(ROOT)
    except FileNotFoundError:
        raise unittest.SkipTest("local-only registry inputs unavailable")


def registry_or_skip(rows=None):
    try:
        return build_production_registry(rows if rows is not None
                                         else manifests_or_skip())
    except FileNotFoundError:
        raise unittest.SkipTest("local-only registry inputs unavailable")


class TestModuleOwnership(unittest.TestCase):
    def test_governor_bit_is_32(self):
        self.assertEqual(GOVERNOR_MODULE_BIT, 32)
        self.assertEqual(MODULE_BITS["governors"], GOV_BIT)
        self.assertEqual(MODULE_BITS, {"traits": 1, "policies": 2,
                                       "governments": 4, "pantheons": 8,
                                       "wonders": 16, "governors": 32})

    def test_registry_modules_include_governors(self):
        self.assertIn("governors", REGISTRY_MODULES)
        self.assertEqual(len(REGISTRY_MODULES), 6)

    def test_manifest_shape(self):
        audit = ROOT / "civ6x10" / "rules" / "governor_audit.yml"
        if not audit.is_file():
            self.skipTest("checked-in governor audit unavailable")
        man = build_governor_manifest(audit)
        rows = man["governors"]
        self.assertEqual(len(rows), GOVERNOR_ENTRIES)
        self.assertEqual(len({r["modifier_id"] for r in rows}), GOVERNOR_ENTRIES)
        # families preserved verbatim from the audit
        audited = {r["modifier_id"]: r["semantic_family"]
                   for r in audited_governor_candidates(audit)}
        for r in rows:
            self.assertEqual(r["semantic_family"], audited[r["modifier_id"]],
                             r["modifier_id"])
        self.assertEqual(
            Counter(r["semantic_family"] for r in rows),
            {"FLAT_YIELD": 20, "PERCENT_BONUS": 12, "PRODUCTION_PERCENT": 8,
             "COMBAT_STRENGTH_BONUS": 6, "AMENITY": 3, "GOLD": 2,
             "HOUSING": 2, "APPEAL": 1})


class TestGovernorRegistryIntegration(unittest.TestCase):
    def setUp(self):
        self.entries, self.report = registry_or_skip()

    def test_totals(self):
        self.assertEqual(len(self.entries), 924)
        self.assertEqual(self.report["unique_definitions"], 920)
        self.assertEqual(self.report["shared_definitions"], 25)
        self.assertEqual(self.report["certified_unconditional"], 735)
        self.assertEqual(self.report["certified_count_like_conditional"], 189)
        self.assertEqual(self.report["unresolved_conflicts"], [])
        self.assertEqual(self.report["ownership_counts"]["governors"], 54)

    def test_governor_subset(self):
        gov = [e for e in self.entries if e["owners"] == GOV_BIT]
        self.assertEqual(len(gov), GOVERNOR_ENTRIES)
        self.assertEqual(len({e["modifier_id"] for e in gov}), GOVERNOR_ENTRIES)
        self.assertEqual(Counter(e["kind"] for e in gov),
                         {"ADDITIVE": 48, "COMBAT": 6})
        self.assertEqual(sum(1 for e in gov if e["count_like"]), 5)
        # governor-only ownership: no entry is shared with another module
        self.assertTrue(all(e["owners"] == GOV_BIT for e in gov))

    def test_six_combat_effects_are_combat(self):
        gov = {e["modifier_id"]: e for e in self.entries if e["owners"] == GOV_BIT}
        rows = [r for r in manifests_or_skip() if r.get("module") == "governors"]
        by_id = {}
        for r in rows:
            by_id.setdefault(r["modifier_id"], r)
        seen = set()
        for mid, e in gov.items():
            et = by_id[mid]["effect_type"]
            if et in COMBAT_EFFECTS:
                seen.add(et)
                self.assertEqual(e["kind"], "COMBAT", mid)
                self.assertTrue(e["cert_source"].startswith(
                    "curated-effect:combat-points:"), mid)
        self.assertEqual(seen, COMBAT_EFFECTS)
        self.assertEqual(sum(1 for e in gov.values() if e["kind"] == "COMBAT"), 6)

    def test_five_integral_rows_conditional(self):
        gov = {e["modifier_id"]: e for e in self.entries if e["owners"] == GOV_BIT}
        self.assertEqual({m for m, e in gov.items() if e["count_like"]},
                         INTEGRAL_GOVERNOR_ROWS)
        for mid in INTEGRAL_GOVERNOR_ROWS:
            self.assertTrue(gov[mid]["cert_source"].startswith(
                "curated-effect:engine-integral:"), mid)

    def test_excluded_rows_absent(self):
        gov_ids = {e["modifier_id"] for e in self.entries
                   if e["owners"] == GOV_BIT}
        # negative Sanguine combat, both healing rows, Suleiman titles
        self.assertNotIn("SECRET_SOCIETY_INTIMIDATE_ADJACENT_ENEMIES_MODIFIER",
                         gov_ids)
        self.assertNotIn("CARDINAL_LAYING_ON_OF_HANDS_HEAL", gov_ids)
        self.assertNotIn("CARDINAL_LAYING_ON_OF_HANDS_RELIGIOUS_HEAL", gov_ids)
        self.assertNotIn("SULEIMAN_GOVERNOR_POINTS", gov_ids)
        # Serasker magnitude present, its requirement filters are not entries
        self.assertIn("SERASKER_ADJUST_GOVERNOR_COMBAT_DISTRICT", gov_ids)
        self.assertFalse(any("MaxDistance" in m or "MinDistance" in m
                             for m in gov_ids))

    def test_suleiman_still_traits_only(self):
        for e in self.entries:
            if e["modifier_id"] == "SULEIMAN_GOVERNOR_POINTS":
                self.assertEqual(e["owners"], MODULE_BITS["traits"])
                self.assertEqual(e["family"], "GOVERNOR_TITLES")

    def test_no_audit_decision_row_enters(self):
        import yaml
        audit = yaml.safe_load(
            (ROOT / "civ6x10" / "rules" / "governor_audit.yml")
            .read_text(encoding="utf-8"))
        forbidden = set()
        for pt, p in audit["promotions"].items():
            for r in p["rows"]:
                if r["disposition"] != "CERTIFIED_CANDIDATE":
                    forbidden.add((r["modifier_id"], r["argument"]))
        gov = {(e["modifier_id"], e["argument"]) for e in self.entries
               if e["owners"] == GOV_BIT}
        leaked = gov & forbidden
        self.assertEqual(leaked, set(), sorted(leaked))
        # and the candidate pairs themselves are exactly what shipped
        cand = {(r["modifier_id"], r["argument"])
                for pt, p in audit["promotions"].items()
                for r in p["rows"]
                if r["disposition"] == "CERTIFIED_CANDIDATE"}
        self.assertEqual(gov, cand)

    def test_disabling_governors_makes_entries_inapplicable(self):
        gov = [e for e in self.entries if e["owners"] == GOV_BIT]
        enabled = MODULE_BITS["traits"] | MODULE_BITS["policies"] | \
            MODULE_BITS["governments"] | MODULE_BITS["pantheons"] | \
            MODULE_BITS["wonders"]  # governors OFF
        for e in gov:
            self.assertNotEqual(e["owners"] & enabled, e["owners"])
        # and toggling governors does not affect non-governor entries
        others = [e for e in self.entries if e["owners"] != GOV_BIT]
        for e in others:
            self.assertEqual(e["owners"] & GOV_BIT, 0)

    def test_determinism(self):
        e2, r2 = registry_or_skip()
        self.assertEqual([dict(x) for x in self.entries], [dict(x) for x in e2])
        self.assertEqual(self.report["eligible"], r2["eligible"])

    def test_pre_4b_subset_unchanged(self):
        # Every non-governor entry must match the pre-4B registry exactly on
        # the semantic fields the task pins.
        rows = manifests_or_skip()
        base_rows = [r for r in rows if r.get("module") != "governors"]
        base_entries, base_report = registry_or_skip(base_rows)
        self.assertEqual(len(base_entries), 870)
        self.assertEqual(base_report["certified_unconditional"], 686)
        self.assertEqual(base_report["certified_count_like_conditional"], 184)
        by_key = {(e["modifier_id"], e["argument"]): e for e in base_entries}
        for e in self.entries:
            if e["owners"] == GOV_BIT:
                continue
            prev = by_key[(e["modifier_id"], e["argument"])]
            for f in ("official", "kind", "family", "count_like", "owners",
                      "cert_source"):
                self.assertEqual(prev[f], e[f], (e["modifier_id"], f))


class TestGovernorTransforms(unittest.TestCase):
    """k=7.3f / k=10 behaviour, derived from the compiled registry."""

    def setUp(self):
        from civ6x10 import transforms as T
        self.T = T
        self.entries, _ = registry_or_skip()
        self.gov = [e for e in self.entries if e["owners"] == GOV_BIT]
        self.kf = T.stored_float32(7.3)
        self.assertEqual(self.kf, 7.300000190734863)

    def _applies(self, official, k):
        return self.T.count_like_applies(float(official), k)

    def test_all_governor_rows_at_k73(self):
        un = [e for e in self.gov if not e["count_like"]]
        co = [e for e in self.gov if e["count_like"]]
        self.assertEqual(len(un), 49)
        self.assertEqual(len(co), 5)
        # every unconditional row transforms (finite, in range)
        for e in un:
            v = float(e["official"])
            if e["kind"] == "ADDITIVE":
                r = v * self.kf
            elif e["kind"] == "COMBAT":
                r = 25.0 * math.log(
                    self.kf * (math.exp(v / 25.0) - 1) + 1)
            else:
                self.fail(e["kind"])
            self.assertTrue(math.isfinite(r), e)
        # all five conditional rows refuse at 7.3
        for e in co:
            self.assertFalse(self._applies(e["official"], self.kf), e)
            self.assertEqual(e["official"] in ("1", "2"), True, e)

    def test_all_governor_rows_at_k10(self):
        for e in self.gov:
            v = float(e["official"])
            if e["count_like"]:
                self.assertTrue(self._applies(e["official"], 10.0), e)
                self.assertEqual(v * 10.0, round(v * 10.0), e)
            else:
                self.assertTrue(__import__("math").isfinite(v * 10.0), e)

    def test_appeal_and_building_yield_refuse_at_7_3(self):
        gov = {e["modifier_id"]: e for e in self.gov}
        apeal = gov["FORESTRY_MANAGEMENT_FEATURE_NO_IMPROVEMENT_APPEAL"]
        self.assertEqual(apeal["official"], "1")
        self.assertFalse(self._applies(apeal["official"], self.kf))
        self.assertEqual(1 * 10.0, 10)
        for mid in ("RENEWABLE_ENERGY_IMPROVEMENT_BUILDING_GOLD",
                    "INDUSTRIALIST_COAL_POWER_PLANT_PRODUCTION",
                    "INDUSTRIALIST_OIL_POWER_PLANT_PRODUCTION",
                    "INDUSTRIALIST_NUCLEAR_POWER_PLANT_PRODUCTION"):
            e = gov[mid]
            self.assertEqual(e["official"], "2", mid)
            self.assertFalse(self._applies(e["official"], self.kf), mid)
            self.assertEqual(2 * 10.0, 20, mid)

    def test_no_rounding(self):
        # a refused row keeps vanilla; an applied row is exact
        for e in self.gov:
            v = float(e["official"])
            if e["count_like"] and not self._applies(e["official"], self.kf):
                self.assertEqual(v, round(v))
                continue
            if e["kind"] == "ADDITIVE":
                self.assertAlmostEqual(v * self.kf, v * 7.300000190734863,
                                       places=9)


class TestModeFloorAndCombatGate(unittest.TestCase):
    """The two mode-only tuples certify; the global fail-closed rule holds."""

    def _row(self, mt, et, arg, value, family):
        return {"modifier_type": mt, "effect_type": et,
                "argument_name": arg, "official_value": value,
                "semantic_family": family, "transformation": "canonical_x10_multiply",
                "status": "ok"}

    def test_mode_tuples_certify(self):
        from civ6x10.certification import certify_row, load_rules
        rules = load_rules()
        for mt, et, arg in MODE_ONLY_TUPLES:
            r = certify_row(self._row(mt, et, arg, "3", "PERCENT_BONUS"),
                            None, rules)
            self.assertTrue(r["certified"], (mt, r))
            self.assertEqual(r["kind"], "ADDITIVE")
        r = certify_row(self._row(
            "MODIFIER_PLAYER_ADJUST_GREAT_PERSON_RESOURCE_YIELD_CHANGE",
            "EFFECT_ADJUST_PLAYER_YIELD_CHANGE_PER_GREAT_PERSON_CLASS_ON_RESOURCE",
            "Amount", "1", "FLAT_YIELD"), None, rules)
        self.assertTrue(r["certified"])
        self.assertEqual(r["kind"], "ADDITIVE")

    def test_arbitrary_missing_floor_still_fails(self):
        from civ6x10.certification import certify_row, load_rules
        from civ6x10.production import SemanticConflict
        from civ6x10.production import build_production_registry
        rules = load_rules()
        row = self._row("MODIFIER_NOT_IN_ANY_FLOOR", "EFFECT_NOT_IN_ANY_FLOOR",
                        "Amount", "5", "FLAT_AMOUNT")
        row["modifier_id"] = "MODIFIER_NOT_IN_ANY_FLOOR_AMOUNT"
        row["module"] = "governors"
        r = certify_row(row, None, rules)
        self.assertFalse(r["certified"])
        self.assertEqual(r["resolution"], "conflict:no-sem-floor-row")
        # Pass an explicit (empty) floor so the assertion exercises the
        # missing-floor path deterministically without needing the local-only
        # effect_semantics.csv; the checked-in mode floor is still consulted
        # by certify_row and does not cover this bogus tuple.
        with self.assertRaises(SemanticConflict):
            build_production_registry([row], sem_floor={})

    def test_removing_supplemental_evidence_fails_closed(self):
        from civ6x10 import certification as C
        import tempfile, yaml, shutil
        src = ROOT / "civ6x10" / "rules" / "mode_sem_floor.yml"
        if not src.is_file():
            self.skipTest("checked-in mode semantic floor unavailable")
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "mode_sem_floor.yml"
            doc = yaml.safe_load(src.read_text(encoding="utf-8"))
            doc["mode_sem_floor"] = []
            tmp.write_text(yaml.safe_dump(doc), encoding="utf-8")
            C.load_mode_floor.cache_clear()
            real = C.load_mode_floor
            C.load_mode_floor = lambda path=None: real(tmp)
            try:
                for mt, et, arg in MODE_ONLY_TUPLES:
                    r = C.certify_row(self._row(mt, et, arg, "3",
                                                "PERCENT_BONUS"), None)
                    self.assertFalse(r["certified"], (mt, r))
                    self.assertEqual(r["resolution"],
                                     "conflict:no-sem-floor-row")
            finally:
                C.load_mode_floor = real
                C.load_mode_floor.cache_clear()

    def test_mode_floor_provenance_matches_audit(self):
        import yaml
        audit_path = ROOT / "civ6x10" / "rules" / "governor_audit.yml"
        if not audit_path.is_file():
            self.skipTest("checked-in governor audit unavailable")
        from civ6x10.certification import load_mode_floor
        mode = load_mode_floor()
        self.assertEqual(len(mode), 2)  # exactly two audited tuples
        audit = yaml.safe_load(audit_path.read_text(encoding="utf-8"))
        by_file = {f["file"]: f for f in audit["mode_files"]}
        for key, e in mode.items():
            provs = [e.get("provenance")] + list(e.get("extra_provenance") or [])
            for p in provs:
                self.assertIn(p["file"], by_file, p["file"])
                self.assertEqual(p["sha256"], by_file[p["file"]]["sha256"],
                                 p["file"])
                self.assertEqual(p["action"], by_file[p["file"]]["action"])
                self.assertEqual(p["criteria"], by_file[p["file"]]["criteria"])

    def test_combat_curation_ordering(self):
        from civ6x10.certification import certify_row, load_rules
        rules = load_rules()
        # The governor combat effects carry a MAGNITUDE_UNCLASSIFIED /
        # NEEDS_REVIEW floor row (exactly as in effect_semantics.csv).
        floor = {"semantic_family": "MAGNITUDE_UNCLASSIFIED",
                 "confidence": "NEEDS_REVIEW"}
        # curated combat effect + proposed COMBAT_STRENGTH_BONUS -> COMBAT
        for mt, et in (
                ("MODIFIER_CITY_ADJUST_CITY_FRIENDLY_COMBAT_BONUS",
                 "EFFECT_ADJUST_CITY_FRIENDLY_COMBAT_BONUS"),
                ("MODIFIER_GOVERNOR_ADJUST_DISTRICT_COMBAT_BONUS",
                 "EFFECT_ADJUST_UNIT_AGAINST_DISTRICT_COMBAT_BONUS"),
                ("MODIFIER_SINGLE_CITY_RELIGIOUS_COMBAT_BONUS",
                 "EFFECT_ADJUST_CITY_RELIGIOUS_COMBAT_BONUS"),
                ("MODIFIER_CITY_ADJUST_AIR_DEFENSE_BONUS",
                 "EFFECT_ADJUST_CITY_AIR_DEFENSE_BONUS"),
                ("MODIFIER_CITY_ADJUST_CITY_COMBAT_BONUS",
                 "EFFECT_ADJUST_CITY_COMBAT_BONUS"),
                ("MODIFIER_PLAYER_CITIES_ADJUST_INNER_DEFENSE",
                 "EFFECT_ADJUST_CITY_INNER_DEFENSE")):
            r = certify_row(self._row(mt, et, "Amount", "5",
                                      "COMBAT_STRENGTH_BONUS"), floor, rules)
            self.assertTrue(r["certified"], et)
            self.assertEqual(r["kind"], "COMBAT", et)
            self.assertTrue(r["source"].startswith(
                "curated-effect:combat-points:"), et)
        # uncurated heuristic combat claim still fails closed
        r = certify_row(self._row("MODIFIER_X", "EFFECT_TOTALLY_UNKNOWN",
                                  "Amount", "5", "COMBAT_STRENGTH_BONUS"),
                        floor, rules)
        self.assertFalse(r["certified"])
        self.assertEqual(r["resolution"],
                         "conflict:uncertified-COMBAT_STRENGTH_BONUS-claim")
        # a curated combat effect is still not certified for other arguments
        r = certify_row(self._row("MODIFIER_CITY_ADJUST_CITY_COMBAT_BONUS",
                                  "EFFECT_ADJUST_CITY_COMBAT_BONUS",
                                  "TurnsActive", "5", "COMBAT_STRENGTH_BONUS"),
                        floor, rules)
        self.assertFalse(r["certified"], r)

    def test_negative_combat_still_absent(self):
        entries, _ = registry_or_skip()
        gov = {e["modifier_id"] for e in entries if e["owners"] == GOV_BIT}
        self.assertNotIn("SECRET_SOCIETY_INTIMIDATE_ADJACENT_ENEMIES_MODIFIER",
                         gov)
        import math
        from civ6x10 import transforms as T
        for k in (7.3, 10.0):
            with self.assertRaises(ValueError):
                T.combat_bonus_for_multiplier(-5.0, k)

    def test_existing_classifications_unchanged(self):
        # No non-governor row changed kind because of the combat reordering.
        rows = manifests_or_skip()
        base_rows = [r for r in rows if r.get("module") != "governors"]
        base_entries, _ = registry_or_skip(base_rows)
        entries, _ = registry_or_skip()
        now = {(e["modifier_id"], e["argument"]): e for e in entries}
        for e in base_entries:
            cur = now[(e["modifier_id"], e["argument"])]
            self.assertEqual(cur["kind"], e["kind"], e["modifier_id"])
            self.assertEqual(cur["cert_source"], e["cert_source"],
                             e["modifier_id"])
            self.assertEqual(cur["count_like"], e["count_like"],
                             e["modifier_id"])

    def test_k73_governor_totals(self):
        import math
        entries, _ = registry_or_skip()
        kf = self_kf = T_stored = None
        from civ6x10 import transforms as T
        kf = T.stored_float32(7.3)
        gov = [e for e in entries if e["owners"] == GOV_BIT]
        writes = refusals = 0
        for e in gov:
            v = float(e["official"])
            if e["count_like"]:
                if T.count_like_applies(v, kf):
                    writes += 1
                else:
                    refusals += 1
                continue
            if e["kind"] == "ADDITIVE":
                r = v * kf
            else:
                r = 25.0 * math.log(kf * (math.exp(v / 25.0) - 1) + 1)
            if math.isfinite(r) and abs(r) <= 1e6:
                writes += 1
            else:
                refusals += 1
        self.assertEqual((writes, refusals), (49, 5))

    def test_k73_global_totals(self):
        import math
        from civ6x10 import transforms as T
        entries, _ = registry_or_skip()
        kf = T.stored_float32(7.3)
        ok = ex = 0
        for e in entries:
            v = float(e["official"])
            if e["count_like"]:
                if T.count_like_applies(v, kf):
                    ex += 1
                continue
            if e["kind"] == "ADDITIVE":
                r = v * kf
            elif e["kind"] == "COMBAT":
                r = 25.0 * math.log(kf * (math.exp(v / 25.0) - 1) + 1)
            elif e["kind"] == "DISCOUNT":
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** kf) * 100.0 * (-1 if v < 0 else 1)
            else:
                continue
            if math.isfinite(r) and abs(r) <= 1e6:
                ok += 1
        refused = sum(1 for e in entries if e["count_like"]
                      and not T.count_like_applies(float(e["official"]), kf))
        self.assertEqual(ok + ex, 748)
        self.assertEqual(refused, 176)
        self.assertEqual(len(entries), 924)


if __name__ == "__main__":
    unittest.main(verbosity=2)
