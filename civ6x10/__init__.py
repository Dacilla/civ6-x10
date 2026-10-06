"""civ6x10: clean-room X10 generator (release 1)."""
from .transforms import (
    canonical_x10_multiply,
    canonical_combat_bonus,
    combat_bonus_for_multiplier,
    repeated_probability,
    repeated_probability_for_multiplier,
    compound_discount_percent,
    compound_discount_for_multiplier,
    scale_flat,
    scale_count,
)

__all__ = [
    "canonical_x10_multiply",
    "canonical_combat_bonus",
    "combat_bonus_for_multiplier",
    "repeated_probability",
    "repeated_probability_for_multiplier",
    "compound_discount_percent",
    "compound_discount_for_multiplier",
    "scale_flat",
    "scale_count",
]
