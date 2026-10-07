"""Certification gate for the production native registry.

The auto classifier (semantics.py) emits only AUTO_RULE heuristics, which are
never production-eligible on their own. A manifest row enters the native
registry only when certify_row() returns certified=True, sourced from:

  sem-floor:<FAMILY>   agreement with data/local/effect_semantics.csv, or
  override:<name>       a curated entry in rules/certified_overrides.yml, or
  category:<FAMILY>     an allowlisted plain-magnitude family under a
                        MAGNITUDE_UNCLASSIFIED floor row.

Anything else resolves to excluded:<reason> (a valid, reported resolution) or
conflict:<reason> (unresolved: generation MUST fail).
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent / "rules" / "certified_overrides.yml"

# Floor families that can never enter production as masses, and their
# resolution when no curated override covers the row.
STRONG_EXCLUDE = {
    "GRANT_OBJECT": "excluded:grant-object",
    "SPATIAL_BUDGET": "excluded:spatial-budget",
    "DEFEATED_STRENGTH_SCALING": "excluded:defeated-strength-scaling",
    "BOOLEAN_UNLOCK": "excluded:boolean-unlock",
    "UNKNOWN": "excluded:unknown-semantics",
    "COUNT_OR_DURATION": "excluded:count-or-duration-unresolved",
    "MULTIPLICATIVE_FACTOR": "excluded:multiplicative-factor-unresolved",
    "MIXED_VALUE_DOMAIN": "excluded:mixed-value-domain",
}


def load_sem_floor(path: str | Path) -> dict:
    """Map (modifier_type, effect_type, argument_name) -> sem-floor row."""
    with open(path, encoding="utf-8", newline="") as fh:
        return {(r["modifier_type"], r["effect_type"], r["argument_name"]): r
                for r in csv.DictReader(fh)}


@lru_cache(maxsize=1)
def load_rules(path: str | Path = RULES_PATH) -> dict:
    import yaml
    return yaml.safe_load(open(path, encoding="utf-8"))


def _count_like(effect_type: str, argument_name: str, manifest_family: str,
                rules: dict) -> bool:
    if argument_name in (rules.get("count_like_args") or []):
        return True
    # Discrete-domain families are indivisible regardless of argument name.
    if manifest_family in ("DURATION", "CHARGES", "MOVEMENT", "RANGE",
                           "RADIUS"):
        return True
    for entry in rules.get("count_like_effects") or []:
        if entry["pattern"] in (effect_type or ""):
            if effect_type in (entry.get("exclude_effects") or []):
                continue
            return True
    return False


def certify_row(manifest_row: dict, sem_row: dict | None,
                rules: dict | None = None) -> dict:
    """Certify one manifest row. Never trusts heuristic confidence.

    Returns {certified, kind, count_like, source, resolution, sem_family,
    proposed_family}. certified=True only with kind set. resolution is
    'certified' | 'excluded:<reason>' | 'conflict:<reason>'.
    """
    rules = rules if rules is not None else load_rules()
    mt = (manifest_row.get("modifier_type") or "").strip()
    et = (manifest_row.get("effect_type") or "").strip()
    arg = (manifest_row.get("argument_name") or "").strip()
    proposed = manifest_row.get("semantic_family", "")
    base = {"sem_family": sem_row["semantic_family"] if sem_row else None,
            "proposed_family": proposed, "kind": None, "count_like": False,
            "source": "", "certified": False, "resolution": ""}

    excluded_effects = {e["effect"] for e in rules.get("excluded_effects") or []}
    if et in excluded_effects:
        return {**base, "resolution": "excluded:curated-effect",
                "source": "override:excluded-effect:" + et}

    if sem_row is None:
        return {**base, "resolution": "conflict:no-sem-floor-row",
                "source": "none"}

    sf = sem_row["semantic_family"]
    count_like = _count_like(et, arg, proposed, rules)

    if sf == "DISCOUNT":
        return {**base, "certified": True, "kind": "DISCOUNT",
                "count_like": False, "source": "sem-floor:DISCOUNT",
                "resolution": "certified"}
    if sf == "COMBAT_STRENGTH_BONUS":
        return {**base, "certified": True, "kind": "COMBAT",
                "count_like": False, "source": "sem-floor:COMBAT_STRENGTH_BONUS",
                "resolution": "certified"}
    if sf == "PROBABILITY":
        if proposed == "PROBABILITY":
            return {**base, "certified": True, "kind": "PROBABILITY",
                    "count_like": False, "source": "sem-floor:PROBABILITY",
                    "resolution": "certified"}
        return {**base, "resolution": "conflict:probability-claim-mismatch",
                "source": "none"}

    if sf == "MAGNITUDE_UNCLASSIFIED":
        # Discount/combat/probability claims need floor agreement, never
        # heuristics alone.
        if proposed in ("DISCOUNT", "COMBAT_STRENGTH_BONUS", "PROBABILITY"):
            return {**base,
                    "resolution": f"conflict:uncertified-{proposed}-claim",
                    "source": "none"}
        # Curated combat-point effects (floor is silent here).
        combat = {e["effect"]: e.get("rationale", "")
                  for e in rules.get("combat_effects") or []}
        if et in combat and arg == "Amount":
            return {**base, "certified": True, "kind": "COMBAT",
                    "count_like": False,
                    "source": "override:combat-points:" + et,
                    "resolution": "certified"}
        # Allowlisted plain-magnitude families.
        category = (rules.get("certified_category_families") or {})
        if proposed in category:
            return {**base, "certified": True,
                    "kind": category[proposed]["kind"],
                    "count_like": count_like,
                    "source": "category:" + proposed,
                    "resolution": "certified"}
        return {**base, "resolution": f"conflict:uncertified-family:{proposed}",
                "source": "none"}

    if sf == "MIXED_VALUE_DOMAIN":
        for entry in rules.get("mixed_overrides") or []:
            if entry["effect"] == et and entry.get("argument", arg) == arg:
                return {**base, "certified": True, "kind": entry["kind"],
                        "count_like": count_like and entry["kind"] == "ADDITIVE",
                        "source": "override:mixed:" + et,
                        "resolution": "certified"}
        return {**base, "resolution": STRONG_EXCLUDE[sf],
                "source": "sem-floor:" + sf}

    if sf in STRONG_EXCLUDE:
        return {**base, "resolution": STRONG_EXCLUDE[sf],
                "source": "sem-floor:" + sf}

    # SELECTOR and any future family: closed world, fail loud.
    return {**base, "resolution": f"conflict:unhandled-sem-family:{sf}",
            "source": "none"}
