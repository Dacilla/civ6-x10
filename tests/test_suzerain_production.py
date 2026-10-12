"""Phase 5B: Suzerain production integration.

Proves the 47 audited Phase-5A.1 candidate rows enter production with the
correct ownership, kinds, conditional state and fail-closed behaviour, and
that nothing from the audit's decision-required / excluded / side-path sets
leaks in.
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
from civ6x10.suzerain import (SUZERAIN_MODULE_BIT,
                              audited_suzerain_candidates,
                              build_suzerain_manifest)

SUZ_BIT = 64
SUZERAIN_ENTRIES = 68  # unique-Suzerain manifest (suzerain.yml)
ENVOY_ENTRIES = 55  # generic 1/3/6-envoy tiers (envoys.yml, same bit)


def envoy_ids():
    import yaml
    man = yaml.safe_load(
        (ROOT / "manifests" / "envoys.yml").read_text(encoding="utf-8"))
    return {(r["modifier_id"], r["argument_name"]) for r in man["envoys"]
            if r.get("status") == "ok"
            and r.get("transformation") != "unchanged"}

BOLOGNA_COUNT_LIKE = {
    "MINOR_CIV_BOLOGNA_GREAT_ADMIRAL_POINTS_BONUS",
    "MINOR_CIV_BOLOGNA_GREAT_ARTIST_POINTS_BONUS",
    "MINOR_CIV_BOLOGNA_GREAT_ENGINEER_POINTS_BONUS",
    "MINOR_CIV_BOLOGNA_GREAT_GENERAL_POINTS_BONUS",
    "MINOR_CIV_BOLOGNA_GREAT_MERCHANT_POINTS_BONUS",
    "MINOR_CIV_BOLOGNA_GREAT_MUSICIAN_POINTS_BONUS",
    "MINOR_CIV_BOLOGNA_GREAT_PROPHET_POINTS_BONUS",
    "MINOR_CIV_BOLOGNA_GREAT_SCIENTIST_POINTS_BONUS",
    "MINOR_CIV_BOLOGNA_GREAT_WRITER_POINTS_BONUS",
}

NGAZARGAMU_DISCOUNT = {
    "MINOR_CIV_NGAZARGAMU_ARMORY_PURCHASE_BONUS",
    "MINOR_CIV_NGAZARGAMU_BARRACKS_STABLE_PURCHASE_BONUS",
    "MINOR_CIV_NGAZARGAMU_MILITARY_ACADEMY_PURCHASE_BONUS",
}

# Rows that must never enter production (representative of each excluded
# class; the authoritative guard is exact candidate-set equality below).
FORBIDDEN_IDS = {
    # main-graph decisions
    "MINOR_CIV_KANDY_BETTER_RELIC_BONUS",
    # main-graph excluded magnitudes
    "MINOR_CIV_KANDY_GRANT_RELIC_BONUS",
    "MINOR_CIV_NALANDA_FREE_TECHNOLOGY_MODIFIER",
    "MINOR_CIV_MEXICO_CITY_REGIONAL_RANGE_BONUS",
    "MINOR_CIV_JERUSALEM_HOLY_SITE_UPGRADE",
    "MINOR_CIV_MOHENJO_DARO_CITIES_FRESHWATER_HOUSING_BONUS",
    # side paths (Lahore +10 admitted in Phase 6B; intrinsics stay out)
    "NIHANG_BARRACKS_STRENGTH",
    "NIHANG_ARMORY_STRENGTH",
    "NIHANG_ACADEMY_STRENGTH",
    "NIHANG_FAITH_FOR_VICTORIES",
    "WOLIN_GREAT_GENERAL_POINTS",
    "WOLIN_GREAT_ADMIRAL_POINTS",
    "MOAI_COASTADJACENCY_CULTURE",
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
    def test_suzerain_bit_is_64(self):
        self.assertEqual(SUZERAIN_MODULE_BIT, 64)
        self.assertEqual(MODULE_BITS["suzerain"], SUZ_BIT)
        self.assertEqual(MODULE_BITS, {"traits": 1, "policies": 2,
                                       "governments": 4, "pantheons": 8,
                                       "wonders": 16, "governors": 32,
                                       "suzerain": 64, "promotions": 128,
                                       "dedications": 256, "modes": 512,
                                       "religion": 1024, "greatpeople": 2048,
                                       "projects": 4096})

    def test_registry_modules_include_suzerain(self):
        self.assertIn("suzerain", REGISTRY_MODULES)
        self.assertIn("envoys", REGISTRY_MODULES)
        self.assertEqual(len(REGISTRY_MODULES), 13)
        self.assertEqual(REGISTRY_MODULES["envoys"], "suzerain")

    def test_manifest_shape(self):
        audit = ROOT / "civ6x10" / "rules" / "suzerain_audit.yml"
        if not audit.is_file():
            self.skipTest("checked-in suzerain audit unavailable")
        man = build_suzerain_manifest(
            audit, backlog_path=ROOT / "civ6x10" / "rules" / "semantic_backlog.yml")
        rows = man["suzerain"]
        self.assertEqual(len(rows), SUZERAIN_ENTRIES)
        self.assertEqual(len({r["modifier_id"] for r in rows}),
                         SUZERAIN_ENTRIES)
        self.assertEqual(len({(r["modifier_id"], r["argument_name"])
                              for r in rows}), SUZERAIN_ENTRIES)
        # families preserved verbatim from the audit
        audited = {(r["modifier_id"], r["argument_name"]): r["semantic_family"]
                   for r in audited_suzerain_candidates(audit)}
        for r in rows:
            if r.get("certification_source") == "phase6a-semantic-backlog":
                continue
            self.assertEqual(r["semantic_family"],
                             audited[(r["modifier_id"], r["argument_name"])],
                             r["modifier_id"])
        # transform mapping: discounts compound, Lahore combat uses the
        # combat formula, everything else additive
        for r in rows:
            if r["modifier_id"] in NGAZARGAMU_DISCOUNT or \
                    "VALLETTA_PURCHASE_CHEAPER" in r["modifier_id"]:
                self.assertEqual(r["transformation"], "compound_discount",
                                 r["modifier_id"])
            elif r["modifier_id"] == "NIHANG_SUZERAIN_COMBAT_BONUS":
                self.assertEqual(r["transformation"],
                                 "canonical_combat_bonus", r["modifier_id"])
            else:
                self.assertEqual(r["transformation"],
                                 "canonical_x10_multiply", r["modifier_id"])
        # module is set through the production path: old rows keep the
        # Phase-5A.1 label, Phase-6B backlog rows carry the Phase-6A label
        sources = Counter(r.get("certification_source") for r in rows)
        self.assertEqual(sources, {"phase5a.1-suzerain-audit": 47,
                                   "phase6a-semantic-backlog": 21})

    def test_manifest_deterministic_and_checked_in(self):
        import yaml
        audit = ROOT / "civ6x10" / "rules" / "suzerain_audit.yml"
        if not audit.is_file():
            self.skipTest("checked-in suzerain audit unavailable")
        checked = ROOT / "manifests" / "suzerain.yml"
        if not checked.is_file():
            self.skipTest("checked-in suzerain manifest unavailable")
        fresh = build_suzerain_manifest(
            audit, backlog_path=ROOT / "civ6x10" / "rules" / "semantic_backlog.yml")
        on_disk = yaml.safe_load(checked.read_text(encoding="utf-8"))
        self.assertEqual(fresh, on_disk)


class TestSuzerainRegistryIntegration(unittest.TestCase):
    def setUp(self):
        self.entries, self.report = registry_or_skip()

    def test_totals(self):
        self.assertEqual(len(self.entries), 2481)
        self.assertEqual(self.report["unique_definitions"], 2475)
        self.assertEqual(self.report["shared_definitions"], 26)
        self.assertEqual(self.report["certified_unconditional"], 1333)
        self.assertEqual(self.report["certified_count_like_conditional"], 1148)
        self.assertEqual(self.report["unresolved_conflicts"], [])
        # 68 unique-Suzerain + 55 generic envoy tiers share bit 64.
        self.assertEqual(self.report["ownership_counts"]["suzerain"], 123)

    def test_suzerain_subset(self):
        # Phase 8B: the City-State module covers unique-Suzerain bonuses
        # (68, suzerain.yml) plus generic envoy tiers (55, envoys.yml).
        suz = [e for e in self.entries if e["owners"] == SUZ_BIT]
        self.assertEqual(len(suz), SUZERAIN_ENTRIES + ENVOY_ENTRIES)
        self.assertEqual(len({e["modifier_id"] for e in suz}),
                         SUZERAIN_ENTRIES + ENVOY_ENTRIES)
        kinds = Counter(e["kind"] for e in suz)
        self.assertEqual(kinds, {"ADDITIVE": 116, "DISCOUNT": 6, "COMBAT": 1})
        self.assertEqual(sum(1 for e in suz if e["count_like"]), 53)
        self.assertEqual(sum(1 for e in suz if not e["count_like"]), 70)
        # suzerain-only ownership: no entry is shared with another module
        self.assertTrue(all(e["owners"] == SUZ_BIT for e in suz))
        envoy_keys = {(e["modifier_id"], e["argument"]) for e in suz} \
            & envoy_ids()
        self.assertEqual(len(envoy_keys), ENVOY_ENTRIES)

    def test_bologna_plus_new_count_like_rows(self):
        suz = {e["modifier_id"]: e for e in self.entries
               if e["owners"] == SUZ_BIT}
        unique_cl = {m for m, e in suz.items()
                     if e["count_like"]
                     and (m, e["argument"]) not in envoy_ids()}
        self.assertEqual(unique_cl,
                         BOLOGNA_COUNT_LIKE | {
                             "MINOR_CIV_CARDIFF_POWER_LIGHTHOUSE",
                             "MINOR_CIV_CARDIFF_POWER_SEAPORT",
                             "MINOR_CIV_CARDIFF_POWER_SHIPYARD",
                             "MINOR_CIV_HATTUSA_ALUMINUM_RESOURCE_XP2",
                             "MINOR_CIV_HATTUSA_COAL_RESOURCE_XP2",
                             "MINOR_CIV_HATTUSA_HORSES_RESOURCE_XP2",
                             "MINOR_CIV_HATTUSA_IRON_RESOURCE_XP2",
                             "MINOR_CIV_HATTUSA_NITER_RESOURCE_XP2",
                             "MINOR_CIV_HATTUSA_OIL_RESOURCE_XP2",
                             "MINOR_CIV_HATTUSA_URANIUM_RESOURCE_XP2",
                             "MINOR_CIV_ZANZIBAR_CINNAMON_RESOURCE_BONUS",
                             "MINOR_CIV_ZANZIBAR_CLOVES_RESOURCE_BONUS",
                         })
        # Envoy-tier count-like rows are the engine-integral building
        # yields (Eiffel-class refusal at fractional Custom).
        envoy_cl = [(m, e) for m, e in suz.items()
                    if e["count_like"]
                    and (m, e["argument"]) in envoy_ids()]
        self.assertEqual(len(envoy_cl), 32)
        for m, e in envoy_cl:
            self.assertTrue(e["cert_source"].startswith(
                "curated-effect:engine-integral:"), m)
        for mid in BOLOGNA_COUNT_LIKE:
            e = suz[mid]
            self.assertEqual(e["kind"], "ADDITIVE", mid)
            self.assertEqual(e["official"], "1", mid)
            self.assertTrue(e["cert_source"].startswith(
                "curated-category:GREAT_PERSON_POINTS"), mid)

    def test_three_ngazargamu_rows_are_discount(self):
        suz = {e["modifier_id"]: e for e in self.entries
               if e["owners"] == SUZ_BIT}
        for mid in NGAZARGAMU_DISCOUNT:
            e = suz[mid]
            self.assertEqual(e["kind"], "DISCOUNT", mid)
            self.assertFalse(e["count_like"], mid)
            self.assertEqual(e["official"], "20", mid)
            self.assertTrue(e["cert_source"].startswith(
                "curated-effect:discount:"
                "EFFECT_ADJUST_ALL_UNITS_PURCHASE_COST"), mid)
        rows = [r for r in manifests_or_skip()
                if r.get("module") == "suzerain"
                and r["modifier_id"] in NGAZARGAMU_DISCOUNT]
        self.assertEqual(len(rows), 3)
        for r in rows:
            self.assertEqual(r["transformation"], "compound_discount",
                             r["modifier_id"])
            self.assertEqual(r["semantic_family"], "PERCENT_DISCOUNT",
                             r["modifier_id"])

    def test_combat_slice_is_exactly_lahore(self):
        suz = {e["modifier_id"]: e for e in self.entries
               if e["owners"] == SUZ_BIT}
        combat = {m for m, e in suz.items() if e["kind"] == "COMBAT"}
        self.assertEqual(combat, {"NIHANG_SUZERAIN_COMBAT_BONUS"})
        e = suz["NIHANG_SUZERAIN_COMBAT_BONUS"]
        self.assertEqual(e["official"], "10")
        self.assertFalse(e["count_like"])
        self.assertFalse(any(e["kind"] == "PROBABILITY"
                             for e in suz.values()))

    def test_exact_candidate_pair_equality(self):
        import yaml
        audit = yaml.safe_load(
            (ROOT / "civ6x10" / "rules" / "suzerain_audit.yml")
            .read_text(encoding="utf-8"))
        cand = {(c["modifier_id"], c["argument"])
                for c in audit["proposed_candidates"]}
        self.assertEqual(len(cand), 47)
        # Phase 6B admits exactly the 21 backlog-resolved suzerain pairs more
        backlog = yaml.safe_load(
            (ROOT / "civ6x10" / "rules" / "semantic_backlog.yml")
            .read_text(encoding="utf-8"))
        extra = {(p["modifier_id"], p["argument"]) for p in
                 backlog["proposed_production_pairs"]
                 if p["owner"] == "suzerain"}
        self.assertEqual(len(extra), 21)
        suz = {(e["modifier_id"], e["argument"]) for e in self.entries
               if e["owners"] == SUZ_BIT}
        # Phase 8B: generic envoy tiers join the unique-Suzerain pairs.
        self.assertEqual(suz, cand | extra | envoy_ids())

    def test_no_decision_or_excluded_row_enters(self):
        import yaml
        audit = yaml.safe_load(
            (ROOT / "civ6x10" / "rules" / "suzerain_audit.yml")
            .read_text(encoding="utf-8"))
        forbidden = {(r["modifier_id"], r["argument_name"])
                     for r in audit["rows"]
                     if r["disposition"] != "CERTIFIED_CANDIDATE"}
        # all 21 main-graph decisions are in the forbidden set
        decisions = {(r["modifier_id"], r["argument_name"])
                     for r in audit["rows"]
                     if r["numeric"] and r["disposition"] == "DECISION_REQUIRED"}
        self.assertEqual(len(decisions), 21)
        self.assertLessEqual(decisions, forbidden)
        # Phase 6B admits exactly 20 of them via the backlog (Kandy
        # ScalingFactor stays out); everything else forbidden stays out.
        backlog = yaml.safe_load(
            (ROOT / "civ6x10" / "rules" / "semantic_backlog.yml")
            .read_text(encoding="utf-8"))
        admitted = {(p["modifier_id"], p["argument"]) for p in
                    backlog["proposed_production_pairs"]
                    if p["owner"] == "suzerain"}
        self.assertEqual(len(admitted), 21)
        suz = {(e["modifier_id"], e["argument"]) for e in self.entries
               if e["owners"] == SUZ_BIT}
        leaked = suz & (forbidden - admitted)
        self.assertEqual(leaked, set(), sorted(leaked))

    def test_no_side_path_cell_enters(self):
        import yaml
        audit = yaml.safe_load(
            (ROOT / "civ6x10" / "rules" / "suzerain_audit.yml")
            .read_text(encoding="utf-8"))
        suz_ids = {e["modifier_id"] for e in self.entries
                   if e["owners"] == SUZ_BIT}
        # every side-path modifier id is absent from production
        side_ids = set()
        for imp, p in audit["side_paths"]["improvements"].items():
            for am in p.get("attached_modifiers", []):
                side_ids.add(am["modifier_id"])
        for unit, p in audit["side_paths"]["units"].items():
            for m in p.get("promotion_modifiers", []):
                side_ids.add(m["modifier_id"])
            for m in p.get("ability_modifiers", []):
                side_ids.add(m["modifier_id"])
        for ab, p in audit["side_paths"]["abilities"].items():
            for m in p.get("modifiers", []):
                side_ids.add(m["modifier_id"])
        self.assertTrue(side_ids)
        # Lahore +10 moved side-path-decision -> candidate by explicit Phase-6A
        # resolution (own Suzerain-gated requirement); it is the one allowed
        # intersection. Everything else intrinsic stays out.
        self.assertEqual(suz_ids & side_ids, {"NIHANG_SUZERAIN_COMBAT_BONUS"})
        # representative spot checks
        for mid in FORBIDDEN_IDS:
            self.assertNotIn(mid, suz_ids, mid)

    def test_disabling_suzerain_makes_entries_inapplicable(self):
        suz = [e for e in self.entries if e["owners"] == SUZ_BIT]
        enabled = (MODULE_BITS["traits"] | MODULE_BITS["policies"] |
                   MODULE_BITS["governments"] | MODULE_BITS["pantheons"] |
                   MODULE_BITS["wonders"] | MODULE_BITS["governors"])
        for e in suz:
            self.assertNotEqual(e["owners"] & enabled, e["owners"])
        others = [e for e in self.entries if e["owners"] != SUZ_BIT]
        self.assertEqual(len(others), 2358)
        for e in others:
            self.assertEqual(e["owners"] & SUZ_BIT, 0)

    def test_determinism(self):
        e2, r2 = registry_or_skip()
        self.assertEqual([dict(x) for x in self.entries],
                         [dict(x) for x in e2])
        self.assertEqual(self.report["eligible"], r2["eligible"])

    def test_pre_5b_subset_unchanged(self):
        # Every non-suzerain entry must match the pre-5B registry exactly on
        # the semantic fields the task pins.
        rows = manifests_or_skip()
        base_rows = [r for r in rows if r.get("module") != "suzerain"]
        base_entries, base_report = registry_or_skip(base_rows)
        self.assertEqual(len(base_entries), 2358)
        self.assertEqual(base_report["unique_definitions"], 2352)
        self.assertEqual(base_report["shared_definitions"], 26)
        self.assertEqual(base_report["certified_unconditional"], 1263)
        self.assertEqual(base_report["certified_count_like_conditional"],
                         1095)
        by_key = {(e["modifier_id"], e["argument"]): e for e in base_entries}
        for e in self.entries:
            if e["owners"] == SUZ_BIT:
                continue
            prev = by_key[(e["modifier_id"], e["argument"])]
            for f in ("official", "kind", "family", "count_like", "owners",
                      "cert_source"):
                self.assertEqual(prev[f], e[f], (e["modifier_id"], f))


class TestSuzerainTransforms(unittest.TestCase):
    """k=7.3f / k=10 behaviour, derived from the compiled registry."""

    def setUp(self):
        from civ6x10 import transforms as T
        self.T = T
        self.entries, _ = registry_or_skip()
        self.suz = [e for e in self.entries if e["owners"] == SUZ_BIT]
        self.kf = T.stored_float32(7.3)
        self.assertEqual(self.kf, 7.300000190734863)

    def _applies(self, official, k):
        return self.T.count_like_applies(float(official), k)

    def test_suzerain_rows_at_k73(self):
        # 70 unconditional apply; all 53 conditionals refuse at 7.3
        # (unique 1s/2s plus envoy 1/2/3/4/6 building yields — every
        # product is fractional, so the Eiffel-class refusal holds).
        un = [e for e in self.suz if not e["count_like"]]
        co = [e for e in self.suz if e["count_like"]]
        self.assertEqual(len(un), 70)
        self.assertEqual(len(co), 53)
        for e in un:
            v = float(e["official"])
            if e["kind"] == "ADDITIVE":
                r = v * self.kf
            elif e["kind"] == "DISCOUNT":
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** self.kf) * 100.0
            elif e["kind"] == "COMBAT":
                r = 25.0 * math.log(
                    self.kf * (math.exp(v / 25.0) - 1) + 1)
            else:
                self.fail(e["kind"])
            self.assertTrue(math.isfinite(r), e)
        for e in co:
            self.assertFalse(self._applies(e["official"], self.kf), e)
            self.assertIn(e["official"], ("1", "2", "3", "4", "6"), e)

    def test_suzerain_rows_at_k10(self):
        for e in self.suz:
            v = float(e["official"])
            if e["count_like"]:
                self.assertTrue(self._applies(e["official"], 10.0), e)
                self.assertEqual(v * 10.0, round(v * 10.0), e)
            elif e["kind"] == "DISCOUNT":
                from civ6x10.transforms import compound_discount_for_multiplier
                r = compound_discount_for_multiplier(v, 10.0)
                self.assertTrue(math.isfinite(r), e)
            else:
                self.assertTrue(math.isfinite(v * 10.0), e)

    def test_bologna_refuses_at_73_applies_at_10(self):
        suz = {e["modifier_id"]: e for e in self.suz}
        for mid in BOLOGNA_COUNT_LIKE:
            e = suz[mid]
            self.assertEqual(e["official"], "1", mid)
            self.assertFalse(self._applies("1", self.kf), mid)
            self.assertEqual(1 * 10.0, 10, mid)

    def test_ngazargamu_discount_uses_discount_transform(self):
        from civ6x10.transforms import compound_discount_for_multiplier
        suz = {e["modifier_id"]: e for e in self.suz}
        for mid in NGAZARGAMU_DISCOUNT:
            e = suz[mid]
            # official 20% at k=7.3 follows the repeated-discount formula,
            # not 20*7.3=146
            r = compound_discount_for_multiplier(20.0, self.kf)
            self.assertLess(r, 100.0, mid)
            self.assertGreater(r, 20.0, mid)
            self.assertNotAlmostEqual(r, 20.0 * self.kf, places=1)

    def test_k73_suzerain_and_global_totals(self):
        import math
        from civ6x10 import transforms as T
        writes = refusals = 0
        for e in self.suz:
            if e["count_like"]:
                if T.count_like_applies(float(e["official"]), self.kf):
                    writes += 1
                else:
                    refusals += 1
                continue
            v = float(e["official"])
            if e["kind"] == "ADDITIVE":
                r = v * self.kf
            elif e["kind"] == "DISCOUNT":
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** self.kf) * 100.0
            elif e["kind"] == "COMBAT":
                r = 25.0 * math.log(
                    self.kf * (math.exp(v / 25.0) - 1) + 1)
            else:
                self.fail(e["kind"])
            if math.isfinite(r) and abs(r) <= 1e6:
                writes += 1
            else:
                refusals += 1
        self.assertEqual((writes, refusals), (70, 53))
        ok = ex = 0
        kerr = T.float_quantization_error(self.kf)
        for e in self.entries:
            if e["count_like"]:
                if _co_applies(e, self.kf, kerr):
                    ex += 1
                continue
            if e["kind"] == "ADDITIVE":
                r = float(e["official"]) * self.kf
            elif e["kind"] == "COMBAT":
                v = float(e["official"])
                r = 25.0 * math.log(self.kf * (math.exp(v / 25.0) - 1) + 1)
            elif e["kind"] == "DISCOUNT":
                v = float(e["official"])
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** self.kf) * 100.0 * (-1 if v < 0 else 1)
            elif e["kind"] == "PROBABILITY":
                r = T.repeated_probability_for_multiplier(
                    float(e["official"]), self.kf)
            elif e["kind"] == "VECTOR":
                T.vector_multiply(e["official"], self.kf)
                r = 0.0
            else:
                self.fail(f"unexpected unconditional kind: {e}")
            if math.isfinite(r) and abs(r) <= 1e6:
                ok += 1
        refused = sum(1 for e in self.entries if e["count_like"]
                      and not _co_applies(e, self.kf, kerr))
        self.assertEqual(ok + ex, 1353)
        self.assertEqual(refused, 1128)
        self.assertEqual(len(self.entries), 2481)


def _co_applies(entry, kf, kerr):
    from civ6x10 import transforms as T
    if entry["kind"] == "REPEAT":
        return False
    if entry["kind"] == "DELTA":
        return T.count_like_applies_delta(
            float(entry["official"]), kf, kerr)
    return T.count_like_applies(float(entry["official"]), kf, kerr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
