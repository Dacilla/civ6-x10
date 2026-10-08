"""Phase-2 Pantheon module tests.

Local-only tests need manifests/data-local (gitignored) and skip in CI.
Audit-file and source-wiring tests run everywhere.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

from civ6x10 import transforms as T


def load_audit():
    import yaml
    return yaml.safe_load(
        open(ROOT / "civ6x10" / "rules" / "pantheon_audit.yml",
             encoding="utf-8"))["pantheons"]


def load_pantheon_manifest():
    import yaml
    man = yaml.safe_load(
        open(ROOT / "manifests" / "pantheons.yml", encoding="utf-8"))
    rows = []
    for r in man["pantheons"]:
        r = dict(r)
        r["module"] = "pantheons"
        rows.append(r)
    return rows


def build_all():
    import yaml
    from civ6x10.production import build_production_registry
    rows = []
    for module in ("traits", "policies", "governments", "pantheons"):
        man = yaml.safe_load(
            open(ROOT / "manifests" / f"{module}.yml", encoding="utf-8"))
        for r in man[module]:
            r = dict(r)
            r["module"] = module
            rows.append(r)
    return build_production_registry(rows)


class TestPantheonAudit(unittest.TestCase):
    def test_every_pantheon_has_explicit_disposition(self):
        audit = load_audit()
        self.assertEqual(len(audit), 23)
        for belief, rec in audit.items():
            self.assertIn(rec["disposition"], ("COMPLETE", "PARTIAL"), belief)
            self.assertTrue(rec["rows"], belief)
            for row in rec["rows"]:
                self.assertIn(row["disposition"],
                              ("CERTIFIED_NUMERIC", "CERTIFIED_COUNT_LIKE",
                               "EXCLUDED"), (belief, row))
                self.assertTrue(row.get("rationale", "").strip(),
                                (belief, row))
                self.assertTrue(row.get("mechanism", "").strip(),
                                (belief, row))

    def test_no_pantheon_silently_generic(self):
        # Every registry pantheon row maps to an audit CERTIFIED entry with
        # an explicit (non-boilerplate) rationale.
        audit = load_audit()
        audited = {}
        for belief, rec in audit.items():
            for row in rec["rows"]:
                if row["disposition"].startswith("CERTIFIED"):
                    audited[(row["modifier_id"], row.get("argument", "Amount"))] = row
        try:
            entries, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        for e in entries:
            if e["owners"] != 8:
                continue
            key = (e["modifier_id"], e["argument"])
            self.assertIn(key, audited, key)
            self.assertGreater(len(audited[key]["rationale"]), 40, key)

    def test_audit_excluded_absent_from_registry(self):
        audit = load_audit()
        try:
            entries, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        ids = {e["modifier_id"] for e in entries}
        for belief, rec in audit.items():
            for row in rec["rows"]:
                if row["disposition"] == "EXCLUDED":
                    self.assertNotIn(row["modifier_id"], ids,
                                     (belief, row))

    def test_official_pantheon_count_is_23(self):
        import sqlite3
        db_path = ROOT / "data" / "local" / "DebugGameplay_official.sqlite"
        if not db_path.is_file():
            self.skipTest("official DB copy unavailable (local-only)")
        db = sqlite3.connect(str(db_path))
        n = db.execute("SELECT COUNT(*) FROM Beliefs "
                       "WHERE BeliefClassType='BELIEF_CLASS_PANTHEON'").fetchone()[0]
        self.assertEqual(n, 23)
        audit = load_audit()
        cur = db.execute("SELECT BeliefType FROM Beliefs "
                         "WHERE BeliefClassType='BELIEF_CLASS_PANTHEON'")
        for (b,) in cur.fetchall():
            self.assertIn(b, audit, b)

    def test_goddess_of_festivals_disposition(self):
        import sqlite3
        audit = load_audit()
        rows = audit["BELIEF_GODDESS_OF_FESTIVALS"]["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["modifier_id"],
            "GODDESS_OF_FESTIVALS_PLANTATION_CULTURE_MODIFIER")
        self.assertEqual(rows[0]["disposition"], "CERTIFIED_NUMERIC")
        # The historical mod targeted a stale ID: prove it matches nothing.
        db_path = ROOT / "data" / "local" / "DebugGameplay_official.sqlite"
        if not db_path.is_file():
            self.skipTest("official DB copy unavailable (local-only)")
        db = sqlite3.connect(str(db_path))
        n = db.execute("SELECT COUNT(*) FROM Modifiers WHERE ModifierId=?",
                       ("GODDESS_OF_FESTIVALS_PLANTATION_TAG_FOOD_MODIFIER",)
                       ).fetchone()[0]
        self.assertEqual(n, 0)


class TestPantheonRegistry(unittest.TestCase):
    def test_registry_counts(self):
        try:
            entries, report = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        self.assertEqual(len(entries), 715)
        self.assertEqual(report["unresolved_conflicts"], [])
        pan = [e for e in entries if e["owners"] == 8]
        self.assertEqual(len(pan), 31)
        kinds = {e["kind"] for e in pan}
        self.assertEqual(kinds, {"ADDITIVE"})
        cl = [e for e in pan if e["count_like"]]
        self.assertEqual(len(cl), 3)
        self.assertEqual({e["modifier_id"] for e in cl},
                         {"DIVINE_SPARK_HOLY_SITE_MODIFIER",
                          "DIVINE_SPARK_SCIENTIST_MODIFIER",
                          "DIVINE_SPARK_WRITER_MODIFIER"})

    def test_pantheon_ownership_bit(self):
        from civ6x10.production import MODULE_BITS
        self.assertEqual(MODULE_BITS["pantheons"], 8)
        try:
            entries, report = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        self.assertEqual(report["shared_definitions"], 25)
        for e in entries:
            if e["owners"] & 8:
                self.assertEqual(e["owners"], 8, e)

    def test_disabling_pantheons_applies_nothing(self):
        # Mirror of the native EnabledOwnerMask rule: an entry applies only
        # if ALL owning bits are enabled.
        try:
            entries, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")

        def applied(entry, enabled):
            return (entry["owners"] & enabled) == entry["owners"]

        pan = [e for e in entries if e["owners"] & 8]
        self.assertTrue(pan)
        for e in pan:
            self.assertTrue(applied(e, 1 | 2 | 4 | 8))
            self.assertFalse(applied(e, 1 | 2 | 4))
        for e in entries:
            if not (e["owners"] & 8):
                self.assertEqual(applied(e, 1 | 2 | 4 | 8),
                                 applied(e, 1 | 2 | 4), e)

    def test_pantheons_do_not_alter_baseline(self):
        # The 684 pre-pantheon rows are byte/semantic stable: rebuild from
        # the three old manifests and compare against the full build minus
        # pantheon-owned entries.
        import yaml
        from civ6x10.production import build_production_registry
        try:
            old_rows = []
            for module in ("traits", "policies", "governments"):
                man = yaml.safe_load(
                    open(ROOT / "manifests" / f"{module}.yml",
                         encoding="utf-8"))
                for r in man[module]:
                    r = dict(r)
                    r["module"] = module
                    old_rows.append(r)
            old_entries, _ = build_production_registry(old_rows)
            entries, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        rest = [e for e in entries if not (e["owners"] & 8)]
        self.assertEqual(len(old_entries), 684)
        self.assertEqual(len(rest), 684)
        self.assertEqual(
            sorted(map(str, old_entries)), sorted(map(str, rest)))

    def test_registry_deterministic(self):
        try:
            e1, _ = build_all()
            e2, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        self.assertEqual(list(map(str, e1)), list(map(str, e2)))

    def test_pantheon_k_variants(self):
        import math
        try:
            entries, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        kf = T.stored_float32(7.3)
        pan = [e for e in entries if e["owners"] == 8]
        un = [e for e in pan if not e["count_like"]]
        self.assertEqual(len(un), 28)
        for k in (1.0, 10.0, 4.25, kf):
            for e in un:
                r = float(e["official"]) * k
                self.assertTrue(math.isfinite(r) and abs(r) <= 1000000,
                                (e, k))
        # k=1 identity spot check on a pantheon row.
        forge = [e for e in un if e["modifier_id"] ==
                 "GOD_OF_THE_FORGE_UNIT_ANCIENT_CLASSICAL_PRODUCTION_MODIFIER"]
        self.assertEqual(len(forge), 1)
        self.assertEqual(float(forge[0]["official"]) * 1.0, 25.0)
        self.assertEqual(float(forge[0]["official"]) * 10.0, 250.0)

    def test_pantheon_count_like(self):
        try:
            entries, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        kf = T.stored_float32(7.3)
        sparks = sorted(
            e["modifier_id"] for e in entries
            if e["owners"] == 8 and e["count_like"])
        self.assertEqual(sparks, ["DIVINE_SPARK_HOLY_SITE_MODIFIER",
                                  "DIVINE_SPARK_SCIENTIST_MODIFIER",
                                  "DIVINE_SPARK_WRITER_MODIFIER"])
        for e in entries:
            if e["modifier_id"] in sparks:
                self.assertEqual(e["official"], "1")
                # 1 x FLOAT32(7.3) = 7.3000002 refuses; 1 x 10 applies.
                self.assertFalse(T.count_like_applies(1.0, kf))
                self.assertTrue(T.count_like_applies(1.0, 10.0, 0.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
