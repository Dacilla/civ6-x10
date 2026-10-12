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


MODE_FLOOR_PATH = (Path(__file__).resolve().parent / "rules"
                   / "mode_sem_floor.yml")


@lru_cache(maxsize=1)
def load_mode_floor(path: str | Path = MODE_FLOOR_PATH) -> dict:
    """Supplemental semantic floor for game-mode-defined data.

    `effect_semantics.csv` is derived from the clean official Gameplay
    database, so DynamicModifiers that only exist inside a game-mode
    UpdateDatabase payload have no floor row there. Without this file those
    tuples hit `conflict:no-sem-floor-row` and fail closed (correct).

    This file is deliberately narrow: it lists EXACTLY the audited tuples
    that Phase 4A.1 certified from the shipped mode payload, each carrying
    the modinfo action/file/SHA-256 provenance. It is NOT a generic DLC or
    game-mode exemption - an unlisted tuple still fails closed.
    """
    import yaml
    if not Path(path).is_file():
        return {}
    doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
    out = {}
    for e in doc.get("mode_sem_floor") or []:
        key = ((e.get("modifier_type") or "").strip(),
               (e.get("effect_type") or "").strip(),
               (e.get("argument") or "").strip())
        out[key] = e
    return out


def mode_floor_for(modifier_type: str, effect_type: str, argument: str,
                   path: str | Path = MODE_FLOOR_PATH) -> dict | None:
    return load_mode_floor(path).get(
        (modifier_type.strip(), effect_type.strip(), argument.strip()))


def _engine_integral_match(modifier_type: str, effect_type: str,
                           argument_name: str, rules: dict) -> dict | None:
    """Matching engine-integral override entry, if any.

    Scoped by (modifier_type, effect_type, argument_name) so a curated entry
    cannot silently widen across every carrier of an effect.
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


def _strong_family_override(modifier_type: str, effect_type: str,
                               argument_name: str, proposed_family: str,
                               sem_family: str | None,
                               rules: dict) -> dict | None:
    """Exact strong-family override for one positively-reviewed argument.

    Exists for the narrow case where a coarse semantic-floor heuristic
    classified a whole EffectType family as a strong exclusion, but a
    particular numeric argument was subsequently reviewed and proven to be
    a plain magnitude. Returns None when no entry names this
    (effect, argument) tuple.

    When an entry DOES name the tuple, every field must agree exactly or
    the row fails closed: a floor-family drift, a different proposed
    family, or any sibling argument never certifies through this path.
    `excluded_effects` is consulted before this function is ever reached,
    so a deliberately excluded EffectType cannot be re-admitted here.

    Entries may carry `count_like: true` for indivisible-count magnitudes
    (Phase 8B discrete grants / resource flows): the runtime integral
    gate then applies. Default false preserves all pre-8B behavior.
    """
    for entry in rules.get("strong_family_overrides") or []:
        if entry.get("effect") != effect_type:
            continue
        if entry.get("argument") != argument_name:
            continue
        if entry.get("expected_floor_family") != sem_family:
            return {"certified": False,
                    "resolution": "conflict:strong-override-floor-drift:"
                                  + str(sem_family)}
        if entry.get("proposed_family") != proposed_family:
            return {"certified": False,
                    "resolution": "conflict:strong-override-family-mismatch:"
                                  + str(proposed_family)}
        return {"certified": True, "kind": entry.get("kind"),
                "count_like": bool(entry.get("count_like", False)),
                "resolution": "certified"}
    return None


def _vector_override(effect_type: str, argument_name: str,
                     official_value: str, rules: dict) -> dict | None:
    """Certification for explicitly-reviewed vector-valued arguments.

    Vector (comma-list) magnitudes never reach the scalar floor logic:
    the official value is non-numeric by design. Each entry names one
    EffectType whose positional numeric lists were reviewed (Phase 8B):
    every element must parse as finite, the paired selector list is
    untouched, malformed/mixed lists fail closed. Unlisted effects fall
    through untouched (scalar path excludes them as non-numeric).
    """
    from .transforms import parse_vector
    for entry in rules.get("vector_overrides") or []:
        if entry.get("effect") != effect_type:
            continue
        if entry.get("argument", "Amount") != argument_name:
            continue
        if parse_vector(official_value or "") is None:
            return {"certified": False,
                    "resolution": "conflict:vector-malformed:" + effect_type}
        return {"certified": True, "kind": entry.get("kind", "VECTOR"),
                "source": "curated-effect:vector:" + effect_type,
                "resolution": "certified"}
    return None


def _transformation_override(manifest_row: dict, rules: dict,
                             key: str) -> dict | None:
    """Certification for explicit 8B pipeline transformations.

    `key` names a rules list (`delta_effects`, `repeat_effects`); each
    entry names one reviewed (effect, argument) tuple plus its native
    kind. Anything unlisted falls through untouched.
    """
    et = (manifest_row.get("effect_type") or "").strip()
    arg = (manifest_row.get("argument_name") or "").strip()
    for entry in rules.get(key) or []:
        if entry.get("effect") != et:
            continue
        if entry.get("argument", "Amount") != arg:
            continue
        return {"certified": True, "kind": entry.get("kind"),
                "count_like": bool(entry.get("count_like", True)),
                "source": "curated-effect:" + key + ":" + et,
                "resolution": "certified"}
    return None


def _effect_arg_override(modifier_type: str, effect_type: str,
                         argument_name: str, rules: dict) -> dict | None:
    """Curated (effect, argument[, modifier_type]) certification.

    For carriers with no semantic-floor row at all (promotion/ability and
    game-mode carriers absent from the clean-DB floor): each entry is
    positive human evidence with its own rationale, the same trust class
    as combat_effects. Excluded EffectTypes keep precedence (checked by
    the caller before the floor logic); unlisted tuples fall through to
    the ordinary conflict path.
    """
    for entry in rules.get("certified_effect_args") or []:
        if entry.get("effect") != effect_type:
            continue
        if entry.get("argument", "Amount") != argument_name:
            continue
        if entry.get("modifier_type") and \
                entry["modifier_type"] != modifier_type:
            continue
        return {"certified": True, "kind": entry.get("kind", "ADDITIVE"),
                "family": entry.get("family", "FLAT_AMOUNT"),
                "count_like": bool(entry.get("count_like", False)),
                "source": "curated-effect:effect-arg:" + effect_type,
                "resolution": "certified"}
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
        # Game-mode-defined data: the clean-DB floor has no row. Consult the
        # narrow audited supplemental floor (provenance-checked) before
        # failing closed. Unlisted tuples still fail closed.
        mode = mode_floor_for(mt, et, arg)
        if mode is None:
            # Promotion/ability/mode carriers: curated per-effect evidence
            # (Phase 8B). Anything unlisted still fails closed below.
            curated = _effect_arg_override(mt, et, arg, rules)
            if curated is not None:
                return {**base, "certified": True, "kind": curated["kind"],
                        "count_like": curated["count_like"],
                        "source": curated["source"],
                        "resolution": "certified"}
            return {**base, "resolution": "conflict:no-sem-floor-row",
                    "source": "none"}
        sem_row = {"semantic_family": mode.get("semantic_family"),
                   "confidence": mode.get("confidence"),
                   "evidence": mode.get("rationale"),
                   "mode_provenance": mode.get("provenance")}

    sf = sem_row["semantic_family"]
    floor_conf = (sem_row.get("confidence") or "").strip()
    mode_provenance = sem_row.get("mode_provenance")
    proven = floor_conf in ("FORMULA_DERIVED", "HUMAN_CERTIFIED", "CERTIFIED")
    count_like = _count_like(et, arg, proposed, rules)

    # Exact strong-family override (checked after excluded_effects and floor
    # resolution, before all ordinary family logic): a positively-reviewed
    # numeric argument on a coarsely-excluded family. Any mismatch fails
    # closed; non-listed tuples fall through untouched.
    strong = _strong_family_override(mt, et, arg, proposed, sf, rules)
    if strong is not None:
        if not strong["certified"]:
            return {**base, "resolution": strong["resolution"],
                    "source": "none"}
        return {**base, "certified": True, "kind": strong["kind"],
                "count_like": bool(strong.get("count_like", False)),
                "source": "curated-effect:strong-family:" + et,
                "resolution": "certified"}

    # Curated per-effect evidence for heuristic-only floors (Phase 8B):
    # an AUTO_PATTERN / NEEDS_REVIEW floor row is never proof by itself,
    # but a certified_effect_args entry naming this exact tuple is positive
    # human evidence (same trust class as combat_effects). Proven floors
    # never reach this branch, so pre-8B certifications are untouched.
    if not proven:
        curated = _effect_arg_override(mt, et, arg, rules)
        if curated is not None:
            return {**base, "certified": True, "kind": curated["kind"],
                    "count_like": curated["count_like"],
                    "source": curated["source"],
                    "resolution": "certified"}

    # Explicit 8B pipeline transformations (checked after excluded_effects;
    # each consults its own reviewed allowlist; unlisted tuples fall through
    # to the ordinary floor logic, which excludes/fails them as before).
    transformation = (manifest_row.get("transformation") or "").strip()
    if transformation == "vector_multiply":
        vectored = _vector_override(
            et, arg, manifest_row.get("official_value") or "", rules)
        if vectored is not None:
            if not vectored["certified"]:
                return {**base, "resolution": vectored["resolution"],
                        "source": "none"}
            return {**base, "certified": True, "kind": vectored["kind"],
                    "count_like": False,
                    "source": vectored["source"],
                    "resolution": "certified"}
    if transformation in ("bridge_delta", "repeat_count"):
        key = "delta_effects" if transformation == "bridge_delta" \
            else "repeat_effects"
        pipelined = _transformation_override(manifest_row, rules, key)
        if pipelined is not None:
            return {**base, "certified": True, "kind": pipelined["kind"],
                    "count_like": pipelined["count_like"],
                    "source": pipelined["source"],
                    "resolution": "certified"}

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
        # Engine-representability override (Phase 3F/3G/4B): the effect
        # applies its magnitude integrally, so the runtime integral gate is
        # mandatory. Semantics stay as allowlisted below.
        eng = _engine_integral_match(mt, et, arg, rules)
        if eng is not None:
            category = (rules.get("certified_category_families") or {})
            if proposed in category:
                fam_kind = category[proposed]["kind"]
                return {**base, "certified": True,
                        "kind": fam_kind,
                        "count_like": True,
                        "source": "curated-effect:engine-integral:" + et,
                        "resolution": "certified"}
            return {**base,
                    "resolution": "conflict:engine-integral-uncertified-family:"
                                  + proposed,
                    "source": "none"}
        # Curated combat-point effects are checked FIRST: an explicitly
        # curated combat effect is positive evidence, so a proposed
        # COMBAT_STRENGTH_BONUS family must not be rejected as a heuristic
        # claim before the curated table is consulted. Uncurated heuristic
        # combat/discount/probability claims still fail closed below.
        combat = {e["effect"]: e.get("rationale", "")
                  for e in rules.get("combat_effects") or []}
        if et in combat and arg == "Amount":
            return {**base, "certified": True, "kind": "COMBAT",
                    "count_like": False,
                    "source": "curated-effect:combat-points:" + et,
                    "resolution": "certified"}
        # Discount/combat/probability claims need floor agreement, never
        # heuristics alone.
        if proposed in ("DISCOUNT", "COMBAT_STRENGTH_BONUS", "PROBABILITY"):
            return {**base,
                    "resolution": f"conflict:uncertified-{proposed}-claim",
                    "source": "none"}
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
