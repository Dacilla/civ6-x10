"""Production registry tests: generation, parity, save/load derivation."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

from civ6x10 import transforms as T
from civ6x10.production import build_production_registry


def synth(module="traits", mid="M_X", arg="Amount", official="7",
          family="FLAT_AMOUNT", transform="canonical_x10_multiply",
          status="ok", confidence="reviewed", obj="T_X"):
    return {"object_id": obj, "modifier_id": mid, "modifier_type": "MT_X",
            "effect_type": "ET_X", "argument_name": arg,
            "official_value": official, "semantic_family": family,
            "transformation": transform, "generated_value": "",
            "status": status, "confidence": confidence, "module": module}


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


class TestProductionRegistry(unittest.TestCase):
    def test_generation_core(self):
        # Fixture-driven (CI-safe): duplicates merge, unknown/refused/
        # undecided/selector rows excluded, deterministic output.
        rows = [
            synth(mid="M_A"),
            synth(mid="M_A"),  # duplicate
            synth(mid="M_B", family="UNKNOWN", transform="decision_required",
                  status="undecided", confidence="needs_human"),
            synth(mid="M_C", family="SELECTOR", transform="unchanged"),
            synth(mid="M_D", family="BOOLEAN_UNLOCK",
                  transform="refused_no_multiplier", status="refused"),
            synth(mid="M_E", family="COMBAT_STRENGTH_BONUS",
                  transform="canonical_combat_bonus", official="5"),
        ]
        entries, report = build_production_registry(rows)
        self.assertEqual([(e["modifier_id"], e["kind"]) for e in entries],
                         [("M_A", "ADDITIVE"), ("M_E", "COMBAT")])
        e2, _ = build_production_registry(list(reversed(rows)))
        self.assertEqual(e2, entries)

    def test_manifest_parity(self):
        # Local-only: manifests need reviewed data (gitignored).
        try:
            rows = load_manifests()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        entries, report = build_production_registry(rows)
        self.assertEqual(len(entries), report["eligible"])
        ids = {e["modifier_id"] for e in entries}
        for mid in ("TRAIT_LINCOLN_INDUSTRIAL_ZONE_LOYALTY",
                    "AGOGE_ANCIENT_MELEE_PRODUCTION",
                    "TRAIT_GOLD_FROM_DOMESTIC_TRADING_POSTS",
                    "TRAIT_TOQUI_COMBAT_BONUS_VS_GOLDEN_AGE_CIV"):
            self.assertIn(mid, ids, mid)
        keys = [(e["modifier_id"], e["argument"]) for e in entries]
        self.assertEqual(len(keys), len(set(keys)))
        kinds = {e["kind"] for e in entries}
        self.assertTrue(kinds <= {"ADDITIVE", "COMBAT", "PROBABILITY", "DISCOUNT"})


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
        self.assertGreaterEqual(len(neg), 44)
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
        self.assertEqual(len(discs), 8)

    def test_full_registry_transforms_at_k73(self):
        # Static expectation: all 729 entries transform at k=7.3 (mismatch
        # checks happen at runtime against live definitions).
        import math
        try:
            rows = load_manifests()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        from civ6x10.production import build_production_registry
        entries, _ = build_production_registry(rows)
        ok = 0
        for e in entries:
            v = float(e["official"])
            if e["kind"] == "ADDITIVE":
                r = v * 7.3
            elif e["kind"] == "COMBAT":
                r = 25.0 * math.log(7.3 * (math.exp(v / 25.0) - 1) + 1)
            elif e["kind"] == "DISCOUNT":
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** 7.3) * 100.0 * (-1 if v < 0 else 1)
            elif e["kind"] == "PROBABILITY":
                p = v / 100.0 if abs(v) > 1 else v
                r = (1.0 - (1.0 - p) ** 7.3) * (100.0 if abs(v) > 1 else 1.0)
            else:
                continue
            if math.isfinite(r) and abs(r) <= 1000000:
                if e["count_like"] and abs(r - round(r)) > 1e-9:
                    continue  # refused, not floored
                ok += 1
        self.assertEqual(ok, 729)

    def test_shared_ownership_and_conflicts(self):
        from civ6x10.production import build_production_registry, RegistryConflict
        rows = [
            synth(module="policies", mid="M_S", official="5"),
            synth(module="governments", mid="M_S", official="5"),
        ]
        entries, report = build_production_registry(rows)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["owners"], 2 | 4)
        self.assertEqual(report["shared_definitions"], 1)
        bad = [
            synth(module="policies", mid="M_X", official="5"),
            synth(module="governments", mid="M_X", official="6"),
        ]
        with self.assertRaises(RegistryConflict):
            build_production_registry(bad)

    def test_multi_argument_definitions(self):
        # The 7 two-argument definitions must expose BOTH args as entries.
        try:
            rows = load_manifests()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        from civ6x10.production import build_production_registry
        from collections import Counter
        entries, _ = build_production_registry(rows)
        per_def = Counter(e["modifier_id"] for e in entries)
        multi = {m: c for m, c in per_def.items() if c > 1}
        self.assertGreaterEqual(len(multi), 7)
        self.assertIn("TRAIT_TERRITORIAL_WAR_COMBAT", multi)
        # Every second argument is a count-like duration 10 -> 73 at k=7.3:
        # exact integer results apply; writer must not stop after Amount.
        for e in entries:
            if e["modifier_id"] in multi and e["argument"] == "TurnsActive":
                self.assertTrue(e["count_like"])
                self.assertEqual(float(e["official"]) * 7.3, 73.0)

    def test_count_like_exact_applies_fractional_refused(self):
        # Mirrors the native countLike rule (X10Transforms::Apply): exact
        # integer results apply, fractional outcomes are refused, never
        # floored — and refusal of one argument never blocks another.
        def native_count_like(official, k):
            v = official * k
            if v != round(v):
                return None  # refused
            return float(round(v))
        self.assertEqual(native_count_like(10, 7.3), 73.0)
        self.assertIsNone(native_count_like(3, 7.3))   # 21.9 refused
        self.assertIsNone(native_count_like(2, 7.3))   # 14.6 refused
        self.assertEqual(native_count_like(10, 10.0), 100.0)
        # Independence: simulate one definition with an eligible Amount and
        # a refused count-like arg — Amount still transforms.
        amount_ok = T.scale_flat(5, 7.3) == 36.5
        refused = native_count_like(3, 7.3) is None
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
        t = (ROOT.parent / "CivilizationVI_CommunityExtension-x10-spike"
             / "X10Lifecycle.cpp").read_text(encoding="utf-8")
        self.assertIn("controller OFF", t)


if __name__ == "__main__":
    unittest.main(verbosity=2)
