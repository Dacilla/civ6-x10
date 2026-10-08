"""Wonder inventory: building -> modifier -> arguments from the official DB copy.

Produces data/local/wonder_effects.csv shaped like the other official
inventories (building_type as the object id column). Deterministic; rerun with:
    python -m civ6x10 inventory-wonders --db <official-copy> --out <csv>
Reads ONLY the copied SQLite database. Attached (EFFECT_ATTACH_MODIFIER)
children are resolved one level so numeric leaves keep their wonder link.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


def build_wonder_inventory(db_path: str | Path) -> list[dict]:
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    wonders = [r[0] for r in db.execute(
        "SELECT BuildingType FROM Buildings WHERE IsWonder=1 ORDER BY BuildingType")]
    rows: list[dict] = []
    for w in wonders:
        l1 = [r[0] for r in db.execute(
            'SELECT ModifierID FROM BuildingModifiers WHERE BuildingType=?', (w,))]
        for mid in sorted(set(l1)):
            _emit_modifier(db, rows, wonder=w, modifier_id=mid, parent="")
    rows.sort(key=lambda r: (r["building_type"], r["modifier_id"], r["argument_name"]))
    return rows


def _emit_modifier(db, rows: list[dict], wonder: str, modifier_id: str,
                   parent: str) -> None:
    mts = [r[0] for r in db.execute(
        'SELECT ModifierType FROM Modifiers WHERE ModifierId=?', (modifier_id,))]
    for mt in mts:
        dyn = [(r[0], r[1]) for r in db.execute(
            'SELECT CollectionType, EffectType FROM DynamicModifiers WHERE ModifierType=?',
            (mt,))]
        args = [(r[0], r[1], r[2]) for r in db.execute(
            'SELECT Name, Type, Value FROM ModifierArguments WHERE ModifierId=?',
            (modifier_id,))]
        for (coll, eff) in dyn or [(None, None)]:
            for (name, typ, val) in args:
                rows.append({
                    "building_type": wonder,
                    "parent_modifier_id": parent,
                    "modifier_id": modifier_id,
                    "modifier_type": mt or "",
                    "collection_type": coll or "",
                    "effect_type": eff or "",
                    "argument_name": name or "",
                    "argument_type": typ or "",
                    "argument_value": val if val is not None else "",
                    "official_value": val if val is not None else "",
                })
        if any(e == 'EFFECT_ATTACH_MODIFIER' for _, e in dyn):
            for (name, _typ, val) in args:
                if name == 'ModifierId' and val:
                    _emit_modifier(db, rows, wonder=wonder,
                                   modifier_id=val, parent=modifier_id)


def write_csv(rows: list[dict], out: str | Path) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["building_type", "parent_modifier_id", "modifier_id",
              "modifier_type", "collection_type", "effect_type",
              "argument_name", "argument_type", "argument_value",
              "official_value"]
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
