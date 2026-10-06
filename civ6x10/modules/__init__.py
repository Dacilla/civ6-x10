"""Per-module manifest builders (traits, policies, governments)."""
from __future__ import annotations

import csv
from pathlib import Path

from ..semantics import infer_family
from ..transforms import (
    canonical_x10_multiply,
    canonical_combat_bonus,
    repeated_probability,
    compound_discount_percent,
)


def _fmt(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s


# Numeric families whose values are indivisible counts. At integer
# multipliers scaling is exact; at fractional k the result is a design
# decision (DECISION_REQUIRED), never silent flooring.
INTEGER_COUNT_FAMILIES = frozenset({
    "CHARGES", "REPEAT_GRANT", "STRUCTURAL_SLOT", "DURATION",
})


def apply_transform(transform: str, official: str) -> tuple[str, str]:
    """Return (generated_value, status). Status is ok | refused | undecided."""
    if transform in ("unchanged",):
        return (official, "ok")
    if transform in ("refused_no_multiplier", "decision_required"):
        return ("", "refused" if "refused" in transform else "undecided")
    try:
        v = float(official)
    except (TypeError, ValueError):
        return ("", "undecided")
    if transform == "canonical_x10_multiply":
        return (_fmt(canonical_x10_multiply(v)), "ok")
    if transform == "canonical_combat_bonus":
        try:
            return (_fmt(canonical_combat_bonus(v)), "ok")
        except ValueError:
            return ("", "undecided")
    if transform == "repeated_probability":
        try:
            return (_fmt(repeated_probability(v)), "ok")
        except ValueError:
            return ("", "undecided")
    if transform == "compound_discount":
        try:
            return (_fmt(compound_discount_percent(v)), "ok")
        except ValueError:
            return ("", "undecided")
    return ("", "undecided")


def build_manifest(rows: list[dict], id_col: str, k: float = 10.0) -> list[dict]:
    """Attach semantic decisions + generated values to inventory rows.

    At fractional k, indivisible-count families (CHARGES, REPEAT_GRANT,
    STRUCTURAL_SLOT, DURATION) become DECISION_REQUIRED/undecided unless
    k*value is already integral — flooring is a provisional policy, never
    certified as canonical.
    """
    from ..transforms import (
        combat_bonus_for_multiplier,
        repeated_probability_for_multiplier,
        compound_discount_for_multiplier,
        scale_flat,
    )
    out: list[dict] = []
    for r in rows:
        vals = [r.get("official_value") or r.get("argument_value") or r.get("db_value") or ""]
        family, transform, confidence = infer_family(
            r.get("modifier_type", ""), r.get("effect_type", ""),
            r.get("argument_name", ""), vals)
        official = vals[0]
        if k == 10.0:
            generated, status = apply_transform(transform, official)
        else:
            generated, status = apply_dynamic(transform, family, official, k)
        if (family in INTEGER_COUNT_FAMILIES and status == "ok"
                and transform != "unchanged"):
            try:
                if abs(float(generated) - round(float(generated))) > 1e-9:
                    generated, status = "", "undecided"
            except (TypeError, ValueError):
                pass
        out.append({
            "object_id": r.get(id_col, ""),
            "modifier_id": r.get("modifier_id", ""),
            "modifier_type": r.get("modifier_type", ""),
            "effect_type": r.get("effect_type", ""),
            "argument_name": r.get("argument_name", ""),
            "official_value": official,
            "semantic_family": family,
            "transformation": transform,
            "generated_value": generated,
            "status": status,
            "confidence": confidence if status != "undecided" else "needs_human",
            "multiplier": k,
        })
    return out


def apply_dynamic(transform: str, family: str, official: str,
                  k: float) -> tuple[str, str]:
    """Arbitrary-k transform application. Same refusal discipline."""
    from ..transforms import (
        combat_bonus_for_multiplier,
        repeated_probability_for_multiplier,
        compound_discount_for_multiplier,
        scale_flat,
    )
    if transform in ("unchanged",):
        return (official, "ok")
    if transform in ("refused_no_multiplier", "decision_required"):
        return ("", "refused" if "refused" in transform else "undecided")
    try:
        v = float(official)
    except (TypeError, ValueError):
        return ("", "undecided")
    try:
        if transform == "canonical_x10_multiply":
            return (_fmt(scale_flat(v, k)), "ok")
        if transform == "canonical_combat_bonus":
            return (_fmt(combat_bonus_for_multiplier(v, k)), "ok")
        if transform == "repeated_probability":
            return (_fmt(repeated_probability_for_multiplier(v, k)), "ok")
        if transform == "compound_discount":
            return (_fmt(compound_discount_for_multiplier(v, k)), "ok")
    except ValueError:
        return ("", "undecided")
    return ("", "undecided")


def load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))
