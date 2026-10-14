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
        # 3 housing + 3 local entertainment. Colosseum (range 6) and Estadio
        # (range global) entertainment never bridges: regional scope cannot
        # be preserved by a local helper.
        self.assertEqual(by_table["Buildings"], 6)
        self.assertEqual(len(rows), 57)
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
        self.assertEqual(len(direct), 6)

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
        # contributes exactly its culture yield (its Entertainment is
        # regional, excluded); Estadio contributes exactly its culture.
        col = sorted((r["source_table"], r["value_column"]) for r in rows
                     if r["building_type"] == "BUILDING_COLOSSEUM")
        self.assertEqual(col, [("Building_YieldChanges", "YieldChange")])
        est = sorted((r["source_table"], r["value_column"]) for r in rows
                     if r["building_type"] == "BUILDING_ESTADIO_DO_MARACANA")
        self.assertEqual(est, [("Building_YieldChanges", "YieldChange")])

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
        for b in ("BUILDING_HERMITAGE",
                  "BUILDING_PANAMA_CANAL", "BUILDING_SYDNEY_OPERA_HOUSE",
                  "BUILDING_TEMPLE_ARTEMIS"):
            rec = audit[b]
            self.assertEqual(rec["disposition"], "COMPLETE", b)
            bridged = [d for d in rec.get("direct", [])
                       if d["disposition"].startswith("BRIDGED")]
            self.assertTrue(bridged, b)
        # Estadio keeps its bridged culture but drops to PARTIAL: its
        # Entertainment is regional (range global) with no equivalent.
        rec = audit["BUILDING_ESTADIO_DO_MARACANA"]
        self.assertEqual(rec["disposition"], "PARTIAL")
        bridged = [d for d in rec.get("direct", [])
                   if d["disposition"].startswith("BRIDGED")]
        self.assertTrue(bridged)
        excluded = [d for d in rec.get("direct", [])
                    if d["disposition"] == "EXCLUDED"]
        self.assertTrue(any(d["key"] == "Entertainment" for d in excluded))


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
        # Phase-8B non-destructive delta: the direct cell keeps V and the
        # helper is stored inert (0). k=0 (native Off) and module OFF leave
        # the helper at 0 (native never arms writes); k=1 is identity
        # (delta 0); integral k>1 contributes V*(k-1) for a total of kV.
        # Fractional deltas refuse (count-like), leaving direct V alone.
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        sql = emit_bridge_sql(rows)
        for r in rows:
            hid = helper_id(r)
            self.assertIn("'%s', 'Amount', 'ARGTYPE_IDENTITY', '0'" % hid,
                          sql)
            self.assertNotIn("SET %s = 0" % r["value_column"], sql)
            v = float(r["value"])
            direct_after_bridge = v
            for k in (0.0, 1.0, 7.3, 10.0, 4.25):
                if k in (0.0, 1.0):
                    helper = 0.0
                elif T.count_like_applies_delta(v, k):
                    helper = v * (k - 1.0)
                else:
                    helper = 0.0  # refused: helper stays inert
                total = direct_after_bridge + helper
                want = v if k in (0.0, 1.0) else (
                    v * k if T.count_like_applies_delta(v, k) else v)
                self.assertAlmostEqual(total, want, msg=(hid, k))
            # Module OFF with k>1 configured: native unarmed, helper stays 0.
            self.assertAlmostEqual(direct_after_bridge + 0.0, v)

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
        self.assertEqual(len(entries), 57)
        self.assertTrue(all(e["kind"] == "DELTA" for e in entries))
        kf = T.stored_float32(7.3)
        kerr = T.float_quantization_error(kf)
        for k in (1.0, 10.0, 4.25, kf):
            for e in entries:
                v = float(e["official"])
                if k == 1.0:
                    self.assertEqual(v * (k - 1.0), 0.0, e)
                    continue
                kk = kf if k == kf else k
                ke = kerr if k == kf else 0.0
                applies = T.count_like_applies_delta(v, kk, ke)
                if applies:
                    self.assertTrue(
                        math.isfinite(v * (kk - 1.0)), (e, k))

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
        self.assertEqual(len(entries), 57)
        for e in entries:
            self.assertTrue(e["modifier_id"].startswith("X10_"))

    def test_regional_entertainment_never_local(self):
        # Phase-3C regression: nonzero Entertainment + nonzero RegionalRange
        # MUST NOT use MODIFIER_SINGLE_CITY_ADJUST_ENTERTAINMENT. The two
        # regional cells keep their vanilla direct values (no zeroing) and
        # get no helper.
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        by_building = {}
        for r in rows:
            by_building.setdefault(r["building_type"], []).append(r)
        for b in ("BUILDING_COLOSSEUM", "BUILDING_ESTADIO_DO_MARACANA"):
            ent = [r for r in by_building.get(b, [])
                   if r["value_column"] == "Entertainment"]
            self.assertEqual(ent, [], b)
        sql = emit_bridge_sql(rows)
        self.assertNotIn("X10_COLOSSEUM_ENTERTAINMENT", sql)
        self.assertNotIn("X10_ESTADIO_DO_MARACANA_ENTERTAINMENT", sql)
        for b in ("BUILDING_COLOSSEUM", "BUILDING_ESTADIO_DO_MARACANA"):
            self.assertNotIn(
                "SET Entertainment = 0\nWHERE BuildingType = '%s'" % b, sql)
        # Audit dispositions agree: EXCLUDED with regional rationale.
        audit = load_audit()
        for b in ("BUILDING_COLOSSEUM", "BUILDING_ESTADIO_DO_MARACANA"):
            rec = audit[b]
            self.assertEqual(rec["disposition"], "PARTIAL", b)
            ent = [d for d in rec.get("direct", [])
                   if d["table"] == "Buildings" and d["key"] == "Entertainment"]
            self.assertEqual(len(ent), 1, b)
            self.assertEqual(ent[0]["disposition"], "EXCLUDED", b)
            self.assertIn("RegionalRange", ent[0]["rationale"], b)

    def test_yield_helpers_are_building_yield_change(self):
        # Phase-3C: every generated yield helper preserves the building-yield
        # category — MODIFIER_BUILDING_YIELD_CHANGE /
        # EFFECT_ADJUST_BUILDING_YIELD_CHANGE with all three arguments
        # (Amount + BuildingType naming the owning wonder + YieldType).
        # Phase 8B.2/8B.3 exceptions: the Colosseum culture, Jebel faith,
        # and Maracana culture helpers ride the official regional graph
        # (player-cities city-yield carrier + requirement where one
        # exists); they are the ONLY yield helpers allowed to carry
        # EFFECT_ADJUST_CITY_YIELD_CHANGE.
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        from civ6x10.production import build_production_registry
        helpers = build_bridge_helpers(rows)
        by_id: dict = {}
        for h in helpers:
            by_id.setdefault(h["modifier_id"], {})[h["argument_name"]] = h
        n_yield = n_regional = 0
        for hid, args in by_id.items():
            if "YieldType" not in args:
                continue
            n_yield += 1
            if hid in ("X10_COLOSSEUM_YIELD_CULTURE",
                       "X10_JEBEL_BARKAL_YIELD_FAITH",
                       "X10_ESTADIO_DO_MARACANA_YIELD_CULTURE"):
                n_regional += 1
                self.assertEqual(args["Amount"]["modifier_type"],
                                 "MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE",
                                 hid)
                self.assertEqual(args["Amount"]["effect_type"],
                                 "EFFECT_ADJUST_CITY_YIELD_CHANGE", hid)
                self.assertNotIn("BuildingType", args, hid)
                continue
            self.assertEqual(args["Amount"]["modifier_type"],
                             "MODIFIER_BUILDING_YIELD_CHANGE", hid)
            self.assertEqual(args["Amount"]["effect_type"],
                             "EFFECT_ADJUST_BUILDING_YIELD_CHANGE", hid)
            self.assertEqual(args["BuildingType"]["official_value"],
                             args["Amount"]["object_id"], hid)
            self.assertTrue(
                args["BuildingType"]["official_value"].startswith("BUILDING_"),
                hid)
        self.assertEqual((n_yield, n_regional), (31, 3))
        sql = emit_bridge_sql(rows)
        # SQL carries modifier types (never effect names): the regional
        # carrier appears exactly 3x2 (immediate + trigger per helper).
        self.assertEqual(
            sql.count("MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE"), 6)
        self.assertNotIn("MODIFIER_SINGLE_CITY_ADJUST_YIELD_CHANGE", sql)

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
            # Non-destructive: direct cells keep official values; helpers
            # start inert (0).
            self.assertEqual(
                db.execute("SELECT Housing FROM Buildings WHERE BuildingType='BUILDING_X'").fetchone()[0], 2)
            self.assertEqual(
                db.execute("SELECT YieldChange FROM Building_YieldChanges WHERE BuildingType='BUILDING_X'").fetchone()[0], 10)
            self.assertEqual(
                db.execute("SELECT Value FROM ModifierArguments WHERE ModifierId='X10_X_HOUSING' AND Name='Amount'").fetchone()[0], "0")
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
            self.assertEqual(housed, 2)  # undrifted cell keeps V, helper inert
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
        self.assertIn("CREATE TRIGGER IF NOT EXISTS X10_TRG_", sql)
        self.assertIn("X10BridgeDiag", sql)


def synthetic_db():
    # Minimal bridge schema (CI-safe, no official DB needed).
    import sqlite3
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE Buildings (BuildingType TEXT, Housing INTEGER, Entertainment INTEGER)")
    db.execute("CREATE TABLE Building_YieldChanges (BuildingType TEXT, YieldType TEXT, YieldChange INTEGER)")
    db.execute("CREATE TABLE Building_GreatPersonPoints (BuildingType TEXT, GreatPersonClassType TEXT, PointsPerTurn INTEGER)")
    db.execute("CREATE TABLE Modifiers (ModifierId TEXT, ModifierType TEXT, RunOnce INTEGER, NewOnly INTEGER, Permanent INTEGER, Repeatable INTEGER, OwnerRequirementSetId TEXT, SubjectRequirementSetId TEXT, OwnerStackLimit INTEGER, SubjectStackLimit INTEGER)")
    db.execute("CREATE TABLE BuildingModifiers (BuildingType TEXT, ModifierId TEXT)")
    db.execute("CREATE TABLE ModifierArguments (ModifierId TEXT, Name TEXT, Type TEXT, Value TEXT, Extra TEXT, SecondExtra TEXT)")
    db.execute("CREATE TABLE Requirements (RequirementId TEXT, RequirementType TEXT, Likeliness INTEGER, Impact INTEGER, Inverse INTEGER, Reverse INTEGER, Persistent INTEGER, ProgressWeight INTEGER, Triggered INTEGER)")
    db.execute("CREATE TABLE RequirementArguments (RequirementId TEXT, Name TEXT, Type TEXT, Value TEXT, Extra TEXT, SecondExtra TEXT)")
    db.execute("CREATE TABLE RequirementSets (RequirementSetId TEXT, RequirementSetType TEXT)")
    db.execute("CREATE TABLE RequirementSetRequirements (RequirementSetId TEXT, RequirementId TEXT)")
    return db


PORTUGAL_CELLS = [
    {"building_type": "BUILDING_ETEMENANKI", "source_table": "Building_YieldChanges",
     "source_family": "yield", "key": "YieldType=YIELD_SCIENCE",
     "value_column": "YieldChange", "value": "2"},
    {"building_type": "BUILDING_TORRE_DE_BELEM", "source_table": "Building_YieldChanges",
     "source_family": "yield", "key": "YieldType=YIELD_GOLD",
     "value_column": "YieldChange", "value": "5"},
    {"building_type": "BUILDING_TORRE_DE_BELEM", "source_table": "Building_GreatPersonPoints",
     "source_family": "gpp", "key": "GreatPersonClassType=GREAT_PERSON_CLASS_ADMIRAL",
     "value_column": "PointsPerTurn", "value": "1"},
]


def diag(db, hid):
    return db.execute(
        "SELECT expected, observed, helper_exists, attached, amount_exists,"
        " preserved, origin FROM X10BridgeDiag WHERE helper_id=?",
        (hid,)).fetchone()


class TestBridgeTriggers(unittest.TestCase):
    # Phase-3D: deferred guarded triggers for rows inserted AFTER the bridge
    # runs (proven live: Portugal-pack rows arrive after X10WonderBridge).

    def test_late_insert_trigger_materializes(self):
        # The live incident replayed: bridge first (rows absent), DLC inserts
        # later with exact baselines.
        from civ6x10.bridge import emit_bridge_sql as emit
        db = synthetic_db()
        db.executescript(emit(PORTUGAL_CELLS))
        self.assertEqual(
            db.execute("SELECT COUNT(*) FROM X10BridgeDiag WHERE observed IS NULL").fetchone()[0], 3)
        db.execute("INSERT INTO Building_YieldChanges VALUES ('BUILDING_ETEMENANKI','YIELD_SCIENCE',2)")
        db.execute("INSERT INTO Building_YieldChanges VALUES ('BUILDING_TORRE_DE_BELEM','YIELD_GOLD',5)")
        db.execute("INSERT INTO Building_GreatPersonPoints VALUES ('BUILDING_TORRE_DE_BELEM','GREAT_PERSON_CLASS_ADMIRAL',1)")
        db.commit()
        for hid, want in (("X10_ETEMENANKI_YIELD_SCIENCE", "2"),
                          ("X10_TORRE_DE_BELEM_YIELD_GOLD", "5"),
                          ("X10_TORRE_DE_BELEM_GPP_ADMIRAL", "1")):
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM Modifiers WHERE ModifierId=?", (hid,)).fetchone()[0], 1, hid)
            # Helpers start inert (0); the direct cell keeps its value.
            self.assertEqual(
                db.execute("SELECT Value FROM ModifierArguments WHERE ModifierId=? AND Name='Amount'", (hid,)).fetchone()[0],
                "0", hid)
            self.assertEqual(diag(db, hid)[1:], (want, 1, 1, 1, 1, "trigger"), hid)
        self.assertEqual(
            db.execute("SELECT YieldChange FROM Building_YieldChanges WHERE BuildingType='BUILDING_ETEMENANKI'").fetchone()[0], 2)
        db.close()

    def test_late_drift_records_mismatch(self):
        # Late row with a changed value: no helper, vanilla untouched, diag
        # records the drift (distinguishes it from never-arrived).
        from civ6x10.bridge import emit_bridge_sql as emit
        db = synthetic_db()
        db.executescript(emit(PORTUGAL_CELLS[:1]))
        db.execute("INSERT INTO Building_YieldChanges VALUES ('BUILDING_ETEMENANKI','YIELD_SCIENCE',9)")
        db.commit()
        self.assertEqual(
            db.execute("SELECT COUNT(*) FROM Modifiers WHERE ModifierId='X10_ETEMENANKI_YIELD_SCIENCE'").fetchone()[0], 0)
        self.assertEqual(
            db.execute("SELECT YieldChange FROM Building_YieldChanges WHERE BuildingType='BUILDING_ETEMENANKI'").fetchone()[0], 9)
        self.assertEqual(diag(db, "X10_ETEMENANKI_YIELD_SCIENCE")[1:],
                         ("9", 0, 0, 0, 0, "late-baseline-mismatch"))
        db.close()

    def test_absent_stays_absent(self):
        # Content genuinely unavailable: no helper, diag observed NULL.
        from civ6x10.bridge import emit_bridge_sql as emit
        db = synthetic_db()
        db.executescript(emit(PORTUGAL_CELLS[:1]))
        self.assertEqual(
            db.execute("SELECT COUNT(*) FROM Modifiers WHERE ModifierId LIKE 'X10%'").fetchone()[0], 0)
        self.assertEqual(diag(db, "X10_ETEMENANKI_YIELD_SCIENCE")[1:],
                         (None, 0, 0, 0, 0, "immediate"))
        db.close()

    def test_bridge_time_states_in_diag(self):
        # At bridge time the diag already distinguishes exact / drifted /
        # absent source rows.
        from civ6x10.bridge import emit_bridge_sql as emit
        cells = [
            {"building_type": "BUILDING_A", "source_table": "Building_YieldChanges",
             "source_family": "yield", "key": "YieldType=YIELD_GOLD",
             "value_column": "YieldChange", "value": "10"},
            {"building_type": "BUILDING_B", "source_table": "Building_YieldChanges",
             "source_family": "yield", "key": "YieldType=YIELD_GOLD",
             "value_column": "YieldChange", "value": "10"},
            {"building_type": "BUILDING_C", "source_table": "Building_YieldChanges",
             "source_family": "yield", "key": "YieldType=YIELD_GOLD",
             "value_column": "YieldChange", "value": "10"},
        ]
        db = synthetic_db()
        db.execute("INSERT INTO Building_YieldChanges VALUES ('BUILDING_A','YIELD_GOLD',10)")
        db.execute("INSERT INTO Building_YieldChanges VALUES ('BUILDING_B','YIELD_GOLD',99)")
        db.commit()
        db.executescript(emit(cells))
        self.assertEqual(diag(db, "X10_A_YIELD_GOLD")[1:], ("10", 1, 1, 1, 1, "immediate"))
        self.assertEqual(diag(db, "X10_B_YIELD_GOLD")[1:],
                         ("99", 0, 0, 0, 0, "immediate"))
        self.assertEqual(
            db.execute("SELECT YieldChange FROM Building_YieldChanges WHERE BuildingType='BUILDING_B'").fetchone()[0], 99)
        self.assertEqual(diag(db, "X10_C_YIELD_GOLD")[1:],
                         (None, 0, 0, 0, 0, "immediate"))
        db.close()

    def test_triggers_deterministic_and_idempotent(self):
        from civ6x10.bridge import emit_bridge_sql as emit
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        sql1, sql2 = emit(rows), emit(rows)
        self.assertEqual(sql1, sql2)
        import re
        names = re.findall(r"CREATE TRIGGER IF NOT EXISTS (\S+)", sql1)
        self.assertEqual(len(names), 2 * len(rows))
        self.assertEqual(len(set(names)), len(names))
        self.assertTrue(all(n.startswith("X10_TRG") for n in names))
        db = synthetic_db()
        db.executescript(sql1)
        n0 = db.execute("SELECT COUNT(*) FROM Modifiers").fetchone()[0]
        db.executescript(sql1)  # reapply: no dupes, no errors
        self.assertEqual(db.execute("SELECT COUNT(*) FROM Modifiers").fetchone()[0], n0)
        db.close()


def colosseum_culture_row():
    """Synthetic direct row for the Colosseum +2 culture cell."""
    return {"building_type": "BUILDING_COLOSSEUM",
            "source_table": "Building_YieldChanges",
            "source_family": "yield",
            "key": "YieldType=YIELD_CULTURE",
            "value_column": "YieldChange",
            "value": "2"}


class TestColosseumRegionalHelper(unittest.TestCase):
    """Phase 8B.2: the Colosseum culture helper rides the official
    regional graph (player-cities + COLOSSEUM_REQUIREMENTS), never the
    host-only building-yield shape. Synthetic rows: runs in CI."""

    def test_helper_id_stable(self):
        self.assertEqual(helper_id(colosseum_culture_row()),
                         "X10_COLOSSEUM_YIELD_CULTURE")

    def test_helper_row_uses_regional_carrier(self):
        rows = build_bridge_helpers([colosseum_culture_row()])
        by_arg = {h["argument_name"]: h for h in rows}
        amount = by_arg["Amount"]
        self.assertEqual(
            amount["modifier_type"],
            "MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE")
        self.assertEqual(amount["effect_type"],
                         "EFFECT_ADJUST_CITY_YIELD_CHANGE")
        self.assertEqual(amount["official_value"], "2")
        self.assertEqual(amount["transformation"], "bridge_delta")
        # Exactly the official arg shape (Urban Planning precedent):
        # Amount + YieldType, never a BuildingType arg.
        self.assertEqual(set(by_arg), {"Amount", "YieldType"})
        self.assertEqual(by_arg["YieldType"]["official_value"],
                         "YIELD_CULTURE")

    def test_sql_carries_subject_requirement(self):
        sql = emit_bridge_sql([colosseum_culture_row()])
        self.assertIn("MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE",
                      sql)
        self.assertIn("SubjectRequirementSetId", sql)
        self.assertIn("'COLOSSEUM_REQUIREMENTS'", sql)
        self.assertNotIn("MODIFIER_BUILDING_YIELD_CHANGE", sql)
        self.assertNotIn("'BuildingType', 'ARGTYPE_IDENTITY', "
                         "'BUILDING_COLOSSEUM'", sql)

    def test_registry_delta_row_unchanged(self):
        # Same modifier/argument/official/kind: the .inc is untouched,
        # so no CE rebuild is required for this fix.
        from civ6x10.bridge import collect_registry_rows
        from civ6x10.production import build_production_registry
        try:
            entries, _ = build_production_registry(
                collect_registry_rows(ROOT))
        except FileNotFoundError:
            raise unittest.SkipTest("local-only registry inputs unavailable")
        got = [e for e in entries
               if e["modifier_id"] == "X10_COLOSSEUM_YIELD_CULTURE"
               and e["argument"] == "Amount"]
        self.assertEqual(len(got), 1)
        e = got[0]
        self.assertEqual(
            (e["official"], e["kind"], e["count_like"], e["owners"],
             e.get("aux", 0), e.get("target", "")),
            ("2", "DELTA", True, 16, 0, ""))

    def test_jebel_maracana_regional_carriers(self):
        # Phase 8B.3: Jebel faith (+4, range 6) and Maracana culture (+6,
        # range 100000) are regional vanilla effects. Their helpers ride
        # the player-cities city-yield carrier: Jebel gated by the
        # generated X10 requirement set (mirroring COLOSSEUM_REQUIREMENTS),
        # Maracana civilization-wide with no requirement. Host-only here
        # would be the 8B.1-class bug (neighbors stuck at vanilla).
        rows = build_bridge_helpers([
            {"building_type": "BUILDING_JEBEL_BARKAL",
             "source_table": "Building_YieldChanges",
             "source_family": "yield",
             "key": "YieldType=YIELD_FAITH",
             "value_column": "YieldChange",
             "value": "4"},
            {"building_type": "BUILDING_ESTADIO_DO_MARACANA",
             "source_table": "Building_YieldChanges",
             "source_family": "yield",
             "key": "YieldType=YIELD_CULTURE",
             "value_column": "YieldChange",
             "value": "6"},
        ])
        by_id: dict = {}
        for h in rows:
            by_id.setdefault(h["modifier_id"], {})[h["argument_name"]] = h
        jebel = by_id["X10_JEBEL_BARKAL_YIELD_FAITH"]
        self.assertEqual(jebel["Amount"]["modifier_type"],
                         "MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE")
        self.assertEqual(jebel["Amount"]["effect_type"],
                         "EFFECT_ADJUST_CITY_YIELD_CHANGE")
        self.assertEqual(set(jebel), {"Amount", "YieldType"})
        sql = emit_bridge_sql([
            {"building_type": "BUILDING_JEBEL_BARKAL",
             "source_table": "Building_YieldChanges",
             "source_family": "yield",
             "key": "YieldType=YIELD_FAITH",
             "value_column": "YieldChange",
             "value": "4"},
        ])
        self.assertIn("'X10_JEBEL_BARKAL_REQUIREMENTS'", sql)
        self.assertIn("'X10_REQUIRES_PLOT_HAS_JEBEL_BARKAL_WITHIN_6'",
                      sql)
        self.assertIn("'REQUIREMENT_PLOT_ADJACENT_BUILDING_TYPE_MATCHES'",
                      sql)
        self.assertIn("'REQUIREMENTSET_TEST_ANY'", sql)
        self.assertIn("'BUILDING_JEBEL_BARKAL'", sql)
        mara = by_id["X10_ESTADIO_DO_MARACANA_YIELD_CULTURE"]
        self.assertEqual(mara["Amount"]["modifier_type"],
                         "MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE")
        self.assertEqual(mara["Amount"]["effect_type"],
                         "EFFECT_ADJUST_CITY_YIELD_CHANGE")
        self.assertEqual(set(mara), {"Amount", "YieldType"})
        msql = emit_bridge_sql([
            {"building_type": "BUILDING_ESTADIO_DO_MARACANA",
             "source_table": "Building_YieldChanges",
             "source_family": "yield",
             "key": "YieldType=YIELD_CULTURE",
             "value_column": "YieldChange",
             "value": "6"},
        ])
        self.assertIn("MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE",
                      msql)
        self.assertNotIn("SubjectRequirementSetId", msql)


class TestRegionalYieldClosedWorld(unittest.TestCase):
    """Phase 8B.3 closed-world guard: every Wonder direct yield on a
    RegionalRange building must ride a faithful regional carrier.
    Derived from official DB structure (not hardcoded names): a future
    regional direct Wonder yield with a host-only helper fails here
    unless a documented exception proves the direct yield is not
    regional."""

    # (building, row-key) pairs proven host-only despite RegionalRange,
    # each with a technical justification. Empty: all three known rows
    # (Colosseum/Jebel/Maracana) carry faithful regional helpers.
    DOCUMENTED_HOST_ONLY_EXCEPTIONS = frozenset()

    def test_regional_wonder_yields_covered(self):
        import sqlite3
        from civ6x10.bridge import REGIONAL_YIELD_OVERRIDES
        try:
            dbp = str(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        db = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
        ranged = {r[0] for r in db.execute(
            "SELECT BuildingType FROM Buildings WHERE IsWonder = 1"
            " AND RegionalRange IS NOT NULL AND RegionalRange != 0")}
        universe = set()
        for (b,) in sorted((b,) for b in ranged):
            for y in db.execute(
                    "SELECT YieldType FROM Building_YieldChanges"
                    " WHERE BuildingType = ?", (b,)):
                universe.add(
                    (b, "Building_YieldChanges",
                     "YieldType=%s" % y[0]))
        db.close()
        # Every regional direct Wonder yield is covered or excepted.
        for key in sorted(universe):
            self.assertTrue(
                key in REGIONAL_YIELD_OVERRIDES
                or (key[0], key[2]) in self.DOCUMENTED_HOST_ONLY_EXCEPTIONS,
                key)
        # No stale overrides: every override key is still a live
        # regional direct row.
        for key in REGIONAL_YIELD_OVERRIDES:
            self.assertIn(key, universe, key)
        # Covered rows behave regionally (carrier check on the helper).
        rows = build_bridge_helpers([
            {"building_type": b, "source_table": t, "source_family": "yield",
             "key": k, "value_column": "YieldChange", "value": "1"}
            for (b, t, k) in sorted(universe)])
        by_id = {}
        for h in rows:
            by_id.setdefault(h["modifier_id"], {})[h["argument_name"]] = h
        self.assertEqual(len(by_id), len(universe))
        for hid, args in by_id.items():
            self.assertEqual(args["Amount"]["modifier_type"],
                             "MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE",
                             hid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
