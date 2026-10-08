"""Phase-3B direct-table bridge tests.

DB-backed tests need data/local copies (gitignored) and skip in CI.
SQL-mechanism tests build synthetic databases in tmp and always run.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

from civ6x10 import transforms as T
from civ6x10.bridge import (
    BRIDGES,
    build_bridge_helpers,
    build_wonder_direct,
    emit_bridge_sql,
    helper_id,
    load_direct_csv,
)


def local_db():
    p = ROOT / "data" / "local" / "DebugGameplay_official.sqlite"
    if not p.is_file():
        raise FileNotFoundError(str(p))
    return p


def load_audit():
    import yaml
    return yaml.safe_load(
        open(ROOT / "civ6x10" / "rules" / "wonder_audit.yml",
             encoding="utf-8"))["wonders"]


class TestDirectInventory(unittest.TestCase):
    def test_closed_world_counts(self):
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        import collections
        by_table = collections.Counter(r["source_table"] for r in rows)
        self.assertEqual(by_table["Building_YieldChanges"], 31)
        self.assertEqual(by_table["Building_GreatPersonPoints"], 20)
        self.assertEqual(by_table["Buildings"], 8)  # 3 housing + 5 entertainment
        # Zero-row gameplay tables stay empty (proves the scan ran).
        import sqlite3
        db = sqlite3.connect(str(local_db()))
        wonders = tuple(
            r[0] for r in db.execute(
                "SELECT BuildingType FROM Buildings WHERE IsWonder=1"))
        for t in ("Building_CitizenYieldChanges",
                  "Building_BuildChargeProductions",
                  "Building_ResourceCosts",
                  "Building_TourismBombs_XP2",
                  "Building_YieldChangesBonusWithPower",
                  "Building_YieldDistrictCopies",
                  "Building_YieldsPerEra",
                  "Adjacent_AppealYieldChanges"):
            n = db.execute(
                "SELECT COUNT(*) FROM %s WHERE BuildingType IN (%s)" % (
                    t, ",".join("?" * len(wonders))), wonders).fetchone()[0]
            self.assertEqual(n, 0, t)
        # Buildings direct nonzero: 13 gameplay magnitudes + 4
        # selector/structural (AdjacentResource x2, GrantFortification x2
        # counted separately below with DefenseModifier/RegionalRange).
        direct = [r for r in rows if r["source_table"] == "Buildings"]
        self.assertEqual(len(direct), 8)

    def test_fixture_spot_values(self):
        # Task fixtures, verified against the clean DB.
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        by_key = {(r["building_type"], r["source_table"], r["key"]): r["value"]
                  for r in rows}
        for key, want in (
                (("BUILDING_HANGING_GARDENS", "Buildings", "-"), "2"),
                (("BUILDING_GREAT_BATH", "Buildings", "-"), None),
                (("BUILDING_PANAMA_CANAL", "Building_YieldChanges",
                  "YieldType=YIELD_GOLD"), "10"),
                (("BUILDING_SYDNEY_OPERA_HOUSE", "Building_YieldChanges",
                  "YieldType=YIELD_CULTURE"), "8"),
                (("BUILDING_TEMPLE_ARTEMIS", "Building_YieldChanges",
                  "YieldType=YIELD_FOOD"), "4")):
            if want is None:
                continue
            self.assertEqual(by_key.get((key[0], key[1], key[2])), want, key)
        # Great Bath has both housing and entertainment rows.
        bath = sorted(r["value_column"] for r in rows
                      if r["building_type"] == "BUILDING_GREAT_BATH")
        self.assertEqual(bath, ["Entertainment", "Housing"])
        # Structural scope never enters the bridged inventory: Colosseum
        # contributes exactly its culture yield + entertainment rows.
        col = sorted((r["source_table"], r["value_column"]) for r in rows
                     if r["building_type"] == "BUILDING_COLOSSEUM")
        self.assertEqual(col, [("Building_YieldChanges", "YieldChange"),
                               ("Buildings", "Entertainment")])

    def test_every_direct_row_has_disposition(self):
        audit = load_audit()
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        for r in rows:
            rec = audit.get(r["building_type"])
            self.assertIsNotNone(rec, r["building_type"])
            keys = {(d["table"], d["key"]) for d in rec.get("direct", [])}
            short = (r["source_table"],
                     r["key"].split("=", 1)[1] if "=" in r["key"]
                     else r["value_column"])
            hit = [k for k in keys
                   if k[0] == short[0] and short[1] in k[1]]
            self.assertTrue(hit, (r["building_type"], r["source_table"],
                                  r["key"]))

    def test_no_complete_wonder_unhandled(self):
        audit = load_audit()
        bridgeable = {"Building_YieldChanges", "Building_GreatPersonPoints",
                      "Buildings"}
        for b, rec in audit.items():
            if rec["disposition"] != "COMPLETE":
                continue
            for d in rec.get("direct", []):
                if d["table"] not in bridgeable:
                    continue
                # Buildings-table structural keys stay excluded.
                if d["table"] == "Buildings" and d["key"] not in (
                        "Housing", "Entertainment"):
                    continue
                self.assertTrue(
                    d["disposition"].startswith("BRIDGED"), (b, d))

    def test_former_nones_represented(self):
        audit = load_audit()
        for b in ("BUILDING_ESTADIO_DO_MARACANA", "BUILDING_HERMITAGE",
                  "BUILDING_PANAMA_CANAL", "BUILDING_SYDNEY_OPERA_HOUSE",
                  "BUILDING_TEMPLE_ARTEMIS"):
            rec = audit[b]
            self.assertEqual(rec["disposition"], "COMPLETE", b)
            bridged = [d for d in rec.get("direct", [])
                       if d["disposition"].startswith("BRIDGED")]
            self.assertTrue(bridged, b)


class TestBridgeMechanics(unittest.TestCase):
    def test_helper_ids_deterministic_and_reserved(self):
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        ids1 = [helper_id(r) for r in rows]
        ids2 = [helper_id(r) for r in rows]
        self.assertEqual(ids1, ids2)
        self.assertEqual(len(set(ids1)), len(ids1))
        self.assertTrue(all(i.startswith("X10_") for i in ids1))
        self.assertTrue(all(len(i) < 256 for i in ids1))
        import sqlite3
        db = sqlite3.connect(str(local_db()))
        n = db.execute("SELECT COUNT(*) FROM Modifiers WHERE ModifierId LIKE 'X10%'"
                       ).fetchone()[0]
        self.assertEqual(n, 0)

    def test_k1_and_off_invariant(self):
        # Invariant: OFF/k=1 -> 0 + V = vanilla; ON at k -> 0 + kV.
        # The SQL zeroes the cell and the helper carries V (asserted from
        # the generated text); the arithmetic is the native ADDITIVE path.
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        sql = emit_bridge_sql(rows)
        for r in rows:
            hid = helper_id(r)
            self.assertIn("'%s', 'Amount', 'ARGTYPE_IDENTITY', '%s'" % (
                hid, r["value"]), sql)
            self.assertIn("SET %s = 0" % r["value_column"], sql)
            v = float(r["value"])
            for k in (0.0, 1.0, 7.3, 10.0, 4.25):
                got = 0.0 + (0.0 if k == 0.0 else T.scale_flat(v, k))
                self.assertAlmostEqual(got, 0.0 if k == 0.0 else v * k)
            self.assertAlmostEqual(0.0 + T.scale_flat(v, 1.0), v)

    def test_bridged_scale_at_arbitrary_k(self):
        import math
        from civ6x10.production import build_production_registry
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        helpers = build_bridge_helpers(rows)
        for h in helpers:
            h["module"] = "wonders"
        entries, report = build_production_registry(helpers)
        self.assertEqual(report["unresolved_conflicts"], [])
        self.assertEqual(len(entries), 59)
        kf = T.stored_float32(7.3)
        for k in (1.0, 10.0, 4.25, kf):
            for e in entries:
                if e["count_like"]:
                    continue
                self.assertTrue(
                    math.isfinite(float(e["official"]) * k), (e, k))

    def test_structural_absent_from_sql_and_registry(self):
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        sql = emit_bridge_sql(rows)
        for token in ("GreatWorks", "RegionalRange", "DefenseModifier",
                      "GrantFortification", "Theming", "NumSlots",
                      "AdjacentResource"):
            self.assertNotIn(token, sql)
        from civ6x10.production import build_production_registry
        helpers = build_bridge_helpers(rows)
        for h in helpers:
            h["module"] = "wonders"
        entries, _ = build_production_registry(helpers)
        self.assertEqual(len(entries), 59)
        for e in entries:
            self.assertTrue(e["modifier_id"].startswith("X10_"))

    def test_drift_fails_closed_synthetic(self):
        # Full mechanism test on a synthetic DB (CI-safe): create, zero,
        # reapply idempotently, then drift one cell and prove isolation.
        import sqlite3
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as td:
            dbp = os.path.join(td, "t.db")
            db = sqlite3.connect(dbp)
            db.execute("CREATE TABLE Buildings (BuildingType TEXT, Housing INTEGER, Entertainment INTEGER)")
            db.execute("CREATE TABLE Building_YieldChanges (BuildingType TEXT, YieldType TEXT, YieldChange INTEGER)")
            db.execute("CREATE TABLE Modifiers (ModifierId TEXT, ModifierType TEXT, RunOnce INTEGER, NewOnly INTEGER, Permanent INTEGER, Repeatable INTEGER, OwnerRequirementSetId TEXT, SubjectRequirementSetId TEXT, OwnerStackLimit INTEGER, SubjectStackLimit INTEGER)")
            db.execute("CREATE TABLE BuildingModifiers (BuildingType TEXT, ModifierId TEXT)")
            db.execute("CREATE TABLE ModifierArguments (ModifierId TEXT, Name TEXT, Type TEXT, Value TEXT, Extra TEXT, SecondExtra TEXT)")
            db.execute("INSERT INTO Buildings VALUES ('BUILDING_X', 2, 0)")
            db.execute("INSERT INTO Building_YieldChanges VALUES ('BUILDING_X', 'YIELD_GOLD', 10)")
            db.commit()
            direct = [
                {"building_type": "BUILDING_X", "source_table": "Buildings",
                 "source_family": "housing", "key": "-",
                 "value_column": "Housing", "value": "2"},
                {"building_type": "BUILDING_X", "source_table": "Building_YieldChanges",
                 "source_family": "yield", "key": "YieldType=YIELD_GOLD",
                 "value_column": "YieldChange", "value": "10"},
            ]
            from civ6x10.bridge import emit_bridge_sql as emit
            db.executescript(emit(direct))
            self.assertEqual(
                db.execute("SELECT Housing FROM Buildings WHERE BuildingType='BUILDING_X'").fetchone()[0], 0)
            self.assertEqual(
                db.execute("SELECT YieldChange FROM Building_YieldChanges WHERE BuildingType='BUILDING_X'").fetchone()[0], 0)
            self.assertEqual(
                db.execute("SELECT Value FROM ModifierArguments WHERE ModifierId='X10_X_HOUSING' AND Name='Amount'").fetchone()[0], "2")
            n0 = db.execute("SELECT COUNT(*) FROM Modifiers").fetchone()[0]
            db.executescript(emit(direct))  # idempotent reapply
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM Modifiers").fetchone()[0], n0)
            # drift the gold cell back (simulating another mod / patch)
            db.execute("UPDATE Building_YieldChanges SET YieldChange=99 WHERE BuildingType='BUILDING_X'")
            db.commit()
            # fresh-apply semantics: drop helpers to simulate a clean load, reapply
            db.execute("DELETE FROM Modifiers WHERE ModifierId LIKE 'X10%'")
            db.execute("DELETE FROM BuildingModifiers WHERE ModifierId LIKE 'X10%'")
            db.execute("DELETE FROM ModifierArguments WHERE ModifierId LIKE 'X10%'")
            db.execute("UPDATE Buildings SET Housing=2 WHERE BuildingType='BUILDING_X'")
            db.commit()
            db.executescript(emit(direct))
            kept = db.execute("SELECT YieldChange FROM Building_YieldChanges WHERE BuildingType='BUILDING_X'").fetchone()[0]
            missing = db.execute("SELECT COUNT(*) FROM Modifiers WHERE ModifierId='X10_X_YIELD_GOLD'").fetchone()[0]
            housed = db.execute("SELECT Housing FROM Buildings WHERE BuildingType='BUILDING_X'").fetchone()[0]
            self.assertEqual(kept, 99)
            self.assertEqual(missing, 0)
            self.assertEqual(housed, 0)  # undrifted cell still bridges
            db.close()

    def test_bridge_sql_shipped_in_controller_package(self):
        # The generated bridge SQL ships inside the controller mod (InGame
        # UpdateDatabase + Files) so helper modifiers exist before native
        # populate.
        mi = (ROOT / "controller" / "X10" / "X10.modinfo").read_text(
            encoding="utf-8")
        self.assertIn('<UpdateDatabase id="X10WonderBridge">', mi)
        self.assertIn("<File>Config/X10WonderBridge.sql</File>", mi)
        sql = (ROOT / "controller" / "X10" / "Config" / "X10WonderBridge.sql"
               ).read_text(encoding="utf-8")
        self.assertIn("X10_PANAMA_CANAL_YIELD_GOLD", sql)
        self.assertIn("AND EXISTS (SELECT 1 FROM Building_YieldChanges", sql)


if __name__ == "__main__":
    unittest.main(verbosity=2)
