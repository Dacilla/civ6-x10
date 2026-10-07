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


if __name__ == "__main__":
    unittest.main(verbosity=2)
