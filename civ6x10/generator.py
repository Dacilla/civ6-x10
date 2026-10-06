"""Generator: deterministic idempotent SQL from manifests.

Never emits relative transformations (no `Value = Value * 10`). Every UPDATE
sets an absolute generated value with a fully-qualified predicate.
"""
from __future__ import annotations


def emit_update(table: str, set_col: str, value: str, where: dict[str, str]) -> str:
    preds = " AND ".join(f"{k} = '{v}'" for k, v in sorted(where.items()))
    return (f"UPDATE {table}\nSET {set_col} = {sql_lit(value)}\n"
            f"WHERE {preds};")


def sql_lit(value: str) -> str:
    try:
        float(value)
        return value
    except (TypeError, ValueError):
        return "'" + str(value).replace("'", "''") + "'"


def statements_for_manifest(entries: list[dict], table: str = "ModifierArguments",
                             value_col: str = "Value") -> list[str]:
    out: list[str] = []
    for e in entries:
        if e["status"] != "ok" or e["transformation"] == "unchanged":
            continue
        if e["argument_name"] in ("ModifierId",):
            continue
        out.append(emit_update(
            table, value_col, e["generated_value"],
            {"ModifierId": e["modifier_id"], "Name": e["argument_name"]}))
    return sorted(set(out))
