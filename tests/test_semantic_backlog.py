"""Phase 6A: unified semantic-backlog research tests.

CI-safe by construction: the backlog builder reads only the checked-in
audit YAMLs (synthetic fixtures for rule tests); no private Firaxis data.
Production-unchanged guards skip cleanly when local build artifacts are
absent.
"""
from __future__ import annotations

import sys
import unittest
from collections import Counter
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
        self.assertEqual(d[RESOLVED_CANDIDATE], 16)
        self.assertEqual(d[RESOLVED_CANDIDATE_COUNT_LIKE], 22)
        self.assertEqual(d[RESOLVED_EXCLUDED], 83)
        # all six pressure rows cleared by the live probe (Toqui pair handled
        # as an addendum below, never in the 142)
        self.assertNotIn(NEEDS_LIVE_PROBE, d)
        # Phase 7A closed the 58 improvement-ownership cells as
        # product_scope:narrow_suzerain_ownership exclusions: no open product
        # decisions remain for Release-1 scope
        self.assertNotIn(NEEDS_PRODUCT_DECISION, d)
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
        self.assertEqual(fresh["proposed_production_pairs"],
                         on_disk["proposed_production_pairs"])
        self.assertEqual(fresh["production_pair_counts"],
                         on_disk["production_pair_counts"])
        self.assertEqual(fresh["probe_cleared_addendum"],
                         on_disk["probe_cleared_addendum"])


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


class TestImprovementOwnershipClosure(unittest.TestCase):
    """Phase 7A: the 58 improvement cells are closed as narrow-ownership
    exclusions (no open product decisions for Release-1 scope)."""

    def test_58_cells_retained_as_product_scope_exclusions(self):
        b = backlog_or_skip()
        rows = [r for r in b["rows"] if r["source_kind"] == "improvement"]
        self.assertEqual(len(rows), 58)
        for r in rows:
            self.assertEqual(r["resolution"], RESOLVED_EXCLUDED, r["root"])
            self.assertIn("product_scope:narrow_suzerain_ownership",
                          r["resolution_rationale"], r["root"])
            # reopenable inventory: full cell metadata retained
            for field in ("root", "root_detail", "argument", "value",
                          "family", "audit_reason"):
                self.assertTrue(r[field], (r["root"], field))

    def test_no_open_product_decisions(self):
        b = backlog_or_skip()
        self.assertNotIn(NEEDS_PRODUCT_DECISION, b["by_resolution"])
        self.assertEqual(
            b["by_group_resolution"]["unique-object ownership"],
            {"RESOLVED_EXCLUDED": 67})

    def test_production_projection_unchanged(self):
        b = backlog_or_skip()
        self.assertEqual(len(b["proposed_production_pairs"]), 37)
        self.assertEqual(b["production_pair_counts"]["unique_production_pairs"],
                         37)


class TestProductionUnchanged(unittest.TestCase):
    def test_registry_digest_unchanged(self):
        import hashlib
        p = ROOT / "build" / "X10ProductionRegistry.inc"
        if not p.is_file():
            self.skipTest("local production registry unavailable")
        self.assertEqual(
            hashlib.sha256(p.read_bytes()).hexdigest(),
            "e9333ad88887a47b9508212e7c6fa3bf21b2c8adacf31d880894684ea537b0ca")

    def test_manifests_unchanged(self):
        import hashlib
        # text-mode read normalizes CRLF/LF: the digest is platform
        # independent (raw bytes differ between Windows and CI checkouts)
        for name, want in (
                ("governors.yml",
                 "02b40bf8c3816da7d3e165538461b27ea60c9777bb343e481430fd1226bb0b99"),
                ("suzerain.yml",
                 "ff5f2090c65c617f4e2adf7ace37808b2af51f6ebd7de211ed66f258340e0702")):
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
                                       "suzerain": 64, "promotions": 128,
                                       "dedications": 256, "modes": 512,
                                       "religion": 1024, "greatpeople": 2048,
                                       "projects": 4096})
        from civ6x10.bridge import REGISTRY_MODULES
        self.assertEqual(len(REGISTRY_MODULES), 13)
        self.assertEqual(REGISTRY_MODULES["envoys"], "suzerain")
        import hashlib
        p = ROOT / "spike" / "EXPECTED_DLL_SHA256.txt"
        if p.is_file():
            self.assertEqual(p.read_text(encoding="utf-8").strip(),
                             "85ea875229ba644a65f00a96373162a8311e0d9f0d12281d7b407bd264c38507")




def _production_pairs(backlog):
    return backlog["proposed_production_pairs"]


class TestProductionProjection(unittest.TestCase):
    """6A.2 normalization: occurrences vs unique production pairs."""

    def test_no_duplicate_production_pair(self):
        b = backlog_or_skip()
        pairs = _production_pairs(b)
        keys = [(p["modifier_id"], p["argument"]) for p in pairs]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(keys), 37)

    def test_projection_counts(self):
        b = backlog_or_skip()
        c = b["production_pair_counts"]
        self.assertEqual(c["unique_production_pairs"], 37)
        self.assertEqual(c["unique_governor_pairs"], 16)
        self.assertEqual(c["unique_suzerain_pairs"], 21)
        self.assertEqual(c["unique_non_count_like"], 16)
        self.assertEqual(c["unique_count_like"], 21)
        self.assertEqual(c["kinds"], {"ADDITIVE": 33, "COMBAT": 1,
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


def _co_applies(entry, kf, kerr):
    from civ6x10 import transforms as T
    kind = entry["kind"]
    if kind in ("REPEAT", 6):
        return False  # non-integral k: every copy stays inert
    if kind in ("DELTA", 5):
        return T.count_like_applies_delta(
            float(entry["official"]), kf, kerr)
    return T.count_like_applies(float(entry["official"]), kf, kerr)


def _registry_entries_or_skip():
    import re
    p = ROOT / "build" / "X10ProductionRegistry.inc"
    if not p.is_file():
        raise unittest.SkipTest("local production registry unavailable")
    out = []
    for m in re.finditer(
            r'\{"([^"]+)", "([^"]*)", "([^"]*)", (\d), (\d), (\d+), (\d+), "([^"]*)"\},',
            p.read_text(encoding="utf-8")):
        out.append({"modifier_id": m.group(1), "argument": m.group(2),
                    "official": m.group(3), "kind": int(m.group(4)),
                    "count_like": bool(int(m.group(5))),
                    "owners": int(m.group(6)), "aux": int(m.group(7)),
                    "target": m.group(8)})
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
        # Phase 6B REALIZED: the three intended rows are already count-like
        # in production; applying the patterns changes nothing further.
        newly = []
        for e in entries:
            et = effects.get((e["modifier_id"], e["argument"]), "")
            if any(p in (et or "") for p in patterns) and not e["count_like"]:
                newly.append((e["modifier_id"], e["argument"], et))
        self.assertEqual(newly, [])
        already = sorted(
            e["modifier_id"] for e in entries
            if any(p in (effects.get((e["modifier_id"], e["argument"]), "")
                         or "") for p in patterns) and e["count_like"])
        for mid in ("CORPORATE_LIBERTARIANISM_RESOURCE_EXTRACTION",
                    "TRAIT_ACCUMULATE_MORE_COAL",
                    "TRAIT_ACCUMULATE_MORE_IRON"):
            self.assertIn(mid, already, mid)
        b = backlog_or_skip()
        recorded = {(r["modifier_id"], r["argument"]) for r in
                    b["proposed_existing_reclassifications"]["rows"]}
        self.assertEqual(recorded, {
            ("CORPORATE_LIBERTARIANISM_RESOURCE_EXTRACTION", "Amount"),
            ("TRAIT_ACCUMULATE_MORE_COAL", "Amount"),
            ("TRAIT_ACCUMULATE_MORE_IRON", "Amount")})


class TestNoPressureBaseline(unittest.TestCase):
    """Hypothetical 6B baseline derived mechanically, not pinned.
    Phase 6B REALIZED below: the live 1010-entry registry decomposes
    exactly into the 971 baseline semantics + 39 new pairs + 3
    reclassifications (registry entries carry int kinds)."""

    def test_hypothetical_totals(self):
        # Phase 6B REALIZED: the hypothetical is now production. Verify the
        # live 1010-entry registry decomposes exactly into the 971 baseline
        # semantics + 39 new pairs + 3 reclassifications.
        import math
        from civ6x10 import transforms as T
        entries = _registry_entries_or_skip()
        self.assertEqual(len(entries), 2481)
        b = backlog_or_skip()
        pairs = _production_pairs(b)
        self.assertEqual(len(pairs), 37)
        addendum = b["probe_cleared_addendum"]["pairs"]
        self.assertEqual(len(addendum), 2)
        new_keys = {(p["modifier_id"], p["argument"]) for p in pairs} | \
            {(p["modifier_id"], p["argument"]) for p in addendum}
        self.assertEqual(len(new_keys), 39)
        by_key = {(e["modifier_id"], e["argument"]): e for e in entries}
        for key in new_keys:
            self.assertIn(key, by_key, key)
        # removing the 39 new pairs leaves the 2442-entry non-backlog set
        base_keys = set(by_key) - new_keys
        self.assertEqual(len(base_keys), 2442)
        # ...except the 3 reclassified rows, which differ only in count_like
        reclass = {(r["modifier_id"], r["argument"])
                   for r in b["proposed_existing_reclassifications"]["rows"]}
        self.assertEqual(len(reclass), 3)
        for key in reclass:
            self.assertTrue(by_key[key]["count_like"], key)
        kf = T.stored_float32(7.3)
        kerr = T.float_quantization_error(kf)
        self.assertEqual(kf, 7.300000190734863)
        # full k=7.3 behavior over the real registry (int kinds 0..6)
        writes = refusals = 0
        for e in entries:
            if e["count_like"]:
                if _co_applies(e, kf, kerr):
                    writes += 1
                else:
                    refusals += 1
                continue
            if e["kind"] == 0:  # ADDITIVE
                r = float(e["official"]) * kf
            elif e["kind"] == 1:  # COMBAT
                v = float(e["official"])
                r = 25.0 * math.log(kf * (math.exp(v / 25.0) - 1) + 1)
            elif e["kind"] == 2:  # PROBABILITY
                r = T.repeated_probability_for_multiplier(
                    float(e["official"]), kf)
            elif e["kind"] == 3:  # DISCOUNT
                v = float(e["official"])
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** kf) * 100.0 * (-1 if v < 0 else 1)
            elif e["kind"] == 4:  # VECTOR
                T.vector_multiply(e["official"], kf)
                r = 0.0
            else:
                self.fail(e)
            if math.isfinite(r) and abs(r) <= 1e6:
                writes += 1
            else:
                refusals += 1
        self.assertEqual((writes, refusals), (1353, 1128))
        self.assertEqual(writes + refusals, 2481)


class TestPressureProbeResults(unittest.TestCase):
    """Phase-6A.2 live evidence: all eight probe rows MATCH on both sessions.

    Anchored to the archived scratch log (checked in as evidence). One
    effect succeeding never auto-clears a sibling: each row below was
    verified independently.
    """

    EXPECTED = {
        "TOQUI_DOMESTIC_LOYALTY": 29.2,
        "TOQUI_FOREIGN_LOYALTY": 29.2,
        "CARDINAL_BISHOP_PRESSURE": 730.0,
        "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_3_LOYALTY_FROM_COUNTERSPY": 29.2,
        "MINOR_CIV_PRESLAV_ARMORY_IDENTITY_BONUS": 14.6,
        "MINOR_CIV_PRESLAV_BARRACKS_STABLE_IDENTITY_BONUS": 14.6,
        "MINOR_CIV_PRESLAV_MILITARY_ACADEMY_IDENTITY_BONUS": 14.6,
        "MINOR_CIV_VATICAN_CITY_GREAT_PERSON_RELIGIOUS_PRESSURE": 2920.0,
    }

    def _sessions(self):
        import re
        p = (ROOT / "spike" / "validation-evidence" /
             "X10Lifecycle.toqui-probe.log")
        if not p.is_file():
            self.skipTest("toqui probe log unavailable")
        txt = p.read_text(encoding="utf-8", errors="replace").splitlines()
        sess, cur = [], []
        for line in txt:
            if "===== X10 native session =====" in line:
                if cur:
                    sess.append(cur)
                cur = [line]
            else:
                cur.append(line)
        sess.append(cur)
        return [[re.sub(r"^\d+ ", "", l).strip() for l in s] for s in sess]

    def test_all_eight_match_on_both_sessions(self):
        import re
        sess = self._sessions()
        self.assertEqual(len(sess), 2)
        for s in sess:
            for mid, want in self.EXPECTED.items():
                hits = [l for l in s if f"id={mid}" in l
                        and "stored_after_add" in l]
                self.assertEqual(len(hits), 1, (mid, len(hits)))
                self.assertIn("MATCH via=store-lookup", hits[0], mid)
                v = float(re.search(r"stored_after_add=([\d.]+)",
                                    hits[0]).group(1))
                self.assertAlmostEqual(v, want, delta=max(0.05, want * 0.001),
                                       msg=mid)
                ref = [l for l in s if f"modifier={mid}" in l
                       and "transform-refused" in l]
                self.assertEqual(ref, [], mid)

    def test_addendum_joins_projection(self):
        b = backlog_or_skip()
        add = b["probe_cleared_addendum"]["pairs"]
        self.assertEqual(len(add), 2)
        self.assertEqual({(p["modifier_id"], p["argument"]) for p in add},
                         {("TOQUI_DOMESTIC_LOYALTY", "Amount"),
                          ("TOQUI_FOREIGN_LOYALTY", "Amount")})
        for p in add:
            self.assertEqual(p["owner"], "traits")
            self.assertEqual((p["family"], p["kind"]), ("LOYALTY", "ADDITIVE"))
            self.assertFalse(p["count_like"])
        gate = b["proposed_gate_evidence"]
        removals = gate.get("exclusion_removals", [])
        self.assertEqual(len(removals), 1)
        self.assertEqual(
            removals[0]["effect"], "EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE")


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



def _dry_run_inputs():
    """Assemble the complete intended Phase-6B gate + candidate set.

    NOTHING is written: rules are deep-copied and extended in memory,
    manifest rows are built/copied in memory, Toqui family review is
    simulated in memory. Returns (manifest_rows, floor, rules, backlog)
    or raises SkipTest.
    """
    import copy
    from civ6x10.bridge import collect_registry_rows
    from civ6x10.backlog import build_backlog
    from civ6x10.certification import load_rules
    try:
        rows = [dict(r) for r in collect_registry_rows(ROOT)]
    except FileNotFoundError:
        raise unittest.SkipTest("local-only registry inputs unavailable")
    try:
        from civ6x10.production import DEFAULT_SEM_PATH
        from civ6x10.certification import load_sem_floor
        if not DEFAULT_SEM_PATH.is_file():
            raise unittest.SkipTest("effect-semantic floor unavailable")
        floor = load_sem_floor(DEFAULT_SEM_PATH)
    except ImportError:
        raise unittest.SkipTest("production certification gate unavailable")
    backlog = build_backlog(
        ROOT / "civ6x10" / "rules" / "governor_audit.yml",
        ROOT / "civ6x10" / "rules" / "suzerain_audit.yml")
    rules = copy.deepcopy(load_rules())
    # proposed count-like patterns (6A backlog proposal, in memory only)
    for pattern in ("RELIGION_EXTRA_PROMOTIONS", "EXTRA_ACCUMULATION",
                    "ATTACKS_PER_TURN", "RESOURCE_POWER_PROVIDED",
                    "FREE_RESOURCE_IMPORT"):
        rules.setdefault("count_like_effects", []).append(
            {"pattern": pattern,
             "rationale": "Phase-6B dry run (6A proposal)"})
    rules.setdefault("discount_effects", []).append(
        {"effect": "EFFECT_ADJUST_BUILDING_PURCHASE_COST",
         "semantics": "PERCENT_DISCOUNT",
         "rationale": "Phase-6B dry run (6A proposal)"})
    # simulated Toqui exclusion removal (live evidence justifies it in 6B)
    rules["excluded_effects"] = [
        e for e in rules.get("excluded_effects", [])
        if e.get("effect") != "EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE"]
    out = []
    for r in rows:
        # simulated 6B manifest review: Toqui Amount rows carry LOYALTY
        if r["modifier_id"] in ("TOQUI_DOMESTIC_LOYALTY",
                                "TOQUI_FOREIGN_LOYALTY") \
                and r["argument_name"] == "Amount":
            r = dict(r)
            r["semantic_family"] = "LOYALTY"
        out.append(r)
    # 37 projection pairs as manifest rows (module = proposed owner).
    # The 2 Toqui pairs are NOT appended: they come from the EXISTING
    # traits rows above, so no second source is ever invented.
    for p in backlog["proposed_production_pairs"]:
        out.append({
            "object_id": p["modifier_id"],
            "modifier_id": p["modifier_id"],
            "modifier_type": p["modifier_type"],
            "effect_type": p["effect_type"],
            "argument_name": p["argument"],
            "official_value": p["value"],
            "semantic_family": p["family"],
            "transformation": {"ADDITIVE": "canonical_x10_multiply",
                               "DISCOUNT": "compound_discount",
                               "COMBAT": "canonical_combat_bonus",
                               "PROBABILITY": "repeated_probability"}[p["kind"]],
            "generated_value": "",
            "status": "ok",
            "confidence": "human_certified",
            "module": p["owner"],
        })
    return out, floor, rules, backlog


class TestPhase6BDryRun(unittest.TestCase):
    """Complete intended Phase-6B gate + set, simulated without writing."""

    def test_toqui_comes_from_existing_traits_manifest(self):
        from civ6x10.bridge import collect_registry_rows
        try:
            rows = collect_registry_rows(ROOT)
        except FileNotFoundError:
            self.skipTest("local-only registry inputs unavailable")
        got = {r["modifier_id"]: r for r in rows
               if r["modifier_id"] in ("TOQUI_DOMESTIC_LOYALTY",
                                       "TOQUI_FOREIGN_LOYALTY")
               and r["argument_name"] == "Amount"}
        self.assertEqual(len(got), 2)
        for mid, r in got.items():
            self.assertEqual(r.get("module"), "traits", mid)
            self.assertEqual(r["official_value"], "4", mid)
            self.assertEqual(r["status"], "ok", mid)

    def test_complete_dry_run(self):
        import math
        from civ6x10 import transforms as T
        from civ6x10.production import build_production_registry
        rows, floor, rules, backlog = _dry_run_inputs()
        entries, report = build_production_registry(
            rows, sem_floor=floor, rules=rules)
        self.assertEqual(report["unresolved_conflicts"], [])
        self.assertEqual(len(entries), 2481)
        self.assertEqual(report["unique_definitions"], 2475)
        self.assertEqual(report["shared_definitions"], 26)
        self.assertEqual(report["certified_unconditional"], 1333)
        self.assertEqual(report["certified_count_like_conditional"], 1148)
        self.assertEqual(report["ownership_counts"]["traits"], 668)
        self.assertEqual(report["ownership_counts"]["policies"], 286)
        self.assertEqual(report["ownership_counts"]["governments"], 18)
        self.assertEqual(report["ownership_counts"]["pantheons"], 34)
        self.assertEqual(report["ownership_counts"]["wonders"], 568)
        self.assertEqual(report["ownership_counts"]["governors"], 70)
        self.assertEqual(report["ownership_counts"]["suzerain"], 123)
        self.assertEqual(report["ownership_counts"]["promotions"], 315)
        self.assertEqual(report["ownership_counts"]["dedications"], 43)
        self.assertEqual(report["ownership_counts"]["modes"], 181)
        self.assertEqual(report["ownership_counts"]["religion"], 31)
        self.assertEqual(report["ownership_counts"]["greatpeople"], 105)
        self.assertEqual(report["ownership_counts"]["projects"], 13)
        kinds = Counter(e["kind"] for e in entries)
        self.assertEqual(kinds, {"ADDITIVE": 1477, "REPEAT": 693,
                                 "COMBAT": 156, "DISCOUNT": 78,
                                 "DELTA": 57, "PROBABILITY": 16,
                                 "VECTOR": 4})
        # all 39 final pairs present with the intended shape
        by_key = {(e["modifier_id"], e["argument"]): e for e in entries}
        final_pairs = (
            {(p["modifier_id"], p["argument"])
             for p in backlog["proposed_production_pairs"]}
            | {(p["modifier_id"], p["argument"]) for p in
               backlog["probe_cleared_addendum"]["pairs"]})
        self.assertEqual(len(final_pairs), 39)
        for key in final_pairs:
            self.assertIn(key, by_key, key)
        # owner split of the 39
        owners = Counter(by_key[k]["owners"] for k in final_pairs)
        self.assertEqual(owners, {32: 16, 64: 21, 1: 2})
        # k=7.3 behavior
        kf = T.stored_float32(7.3)
        kerr = T.float_quantization_error(kf)
        self.assertEqual(kf, 7.300000190734863)
        writes = refusals = 0
        for e in entries:
            if e["count_like"]:
                if _co_applies(e, kf, kerr):
                    writes += 1
                else:
                    refusals += 1
                continue
            if e["kind"] == "ADDITIVE":
                r = float(e["official"]) * kf
            elif e["kind"] == "COMBAT":
                v = float(e["official"])
                r = 25.0 * math.log(kf * (math.exp(v / 25.0) - 1) + 1)
            elif e["kind"] == "DISCOUNT":
                v = float(e["official"])
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** kf) * 100.0 * (-1 if v < 0 else 1)
            elif e["kind"] == "PROBABILITY":
                r = T.repeated_probability_for_multiplier(
                    float(e["official"]), kf)
            elif e["kind"] == "VECTOR":
                T.vector_multiply(e["official"], kf)
                r = 0.0
            else:
                self.fail(e)
            if math.isfinite(r) and abs(r) <= 1e6:
                writes += 1
            else:
                refusals += 1
        self.assertEqual((writes, refusals), (1353, 1128))
        self.assertEqual(writes + refusals, 2481)
        # k=10: everything transform-applicable (REPEAT copies 2..10
        # activate at integral k; DELTA V*9 integral for integral V).
        for e in entries:
            key = (e["modifier_id"], e["argument"])
            if e["count_like"]:
                if e["kind"] == "REPEAT":
                    continue
                if e["kind"] == "DELTA":
                    self.assertTrue(
                        T.count_like_applies_delta(
                            float(e["official"]), 10.0, 0.0), key)
                    continue
                v = float(e["official"])
                self.assertTrue(T.count_like_applies(v, 10.0), key)
                continue
            if e["kind"] == "ADDITIVE":
                r = float(e["official"]) * 10.0
            elif e["kind"] == "COMBAT":
                v = float(e["official"])
                r = 25.0 * math.log(10.0 * (math.exp(v / 25.0) - 1) + 1)
            elif e["kind"] == "DISCOUNT":
                v = float(e["official"])
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** 10.0) * 100.0
            elif e["kind"] == "PROBABILITY":
                r = T.repeated_probability_for_multiplier(
                    float(e["official"]), 10.0)
            elif e["kind"] == "VECTOR":
                T.vector_multiply(e["official"], 10.0)
                r = 0.0
            else:
                self.fail(e)
            self.assertTrue(math.isfinite(r), key)

if __name__ == "__main__":
    unittest.main(verbosity=2)
