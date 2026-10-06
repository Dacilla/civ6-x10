"""Spike tests: arbitrary multipliers, config parsing, reconstruction."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from civ6x10 import transforms as T
from civ6x10 import config as C


class TestArbitraryTransforms(unittest.TestCase):
    def test_k1_is_identity_flat(self):
        self.assertEqual(T.scale_flat(7, 1.0), 7.0)

    def test_arbitrary_flat(self):
        self.assertAlmostEqual(T.scale_flat(4, 7.3), 29.2)

    def test_k10_matches_canonical(self):
        for v in (1, 2, 5, 10, 0.5):
            self.assertAlmostEqual(T.combat_bonus_for_multiplier(v, 10.0),
                                   T.canonical_combat_bonus(v))
        for v in (1, 2, 5, 10, 25, 50):
            self.assertAlmostEqual(
                T.repeated_probability_for_multiplier(v / 100, 10.0),
                T.repeated_probability(v / 100))
            self.assertAlmostEqual(
                T.compound_discount_for_multiplier(-v, 10.0),
                T.compound_discount_percent(-v))

    def test_combat_k73(self):
        # b_7.3 for +5: 25*ln(7.3*(exp(0.2)-1)+1)
        import math
        expect = 25.0 * math.log(7.3 * (math.exp(5 / 25.0) - 1) + 1)
        self.assertAlmostEqual(T.combat_bonus_for_multiplier(5, 7.3), expect)
        self.assertGreater(T.combat_bonus_for_multiplier(5, 7.3), 5)
        self.assertLess(T.combat_bonus_for_multiplier(5, 7.3),
                        T.canonical_combat_bonus(5))

    def test_counts_have_no_canonical_floor(self):
        # Fractional scaling of indivisible counts is DECISION_REQUIRED:
        # there is deliberately no public helper that floors 3 x 2.5.
        self.assertFalse(hasattr(T, "scale_count"))
        from civ6x10.modules import build_manifest
        rows = build_manifest([{
            "trait_type": "T", "modifier_id": "M",
            "modifier_type": "MODIFIER_X", "effect_type": "EFFECT_X",
            "argument_name": "Charges", "official_value": "3",
        }], "trait_type", k=2.5)
        self.assertEqual(rows[0]["status"], "undecided")

    def test_invalid_k_rejected(self):
        for bad in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                T.scale_flat(5, bad)
            with self.assertRaises(ValueError):
                T.combat_bonus_for_multiplier(5, bad)


class TestConfigParsing(unittest.TestCase):
    def test_parse_ok(self):
        self.assertEqual(C.parse_multiplier("7.3"), 7.3)
        self.assertEqual(C.parse_multiplier(0), 0.0)
        self.assertEqual(C.parse_multiplier(100), 100.0)

    def test_parse_rejects(self):
        for bad in ("abc", None, -0.5, 101, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                C.parse_multiplier(bad)

    def test_module_config(self):
        out = C.parse_module_config({"traits": "7.3", "policies": 4.25})
        self.assertEqual(out, {"traits": 7.3, "policies": 4.25})
        with self.assertRaises(ValueError):
            C.parse_module_config({"nope": 2})

    def test_reconstruction_key_stable(self):
        k1 = C.reconstruction_key(module="policies", modifier_id="M",
                                  argument_name="Amount",
                                  official_value="5", multiplier=7.3)
        self.assertEqual(k1, C.reconstruction_key(
            module="policies", modifier_id="M", argument_name="Amount",
            official_value="5", multiplier=7.3))
        self.assertNotEqual(k1, C.reconstruction_key(
            module="policies", modifier_id="M", argument_name="Amount",
            official_value="5", multiplier=10.0))
        # identity includes target: same value+k on another modifier differs
        self.assertNotEqual(k1, C.reconstruction_key(
            module="policies", modifier_id="OTHER", argument_name="Amount",
            official_value="5", multiplier=7.3))

    def test_component_registry_data_driven(self):
        self.assertIn("traits", C.registered_components())
        C.register_component("wonders", "Wonders")
        self.assertIn("wonders", C.registered_components())
        out = C.parse_module_config({"wonders": 2})
        self.assertEqual(out, {"wonders": 2.0})
        with self.assertRaises(ValueError):
            C.register_component("bad name!")


class TestDoubleApplication(unittest.TestCase):
    def test_second_apply_is_noop_by_comparison(self):
        # save/reload rule: recompute official*k; write only on difference.
        official, k = "5", 7.3
        first = T.scale_flat(float(official), k)
        second = T.scale_flat(float(official), k)
        self.assertEqual(first, second)
        # a stored value already equal to expected needs no write
        self.assertTrue(str(first) == str(second))

    def test_no_relative_statements(self):
        from civ6x10.generator import statements_for_manifest
        rows = [{"object_id": "T", "modifier_id": "M", "modifier_type": "MT",
                 "effect_type": "E", "argument_name": "Amount",
                 "official_value": "36.5", "semantic_family": "FLAT_AMOUNT",
                 "transformation": "canonical_x10_multiply",
                 "generated_value": "36.5", "status": "ok",
                 "confidence": "reviewed"}]
        for s in statements_for_manifest(rows):
            self.assertNotIn("*", s.split("SET")[1].split("WHERE")[0].replace("'", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
