"""Certification gate for the production native registry.

The auto classifier (semantics.py) emits only AUTO_RULE heuristics, which are
never production-eligible on their own. A manifest row enters the native
registry only when certify_row() returns certified=True, sourced from:

  sem-floor:<FAMILY>   agreement with data/local/effect_semantics.csv, or
  curated ...         a curated entry in rules/certified_overrides.yml, or
  curated-category    an allowlisted plain-magnitude family under a
                        MAGNITUDE_UNCLASSIFIED floor row.

Trust policy: FORMULA_DERIVED (or explicitly human-certified) floor rows may
directly certify a special transform. AUTO_PATTERN / NEEDS_REVIEW floor rows
may inform the audit but can NEVER certify COMBAT / DISCOUNT / PROBABILITY
without a curated override entry carrying rationale. Strong exclusions stay
conservative even when heuristic (false exclusion is safe); special
transforms require positive proof.

Source vocabulary (tight reporting):
  formula-derived:<FAMILY>  FORMULA_DERIVED floor row (positive proof)
  curated-effect:<what>     curated override entry (discount/combat/mixed/excluded)
  curated-category:<FAMILY> allowlisted plain-magnitude category
No heuristic-floor-only row ever receives COMBAT / DISCOUNT / PROBABILITY.
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


def _engine_integral_match(modifier_type: str, effect_type: str,
                           argument_name: str, rules: dict) -> dict | None:
    """Return the matching engine-integral override entry, if any.

    Scoped by (modifier_type, effect, argument) so a curated entry cannot
    silently widen across every carrier of an effect.
    """
    for entry in rules.get("engine_integral_effects") or []:
        if entry.get("effect") != effect_type:
            continue
        if entry.get("modifier_type") and entry["modifier_type"] != modifier_type:
            continue
        if entry.get("argument") and entry["argument"] != argument_name:
            continue
        return entry
    return None


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
                "source": "curated-effect:excluded-effect:" + et}

    if sem_row is None:
        return {**base, "resolution": "conflict:no-sem-floor-row",
                "source": "none"}

    sf = sem_row["semantic_family"]
    floor_conf = (sem_row.get("confidence") or "").strip()
    proven = floor_conf in ("FORMULA_DERIVED", "HUMAN_CERTIFIED", "CERTIFIED")
    count_like = _count_like(et, arg, proposed, rules)

    if sf == "DISCOUNT":
        # AUTO_PATTERN / NEEDS_REVIEW floor rows cannot certify a special
        # transform: every release-slice discount effect needs a curated
        # classification (percent vs flat vs excluded).
        table = {e["effect"]: e for e in rules.get("discount_effects") or []}
        entry = table.get(et)
        if entry is None:
            return {**base, "resolution": "conflict:unclassified-discount-effect",
                    "source": "none"}
        if entry.get("semantics") == "PERCENT_DISCOUNT":
            return {**base, "certified": True, "kind": "DISCOUNT",
                    "count_like": False,
                    "source": "curated-effect:discount:" + et,
                    "resolution": "certified"}
        if entry.get("semantics") == "FLAT_COST_REDUCTION":
            return {**base, "certified": True, "kind": "ADDITIVE",
                    "count_like": False,
                    "source": "curated-effect:flat-cost:" + et,
                    "resolution": "certified"}
        return {**base, "resolution": "excluded:curated-discount-effect",
                "source": "curated-effect:discount-excluded:" + et}
    if sf == "COMBAT_STRENGTH_BONUS":
        if proven:
            return {**base, "certified": True, "kind": "COMBAT",
                    "count_like": False,
                    "source": "formula-derived:COMBAT_STRENGTH_BONUS",
                    "resolution": "certified"}
        combat = {e["effect"]: e.get("rationale", "")
                  for e in rules.get("combat_effects") or []}
        if et in combat and arg == "Amount":
            return {**base, "certified": True, "kind": "COMBAT",
                    "count_like": False,
                    "source": "curated-effect:combat-points:" + et,
                    "resolution": "certified"}
        return {**base, "resolution": "conflict:uncertified-combat-claim",
                "source": "none"}
    if sf == "PROBABILITY":
        if proven and proposed == "PROBABILITY":
            return {**base, "certified": True, "kind": "PROBABILITY",
                    "count_like": False,
                    "source": "formula-derived:PROBABILITY",
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
                    "source": "curated-effect:combat-points:" + et,
                    "resolution": "certified"}
        # Curated flat-cost effects (floor says discount; audit says flat).
        flat = {e["effect"] for e in rules.get("discount_effects") or []
                if e.get("semantics") == "FLAT_COST_REDUCTION"}
        if et in flat:
            return {**base, "certified": True, "kind": "ADDITIVE",
                    "count_like": False,
                    "source": "curated-effect:flat-cost:" + et,
                    "resolution": "certified"}
        # Engine-representability override (Phase 3F): the effect applies
        # Amount as an integer. Semantics stay as certified (same family and
        # kind), but the runtime integral gate becomes mandatory so a
        # fractional result is refused instead of engine-truncated.
        eng = _engine_integral_match(mt, et, arg, rules)
        if eng is not None:
            category = (rules.get("certified_category_families") or {})
            if proposed in category:
                return {**base, "certified": True,
                        "kind": category[proposed]["kind"],
                        "count_like": True,
                        "source": "curated-effect:engine-integral:" + et,
                        "resolution": "certified"}
            return {**base,
                    "resolution": "conflict:engine-integral-uncertified-family:"
                                  + proposed,
                    "source": "none"}
        # Allowlisted plain-magnitude families.
        category = (rules.get("certified_category_families") or {})
        if proposed in category:
            return {**base, "certified": True,
                    "kind": category[proposed]["kind"],
                    "count_like": count_like,
                    "source": "curated-category:" + proposed,
                    "resolution": "certified"}
        return {**base, "resolution": f"conflict:uncertified-family:{proposed}",
                "source": "none"}

    if sf == "MIXED_VALUE_DOMAIN":
        for entry in rules.get("mixed_overrides") or []:
            if entry["effect"] == et and entry.get("argument", arg) == arg:
                return {**base, "certified": True, "kind": entry["kind"],
                        "count_like": count_like and entry["kind"] == "ADDITIVE",
                        "source": "curated-effect:mixed:" + et,
                        "resolution": "certified"}
        return {**base, "resolution": STRONG_EXCLUDE[sf],
                "source": "sem-floor:" + sf}

    if sf in STRONG_EXCLUDE:
        return {**base, "resolution": STRONG_EXCLUDE[sf],
                "source": "sem-floor:" + sf}

    # SELECTOR and any future family: closed world, fail loud.
    return {**base, "resolution": f"conflict:unhandled-sem-family:{sf}",
            "source": "none"}
