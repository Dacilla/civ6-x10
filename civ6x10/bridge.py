"""Direct-table bridge: scalar wonder data as generated helper modifiers.

Some official wonder magnitudes live in direct building tables/columns, not
in ModifierArguments (Building_YieldChanges, Building_GreatPersonPoints,
Buildings.Housing, Buildings.Entertainment). The native engine only
transforms populated definitions, so each certifiable direct scalar V is
bridged:
  authoritative direct value V
    -> generated guarded SQL zeroes the direct cell AND creates one helper
       modifier carrying Amount=V attached to the wonder
    -> the helper flows through the existing native registry
       (official-mismatch guard, FLOAT32 k, count rules, store lookup)

Invariant (no new native arithmetic required):
  module OFF or k=1:  0 + V = vanilla (helper passes through untransformed)
  module ON at k:     0 + kV = semantic multiplier.

Every statement is guarded on the audited official value: drift (or another
mod) means zeroing never fires AND the helper is never created, leaving
vanilla untouched while the dormant registry row can never match at runtime.
Helper IDs are deterministic (X10_<BUILDING>_<TAG>) from this generator,
never handwritten; zero official X10_-prefixed collisions exist.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

# Each bridge: direct source, helper shape, native kind behavior.
# Equivalence per family is proven in docs/WONDER_AUDIT.md:
# - yield: direct BuildingModifiers precedents ELECTRONICSFACTORY_CULTURE
#   and TSIKHE_FAITH_GOLDEN_AGE (own building attach, Amount+BuildingType+
#   YieldType, COLLECTION_OWNER) — building yield stays building yield.
# - gpp/housing/local-entertainment: official single-city shapes with
#   identical effect+collection (Divine Spark GPP with BUILDING_IS_LIBRARY
#   building scope; Religious Community / Feed the World shrine housing,
#   all-zero flags; Thermal Bath entertainment attached to its building).
# - regional entertainment has NO equivalent: the only official regional
#   modifier (GREATPERSON_EXTRA_REGIONAL_BUILDING_ENTERTAINMENT) is a
#   great-person one-shot (RunOnce=1, Permanent=1, district-in-tile target),
#   not a persistent wonder aura. Nonzero Entertainment + nonzero
#   RegionalRange is therefore never bridged (guard in build_wonder_direct).
BRIDGES = [
    {
        "family": "yield",
        "source_table": "Building_YieldChanges",
        "key_cols": ["YieldType"],
        "value_col": "YieldChange",
        "modifier_type": "MODIFIER_BUILDING_YIELD_CHANGE",
        "effect_type": "EFFECT_ADJUST_BUILDING_YIELD_CHANGE",
        "extra_args": ["BuildingType", "YieldType"],
        "tag": lambda r: r["key_YieldType"],
    },
    {
        "family": "gpp",
        "source_table": "Building_GreatPersonPoints",
        "key_cols": ["GreatPersonClassType"],
        "value_col": "PointsPerTurn",
        "modifier_type": "MODIFIER_SINGLE_CITY_ADJUST_GREAT_PERSON_POINT",
        "effect_type": "EFFECT_ADJUST_GREAT_PERSON_POINTS",
        "extra_args": ["GreatPersonClassType"],
        "tag": lambda r: "GPP_" + r["key_GreatPersonClassType"].replace(
            "GREAT_PERSON_CLASS_", ""),
    },
    {
        "family": "housing",
        "source_table": "Buildings",
        "key_cols": [],
        "value_col": "Housing",
        "modifier_type": "MODIFIER_SINGLE_CITY_ADJUST_BUILDING_HOUSING",
        "effect_type": "EFFECT_ADJUST_BUILDING_HOUSING",
        "extra_args": [],
        "tag": lambda r: "HOUSING",
    },
    {
        "family": "entertainment",
        "source_table": "Buildings",
        "key_cols": [],
        "value_col": "Entertainment",
        "modifier_type": "MODIFIER_SINGLE_CITY_ADJUST_ENTERTAINMENT",
        "effect_type": "EFFECT_ADJUST_CITY_ENTERTAINMENT",
        "extra_args": [],
        "tag": lambda r: "ENTERTAINMENT",
    },
]

# Direct-table cells that are structural/selectors: inventoried but never
# bridged or multiplied. (Rationale per row lives in wonder_audit.yml.)
NON_BRIDGED_TABLES = {
    "Building_GreatWorks": "structural slots/theming (capacity, not magnitude)",
    "Buildings_XP2": "map/flag fields (bridge/canal/flood/pillage)",
}


def build_wonder_direct(db_path: str | Path) -> list[dict]:
    """Closed-world direct-effect inventory for official wonders.

    Regression guard (Phase 3C): nonzero Entertainment + nonzero
    RegionalRange MUST NOT bridge to MODIFIER_SINGLE_CITY_ADJUST_ENTERTAINMENT
    (regional scope cannot be preserved by a local helper). Those cells are
    inventoried in the audit with EXCLUDED dispositions, never emitted here.
    """
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    wonders = [r[0] for r in db.execute(
        "SELECT BuildingType FROM Buildings WHERE IsWonder=1 ORDER BY BuildingType")]
    regional = {b for (b,) in db.execute(
        "SELECT BuildingType FROM Buildings WHERE IsWonder=1 "
        "AND RegionalRange IS NOT NULL AND RegionalRange != 0")}
    rows: list[dict] = []
    for spec in BRIDGES:
        t = spec["source_table"]
        if t == "Buildings":
            cols = ["BuildingType", spec["value_col"]]
            q = "SELECT BuildingType, %s AS v FROM Buildings WHERE IsWonder=1" % spec["value_col"]
            for b, v in db.execute(q):
                if v is None or v == 0 or v == "":
                    continue
                if spec["family"] == "entertainment" and b in regional:
                    continue
                rows.append(_direct_row(b, spec, {}, v))
        else:
            key_sel = ", ".join(spec["key_cols"])
            q = "SELECT BuildingType, %s, %s AS v FROM %s" % (
                key_sel, spec["value_col"], t)
            for rec in db.execute(q):
                rec = dict(rec)
                b = rec.pop("BuildingType")
                v = rec.pop("v")
                if b not in wonders or v is None or v == 0 or v == "":
                    continue
                try:
                    float(v)
                except (TypeError, ValueError):
                    continue
                rows.append(_direct_row(b, spec, rec, v))
    rows.sort(key=lambda r: (r["building_type"], r["source_table"],
                             r["key"], str(r["value"])))
    return rows


def _direct_row(building: str, spec: dict, keys: dict, value) -> dict:
    key = "|".join("%s=%s" % (k, keys[k]) for k in sorted(keys)) if keys else "-"
    return {
        "building_type": building,
        "source_table": spec["source_table"],
        "source_family": spec["family"],
        "key": key,
        "value_column": spec["value_col"],
        "value": str(value),
    }


def write_direct_csv(rows: list[dict], out: str | Path) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["building_type", "source_table", "source_family", "key",
              "value_column", "value"]
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def load_direct_csv(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


REGISTRY_MODULES = ("traits", "policies", "governments", "pantheons", "wonders")


def collect_registry_rows(root: str | Path) -> list[dict]:
    """All production input rows: 5 manifests + generated bridge helpers.

    Single source shared by the CLI and the test-suite so the shipped
    registry can never silently diverge from what tests certify.
    """
    import yaml
    root = Path(root)
    rows: list[dict] = []
    for module in REGISTRY_MODULES:
        man = yaml.safe_load(
            open(root / "manifests" / f"{module}.yml", encoding="utf-8"))
        for r in man[module]:
            r = dict(r)
            r["module"] = module
            rows.append(r)
    direct_csv = root / "data" / "local" / "wonder_direct.csv"
    if direct_csv.is_file():
        for h in build_bridge_helpers(load_direct_csv(direct_csv)):
            h = dict(h)
            h["module"] = "wonders"
            rows.append(h)
    return rows


def helper_id(row: dict) -> str:
    spec = next(s for s in BRIDGES if s["family"] == row["source_family"])
    keys = dict(p.split("=", 1) for p in row["key"].split("|")) if row["key"] != "-" else {}
    keyrec = {"key_" + k: v for k, v in keys.items()}
    return "X10_%s_%s" % (row["building_type"].replace("BUILDING_", ""),
                          spec["tag"](keyrec))


def _extra_value(extra: str, keys: dict, row: dict) -> str:
    # YieldType / GreatPersonClassType come from the direct row key;
    # BuildingType names the owning wonder (Electronics Factory precedent:
    # the helper's BuildingType arg is its own attached building).
    if extra in keys:
        return keys[extra]
    if extra == "BuildingType":
        return row["building_type"]
    raise KeyError(extra)


def build_bridge_helpers(direct_rows: list[dict]) -> list[dict]:
    """Manifest-shaped helper rows (module=wonders) for bridged direct cells."""
    from .modules import build_manifest
    spec_by_family = {s["family"]: s for s in BRIDGES}
    raws = []
    for r in direct_rows:
        spec = spec_by_family[r["source_family"]]
        keys = dict(p.split("=", 1) for p in r["key"].split("|")) if r["key"] != "-" else {}
        raws.append({
            "building_type": r["building_type"],
            "modifier_id": helper_id(r),
            "modifier_type": spec["modifier_type"],
            "effect_type": spec["effect_type"],
            "argument_name": "Amount",
            "official_value": str(r["value"]),
            "argument_value": str(r["value"]),
            "bridged_from": "%s|%s|%s" % (r["building_type"], r["source_table"], r["key"]),
        })
        for extra in spec["extra_args"]:
            val = _extra_value(extra, keys, r)
            raws.append({
                "building_type": r["building_type"],
                "modifier_id": helper_id(r),
                "modifier_type": spec["modifier_type"],
                "effect_type": spec["effect_type"],
                "argument_name": extra,
                "official_value": val,
                "argument_value": val,
                "bridged_from": "%s|%s|%s" % (r["building_type"], r["source_table"], r["key"]),
            })
    # id_col="building_type" fills object_id; effect_type preset survives
    # review._join_effect's setdefault.
    return build_manifest(raws, "building_type")


def _baseline_pred(row: dict) -> str:
    spec = next(s for s in BRIDGES if s["family"] == row["source_family"])
    keys = dict(p.split("=", 1) for p in row["key"].split("|")) if row["key"] != "-" else {}
    parts = ["BuildingType = '%s'" % row["building_type"]]
    for k in sorted(keys):
        parts.append("%s = '%s'" % (k, keys[k].replace("'", "''")))
    parts.append("%s = %s" % (row["value_column"], row["value"]))
    return " AND ".join(parts)


def emit_bridge_sql(direct_rows: list[dict]) -> str:
    """Guarded helper-creation + direct-zeroing SQL (deterministic)."""
    spec_by_family = {s["family"]: s for s in BRIDGES}
    chunks = [
        "-- GENERATED by civ6x10.bridge from audited direct wonder values.",
        "-- Do not hand-edit. Regenerate: python -m civ6x10 generate-bridge-sql",
        "-- Each helper is created ONLY when the direct cell still holds its",
        "-- audited official value, and each direct cell is zeroed ONLY when",
        "-- it holds that value AND its helper exists. Drift leaves vanilla",
        "-- untouched and the dormant registry row can never match at runtime.",
        "-- Helpers run InGame (UpdateDatabase) before native populate.",
        "",
    ]
    for r in direct_rows:
        spec = spec_by_family[r["source_family"]]
        hid = helper_id(r)
        base = _baseline_pred(r)
        keys = dict(p.split("=", 1) for p in r["key"].split("|")) if r["key"] != "-" else {}
        chunks.append("-- %s %s=%s (bridged)" % (
            r["building_type"], r["value_column"], r["value"]))
        chunks.append(
            "INSERT INTO Modifiers (ModifierId, ModifierType, RunOnce, NewOnly,"
            " Permanent, Repeatable)\n"
            "SELECT '%s', '%s', 0, 0, 0, 0\n"
            "WHERE NOT EXISTS (SELECT 1 FROM Modifiers WHERE ModifierId = '%s')\n"
            "  AND EXISTS (SELECT 1 FROM %s WHERE %s);" % (
                hid, spec["modifier_type"], hid, r["source_table"], base))
        chunks.append(
            "INSERT INTO BuildingModifiers (BuildingType, ModifierId)\n"
            "SELECT '%s', '%s'\n"
            "WHERE NOT EXISTS (SELECT 1 FROM BuildingModifiers"
            " WHERE BuildingType = '%s' AND ModifierId = '%s')\n"
            "  AND EXISTS (SELECT 1 FROM %s WHERE %s);" % (
                r["building_type"], hid, r["building_type"], hid,
                r["source_table"], base))
        chunks.append(
            "INSERT INTO ModifierArguments (ModifierId, Name, Type, Value)\n"
            "SELECT '%s', 'Amount', 'ARGTYPE_IDENTITY', '%s'\n"
            "WHERE NOT EXISTS (SELECT 1 FROM ModifierArguments"
            " WHERE ModifierId = '%s' AND Name = 'Amount')\n"
            "  AND EXISTS (SELECT 1 FROM %s WHERE %s);" % (
                hid, r["value"], hid, r["source_table"], base))
        for extra in spec["extra_args"]:
            chunks.append(
                "INSERT INTO ModifierArguments (ModifierId, Name, Type, Value)\n"
                "SELECT '%s', '%s', 'ARGTYPE_IDENTITY', '%s'\n"
                "WHERE NOT EXISTS (SELECT 1 FROM ModifierArguments"
                " WHERE ModifierId = '%s' AND Name = '%s')\n"
                "  AND EXISTS (SELECT 1 FROM %s WHERE %s);" % (
                    hid, extra, _extra_value(extra, keys, r).replace("'", "''"), hid, extra,
                    r["source_table"], base))
        vcol = r["value_column"]
        chunks.append(
            "UPDATE %s SET %s = 0\nWHERE %s\n"
            "  AND EXISTS (SELECT 1 FROM Modifiers WHERE ModifierId = '%s');"
            % (r["source_table"], vcol, base, hid))
        chunks.append("")
    return "\n".join(chunks)
