"""Phase 8B Playtest-1 closure regression guards.

These lock the four known-correct results from §2 so coverage expansion
cannot silently break them:

A. Monument to the Gods: vanilla +15% wonder production -> +150% at x10
   (additive magnitude; the city headline number never showed it).
B. Discipline: vanilla +5 vs Barbarians -> ~+29 via the nonlinear combat
   transform at x10 (never naive +50).
C. Eiffel Tower: vanilla +2 Appeal -> +20 at integer x10; Custom 7.3
   (2 x 7.3 = 14.6) is deliberately refused (whole-valued Appeal).
D. Custom 7.3 count-like refusal semantics (exact-integral or nothing).

Plus new-kind math guards (vector / bridge-delta / repeat-count).
"""
from __future__ import annotations

import unittest

from civ6x10 import transforms as T


class TestKnownCorrectMagnitudes(unittest.TestCase):
    def test_monument_to_the_gods_x10(self):
        # A: +15% Ancient/Classical Wonder production scales additively.
        self.assertEqual(T.scale_flat(15.0, 10.0), 150.0)

    def test_discipline_nonlinear_combat(self):
        # B: +5 combat strength vs Barbarians -> ~+29, NOT +50.
        got = T.combat_bonus_for_multiplier(5.0, 10.0)
        self.assertAlmostEqual(got, 29.0, delta=1.0)
        self.assertLess(got, 50.0)

    def test_eiffel_integer_x10(self):
        # C: +2 Appeal -> +20 at integer x10.
        self.assertEqual(T.scale_flat(2.0, 10.0), 20.0)

    def test_eiffel_custom_73_refused(self):
        # C: 2 x 7.3 = 14.6 is not whole -> refused for Appeal.
        k = T.stored_float32(7.3)
        self.assertFalse(T.count_like_applies(2.0, k))

    def test_custom_73_exact_integral_accepted(self):
        # D: 10 x 7.3 = 73 is exact -> a count-like effect may apply it.
        k = T.stored_float32(7.3)
        self.assertTrue(T.count_like_applies(10.0, k))

    def test_custom_73_genuine_fraction_refused(self):
        # D: 6 x 7.3 = 43.8 (Jebel Barkal) refuses, remaining 6.
        k = T.stored_float32(7.3)
        self.assertFalse(T.count_like_applies(6.0, k))

    def test_custom_25_exact_half_accepted(self):
        # D: official 2 x Custom 2.5 = exact 5 is valid.
        k = T.stored_float32(2.5)
        self.assertTrue(T.count_like_applies(2.0, k))


class TestVectorMath(unittest.TestCase):
    def test_petra_x10(self):
        # Petra Amount 2,2,1 at x10 -> 20,20,10 (order preserved).
        self.assertEqual(T.vector_multiply("2,2,1", 10.0), "20,20,10")

    def test_halicarnassus_x10(self):
        self.assertEqual(T.vector_multiply("1,1,1", 10.0), "10,10,10")

    def test_spaced_vector(self):
        self.assertEqual(T.vector_multiply("1, 1", 10.0), "10,10")

    def test_malformed_vectors_fail(self):
        for bad in ("", "10", "2,,1", "2,ERA_INFO,1", "a,b", "1,2,",
                    "inf,1", "nan,2"):
            with self.assertRaises(ValueError, msg=bad):
                T.vector_multiply(bad, 10.0)

    def test_scalar_is_not_vector(self):
        self.assertIsNone(T.parse_vector("10"))
        self.assertIsNone(T.parse_vector(""))

    def test_six_element_vector(self):
        self.assertEqual(
            T.vector_multiply("10,10,10,10,10,10", 10.0),
            "100,100,100,100,100,100")


class TestBridgeDeltaMath(unittest.TestCase):
    def test_delta_x10(self):
        # Direct keeps V=2 (UI truthful); helper adds 2*9=18; total 20.
        self.assertEqual(T.bridge_delta(2.0, 10.0), 18.0)

    def test_delta_k1_inert(self):
        self.assertEqual(T.bridge_delta(2.0, 1.0), 0.0)

    def test_delta_k0_never_reaches_transform(self):
        # k=0 (Off) disarms the native writer upstream, so a delta is
        # never computed for it. Raw math documented here only:
        self.assertEqual(T.bridge_delta(2.0, 0.0), -2.0)

    def test_delta_invalid_k_refused(self):
        with self.assertRaises(ValueError):
            T.bridge_delta(2.0, -1.0)


class TestRepeatCountMath(unittest.TestCase):
    def test_x10_nine_copies(self):
        self.assertEqual(T.repeat_copies(10.0, 0.0), 9)

    def test_fractional_refused(self):
        k = T.stored_float32(7.3)
        self.assertIsNone(T.repeat_copies(k))

    def test_k1_zero_copies(self):
        self.assertEqual(T.repeat_copies(1.0, 0.0), 0)

    def test_over_maximum_refused(self):
        self.assertIsNone(T.repeat_copies(101.0, 0.0))
        self.assertEqual(T.repeat_copies(100.0, 0.0), 99)


if __name__ == "__main__":
    unittest.main(verbosity=2)
