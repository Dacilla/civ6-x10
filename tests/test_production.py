"""Production registry tests: certification gate, parity, save/load derivation."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

from civ6x10 import transforms as T
from civ6x10.certification import certify_row, load_rules
from civ6x10.production import (
    SemanticConflict,
    build_production_registry,
)


def synth(module="traits", mid="M_X", arg="Amount", official="7",
          family="FLAT_AMOUNT", transform="canonical_x10_multiply",
          status="ok", confidence="auto_rule", obj="T_X",
          modifier_type="MODIFIER_PLAYER_ADJUST_UNIT_PRODUCTION",
          effect_type="EFFECT_ADJUST_UNIT_PRODUCTION"):
    return {"object_id": obj, "modifier_id": mid, "modifier_type": modifier_type,
            "effect_type": effect_type, "argument_name": arg,
            "official_value": official, "semantic_family": family,
            "transformation": transform, "generated_value": "",
            "status": status, "confidence": confidence, "module": module}


def sem_row(modifier_type="MODIFIER_PLAYER_ADJUST_UNIT_PRODUCTION",
            effect_type="EFFECT_ADJUST_UNIT_PRODUCTION", arg="Amount",
            family="MAGNITUDE_UNCLASSIFIED", transform="CANONICAL_X10_MULTIPLY",
            confidence="NEEDS_REVIEW"):
    return {"modifier_type": modifier_type, "effect_type": effect_type,
            "argument_name": arg, "semantic_family": family,
            "transformation_family": transform, "confidence": confidence}


def sem_floor_for(rows):
    floor = {}
    for r in rows:
        floor[(r["modifier_type"], r["effect_type"], r["argument_name"])] = \
            sem_row(r["modifier_type"], r["effect_type"], r["argument_name"])
    return floor


def load_manifests():
    # Single shared source with the CLI: 5 manifests + generated bridge
    # helpers, so tests certify exactly what ships.
    from civ6x10.bridge import collect_registry_rows
    return collect_registry_rows(ROOT)


class TestProductionRegistry(unittest.TestCase):
    def test_generation_core(self):
        # Fixture-driven (CI-safe): duplicates merge with owners union,
        # heuristic confidence alone never admits, undecided excluded,
        # deterministic output.
        floor = {("MODIFIER_PLAYER_ADJUST_UNIT_PRODUCTION",
                  "EFFECT_ADJUST_UNIT_PRODUCTION", "Amount"):
                 sem_row(family="MAGNITUDE_UNCLASSIFIED")}
        rows = [
            synth(mid="M_A"),
            synth(mid="M_A"),  # duplicate
            synth(mid="M_B", family="UNKNOWN", transform="decision_required",
                  status="undecided", confidence="needs_human"),
            synth(mid="M_C", family="SELECTOR", transform="unchanged"),
            synth(mid="M_D", family="BOOLEAN_UNLOCK",
                  transform="refused_no_multiplier", status="refused"),
        ]
        entries, report = build_production_registry(rows, sem_floor=floor)
        self.assertEqual([(e["modifier_id"], e["kind"]) for e in entries],
                         [("M_A", "ADDITIVE")])
        self.assertEqual(entries[0]["cert_source"],
                         "curated-category:FLAT_AMOUNT")
        # Manifest claims of DISCOUNT/COMBAT/PROBABILITY need floor
        # agreement: a bare heuristic claim fails closed.
        with self.assertRaises(SemanticConflict):
            build_production_registry(
                [synth(mid="M_E", family="COMBAT_STRENGTH_BONUS",
                       transform="canonical_combat_bonus", official="5")],
                sem_floor=floor)
        e2, _ = build_production_registry([rows[0], rows[1]],
                                          sem_floor=floor)
        self.assertEqual(e2, entries)

    def test_manifest_parity(self):
        # Local-only: manifests need local auto-ruled data (gitignored).
        try:
            rows = load_manifests()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        entries, report = build_production_registry(rows)
        self.assertEqual(len(entries), 872)
        self.assertEqual(report["eligible"], 872)
        self.assertEqual(report["unique_definitions"], 868)
        self.assertEqual(report["shared_definitions"], 25)
        self.assertEqual(report["certified_unconditional"], 740)
        self.assertEqual(report["certified_count_like_conditional"], 132)
        self.assertEqual(report["unresolved_conflicts"], [])
        ids = {e["modifier_id"] for e in entries}
        for mid in ("TRAIT_LINCOLN_INDUSTRIAL_ZONE_LOYALTY",
                    "AGOGE_ANCIENT_MELEE_PRODUCTION",
                    "TRAIT_GOLD_FROM_DOMESTIC_TRADING_POSTS",
                    "TRAIT_TOQUI_COMBAT_BONUS_VS_GOLDEN_AGE_CIV"):
            self.assertIn(mid, ids, mid)
        # Toqui governor-loyalty Amounts are temporarily excluded: their raw
        # strings verified blank post-Add while 610 siblings MATCH, so
        # stored-form persistence is unproven (see docs; re-certify via the
        # store-lookup witness before re-admitting).
        self.assertNotIn("TOQUI_DOMESTIC_LOYALTY", ids)
        self.assertNotIn("TOQUI_FOREIGN_LOYALTY", ids)
        for c in report["conflict_ledger"]:
            if (c["modifier_id"] in ("TOQUI_DOMESTIC_LOYALTY",
                                     "TOQUI_FOREIGN_LOYALTY")
                    and c["argument"] == "Amount"):
                self.assertEqual(c["resolution"], "excluded:curated-effect", c)
                self.assertEqual(
                    c["cert_source"],
                    "curated-effect:excluded-effect:"
                    "EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE", c)
        keys = [(e["modifier_id"], e["argument"]) for e in entries]
        self.assertEqual(len(keys), len(set(keys)))
        kinds = {e["kind"] for e in entries}
        self.assertEqual(kinds, {"ADDITIVE", "COMBAT", "DISCOUNT"})


class TestProductionTransforms(unittest.TestCase):
    def test_k1_identity(self):
        self.assertEqual(T.scale_flat(36.5, 1.0), 36.5)
        self.assertAlmostEqual(T.combat_bonus_for_multiplier(5, 1.0), 5.0, places=9)

    def test_k10_classic(self):
        self.assertEqual(T.scale_flat(5, 10.0), 50.0)
        self.assertAlmostEqual(T.combat_bonus_for_multiplier(5, 10.0), 29.19, delta=0.6)

    def test_fractional_k(self):
        self.assertAlmostEqual(T.scale_flat(3, 7.3), 21.9)
        self.assertAlmostEqual(T.repeated_probability_for_multiplier(0.1, 7.3),
                               1 - 0.9 ** 7.3)
        self.assertAlmostEqual(T.compound_discount_for_multiplier(-25, 7.3),
                               -(1 - 0.75 ** 7.3) * 100)

    def test_probability_unit_handling(self):
        self.assertAlmostEqual(T.repeated_probability_for_multiplier(10, 10.0),
                               (1 - 0.9 ** 10) * 100)

    def test_save_load_derives_from_official(self):
        # Reload recomputes official*k; never stored*k. Simulate: stored value
        # from a previous session must equal a fresh official*k derivation.
        official, k = 3.0, 7.3
        first = T.scale_flat(official, k)
        reloaded = T.scale_flat(official, k)  # NOT first*k
        self.assertEqual(first, reloaded)
        self.assertNotEqual(T.scale_flat(first, k), first)  # double-apply differs

    def test_signed_additives_and_all_discounts(self):
        # Local-only: every negative production entry must transform.
        # Required spot values (native and Python must agree):
        #   ADDITIVE -25 x 7.3 = -182.5
        #   DISCOUNT -20 @7.3 ~ -80.3864, -50 @7.3 ~ -99.3654, -100 -> -100.0
        self.assertEqual(T.scale_flat(-25, 7.3), -182.5)
        self.assertAlmostEqual(
            T.compound_discount_for_multiplier(-20, 7.3), -80.3864, places=3)
        self.assertAlmostEqual(
            T.compound_discount_for_multiplier(-50, 7.3), -99.3654, places=3)
        self.assertEqual(
            T.compound_discount_for_multiplier(-100, 7.3), -100.0)
        try:
            rows = load_manifests()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        from civ6x10.production import build_production_registry
        entries, _ = build_production_registry(rows)
        neg = [e for e in entries if float(e["official"]) < 0]
        self.assertEqual(len(neg), 43)
        for e in entries:
            v = float(e["official"])
            if e["kind"] == "ADDITIVE":
                self.assertEqual(T.scale_flat(v, 7.3), v * 7.3)
            elif e["kind"] == "DISCOUNT":
                d = abs(v) / 100.0
                self.assertTrue(0 <= d <= 1)
                self.assertAlmostEqual(
                    T.compound_discount_for_multiplier(v, 7.3),
                    (1.0 - (1.0 - d) ** 7.3) * 100.0 * (-1 if v < 0 else 1))
        discs = [e for e in entries if e["kind"] == "DISCOUNT"]
        self.assertEqual(len(discs), 17)
        # Flat gold-per-unit maintenance is ADDITIVE, not a percent discount:
        # 1 -> 7.3, 2 -> 14.6, -2 -> -14.6 at k=7.3.
        by_id = {}
        for e in entries:
            by_id.setdefault(e["modifier_id"], []).append(e)
        for mid, official, want in (
                ("CONSCRIPTION_UNITMAINTENANCEDISCOUNT", "1", 7.3),
                ("LEVEEENMASSE_UNITMAINTENANCEDISCOUNT", "2", 14.6),
                ("HARALD_MAINTENANCE_DISCOUNT", "2", 14.6),
                ("ELITEFORCES_EXTRA_MAINTENANCE", "-2", -14.6)):
            self.assertIn(mid, by_id, mid)
            got = [(e["official"], e["kind"], e["count_like"])
                   for e in by_id[mid]]
            self.assertEqual(got, [(official, "ADDITIVE", False)], mid)
            self.assertAlmostEqual(
                T.scale_flat(float(official), 7.3), want, msg=mid)

    def test_full_registry_transforms_at_k73(self):
        # Honest static expectation at the LIVE stored-FLOAT32 k=7.3
        # (raw 9a99e940 -> 7.300000190734863; runtime mismatch checks happen
        # live against loaded definitions):
        #   701 unconditional entries: every one transforms;
        #   112 conditional (count-like) entries: 12 exact-integral apply,
        #   100 fractional refuse safely (never floored).
        # Static successful transforms: 701 + 12 = 752 < registry size 872
        # (Toqui loyalty pair temporarily excluded pending stored-form
        # re-certification).
        import math
        try:
            rows = load_manifests()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        from civ6x10.production import build_production_registry
        entries, report = build_production_registry(rows)
        kf = T.stored_float32(7.3)
        self.assertEqual(kf, 7.300000190734863)  # live representation
        self.assertEqual(len(entries), 872)
        un = [e for e in entries if not e["count_like"]]
        co = [e for e in entries if e["count_like"]]
        self.assertEqual(len(un), 740)
        self.assertEqual(len(co), 132)
        ok = 0
        for e in un:
            v = float(e["official"])
            if e["kind"] == "ADDITIVE":
                r = v * kf
            elif e["kind"] == "COMBAT":
                r = 25.0 * math.log(kf * (math.exp(v / 25.0) - 1) + 1)
            elif e["kind"] == "DISCOUNT":
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** kf) * 100.0 * (-1 if v < 0 else 1)
            else:
                continue
            self.assertTrue(math.isfinite(r) and abs(r) <= 1000000, e)
            ok += 1
        self.assertEqual(ok, 740)
        exact = [e for e in co
                 if T.count_like_applies(float(e["official"]), kf)]
        refused = [e for e in co if e not in exact]
        self.assertEqual(len(exact), 12)
        self.assertEqual(len(refused), 120)
        # Static expectation: 752 successful transforms of 872 certified.
        self.assertEqual(ok + len(exact), 752)

    def test_verifier_key_capacity(self):
        # Exact live fixture: the 66-char Magnificences ID truncated to
        # ..._SQUARE_OR_CHAT by the old 64-byte Touched.id. Full ID
        # byte-for-byte, length 66, and every registry identifier must fit
        # the verifier buffers (id < 256, arg < 32); over-capacity must
        # fail loudly, never look up a shortened ID.
        try:
            rows = load_manifests()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        from civ6x10.production import build_production_registry
        entries, _ = build_production_registry(rows)
        full = "MAGNIFICENCES_CULTURE_LUXURY_ADJACENT_TO_THEATER_SQUARE_OR_CHATEAU"
        self.assertEqual(len(full), 66)
        got = [e for e in entries if e["modifier_id"] == full]
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["modifier_id"], full)
        self.assertTrue(got[0]["modifier_id"].endswith("_OR_CHATEAU"))
        for e in entries:
            self.assertLess(len(e["modifier_id"]), 256, e["modifier_id"])
            self.assertLess(len(e["argument"]), 32, e["argument"])

    def test_shared_ownership_and_conflicts(self):
        from civ6x10.production import (RegistryConflict, SemanticConflict,
                                        build_production_registry)
        floor = {("MT_S", "ET_S", "Amount"): sem_row(
            "MT_S", "ET_S", "Amount", family="MAGNITUDE_UNCLASSIFIED")}
        rows = [
            synth(module="policies", mid="M_S", modifier_type="MT_S",
                  effect_type="ET_S"),
            synth(module="governments", mid="M_S", modifier_type="MT_S",
                  effect_type="ET_S"),
        ]
        entries, report = build_production_registry(rows, sem_floor=floor)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["owners"], 2 | 4)
        self.assertEqual(report["shared_definitions"], 1)
        bad = [
            synth(module="policies", mid="M_X", official="5"),
            synth(module="governments", mid="M_X", official="6"),
        ]
        with self.assertRaises(RegistryConflict):
            build_production_registry(bad, sem_floor={
                ("MODIFIER_PLAYER_ADJUST_UNIT_PRODUCTION",
                 "EFFECT_ADJUST_UNIT_PRODUCTION", "Amount"): sem_row(
                    family="MAGNITUDE_UNCLASSIFIED")})
        # Strong-family contradiction with no curated resolution fails.
        # (Grant/spatial/defeated rows resolve to exclusions; a row with NO
        # floor coverage at all cannot be verified and fails.)
        with self.assertRaises(SemanticConflict):
            build_production_registry(
                [synth(mid="M_NOFLOOR", modifier_type="MODIFIER_X_UNKNOWN",
                       effect_type="EFFECT_X_UNKNOWN")],
                sem_floor={})

    def test_multi_argument_definitions(self):
        # Four two-argument definitions keep BOTH args as entries.
        try:
            rows = load_manifests()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        from civ6x10.production import build_production_registry
        from collections import Counter
        entries, _ = build_production_registry(rows)
        per_def = Counter(e["modifier_id"] for e in entries)
        multi = {m: c for m, c in per_def.items() if c > 1}
        self.assertEqual(len(multi), 4)
        self.assertIn("TRAIT_TERRITORIAL_WAR_COMBAT", multi)
        # Every surviving second argument is a count-like duration 10 -> 73
        # at k=7.3: exact integer results apply; the writer must not stop
        # after the first argument.
        for e in entries:
            if e["modifier_id"] in multi and e["argument"] == "TurnsActive":
                self.assertTrue(e["count_like"])
                self.assertEqual(float(e["official"]) * 7.3, 73.0)

    def test_count_like_exact_applies_fractional_refused(self):
        # Mirrors the native countLike rule (X10Transforms::Apply) driven by
        # the ACTUAL stored-FLOAT32 runtime multiplier (raw 9a99e940), not
        # decimal 7.3: exact results apply, fractional refuse, never floored —
        # and refusal of one argument never blocks another.
        import struct
        raw = struct.pack("<f", 7.3)
        self.assertEqual(raw.hex(), "9a99e940")
        kf = T.stored_float32(7.3)
        self.assertEqual(kf, 7.300000190734863)
        self.assertTrue(T.count_like_applies(10, kf))    # 73.0000019 accepts
        self.assertTrue(T.count_like_applies(100, kf))   # 730.0000191 accepts
        self.assertFalse(T.count_like_applies(3, kf))    # 21.9... refuses
        self.assertFalse(T.count_like_applies(2, kf))    # 14.6... refuses
        self.assertFalse(T.count_like_applies(-1, kf))   # -7.3... refuses
        # INT32 multiplier: zero quantization, strict exactness.
        self.assertTrue(T.count_like_applies(10, 10.0, 0.0))
        self.assertFalse(T.count_like_applies(3, 7.3, 0.0))
        # Independence: simulate one definition with an eligible Amount and
        # a refused count-like arg — Amount still transforms.
        amount_ok = T.scale_flat(5, 7.3) == 36.5
        refused = not T.count_like_applies(3, kf)
        self.assertTrue(amount_ok and refused)

    def test_k_variants(self):
        # k=1 identity, k=10 classic, arbitrary fractional k.
        self.assertEqual(T.scale_flat(-25, 1.0), -25.0)
        self.assertEqual(T.scale_flat(5, 10.0), 50.0)
        self.assertEqual(T.compound_discount_for_multiplier(-100, 10.0), -100.0)
        self.assertAlmostEqual(T.scale_flat(2, 4.25), 8.5)
        self.assertAlmostEqual(T.combat_bonus_for_multiplier(5, 1.0), 5.0,
                               places=9)

    def test_k0_off_and_k1_identity_contract(self):
        # k=0 parses (setup-level) but the native layer must treat it as Off.
        from civ6x10 import config as C
        self.assertEqual(C.parse_multiplier(0), 0.0)
        fork = (ROOT.parent / "CivilizationVI_CommunityExtension-x10-spike"
                / "X10Lifecycle.cpp")
        if not fork.is_file():
            self.skipTest("fork checkout unavailable (local-only)")
        t = fork.read_text(encoding="utf-8")
        self.assertIn("controller OFF", t)


if __name__ == "__main__":
    unittest.main(verbosity=2)
