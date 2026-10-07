"""Production registry generation for the native controller (release 1).

Reads the reviewed per-object manifests, CERTIFIES each row through the
effect-semantic floor + curated overrides (civ6x10.certification), and emits
a C++ registry consumed by the CE fork. Deterministic. No hand-maintained
modifier IDs: every entry traces to a manifest row + certification source.

AUTO_RULE heuristics are never eligible on their own; generation FAILS on
any unresolved semantic conflict.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from .certification import certify_row, load_rules, load_sem_floor

DEFAULT_SEM_PATH = Path(__file__).resolve().parents[1] / "data" / "local" \
    / "effect_semantics.csv"

# manifest transformation -> native TransformKind (only reached for rows
# whose KIND was certified; the gate, not this table, decides the kind).
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

# Certified native kinds (closed world: the gate emits only these).
CERTIFIED_KINDS = frozenset({"ADDITIVE", "COMBAT", "PROBABILITY", "DISCOUNT"})

# Module ownership bits. A generated entry carries the UNION of owning
# modules; duplicates must agree on official/transform/family/count-like or
# generation fails instead of silently choosing one.
MODULE_BITS = {"traits": 1, "policies": 2, "governments": 4}


# Indivisible-count families: native may apply them only for exact integer
# results (checked at runtime per entry); fractional outcomes are refused.
COUNT_LIKE_FAMILIES = frozenset({"CHARGES", "DURATION"})


class RegistryConflict(Exception):
    pass


class SemanticConflict(Exception):
    """Unresolved strong-family contradiction: generation fails closed."""
    pass


def build_production_registry(manifest_rows: list[dict],
                              sem_floor: dict | None = None,
                              rules: dict | None = None,
                              sem_path: str | Path = DEFAULT_SEM_PATH
                              ) -> tuple[list[dict], dict]:
    """Return (entries, coverage_report).

    Every candidate row is certified through the sem floor + curated
    overrides. Certified rows become entries with the CERTIFIED kind (which
    may differ from the manifest's heuristic proposal); excluded rows are
    reported by reason; any unresolved conflict raises SemanticConflict.

    entries: deduped {owners, owner_names, modifier_id, argument, official,
      kind, family, count_like, cert_source} sorted deterministically.
    """
    if sem_floor is None:
        if not Path(sem_path).is_file():
            raise FileNotFoundError(
                f"effect-semantic floor not found: {sem_path} "
                "(generation is local-only; run where data/local is present)")
        sem_floor = load_sem_floor(sem_path)
    if rules is None:
        rules = load_rules()
    seen: dict[tuple[str, str], dict] = {}
    excluded = Counter()
    ledger: list[dict] = []
    for r in manifest_rows:
        key = (r["modifier_id"], r["argument_name"])
        if r["status"] != "ok":
            excluded[f"status:{r['status']}"] += 1
            continue
        if r["transformation"] == "unchanged":
            excluded["selector-or-unchanged"] += 1
            continue
        try:
            float(r["official_value"])
        except (TypeError, ValueError):
            excluded["value:non-numeric"] += 1
            continue
        sem_row = sem_floor.get(
            (r.get("modifier_type", "").strip(),
             r.get("effect_type", "").strip(),
             r.get("argument_name", "").strip()))
        cert = certify_row(r, sem_row, rules)
        record = {
            "modifier_id": r["modifier_id"],
            "effect_type": r.get("effect_type", ""),
            "argument": r["argument_name"],
            "sem_family": cert["sem_family"],
            "proposed_family": cert["proposed_family"],
            "proposed_transform": r.get("transformation", ""),
            "cert_source": cert["source"] or "(none)",
            "resolution": cert["resolution"],
        }
        ledger.append(record)
        if cert["resolution"].startswith("conflict:"):
            continue  # unresolved: fails below
        if not cert["certified"]:
            excluded[cert["resolution"]] += 1
            continue
        if cert["kind"] not in CERTIFIED_KINDS:
            ledger[-1] = {**record,
                          "resolution": f"conflict:uncertified-kind:{cert['kind']}"}
            continue
        module = r.get("module", "")
        count_like = bool(cert["count_like"])
        kind = cert["kind"]
        if key not in seen:
            seen[key] = {
                "owners": MODULE_BITS.get(module, 0),
                "owner_names": [module] if module else [],
                "modifier_id": r["modifier_id"],
                "argument": r["argument_name"],
                "official": r["official_value"],
                "kind": kind,
                "family": cert["proposed_family"],
                "count_like": count_like,
                "cert_source": cert["source"],
            }
        else:
            prev = seen[key]
            if (prev["official"] != r["official_value"]
                    or prev["kind"] != kind
                    or prev["family"] != cert["proposed_family"]
                    or prev["count_like"] != count_like):
                raise RegistryConflict(
                    f"duplicate {key} disagrees: {prev} vs {r}")
            prev["owners"] |= MODULE_BITS.get(module, 0)
            if module and module not in prev["owner_names"]:
                prev["owner_names"].append(module)
            excluded["duplicate:merged"] += 1
    entries = sorted(seen.values(),
                     key=lambda e: (e["modifier_id"], e["argument"]))
    unresolved = [c for c in ledger
                  if c["resolution"].startswith("conflict:")]
    if unresolved:
        raise SemanticConflict(
            f"{len(unresolved)} unresolved semantic conflicts "
            "(strong-family contradiction with no curated resolution); "
            "first: " + repr(unresolved[:5]))
    owner_counts = Counter()
    shared = 0
    for e in entries:
        owner_counts[tuple(sorted(e["owner_names"]))] += 1
        if len(e["owner_names"]) > 1:
            shared += 1
    unconditional = sum(1 for e in entries if not e["count_like"])
    conditional = sum(1 for e in entries if e["count_like"])
    report = {
        "total_candidates": len(manifest_rows),
        "eligible": len(entries),
        "unique_definitions": len({e["modifier_id"] for e in entries}),
        "shared_definitions": shared,
        "certified_unconditional": unconditional,
        "certified_count_like_conditional": conditional,
        "ownership_counts": {"+".join(k) if k else "(none)": v
                             for k, v in sorted(owner_counts.items())},
        "excluded": dict(sorted(excluded.items())),
        "certification_sources": dict(sorted(Counter(
            e["cert_source"] for e in entries).items())),
        "conflict_ledger": ledger,
        "unresolved_conflicts": [],
        "ownership_rule": ("A shared definition is transformed only if ALL "
                           "owning supported modules are enabled; disabling "
                           "one module never leaves its mutation active via "
                           "another owner."),
    }
    return entries, report


def emit_cxx(entries: list[dict]) -> str:
    """Emit the generated C++ registry include (deterministic)."""
    lines = [
        "// GENERATED by civ6x10.production from CERTIFIED manifest rows.",
        "// Do not hand-edit. Regenerate: python -m civ6x10 generate-registry",
        "// Each entry derives from: authoritative official value + runtime k,",
        "// admitted only via sem-floor agreement or curated override",
        "// (see civ6x10/rules/certified_overrides.yml + conflict ledger).",
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
