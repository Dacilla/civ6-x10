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


def stored_float32(k: float) -> float:
    """Widen the stored FLOAT32 encoding of k, exactly as the native
    config reader delivers it (e.g. setup 7.3 -> 7.300000190734863)."""
    import struct
    return struct.unpack("<f", struct.pack("<f", k))[0]


def float_quantization_error(k_float: float) -> float:
    """Half-ULP source error of a stored float multiplier (0 for integrals
    exactly representable paths is NOT assumed: callers pass INT32 k with
    error 0 explicitly). Stepped in FLOAT32 precision to mirror nextafterf.
    """
    import struct
    bits = struct.unpack("<I", struct.pack("<f", k_float))[0]
    up = struct.unpack("<f", struct.pack("<I", bits + 1))[0]
    down = struct.unpack("<f", struct.pack("<I", bits - 1))[0]
    return max(up - k_float, k_float - down) / 2.0


def count_like_applies(official: float, k_float: float,
                       k_err: float | None = None) -> bool:
    """FLOAT32-quantization-aware integrality (mirrors X10Transforms::Apply).

    Exact-integer results accept (rounding absorbs only propagated source
    error); genuine fractions refuse. Never a coarse epsilon.
    """
    import math
    if k_err is None:
        k_err = float_quantization_error(k_float)
    v = official * k_float
    r = round(v)
    tol = abs(official) * k_err + 1e-9 * max(1.0, abs(v))
    return tol < 0.5 and abs(v - r) <= tol


def _require_positive_multiplier(k: float) -> None:
    if not math.isfinite(k) or k < 0:
        raise ValueError(f"multiplier must be >= 0 and finite: {k}")
