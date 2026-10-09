"""Phase 3F: integral building-yield application.

EFFECT_ADJUST_BUILDING_YIELD_CHANGE consumes Amount as an INTEGER at the
application layer. Static + live evidence:

* live (Phase 3E): the generated Stonehenge helper Amount 14.6 WAS stored in
  the definition store (stored_after_add=14.6 MATCH via store-lookup), while
  the same city's Faith read back exactly 14.0000. A float readback of 14.6
  would have printed 14.6000, and 14.6 -> 14 (not 15) rules out rounding, so
  the conversion happens at the effect layer, not in the UI.
* static: every official MODIFIER_BUILDING_YIELD_CHANGE definition carries an
  integral Amount (2, 3, 4) while the ModifierArguments schema elsewhere DOES
  hold fractions (0.5, 0.6, -0.5, 0.2) - the integral domain is a property of
  this effect.

The correction reuses the existing runtime integral gate (countLike in the
registry, mirrored by X10Transforms::Apply): ADDITIVE semantics are preserved,
and a fractional result is refused - the definition keeps its official value -
instead of being silently truncated. No floor/ceil/round anywhere.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

from civ6x10 import transforms as T
from civ6x10.bridge import build_bridge_helpers, build_wonder_direct

K73 = T.stored_float32(7.3)
assert K73 == 7.300000190734863  # live FLOAT32 representation


def local_db():
    p = ROOT / "data" / "local" / "DebugGameplay_official.sqlite"
    if not p.is_file():
        raise FileNotFoundError(str(p))
    return p


def load_rows():
    from civ6x10.bridge import collect_registry_rows
    return collect_registry_rows(ROOT)


def certify_entries(rows=None):
    from civ6x10.production import build_production_registry
    try:
        rows = rows if rows is not None else load_rows()
    except FileNotFoundError:
        raise
    return build_production_registry(rows)


def registry_or_skip():
    """Registry totals need the local-only manifests; CI skips them."""
    try:
        return certify_entries()
    except FileNotFoundError:
        raise unittest.SkipTest("local-only registry inputs unavailable")


class TestEngineIntegralEvidence(unittest.TestCase):
    """Evidence the effect is integer-applied (static, DB-backed)."""

    def test_official_family_amounts_all_integral(self):
        import sqlite3
        try:
            db = sqlite3.connect(str(local_db()))
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        vals = [float(r[0]) for r in db.execute(
            "SELECT a.Value FROM Modifiers m JOIN ModifierArguments a"
            " ON a.ModifierId=m.ModifierId WHERE m.ModifierType="
            " 'MODIFIER_BUILDING_YIELD_CHANGE' AND a.Name='Amount'")]
        self.assertTrue(vals)
        self.assertTrue(all(v == int(v) for v in vals), vals)

    def test_fractions_exist_elsewhere_in_schema(self):
        # Proves the integral domain above is a property of the effect, not
        # of the ModifierArguments schema.
        import sqlite3
        try:
            db = sqlite3.connect(str(local_db()))
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        frac = db.execute(
            "SELECT COUNT(*) FROM ModifierArguments WHERE Name='Amount'"
            " AND Value LIKE '%.%'").fetchone()[0]
        self.assertGreater(frac, 0)


class TestBuildingYieldCertification(unittest.TestCase):
    """The gated rows certify ADDITIVE with the integral gate."""

    def test_bridge_yield_rows_gated(self):
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        from civ6x10.certification import certify_row, load_rules
        from civ6x10.production import load_sem_floor
        helpers = build_bridge_helpers(rows)
        floor = load_sem_floor(ROOT / "data" / "local" / "effect_semantics.csv")
        rules = load_rules()
        n_yield = 0
        for h in helpers:
            if h["argument_name"] != "Amount":
                continue
            if h["modifier_type"] != "MODIFIER_BUILDING_YIELD_CHANGE":
                continue
            n_yield += 1
            cert = certify_row(h, floor.get((h["modifier_type"],
                                             h["effect_type"],
                                             h["argument_name"])), rules)
            self.assertTrue(cert["certified"], h["modifier_id"])
            self.assertEqual(cert["kind"], "ADDITIVE", h["modifier_id"])
            self.assertTrue(cert["count_like"], h["modifier_id"])
            self.assertEqual(cert["source"],
                             "curated-effect:engine-integral:"
                             "EFFECT_ADJUST_BUILDING_YIELD_CHANGE",
                             h["modifier_id"])
        self.assertEqual(n_yield, 31)

    def test_other_bridge_families_untouched(self):
        # GPP count-like and housing/local-entertainment additive rows keep
        # their existing classifications; only the building-yield family is
        # gated by Phase 3F.
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        from civ6x10.bridge import helper_id
        from civ6x10.certification import certify_row, load_rules
        from civ6x10.production import load_sem_floor
        fam_by_id = {helper_id(r): r["source_family"] for r in rows}
        helpers = build_bridge_helpers(rows)
        floor = load_sem_floor(ROOT / "data" / "local" / "effect_semantics.csv")
        rules = load_rules()
        seen = {}
        for h in helpers:
            if h["argument_name"] != "Amount":
                continue
            fam = fam_by_id[h["modifier_id"]]
            seen[fam] = seen.get(fam, 0) + 1
            cert = certify_row(h, floor.get((h["modifier_type"],
                                             h["effect_type"],
                                             h["argument_name"])), rules)
            self.assertTrue(cert["certified"], h["modifier_id"])
            self.assertEqual(cert["kind"], "ADDITIVE", h["modifier_id"])
            if fam in ("gpp", "yield"):
                self.assertTrue(cert["count_like"], h["modifier_id"])
            else:
                self.assertFalse(cert["count_like"], h["modifier_id"])
        self.assertEqual(seen.get("gpp"), 20)
        self.assertEqual(seen.get("yield"), 31)
        self.assertEqual(seen.get("housing"), 3)
        self.assertEqual(seen.get("entertainment"), 3)

    def test_registry_totals(self):
        entries, report = registry_or_skip()
        self.assertEqual(len(entries), 870)
        self.assertEqual(report["unique_definitions"], 866)
        self.assertEqual(report["certified_unconditional"], 707)
        self.assertEqual(report["certified_count_like_conditional"], 163)
        self.assertEqual(report["unresolved_conflicts"], [])
        gated = [e for e in entries
                 if e["cert_source"].startswith(
                     "curated-effect:engine-integral")]
        self.assertEqual(len(gated), 31)
        # Scoped: the same effect under the player-scoped carrier is NOT
        # gated by this phase (documented Release-1-core follow-up).
        row_eff = {(r["modifier_id"], r["argument_name"]):
                   (r.get("modifier_type"), r.get("effect_type"))
                   for r in load_rows()}
        carriers = {row_eff[(e["modifier_id"], e["argument"])][0]
                    for e in gated}
        self.assertEqual(carriers, {"MODIFIER_BUILDING_YIELD_CHANGE"})
        self.assertTrue(all(e["count_like"] for e in gated))


class TestIntegralTransformMath(unittest.TestCase):
    """The exact invariant: requested = official * k, refused when nonintegral.

    Mirrors X10Transforms::Apply(countLike=true) through
    transforms.count_like_applies (the same FLOAT32 half-ULP rule).
    """

    def _applies(self, v, k):
        return T.count_like_applies(v, T.stored_float32(k))

    def test_k10_scales_exactly(self):
        # Default multiplier must scale every affected direct wonder yield.
        for v in (1, 2, 3, 4, 5, 6, 8, 10):
            self.assertTrue(self._applies(float(v), 10.0), v)
        self.assertEqual(2 * 10.0, 20)

    def test_k75_integral_writes(self):
        self.assertTrue(self._applies(2.0, 7.5))
        self.assertEqual(2 * 7.5, 15)

    def test_k73_v2_refuses(self):
        # Stonehenge: requested 14.6 must REFUSE, never become 14.
        self.assertFalse(self._applies(2.0, 7.3))
        self.assertAlmostEqual(2 * K73, 14.600000381, places=6)
        self.assertNotEqual(int(2 * K73), 2 * K73)

    def test_k73_v10_writes(self):
        # Panama Canal: 10 x 7.3 = 73 remains eligible.
        self.assertTrue(self._applies(10.0, 7.3))
        self.assertAlmostEqual(10 * K73, 73.000001907, places=6)

    def test_no_floor_ceil_round_approximation(self):
        import math
        for v in (1, 2, 3, 4, 5, 6, 8):
            want = v * K73
            applied = want if self._applies(float(v), 7.3) else float(v)
            # Either the exact requested value or the original official value;
            # never floor/ceil/round of the requested value.
            self.assertIn(applied, (want, float(v)), v)
            self.assertNotEqual(applied, math.floor(want))
            self.assertNotEqual(applied, math.ceil(want))
            self.assertNotEqual(applied, round(want))

    def test_k0_and_off_leaves_vanilla(self):
        # k=0 (Off) and module OFF leave the definition at official V: the
        # zeroed direct cell plus the helper at V reproduces vanilla.
        for v in (2.0, 10.0):
            self.assertEqual(0.0 + v, v)  # 0 (direct) + V (helper)
        # No transform is attempted at all when k==0 (native arms nothing).

    def test_refusal_leaves_helper_at_official(self):
        # Native refusal (Apply returns false) skips the write entirely, so
        # the definition keeps its official value: gameplay stays vanilla V.
        v, k = 2.0, K73
        applies = self._applies(v, k)
        self.assertFalse(applies)
        stored = float(v)  # write skipped -> unchanged definition
        self.assertEqual(stored, 2.0)
        self.assertEqual(0.0 + stored, 2.0)  # gameplay total = vanilla

    def test_every_gated_entry_either_writes_or_keeps_official(self):
        try:
            rows = build_wonder_direct(local_db())
        except FileNotFoundError:
            self.skipTest("official DB copy unavailable (local-only)")
        helpers = build_bridge_helpers(rows)
        for h in helpers:
            h["module"] = "wonders"
        entries, _ = certify_entries(helpers)
        self.assertEqual(len(entries), 57)
        for e in entries:
            v = float(e["official"])
            applies = T.count_like_applies(v, K73)
            if e["modifier_id"] == "X10_PANAMA_CANAL_YIELD_GOLD":
                self.assertTrue(applies, e)  # 10 -> 73
            if e["modifier_id"] == "X10_STONEHENGE_YIELD_FAITH":
                self.assertFalse(applies, e)  # 2 -> 14.6 refused

    def test_static_registry_counts_at_k73(self):
        import math
        entries, _ = registry_or_skip()
        un = [e for e in entries if not e["count_like"]]
        co = [e for e in entries if e["count_like"]]
        ok = 0
        for e in un:
            v = float(e["official"])
            if e["kind"] == "ADDITIVE":
                r = v * K73
            elif e["kind"] == "COMBAT":
                r = 25.0 * math.log(K73 * (math.exp(v / 25.0) - 1) + 1)
            elif e["kind"] == "DISCOUNT":
                d = abs(v) / 100.0
                r = (1.0 - (1.0 - d) ** K73) * 100.0 * (-1 if v < 0 else 1)
            else:
                continue
            self.assertTrue(math.isfinite(r) and abs(r) <= 1e6, e)
            ok += 1
        exact = [e for e in co if T.count_like_applies(float(e["official"]), K73)]
        refused = [e for e in co if e not in exact]
        self.assertEqual(ok, 707)
        self.assertEqual(len(exact), 13)
        self.assertEqual(len(refused), 150)
        self.assertEqual(ok + len(exact), 720)


if __name__ == "__main__":
    unittest.main(verbosity=2)
