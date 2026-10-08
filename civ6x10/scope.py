"""RELEASE_1 scoping: registry rows reachable from traits/policies/governments/pantheons."""
from __future__ import annotations

import csv
from pathlib import Path


def load_pairs(path: Path, type_col: str, arg_col: str) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    try:
        fh = open(path, encoding="utf-8", newline="")
    except FileNotFoundError:
        return pairs  # fixture dirs predate a module inventory
    with fh:
        for r in csv.DictReader(fh):
            mt, arg = (r.get(type_col) or "").strip(), (r.get(arg_col) or "").strip()
            if mt and arg:
                pairs.add((mt, arg))
    return pairs


def build_release1_scope(audit_data: Path) -> tuple[list[dict], dict]:
    """Return (scoped_registry_rows, stats).

    Scope key is (modifier_type, argument_name) present in any of the
    official inventories (traits, policies, governments, pantheons).
    Deterministic; counts derived, never hard-coded.
    """
    trait_pairs = load_pairs(audit_data / "official_traits.csv", "modifier_type", "argument_name")
    pol_pairs = load_pairs(audit_data / "policy_effects.csv", "modifier_type", "argument_name")
    gov_pairs = load_pairs(audit_data / "government_effects.csv", "modifier_type", "argument_name")
    pan_pairs = load_pairs(audit_data / "pantheon_effects.csv", "modifier_type", "argument_name")
    wanted = trait_pairs | pol_pairs | gov_pairs | pan_pairs

    scoped: list[dict] = []
    total = needs = 0
    with open(audit_data / "effect_semantics.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            total += 1
            if r.get("confidence") == "NEEDS_REVIEW":
                needs += 1
            if (r.get("modifier_type", "").strip(), r.get("argument_name", "").strip()) in wanted:
                r = dict(r)
                r["release1_source"] = "|".join(sorted(
                    s for s, ps in (("trait", trait_pairs), ("policy", pol_pairs),
                                    ("government", gov_pairs), ("pantheon", pan_pairs))
                    if (r["modifier_type"].strip(), r["argument_name"].strip()) in ps))
                scoped.append(r)
    scoped.sort(key=lambda r: (r["modifier_type"], r.get("effect_type", ""), r["argument_name"]))
    scoped_needs = sum(1 for r in scoped if r.get("confidence") == "NEEDS_REVIEW")
    stats = {
        "global_rows": total,
        "global_needs_review": needs,
        "release1_rows": len(scoped),
        "release1_needs_review": scoped_needs,
        "trait_pairs": len(trait_pairs),
        "policy_pairs": len(pol_pairs),
        "government_pairs": len(gov_pairs),
        "pantheon_pairs": len(pan_pairs),
    }
    return scoped, stats
