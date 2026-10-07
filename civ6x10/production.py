"""Production registry generation for the native controller (release 1).

Reads the reviewed per-object manifests, selects native-eligible entries,
dedupes them, and emits a C++ registry consumed by the CE fork. Deterministic.
No hand-maintained modifier IDs: every entry traces to a manifest row.
"""
from __future__ import annotations

from collections import Counter

# manifest transformation -> native TransformKind
TRANSFORM_KIND = {
    "canonical_x10_multiply": "ADDITIVE",
    "canonical_combat_bonus": "COMBAT",
    "repeated_probability": "PROBABILITY",
    "compound_discount": "DISCOUNT",
}

# Families eligible for native transformation (automatic, reviewed).
# Everything else (UNKNOWN, SELECTOR, BOOLEAN_UNLOCK, MIXED_*, NEEDS_REVIEW
# leftovers) is excluded with a recorded reason.
ELIGIBLE_FAMILIES = frozenset({
    "FLAT_AMOUNT", "FLAT_YIELD", "PERCENT_BONUS", "PRODUCTION_PERCENT",
    "GREAT_PERSON_POINTS", "AMENITY", "HOUSING", "LOYALTY", "TOURISM",
    "FAITH", "GOLD", "EXPERIENCE", "DURATION", "CHARGES", "MOVEMENT",
    "RANGE", "RADIUS", "COMBAT_STRENGTH_BONUS", "DEFEATED_STRENGTH_SCALING",
    "PROBABILITY", "DISCOUNT", "MULTIPLICATIVE_FACTOR", "COUNT_OR_DURATION",
})

# Module ownership bits. A generated entry carries the UNION of owning
# modules; duplicates must agree on official/transform/family/count-like or
# generation fails instead of silently choosing one.
MODULE_BITS = {"traits": 1, "policies": 2, "governments": 4}


# Indivisible-count families: native may apply them only for exact integer
# results (checked at runtime per entry); fractional outcomes are refused.
COUNT_LIKE_FAMILIES = frozenset({"CHARGES", "DURATION"})


class RegistryConflict(Exception):
    pass


def build_production_registry(manifest_rows: list[dict]) -> tuple[list[dict], dict]:
    """Return (entries, coverage_report).

    entries: deduped {module, modifier_id, argument, official, kind,
      count_like} sorted for deterministic emission.
    """
    seen: dict[tuple[str, str], dict] = {}
    excluded = Counter()
    for r in manifest_rows:
        key = (r["modifier_id"], r["argument_name"])
        if r["status"] != "ok":
            excluded[f"status:{r['status']}"] += 1
            continue
        if r["transformation"] == "unchanged":
            excluded["selector-or-unchanged"] += 1
            continue
        if r["confidence"] != "reviewed":
            excluded["confidence:not-reviewed"] += 1
            continue
        if r["semantic_family"] not in ELIGIBLE_FAMILIES:
            excluded[f"family:{r['semantic_family']}"] += 1
            continue
        kind = TRANSFORM_KIND.get(r["transformation"])
        if kind is None:
            excluded[f"transform:{r['transformation']}"] += 1
            continue
        try:
            float(r["official_value"])
        except (TypeError, ValueError):
            excluded["value:non-numeric"] += 1
            continue
        module = r.get("module", "")
        count_like = r["semantic_family"] in COUNT_LIKE_FAMILIES
        if key not in seen:
            seen[key] = {
                "owners": MODULE_BITS.get(module, 0),
                "owner_names": [module] if module else [],
                "modifier_id": r["modifier_id"],
                "argument": r["argument_name"],
                "official": r["official_value"],
                "kind": kind,
                "family": r["semantic_family"],
                "count_like": count_like,
            }
        else:
            prev = seen[key]
            if (prev["official"] != r["official_value"]
                    or prev["kind"] != kind
                    or prev["family"] != r["semantic_family"]
                    or prev["count_like"] != count_like):
                raise RegistryConflict(
                    f"duplicate {key} disagrees: {prev} vs {r}")
            prev["owners"] |= MODULE_BITS.get(module, 0)
            if module and module not in prev["owner_names"]:
                prev["owner_names"].append(module)
            excluded["duplicate:merged"] += 1
    entries = sorted(seen.values(),
                     key=lambda e: (e["modifier_id"], e["argument"]))
    owner_counts = Counter()
    shared = 0
    for e in entries:
        owner_counts[tuple(sorted(e["owner_names"]))] += 1
        if len(e["owner_names"]) > 1:
            shared += 1
    report = {
        "total_candidates": len(manifest_rows),
        "eligible": len(entries),
        "unique_definitions": len({e["modifier_id"] for e in entries}),
        "shared_definitions": shared,
        "ownership_counts": {"+".join(k) if k else "(none)": v
                             for k, v in sorted(owner_counts.items())},
        "excluded": dict(sorted(excluded.items())),
        "ownership_rule": ("A shared definition is transformed only if ALL "
                           "owning supported modules are enabled; disabling "
                           "one module never leaves its mutation active via "
                           "another owner."),
    }
    return entries, report


def emit_cxx(entries: list[dict]) -> str:
    """Emit the generated C++ registry include (deterministic)."""
    lines = [
        "// GENERATED by civ6x10.production from reviewed manifests.",
        "// Do not hand-edit. Regenerate: python -m civ6x10 generate-registry",
        "// Each entry derives from: authoritative official value + runtime k.",
        "// owners bitmask: 1=traits 2=policies 4=governments. A shared entry",
        "// applies only when ALL owning modules are enabled.",
        "#pragma once",
        "struct X10RegistryEntry {",
        "    const char* modifierId;",
        "    const char* argument;",
        "    const char* official;",
        "    int kind; // 0=ADDITIVE 1=COMBAT 2=PROBABILITY 3=DISCOUNT",
        "    int countLike; // runtime integral-result check required",
        "    int owners; // module bitmask",
        "};",
        "static const X10RegistryEntry kX10ProductionRegistry[] = {",
    ]
    kind_id = {"ADDITIVE": 0, "COMBAT": 1, "PROBABILITY": 2, "DISCOUNT": 3}
    for e in entries:
        lines.append(
            f'    {{"{e["modifier_id"]}", "{e["argument"]}", '
            f'"{e["official"]}", {kind_id[e["kind"]]}, '
            f'{"1" if e["count_like"] else "0"}, {e["owners"]}}},')
    lines.append("};")
    lines.append(f"static const int kX10ProductionRegistryCount = {len(entries)};")
    return "\n".join(lines) + "\n"
