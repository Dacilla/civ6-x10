"""Canonical X10 mathematics (independently implemented from audit evidence).

All functions are pure and deterministic. They encode *semantic* equivalence,
not balance adjustments.
"""
from __future__ import annotations

import math


def canonical_x10_multiply(value: float) -> float:
    """Additive magnitudes: ten times the semantic effect."""
    return value * 10.0


def canonical_combat_bonus(vanilla_bonus: float) -> float:
    """Combat-strength bonus preserving tenfold damage (audit §9)."""
    return combat_bonus_for_multiplier(vanilla_bonus, 10.0)


def combat_bonus_for_multiplier(vanilla_bonus: float, k: float) -> float:
    """Generalized combat transform: b_k = 25*ln(k*(exp(b/25)-1)+1).

    k=10 reproduces canonical_combat_bonus. Known tenfold: +1 -> +9,
    +2 -> +15, +5 -> +29, +10 -> +44.
    """
    _require_positive_multiplier(k)
    inner = k * math.exp(vanilla_bonus / 25.0) - (k - 1.0)
    if inner <= 0:
        raise ValueError(f"no meaningful {k}x tenfold for bonus {vanilla_bonus}")
    return 25.0 * math.log(inner)


def repeated_probability(p: float) -> float:
    """Ten independent trials: p10 = 1 - (1 - p)^10."""
    return repeated_probability_for_multiplier(p, 10.0)


def repeated_probability_for_multiplier(p: float, k: float) -> float:
    """Generalized: p_k = 1 - (1-p)^k. Fraction or percent in, same unit out."""
    _require_positive_multiplier(k)
    unit_is_percent = abs(p) > 1.0
    frac = p / 100.0 if unit_is_percent else p
    if not 0.0 <= frac <= 1.0:
        raise ValueError(f"probability out of range: {p}")
    out = 1.0 - (1.0 - frac) ** k
    return out * 100.0 if unit_is_percent else out


def compound_discount_percent(discount_percent: float) -> float:
    """Percentage discount applied ten times (repeated-effect equivalence)."""
    return compound_discount_for_multiplier(discount_percent, 10.0)


def compound_discount_for_multiplier(discount_percent: float, k: float) -> float:
    """Generalized: d_k = -(1-(1-d)^k)*100 for signed-percent input."""
    _require_positive_multiplier(k)
    d = abs(discount_percent) / 100.0
    if not 0.0 <= d <= 1.0:
        raise ValueError(f"discount out of range: {discount_percent}")
    out = (1.0 - (1.0 - d) ** k) * 100.0
    return -out if discount_percent < 0 else out


def scale_flat(value: float, k: float) -> float:
    """Additive magnitudes at arbitrary multiplier k."""
    _require_positive_multiplier(k)
    return value * k


def _require_positive_multiplier(k: float) -> None:
    if not math.isfinite(k) or k < 0:
        raise ValueError(f"multiplier must be >= 0 and finite: {k}")
