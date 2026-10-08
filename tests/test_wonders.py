"""Phase-3 Wonder module tests.

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
        open(ROOT / "civ6x10" / "rules" / "wonder_audit.yml",
             encoding="utf-8"))["wonders"]


def build_all():
    # Modifier-backed stream only (5 manifests, no bridge helpers):
    # pins the Phase-3 audit mapping. Bridge helpers are a separate
    # audited stream covered by test_bridge.py; the shipped union
    # (collect_registry_rows) is pinned in test_production.py.
    import yaml
    from civ6x10.production import build_production_registry
    rows = []
    for module in ("traits", "policies", "governments", "pantheons",
                   "wonders"):
        man = yaml.safe_load(
            open(ROOT / "manifests" / f"{module}.yml", encoding="utf-8"))
        for r in man[module]:
            r = dict(r)
            r["module"] = module
            rows.append(r)
    return build_production_registry(rows)


class TestWonderAudit(unittest.TestCase):
    def test_official_wonder_count_is_53(self):
        import sqlite3
        db_path = ROOT / "data" / "local" / "DebugGameplay_official.sqlite"
        if not db_path.is_file():
            self.skipTest("official DB copy unavailable (local-only)")
        db = sqlite3.connect(str(db_path))
        n = db.execute("SELECT COUNT(*) FROM Buildings WHERE IsWonder=1"
                       ).fetchone()[0]
        self.assertEqual(n, 53)
        audit = load_audit()
        cur = db.execute("SELECT BuildingType FROM Buildings WHERE IsWonder=1")
        for (b,) in cur.fetchall():
            self.assertIn(b, audit, b)

    def test_every_wonder_has_explicit_disposition(self):
        audit = load_audit()
        self.assertEqual(len(audit), 53)
        for building, rec in audit.items():
            self.assertIn(rec["disposition"],
                          ("COMPLETE", "PARTIAL", "UNSUPPORTED", "NONE"),
                          building)
            for row in rec["rows"]:
                self.assertIn(row["disposition"],
                              ("CERTIFIED_NUMERIC", "CERTIFIED_COUNT_LIKE",
                               "EXCLUDED"), (building, row))
                self.assertTrue(row.get("rationale", "").strip(),
                                (building, row))
                self.assertTrue(row.get("mechanism", "").strip(),
                                (building, row))

    def test_no_wonder_silently_generic(self):
        # Every registry wonder row maps to an audit CERTIFIED entry with
        # an explicit (non-boilerplate) rationale.
        audit = load_audit()
        audited = {}
        for building, rec in audit.items():
            for row in rec["rows"]:
                if row["disposition"].startswith("CERTIFIED"):
                    audited[(row["modifier_id"], row.get("argument", "Amount"))] = row
        try:
            entries, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        n = 0
        for e in entries:
            if e["owners"] != 16:
                continue
            n += 1
            key = (e["modifier_id"], e["argument"])
            self.assertIn(key, audited, key)
            self.assertGreater(len(audited[key]["rationale"]), 20, key)
        self.assertEqual(n, 97)

    def test_audit_excluded_absent_from_registry(self):
        audit = load_audit()
        try:
            entries, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        ids = {e["modifier_id"] for e in entries}
        for building, rec in audit.items():
            for row in rec["rows"]:
                if row["disposition"] == "EXCLUDED" and row.get("argument") in (
                        "Amount", "Delta", "Radius", "GovernmentSlotType",
                        "ScalingFactor", "PromotionType", "TechBoost",
                        "EndEraType"):
                    # Excluded numerics/structural must not enter; selector
                    # rows never enter by construction.
                    if row.get("official") in (None, ""):
                        continue
                    try:
                        float(row["official"])
                    except (TypeError, ValueError):
                        continue
                    self.assertNotIn(row["modifier_id"], ids,
                                     (building, row))

    def test_wonder_rollup_counts(self):
        from collections import Counter
        audit = load_audit()
        c = Counter(rec["disposition"] for rec in audit.values())
        self.assertEqual(c["COMPLETE"], 22)
        self.assertEqual(c["PARTIAL"], 29)
        self.assertEqual(c["UNSUPPORTED"] + c["NONE"], 2)


class TestWonderRegistry(unittest.TestCase):
    def test_registry_counts(self):
        try:
            entries, report = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        self.assertEqual(len(entries), 813)
        self.assertEqual(report["unresolved_conflicts"], [])
        won = [e for e in entries if e["owners"] == 16]
        self.assertEqual(len(won), 97)
        kinds = {e["kind"] for e in won}
        self.assertEqual(kinds, {"ADDITIVE", "DISCOUNT"})
        discs = sorted(e["modifier_id"] for e in won
                       if e["kind"] == "DISCOUNT")
        self.assertEqual(discs, ["MEENAKSHITEMPLE_GURU_DISCOUNT",
                                 "ORACLE_PATRONAGE_FAITH_DISCOUNT"])
        cl = [e for e in won if e["count_like"]]
        self.assertEqual(len(cl), 23)

    def test_wonder_ownership_bit(self):
        from civ6x10.production import MODULE_BITS
        self.assertEqual(MODULE_BITS["wonders"], 16)
        try:
            entries, report = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        self.assertEqual(report["shared_definitions"], 25)
        for e in entries:
            if e["owners"] & 16:
                self.assertEqual(e["owners"], 16, e)

    def test_disabling_wonders_applies_nothing(self):
        # Mirror of the native EnabledOwnerMask rule: an entry applies only
        # if ALL owning bits are enabled.
        try:
            entries, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")

        def applied(entry, enabled):
            return (entry["owners"] & enabled) == entry["owners"]

        won = [e for e in entries if e["owners"] & 16]
        self.assertTrue(won)
        full = 1 | 2 | 4 | 8 | 16
        for e in won:
            self.assertTrue(applied(e, full))
            self.assertFalse(applied(e, full & ~16))
        for e in entries:
            if not (e["owners"] & 16):
                self.assertEqual(applied(e, full),
                                 applied(e, full & ~16), e)

    def test_wonders_do_not_alter_baseline(self):
        # Non-wonder subset is exactly the 715 pantheon-phase rows plus
        # Suleiman governor titles (newly certified by the narrow Delta
        # rule): no existing row changed kind, official, family, count-like
        # status, or ownership. (One-time line-level proof that all 715
        # shipped .inc lines persist byte-identical was done at migration;
        # the shipped file has since moved to 813.)
        import yaml
        from civ6x10.production import build_production_registry
        try:
            old_rows = []
            for module in ("traits", "policies", "governments", "pantheons"):
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
        rest = [e for e in entries if not (e["owners"] & 16)]
        self.assertEqual(len(old_entries), 716)
        self.assertEqual(len(rest), 716)
        self.assertEqual(sorted(map(str, old_entries)),
                         sorted(map(str, rest)))
        sul = [e for e in rest
               if e["modifier_id"] == "SULEIMAN_GOVERNOR_POINTS"]
        self.assertEqual(len(sul), 1)
        self.assertTrue(sul[0]["count_like"])
        self.assertEqual(sul[0]["cert_source"],
                         "curated-category:GOVERNOR_TITLES")

    def test_registry_deterministic(self):
        try:
            e1, _ = build_all()
            e2, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        self.assertEqual(list(map(str, e1)), list(map(str, e2)))

    def test_wonder_k_variants(self):
        import math
        try:
            entries, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        kf = T.stored_float32(7.3)
        won = [e for e in entries if e["owners"] == 16]
        un = [e for e in won if not e["count_like"]]
        self.assertEqual(len(un), 74)
        for k in (1.0, 10.0, 4.25, kf):
            for e in un:
                v = float(e["official"])
                if e["kind"] == "DISCOUNT":
                    d = abs(v) / 100.0
                    r = (1.0 - (1.0 - d) ** k) * 100.0 * (-1 if v < 0 else 1)
                else:
                    r = v * k
                self.assertTrue(math.isfinite(r) and abs(r) <= 1000000,
                                (e, k))
        # k=1 identity spot check on a wonder row.
        zeus = [e for e in un if e["modifier_id"] ==
                "STAUEZEUS_ANTI_CAVALRY_PRODUCTION"]
        self.assertEqual(len(zeus), 1)
        self.assertEqual(float(zeus[0]["official"]) * 1.0, 50.0)
        self.assertEqual(float(zeus[0]["official"]) * 10.0, 500.0)

    def test_wonder_count_like(self):
        try:
            entries, _ = build_all()
        except FileNotFoundError:
            self.skipTest("manifests unavailable (run review locally)")
        kf = T.stored_float32(7.3)
        won_cl = sorted(e["modifier_id"] for e in entries
                        if e["owners"] == 16 and e["count_like"])
        # 23 wonder-owned conditionals: charges, appeal, capacity,
        # population, DVP, era score, Casa titles, Oracle GPP, free power.
        self.assertEqual(len(won_cl), 23)
        exact = [m for m in won_cl
                 if T.count_like_applies(
                     float([e for e in entries
                            if e["modifier_id"] == m][0]["official"]), kf)]
        self.assertEqual(exact, ["BIOSPHERE_MODIFIED_FREE_POWER"])
        # Oracle GPP refuses at 7.3f, applies at integer k.
        self.assertFalse(T.count_like_applies(2.0, kf))
        self.assertTrue(T.count_like_applies(2.0, 10.0, 0.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
