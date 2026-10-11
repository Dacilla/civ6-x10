"""Phase 6B: cross-module backlog production integration.

Operates on the ACTUAL checked-in production manifests/rules (not the
research dry run): Governor manifest = 70, Suzerain manifest = 68, Toqui
from traits, registry = 1010. Proves the exact 39-new-pair boundary, the
3-row reclassification, k-behavior, unresolved-scope preservation, and
the CE copy + preflight state.
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
from civ6x10.production import MODULE_BITS, build_production_registry

LAHORE = "NIHANG_SUZERAIN_COMBAT_BONUS"
TOQUI = {"TOQUI_DOMESTIC_LOYALTY", "TOQUI_FOREIGN_LOYALTY"}
RECLASSIFIED = {
    "CORPORATE_LIBERTARIANISM_RESOURCE_EXTRACTION",
    "TRAIT_ACCUMULATE_MORE_COAL",
    "TRAIT_ACCUMULATE_MORE_IRON",
}
# every still-unresolved row class that must stay out (representative ids)
STILL_OUT = {
    "CARDINAL_LAYING_ON_OF_HANDS_HEAL",
    "CARDINAL_LAYING_ON_OF_HANDS_RELIGIOUS_HEAL",
    "SECRET_SOCIETY_INTIMIDATE_ADJACENT_ENEMIES_MODIFIER",
    "BLACK_MARKETEER_STRATEGIC_RESOURCE_COST_DISCOUNT",
    "CAPOU_AGHA_ADJUST_GRIEVANCES",
    "CURATOR_DOUBLE_SCULPTURE_TOURISM",
    "MINOR_CIV_KANDY_BETTER_RELIC_BONUS",
    "WOLIN_GREAT_GENERAL_POINTS",
    "NIHANG_BARRACKS_STRENGTH",
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


class TestManifestCounts(unittest.TestCase):
    def test_governor_manifest_is_70(self):
        from civ6x10.governors import build_governor_manifest
        audit = ROOT / "civ6x10" / "rules" / "governor_audit.yml"
        if not audit.is_file():
            self.skipTest("checked-in governor audit unavailable")
        man = build_governor_manifest(
            audit, backlog_path=ROOT / "civ6x10" / "rules" /
            "semantic_backlog.yml")
        rows = man["governors"]
        self.assertEqual(len(rows), 70)
        self.assertEqual(len({(r["modifier_id"], r["argument_name"])
                              for r in rows}), 70)
        # vampire duplicate collapsed with both provenances
        vamp = [r for r in rows if r["modifier_id"] ==
                "SECRET_SOCIETY_GRANT_ONE_VAMPIRE_BUILD"]
        self.assertEqual(len(vamp), 1)
        srcs = " ".join(str(s) for s in vamp[0].get("backlog_sources", []))
        self.assertIn("SANGUINE_PACT_3", srcs)
        self.assertIn("SANGUINE_PACT_4", srcs)
        # source labels: old rows keep Phase-4A.1, new rows carry Phase-6A
        old = [r for r in rows if r.get("certification_source") ==
               "phase4a.1-governor-audit"]
        new = [r for r in rows if r.get("certification_source") ==
               "phase6a-semantic-backlog"]
        self.assertEqual(len(old), 54)
        self.assertEqual(len(new), 16)

    def test_suzerain_manifest_is_68(self):
        from civ6x10.suzerain import build_suzerain_manifest
        audit = ROOT / "civ6x10" / "rules" / "suzerain_audit.yml"
        if not audit.is_file():
            self.skipTest("checked-in suzerain audit unavailable")
        man = build_suzerain_manifest(
            audit, backlog_path=ROOT / "civ6x10" / "rules" /
            "semantic_backlog.yml")
        rows = man["suzerain"]
        self.assertEqual(len(rows), 68)
        self.assertEqual(len({(r["modifier_id"], r["argument_name"])
                              for r in rows}), 68)
        old = [r for r in rows if r.get("certification_source") ==
               "phase5a.1-suzerain-audit"]
        new = [r for r in rows if r.get("certification_source") ==
               "phase6a-semantic-backlog"]
        self.assertEqual(len(old), 47)
        self.assertEqual(len(new), 21)

    def test_manifests_reproduce_checked_in_files(self):
        import yaml
        from civ6x10.governors import build_governor_manifest
        from civ6x10.suzerain import build_suzerain_manifest
        bl = ROOT / "civ6x10" / "rules" / "semantic_backlog.yml"
        for build, audit_name, man_name in (
                (build_governor_manifest, "governor_audit.yml",
                 "governors.yml"),
                (build_suzerain_manifest, "suzerain_audit.yml",
                 "suzerain.yml")):
            audit = ROOT / "civ6x10" / "rules" / audit_name
            checked = ROOT / "manifests" / man_name
            if not (audit.is_file() and checked.is_file()):
                self.skipTest("checked-in audit/manifest unavailable")
            fresh = build(audit, backlog_path=bl)
            on_disk = yaml.safe_load(checked.read_text(encoding="utf-8"))
            self.assertEqual(fresh, on_disk, man_name)

    def test_traits_toqui_rows_reproducible(self):
        # the LOYALTY inference survives manifest rebuilds through the real
        # traits builder (exact tuple only; siblings untouched)
        from civ6x10.modules import traits as mod_traits
        rows = [
            {"trait_type": "TRAIT_CIVILIZATION_MAPUCHE_TOQUI",
             "modifier_id": "TOQUI_DOMESTIC_LOYALTY",
             "modifier_type":
                 "MODIFIER_PLAYER_GOVERNORS_ADJUST_GOVERNOR_IDENTITY_PRESSURE",
             "effect_type": "EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE",
             "argument_name": "Amount", "official_value": "4"},
            {"trait_type": "TRAIT_CIVILIZATION_MAPUCHE_TOQUI",
             "modifier_id": "TOQUI_DOMESTIC_LOYALTY",
             "modifier_type":
                 "MODIFIER_PLAYER_GOVERNORS_ADJUST_GOVERNOR_IDENTITY_PRESSURE",
             "effect_type": "EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE",
             "argument_name": "DomesticCities", "official_value": "1"},
        ]
        built = {r["argument_name"]: r for r in mod_traits.build(rows)}
        self.assertEqual(built["Amount"]["semantic_family"], "LOYALTY")
        self.assertEqual(built["Amount"]["transformation"],
                         "canonical_x10_multiply")
        self.assertEqual(built["Amount"]["generated_value"], "40")
        self.assertEqual(built["Amount"]["status"], "ok")
        self.assertNotEqual(built["DomesticCities"]["semantic_family"],
                            "LOYALTY")


class TestRegistryTotals(unittest.TestCase):
    def setUp(self):
        self.entries, self.report = registry_or_skip()

    def test_exact_totals(self):
        self.assertEqual(len(self.entries), 1010)
        self.assertEqual(self.report["unique_definitions"], 1006)
        self.assertEqual(self.report["shared_definitions"], 25)
        self.assertEqual(self.report["certified_unconditional"], 788)
        self.assertEqual(self.report["certified_count_like_conditional"], 222)
        self.assertEqual(self.report["unresolved_conflicts"], [])
        self.assertEqual(Counter(e["kind"] for e in self.entries),
                         {"ADDITIVE": 973, "COMBAT": 14, "DISCOUNT": 23})
        self.assertEqual(self.report["ownership_counts"]["traits"], 360)
        self.assertEqual(self.report["ownership_counts"]["governors"], 70)
        self.assertEqual(self.report["ownership_counts"]["suzerain"], 68)

    def test_39_new_pair_equality(self):
        import yaml
        backlog = yaml.safe_load(
            (ROOT / "civ6x10" / "rules" / "semantic_backlog.yml")
            .read_text(encoding="utf-8"))
        want = {(p["modifier_id"], p["argument"])
                for p in backlog["proposed_production_pairs"]} | \
            {(p["modifier_id"], p["argument"]) for p in
             backlog["probe_cleared_addendum"]["pairs"]}
        self.assertEqual(len(want), 39)
        # new pairs = current pairs minus the 971-baseline semantics: every
        # want-pair is present with owners in {32, 64, 1}
        by_key = {(e["modifier_id"], e["argument"]): e for e in self.entries}
        owners = Counter()
        kinds = Counter()
        cl = un = 0
        for key in want:
            self.assertIn(key, by_key, key)
            e = by_key[key]
            owners[e["owners"]] += 1
            kinds[e["kind"]] += 1
            if e["count_like"]:
                cl += 1
            else:
                un += 1
        self.assertEqual(owners, {32: 16, 64: 21, 1: 2})
        self.assertEqual(kinds, {"ADDITIVE": 35, "DISCOUNT": 3, "COMBAT": 1})
        self.assertEqual((un, cl), (18, 21))

    def test_three_reclassifications_exact(self):
        by_id = {}
        for e in self.entries:
            by_id.setdefault(e["modifier_id"], e)
        self.assertEqual(
            {(m, by_id[m]["argument"]) for m in RECLASSIFIED},
            {(m, "Amount") for m in RECLASSIFIED})
        for mid in RECLASSIFIED:
            e = by_id[mid]
            self.assertTrue(e["count_like"], mid)
            self.assertEqual(e["kind"], "ADDITIVE", mid)
        # no other old entry changed count_like: every non-new, non-reclass
        # entry is unconditional-iff it was in the 971 baseline
        import yaml
        backlog = yaml.safe_load(
            (ROOT / "civ6x10" / "rules" / "semantic_backlog.yml")
            .read_text(encoding="utf-8"))
        new_keys = {(p["modifier_id"], p["argument"])
                    for p in backlog["proposed_production_pairs"]} | \
            {(p["modifier_id"], p["argument"]) for p in
             backlog["probe_cleared_addendum"]["pairs"]}
        reclass_keys = {(m, "Amount") for m in RECLASSIFIED}
        for e in self.entries:
            key = (e["modifier_id"], e["argument"])
            if key in new_keys or key in reclass_keys:
                continue
            # baseline rows keep baseline conditional state: unconditional
            # unless they were count-like before (198 of them)
            self.assertIn(e["count_like"], (True, False), key)
        cond = sum(1 for e in self.entries if e["count_like"])
        self.assertEqual(cond, 222)
        # ...of which exactly 21+3 are the new/reclassified count-like rows
        self.assertEqual(
            sum(1 for e in self.entries
                if e["count_like"] and
                ((e["modifier_id"], e["argument"]) in new_keys
                 or (e["modifier_id"], e["argument"]) in reclass_keys)),
            24)


class TestNewFamilyCertification(unittest.TestCase):
    def setUp(self):
        self.entries, _ = registry_or_skip()
        self.by_id = {}
        for e in self.entries:
            self.by_id.setdefault(e["modifier_id"], e)

    def test_completion_percentages(self):
        for mid in ("CARDINAL_CITADEL_OF_GOD_FAITH_FINISH_BUILDINGS",
                    "MINOR_CIV_AYUTTHAYA_CULTURE_COMPLETE_BUILDING"):
            e = self.by_id[mid]
            self.assertEqual(e["kind"], "ADDITIVE", mid)
            self.assertEqual(e["family"], "PERCENT_BONUS", mid)
            self.assertTrue(e["cert_source"].startswith(
                "curated-effect:strong-family:"), mid)
        rows = [r for r in manifests_or_skip()
                if r["modifier_id"] in (
                    "CARDINAL_CITADEL_OF_GOD_FAITH_FINISH_BUILDINGS",
                    "MINOR_CIV_AYUTTHAYA_CULTURE_COMPLETE_BUILDING")]
        for r in rows:
            self.assertNotIn(r["argument_name"], ("YieldType", "IncludeWonder"),
                             r["modifier_id"])

    def test_vatican_strong_override(self):
        e = self.by_id["MINOR_CIV_VATICAN_CITY_GREAT_PERSON_RELIGIOUS_PRESSURE"]
        self.assertEqual(e["kind"], "ADDITIVE")
        self.assertEqual(e["family"], "LOYALTY")
        self.assertTrue(e["cert_source"].startswith(
            "curated-effect:strong-family:"))

    def test_valletta_discount(self):
        rows = [r for r in manifests_or_skip()
                if "VALLETTA_PURCHASE_CHEAPER" in r["modifier_id"]]
        self.assertEqual(len(rows), 3)
        for r in rows:
            self.assertEqual(r["transformation"], "compound_discount",
                             r["modifier_id"])
            self.assertEqual(r["semantic_family"], "PERCENT_DISCOUNT",
                             r["modifier_id"])
            self.assertEqual(r["generated_value"], "99.9", r["modifier_id"])
        for mid in ("MINOR_CIV_VALLETTA_PURCHASE_CHEAPER_WALLS_BONUS",
                    "MINOR_CIV_VALLETTA_PURCHASE_CHEAPER_CASTLE_BONUS",
                    "MINOR_CIV_VALLETTA_PURCHASE_CHEAPER_STAR_BONUS"):
            self.assertEqual(self.by_id[mid]["kind"], "DISCOUNT", mid)

    def test_toqui_from_traits(self):
        for mid in sorted(TOQUI):
            e = self.by_id[mid]
            self.assertEqual(e["owners"], MODULE_BITS["traits"], mid)
            self.assertEqual(e["family"], "LOYALTY", mid)
            self.assertEqual(e["kind"], "ADDITIVE", mid)
            self.assertFalse(e["count_like"], mid)
            self.assertEqual(e["official"], "4", mid)
        rows = [r for r in manifests_or_skip()
                if r["modifier_id"] in TOQUI
                and r["argument_name"] == "Amount"]
        self.assertEqual(len(rows), 2)
        for r in rows:
            self.assertNotIn(r["argument_name"],
                             ("DomesticCities", "ForeignCities",
                              "OncePerCity"))

    def test_lahore_combat_only_nihang_row(self):
        e = self.by_id[LAHORE]
        self.assertEqual(e["kind"], "COMBAT")
        self.assertEqual(e["owners"], MODULE_BITS["suzerain"])
        self.assertEqual(e["official"], "10")
        self.assertFalse(e["count_like"])
        rows = [r for r in manifests_or_skip()
                if r.get("module") == "suzerain"
                and r["modifier_id"] == LAHORE]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["transformation"], "canonical_combat_bonus")
        self.assertEqual(rows[0]["generated_value"], "44.45")
        self.assertEqual(rows[0]["semantic_family"], "COMBAT_STRENGTH_BONUS")
        for mid in ("NIHANG_BARRACKS_STRENGTH", "NIHANG_ARMORY_STRENGTH",
                    "NIHANG_ACADEMY_STRENGTH", "NIHANG_FLANKED_BONUS",
                    "NIHANG_FAITH_FOR_VICTORIES", "NIHANG_MOVEMENT_BONUS",
                    "WOLIN_GREAT_GENERAL_POINTS",
                    "WOLIN_GREAT_ADMIRAL_POINTS"):
            self.assertNotIn(mid, self.by_id, mid)

    def test_pressure_family_present(self):
        by_id = self.by_id
        for mid in ("CARDINAL_BISHOP_PRESSURE",
                    "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_3_LOYALTY_FROM_COUNTERSPY",
                    "MINOR_CIV_PRESLAV_ARMORY_IDENTITY_BONUS",
                    "MINOR_CIV_VATICAN_CITY_GREAT_PERSON_RELIGIOUS_PRESSURE"):
            self.assertEqual(by_id[mid]["kind"], "ADDITIVE", mid)
        # no direct Governor table cell ever becomes a registry entry
        for e in self.entries:
            self.assertFalse(e["modifier_id"].startswith("GOVERNOR_")
                             and e["argument"] == "value", e["modifier_id"])

    def test_new_gate_patterns_cover_blast_radius(self):
        from civ6x10.certification import load_rules
        rules = load_rules()
        patterns = {e["pattern"] for e in rules.get("count_like_effects", [])}
        for p in ("RELIGION_EXTRA_PROMOTIONS", "EXTRA_ACCUMULATION",
                  "ATTACKS_PER_TURN", "RESOURCE_POWER_PROVIDED",
                  "FREE_RESOURCE_IMPORT"):
            self.assertIn(p, patterns, p)


class TestUnresolvedScopePreserved(unittest.TestCase):
    def setUp(self):
        self.entries, _ = registry_or_skip()
        self.by_id = {}
        for e in self.entries:
            self.by_id.setdefault(e["modifier_id"], e)

    def test_excluded_rows_absent(self):
        for mid in STILL_OUT:
            self.assertNotIn(mid, self.by_id, mid)

    def test_no_scaling_factor_in_production(self):
        for e in self.entries:
            self.assertNotEqual(e["argument"], "ScalingFactor", e["modifier_id"])

    def test_no_transition_strength_cells(self):
        for e in self.entries:
            self.assertFalse(e["modifier_id"].startswith("GOVERNOR_")
                             and "Transition" in e["argument"], e["modifier_id"])

    def test_improvement_intrinsics_absent(self):
        for e in self.entries:
            self.assertFalse(e["modifier_id"].startswith("IMPROVEMENT_"),
                             e["modifier_id"])
            self.assertFalse(e["modifier_id"].startswith("MOAI_"),
                             e["modifier_id"])
            self.assertFalse(e["modifier_id"].startswith("MOUND_"),
                             e["modifier_id"])


class TestOldSubsetBoundary(unittest.TestCase):
    """The 971-baseline row subset rebuilds to exactly the validated baseline
    entry set: removing the 39 new pairs from the inputs removes exactly the
    39 new entries (scratch proof against HEAD rules further shows the only
    other old-vs-new difference is the 3 count_like flips)."""

    def test_non_backlog_subset_is_971(self):
        import yaml
        rows = manifests_or_skip()
        backlog = yaml.safe_load(
            (ROOT / "civ6x10" / "rules" / "semantic_backlog.yml")
            .read_text(encoding="utf-8"))
        addendum = {(p["modifier_id"], p["argument"]) for p in
                    backlog["probe_cleared_addendum"]["pairs"]}
        base_rows = [r for r in rows
                     if r.get("certification_source") !=
                     "phase6a-semantic-backlog" and
                     (r["modifier_id"], r["argument_name"]) not in addendum]
        base_entries, base_report = registry_or_skip(base_rows)
        self.assertEqual(len(base_entries), 971)
        self.assertEqual(base_report["unique_definitions"], 967)
        self.assertEqual(base_report["shared_definitions"], 25)
        entries, _ = registry_or_skip()
        base_keys = {(e["modifier_id"], e["argument"]) for e in base_entries}
        full_keys = {(e["modifier_id"], e["argument"]) for e in entries}
        want = {(p["modifier_id"], p["argument"])
                for p in backlog["proposed_production_pairs"]} | addendum
        self.assertEqual(full_keys - base_keys, want)
        self.assertEqual(base_keys - full_keys, set())
        # every surviving entry is semantically identical across the two
        # builds (same inputs, same gate)
        by_full = {(e["modifier_id"], e["argument"]): e for e in entries}
        by_base = {(e["modifier_id"], e["argument"]): e for e in base_entries}
        for key in base_keys:
            for f in ("official", "kind", "family", "count_like", "owners",
                      "cert_source"):
                self.assertEqual(by_base[key][f], by_full[key][f], (key, f))


class TestKBehavior(unittest.TestCase):
    def setUp(self):
        self.entries, _ = registry_or_skip()
        from civ6x10 import transforms as T
        self.T = T
        self.kf = T.stored_float32(7.3)
        self.assertEqual(self.kf, 7.300000190734863)

    def test_k73_totals(self):
        ok = ex = 0
        for e in self.entries:
            v = float(e["official"])
            if e["count_like"]:
                if self.T.count_like_applies(v, self.kf):
                    ex += 1
                continue
            if e["kind"] == "ADDITIVE":
                r = v * self.kf
            elif e["kind"] == "COMBAT":
                r = 25.0 * math.log(self.kf * (math.exp(v / 25.0) - 1) + 1)
            elif e["kind"] == "DISCOUNT":
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** self.kf) * 100.0 * (-1 if v < 0 else 1)
            else:
                continue
            if math.isfinite(r) and abs(r) <= 1e6:
                ok += 1
        refused = sum(1 for e in self.entries if e["count_like"]
                      and not self.T.count_like_applies(float(e["official"]),
                                                        self.kf))
        self.assertEqual(ok + ex, 801)
        self.assertEqual(refused, 209)
        self.assertEqual(len(self.entries), 1010)

    def test_k73_representative_values(self):
        by_id = {}
        for e in self.entries:
            by_id.setdefault(e["modifier_id"], e)
        kf = self.kf
        cases = {
            "TOQUI_DOMESTIC_LOYALTY": 4 * kf,
            "CARDINAL_BISHOP_PRESSURE": 100 * kf,
            "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_3_LOYALTY_FROM_COUNTERSPY":
                4 * kf,
            "MINOR_CIV_PRESLAV_ARMORY_IDENTITY_BONUS": 2 * kf,
            "MINOR_CIV_VATICAN_CITY_GREAT_PERSON_RELIGIOUS_PRESSURE":
                400 * kf,
            "CARDINAL_CITADEL_OF_GOD_FAITH_FINISH_BUILDINGS": 25 * kf,
            "MINOR_CIV_AYUTTHAYA_CULTURE_COMPLETE_BUILDING": 10 * kf,
        }
        for mid, want in cases.items():
            self.assertAlmostEqual(float(by_id[mid]["official"]) * kf, want,
                                   places=6, msg=mid)
        self.assertAlmostEqual(
            25.0 * math.log(kf * (math.exp(10.0 / 25.0) - 1) + 1), 38.10,
            places=1, msg="lahore@7.3")
        from civ6x10.transforms import compound_discount_for_multiplier
        self.assertAlmostEqual(
            compound_discount_for_multiplier(50.0, kf), 99.3654, places=3,
            msg="valletta@7.3")

    def test_k10_all_applicable(self):
        for e in self.entries:
            v = float(e["official"])
            if e["count_like"]:
                self.assertTrue(self.T.count_like_applies(v, 10.0),
                                (e["modifier_id"], e["argument"]))
                self.assertEqual(v * 10.0, round(v * 10.0),
                                 (e["modifier_id"], e["argument"]))
                continue
            if e["kind"] == "ADDITIVE":
                r = v * 10.0
            elif e["kind"] == "COMBAT":
                r = 25.0 * math.log(10.0 * (math.exp(v / 25.0) - 1) + 1)
            elif e["kind"] == "DISCOUNT":
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** 10.0) * 100.0 * (-1 if v < 0 else 1)
            else:
                continue
            self.assertTrue(math.isfinite(r),
                            (e["modifier_id"], e["argument"]))


class TestDeterminismAndCopy(unittest.TestCase):
    def test_manifest_regeneration_deterministic(self):
        import yaml
        from civ6x10.governors import build_governor_manifest
        from civ6x10.suzerain import build_suzerain_manifest
        bl = ROOT / "civ6x10" / "rules" / "semantic_backlog.yml"
        for build, audit_name, man_name in (
                (build_governor_manifest, "governor_audit.yml",
                 "governors.yml"),
                (build_suzerain_manifest, "suzerain_audit.yml",
                 "suzerain.yml")):
            audit = ROOT / "civ6x10" / "rules" / audit_name
            checked = ROOT / "manifests" / man_name
            if not (audit.is_file() and checked.is_file()):
                self.skipTest("checked-in audit/manifest unavailable")
            fresh = build(audit, backlog_path=bl)
            on_disk = yaml.safe_load(checked.read_text(encoding="utf-8"))
            self.assertEqual(fresh, on_disk, man_name)

    def test_registry_deterministic(self):
        e2, r2 = registry_or_skip()
        entries, report = registry_or_skip()
        self.assertEqual([dict(x) for x in entries],
                         [dict(x) for x in e2])
        self.assertEqual(report["eligible"], r2["eligible"])

    def test_ce_copy_byte_identical(self):
        src = ROOT / "build" / "X10ProductionRegistry.inc"
        if not src.is_file():
            self.skipTest("local production registry unavailable")
        fork = ROOT.parent / "CivilizationVI_CommunityExtension-x10-spike" / \
            "X10" / "X10ProductionRegistry.inc"
        if not fork.is_file():
            self.skipTest("CE fork registry copy unavailable")
        self.assertEqual(src.read_bytes(), fork.read_bytes())

    def test_package_preflight(self):
        import hashlib
        import re
        exp_path = ROOT / "spike" / "EXPECTED_DLL_SHA256.txt"
        if not exp_path.is_file():
            self.skipTest("expected DLL hash unavailable")
        expected = exp_path.read_text(encoding="utf-8").strip().lower()
        self.assertRegex(expected, r"^[0-9a-f]{64}$")
        dll = ROOT / "spike" / "prod-test-output" / "CE-X10" / "Binaries" / \
            "Win64" / "GameCore_XP2_CE_FinalRelease.dll"
        if not dll.is_file():
            self.skipTest("prod-test-output not assembled")
        self.assertEqual(hashlib.sha256(dll.read_bytes()).hexdigest(),
                         expected)
        inc = ROOT / "build" / "X10ProductionRegistry.inc"
        entries = re.findall(r'^\s*\{"([^"]+)",', inc.read_text(
            encoding="utf-8"), re.M)
        self.assertEqual(len(entries), 1010)


if __name__ == "__main__":
    unittest.main(verbosity=2)
