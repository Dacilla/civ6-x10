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
        # text-mode read normalizes CRLF/LF: the digest is platform
        # independent (raw bytes differ between Windows and CI checkouts)
        for name, want in (
                ("governors.yml",
                 "95587a42c7ba849a8ddff79428f32e001a036aaf6c4380fe2cfa59384a74d847"),
                ("suzerain.yml",
                 "5f72f4fcdc739cdcfb9b1cb49e2d3df87d487db4aaabbd2ed7a1ceffc84e8182")):
            p = ROOT / "manifests" / name
            if not p.is_file():
                self.skipTest(f"local manifest {name} unavailable")
            self.assertEqual(hashlib.sha256(
                p.read_text(encoding="utf-8").encode("utf-8")).hexdigest(),
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




def _production_pairs(backlog):
    return backlog["proposed_production_pairs"]


class TestProductionProjection(unittest.TestCase):
    """6A.2 normalization: occurrences vs unique production pairs."""

    def test_no_duplicate_production_pair(self):
        b = backlog_or_skip()
        pairs = _production_pairs(b)
        keys = [(p["modifier_id"], p["argument"]) for p in pairs]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(keys), 31)

    def test_projection_counts(self):
        b = backlog_or_skip()
        c = b["production_pair_counts"]
        self.assertEqual(c["unique_production_pairs"], 31)
        self.assertEqual(c["unique_governor_pairs"], 14)
        self.assertEqual(c["unique_suzerain_pairs"], 17)
        self.assertEqual(c["unique_non_count_like"], 10)
        self.assertEqual(c["unique_count_like"], 21)
        self.assertEqual(c["kinds"], {"ADDITIVE": 27, "COMBAT": 1,
                                      "DISCOUNT": 3})

    def test_vampire_duplicate_provenance_retained(self):
        b = backlog_or_skip()
        pairs = {(p["modifier_id"], p["argument"]): p
                 for p in _production_pairs(b)}
        key = ("SECRET_SOCIETY_GRANT_ONE_VAMPIRE_BUILD", "Amount")
        self.assertIn(key, pairs)
        p = pairs[key]
        # one production pair, both promotion provenances aggregated
        self.assertEqual(p["occurrences"], 2)
        promos = {s[2] for s in p["sources"]}
        self.assertIn("GOVERNOR_PROMOTION_SANGUINE_PACT_3", promos)
        self.assertIn("GOVERNOR_PROMOTION_SANGUINE_PACT_4", promos)
        self.assertEqual(p["count_like"], True)
        # source occurrences are NOT collapsed: the audit trail keeps both
        occ = [r for r in b["rows"]
               if (r["modifier_id"], r["argument"]) == key]
        self.assertEqual(len(occ), 2)
        self.assertEqual(
            {r["resolution"] for r in occ},
            {RESOLVED_CANDIDATE_COUNT_LIKE})

    def test_count_like_occurrences_stay_22(self):
        # the imported-resolution count is not edited to match the unique
        # production count; the distinction is documented, not erased
        b = backlog_or_skip()
        self.assertEqual(b["by_resolution"][RESOLVED_CANDIDATE_COUNT_LIKE],
                         22)


def _registry_entries_or_skip():
    import re
    p = ROOT / "build" / "X10ProductionRegistry.inc"
    if not p.is_file():
        raise unittest.SkipTest("local production registry unavailable")
    out = []
    for m in re.finditer(
            r'\{"([^"]+)", "([^"]+)", "([^"]+)", (\d), (\d), (\d+)\},',
            p.read_text(encoding="utf-8")):
        out.append({"modifier_id": m.group(1), "argument": m.group(2),
                    "official": m.group(3), "kind": int(m.group(4)),
                    "count_like": bool(int(m.group(5))),
                    "owners": int(m.group(6))})
    return out


def _manifest_effect_types():
    from civ6x10.bridge import collect_registry_rows
    try:
        rows = collect_registry_rows(ROOT)
    except FileNotFoundError:
        raise unittest.SkipTest("local-only registry inputs unavailable")
    return {(r["modifier_id"], r["argument_name"]): r.get("effect_type")
            for r in rows}


class TestBlastRadius(unittest.TestCase):
    """EXTRA_ACCUMULATION pattern applied to the CURRENT registry."""

    def test_complete_blast_radius(self):
        entries = _registry_entries_or_skip()
        effects = _manifest_effect_types()
        patterns = ["RELIGION_EXTRA_PROMOTIONS", "EXTRA_ACCUMULATION",
                    "ATTACKS_PER_TURN", "RESOURCE_POWER_PROVIDED",
                    "FREE_RESOURCE_IMPORT"]
        changed = []
        for e in entries:
            et = effects.get((e["modifier_id"], e["argument"]), "")
            if any(p in (et or "") for p in patterns) and not e["count_like"]:
                changed.append((e["modifier_id"], e["argument"], et))
        # mechanically derived complete set: exactly the three recorded rows
        self.assertEqual(
            sorted(m for m, _, _ in changed),
            ["CORPORATE_LIBERTARIANISM_RESOURCE_EXTRACTION",
             "TRAIT_ACCUMULATE_MORE_COAL",
             "TRAIT_ACCUMULATE_MORE_IRON"])
        b = backlog_or_skip()
        recorded = {(r["modifier_id"], r["argument"]) for r in
                    b["proposed_existing_reclassifications"]["rows"]}
        self.assertEqual(recorded,
                         {(m, a) for m, a, _ in changed})


class TestNoPressureBaseline(unittest.TestCase):
    """Hypothetical 6B baseline derived mechanically, not pinned."""

    def test_hypothetical_totals(self):
        import math
        from civ6x10 import transforms as T
        entries = _registry_entries_or_skip()
        self.assertEqual(len(entries), 971)
        b = backlog_or_skip()
        pairs = _production_pairs(b)
        self.assertEqual(len(pairs), 31)
        # no collision: every pair is a new definition (shared stays 25)
        reg_keys = {(e["modifier_id"], e["argument"]) for e in entries}
        new_keys = {(p["modifier_id"], p["argument"]) for p in pairs}
        self.assertEqual(reg_keys & new_keys, set())
        self.assertEqual(967 + 31, 998)
        self.assertEqual(971 + 31, 1002)
        # split the new pairs by conditional state
        kf = T.stored_float32(7.3)
        self.assertEqual(kf, 7.300000190734863)
        new_writes = new_refusals = 0
        for p in pairs:
            v = float(p["value"])
            if p["count_like"]:
                if T.count_like_applies(v, kf):
                    new_writes += 1
                else:
                    new_refusals += 1
                self.assertTrue(T.count_like_applies(v, 10.0),
                                p["modifier_id"])
                continue
            if p["kind"] == "ADDITIVE":
                r = v * kf
            elif p["kind"] == "DISCOUNT":
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** kf) * 100.0
            elif p["kind"] == "COMBAT":
                r = 25.0 * math.log(kf * (math.exp(v / 25.0) - 1) + 1)
            else:
                self.fail(p)
            self.assertTrue(math.isfinite(r), p["modifier_id"])
            new_writes += 1
        self.assertEqual((new_writes, new_refusals), (10, 21))
        # the three reclassifications move writes -> refusals
        reclass = b["proposed_existing_reclassifications"]["rows"]
        self.assertEqual(len(reclass), 3)
        moved = 0
        for r in reclass:
            v = float(r["official"])
            self.assertFalse(T.count_like_applies(v, kf), r["modifier_id"])
            moved += 1
        self.assertEqual(moved, 3)
        # full hypothetical simulation over 971 + 31 with 3 flipped
        flipped = {(r["modifier_id"], r["argument"]) for r in reclass}
        hypo = [dict(e, count_like=True)
                if (e["modifier_id"], e["argument"]) in flipped else e
                for e in entries]
        for p in pairs:
            hypo.append({"modifier_id": p["modifier_id"],
                         "argument": p["argument"],
                         "official": p["value"],
                         "kind": {"ADDITIVE": 0, "COMBAT": 1,
                                  "PROBABILITY": 2,
                                  "DISCOUNT": 3}[p["kind"]],
                         "count_like": p["count_like"], "owners": 64})
        self.assertEqual(len(hypo), 1002)
        writes = refusals = 0
        for e in hypo:
            v = float(e["official"])
            if e["count_like"]:
                if T.count_like_applies(v, kf):
                    writes += 1
                else:
                    refusals += 1
                continue
            if e["kind"] == 0:
                r = v * kf
            elif e["kind"] == 1:
                r = 25.0 * math.log(kf * (math.exp(v / 25.0) - 1) + 1)
            elif e["kind"] == 3:
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** kf) * 100.0
            else:
                continue
            if math.isfinite(r) and abs(r) <= 1e6:
                writes += 1
            else:
                refusals += 1
        self.assertEqual((writes, refusals), (793, 209))
        self.assertEqual(writes + refusals, 1002)
        un = sum(1 for e in hypo if not e["count_like"])
        co = sum(1 for e in hypo if e["count_like"])
        self.assertEqual((un, co), (780, 222))


class TestToquiProbePreflight(unittest.TestCase):
    """The prepared pressure probe is exactly as specified (files only)."""

    def _parse_inc(self):
        import re
        p = ROOT / "spike" / "toqui-probe" / "ToquiTestRegistry.inc"
        if not p.is_file():
            self.skipTest("toqui probe scratch registry unavailable")
        return re.findall(
            r'\{"([^"]+)", "([^"]+)", "([^"]+)", (\d), (\d), (\d+)\},',
            p.read_text(encoding="utf-8"))

    def test_scratch_registry_has_exactly_eight_pairs(self):
        import re
        rows = self._parse_inc()
        self.assertEqual(len(rows), 8)
        by_id = {m[0]: m for m in rows}
        expected = {
            "TOQUI_DOMESTIC_LOYALTY": ("Amount", "4", 32),
            "TOQUI_FOREIGN_LOYALTY": ("Amount", "4", 32),
            "CARDINAL_BISHOP_PRESSURE": ("Amount", "100", 32),
            "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_3_LOYALTY_FROM_COUNTERSPY":
                ("Amount", "4", 32),
            "MINOR_CIV_PRESLAV_ARMORY_IDENTITY_BONUS": ("Amount", "2", 64),
            "MINOR_CIV_PRESLAV_BARRACKS_STABLE_IDENTITY_BONUS":
                ("Amount", "2", 64),
            "MINOR_CIV_PRESLAV_MILITARY_ACADEMY_IDENTITY_BONUS":
                ("Amount", "2", 64),
            "MINOR_CIV_VATICAN_CITY_GREAT_PERSON_RELIGIOUS_PRESSURE":
                ("Amount", "400", 64),
        }
        self.assertEqual(set(by_id), set(expected))
        for mid, (arg, official, owners) in expected.items():
            m = by_id[mid]
            self.assertEqual((m[1], m[2], int(m[5])), (arg, official, owners),
                             mid)
            self.assertEqual((m[3], m[4]), ("0", "0"), mid)  # no count-like

    def test_expected_k73_values(self):
        from civ6x10 import transforms as T
        kf = T.stored_float32(7.3)
        for official, want in (("4", 29.2), ("100", 730.0), ("2", 14.6),
                               ("400", 2920.0)):
            self.assertAlmostEqual(float(official) * kf, want, delta=0.05)

    def test_probe_lua_covers_all_eight(self):
        p = ROOT / "spike" / "toqui-probe" / "toqui_probe.lua"
        if not p.is_file():
            self.skipTest("toqui probe lua unavailable")
        text = p.read_text(encoding="utf-8")
        for mid in ("TOQUI_DOMESTIC_LOYALTY", "TOQUI_FOREIGN_LOYALTY",
                    "CARDINAL_BISHOP_PRESSURE",
                    "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_3_LOYALTY_FROM_COUNTERSPY",
                    "MINOR_CIV_PRESLAV_ARMORY_IDENTITY_BONUS",
                    "MINOR_CIV_PRESLAV_BARRACKS_STABLE_IDENTITY_BONUS",
                    "MINOR_CIV_PRESLAV_MILITARY_ACADEMY_IDENTITY_BONUS",
                    "MINOR_CIV_VATICAN_CITY_GREAT_PERSON_RELIGIOUS_PRESSURE"):
            self.assertIn(mid, text)
        self.assertIn("X10ToquiProbe", text)

    def test_probe_readme_exists_with_restore_path(self):
        p = ROOT / "spike" / "toqui-probe" / "README.md"
        if not p.is_file():
            self.skipTest("toqui probe readme unavailable")
        text = p.read_text(encoding="utf-8")
        self.assertIn("b6862b28", text)
        self.assertIn("Restore", text)

if __name__ == "__main__":
    unittest.main(verbosity=2)
