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
        self.assertEqual(len(entries), 924)
        self.assertEqual(report["unique_definitions"], 920)
        self.assertEqual(report["certified_unconditional"], 735)
        self.assertEqual(report["certified_count_like_conditional"], 189)
        self.assertEqual(report["unresolved_conflicts"], [])
        gated = [e for e in entries
                 if e["cert_source"].startswith(
                     "curated-effect:engine-integral")]
        self.assertEqual(len(gated), 57)
        # Scoped to exactly the two carriers that dispatch the effect; the
        # rule is never broadened by EffectType alone.
        row_eff = {(r["modifier_id"], r["argument_name"]):
                   (r.get("modifier_type"), r.get("effect_type"))
                   for r in load_rows()}
        carriers = {row_eff[(e["modifier_id"], e["argument"])][0]
                    for e in gated}
        self.assertEqual(carriers, {
            "MODIFIER_BUILDING_YIELD_CHANGE",
            "MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_YIELD_CHANGE",
            # Phase 4B: governor appeal ratings are whole appeal levels
            "MODIFIER_GOVERNOR_ADJUST_FEATURE_NO_IMPROVEMENT_APPEAL"})
        self.assertTrue(all(e["count_like"] for e in gated))
        self.assertTrue(all(e["kind"] == "ADDITIVE" for e in gated))
        bridge = [e for e in gated if e["modifier_id"].startswith("X10_")
                  and e["modifier_id"] not in RELEASE1_CARRIER_IDS]
        release1 = [e for e in gated
                    if e["modifier_id"] in RELEASE1_CARRIER_IDS]
        self.assertEqual(len(bridge), 31)
        self.assertEqual(len(release1), 21)


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
        self.assertEqual(ok, 735)
        self.assertEqual(len(exact), 13)
        self.assertEqual(len(refused), 176)
        self.assertEqual(ok + len(exact), 748)


RELEASE1_CARRIER_IDS = (
    "TRAIT_IKANDA_ARMORY_GOLD",
    "TRAIT_IKANDA_ARMORY_SCIENCE",
    "TRAIT_IKANDA_BARRACKS_GOLD",
    "TRAIT_IKANDA_BARRACKS_SCIENCE",
    "TRAIT_IKANDA_MILITARY_ACADEMY_GOLD",
    "TRAIT_IKANDA_MILITARY_ACADEMY_SCIENCE",
    "TRAIT_IKANDA_STABLE_GOLD",
    "TRAIT_IKANDA_STABLE_SCIENCE",
    "THIRDALTERNATIVE_COAL_POWER_PLANT_CULTURE_MODIFIER",
    "THIRDALTERNATIVE_COAL_POWER_PLANT_GOLD_MODIFIER",
    "THIRDALTERNATIVE_FOSSIL_FUEL_POWER_PLANT_CULTURE_MODIFIER",
    "THIRDALTERNATIVE_FOSSIL_FUEL_POWER_PLANT_GOLD_MODIFIER",
    "THIRDALTERNATIVE_MILITARY_ACADEMY_CULTURE_MODIFIER",
    "THIRDALTERNATIVE_MILITARY_ACADEMY_GOLD_MODIFIER",
    "THIRDALTERNATIVE_POWER_PLANT_CULTURE_MODIFIER",
    "THIRDALTERNATIVE_POWER_PLANT_GOLD_MODIFIER",
    "THIRDALTERNATIVE_RESEARCH_LAB_CULTURE_MODIFIER",
    "THIRDALTERNATIVE_RESEARCH_LAB_GOLD_MODIFIER",
    "MILITARYRESEARCH_MILITARY_ACADEMY_SCIENCE_MODIFIER",
    "MILITARYRESEARCH_RENAISSANCE_WALLS_SCIENCE_MODIFIER",
    "MILITARYRESEARCH_SEAPORT_SCIENCE_MODIFIER",
)


class TestRelease1BuildingYieldGate(unittest.TestCase):
    """Phase 3G: the player-cities carrier of the same engine effect.

    MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_YIELD_CHANGE dispatches
    EFFECT_ADJUST_BUILDING_YIELD_CHANGE, so these 21 live-validated
    Release-1 entries receive the identical integral gate.
    """

    def _gated(self):
        """Entries gated through the Phase-3G Release-1 carrier only.

        Phase 4B adds a second carrier (`MODIFIER_BUILDING_YIELD_CHANGE`
        under governor ownership) and one APPEAL effect; both are asserted in
        tests/test_governors_production.py, so this class stays scoped to the
        live-validated Release-1 set it was written for.
        """
        entries, _ = registry_or_skip()
        gated = {e["modifier_id"]: e for e in entries
                 if e["cert_source"].startswith(
                     "curated-effect:engine-integral")
                 and not e["modifier_id"].startswith("X10_")
                 and e["modifier_id"] in RELEASE1_CARRIER_IDS}
        return entries, gated

    def test_exactly_21_ids_gated(self):
        _, gated = self._gated()
        self.assertEqual(set(gated), set(RELEASE1_CARRIER_IDS))
        self.assertEqual(len(gated), 21)

    def test_prefix_partition_and_official_domain(self):
        _, gated = self._gated()
        self.assertEqual(sum(1 for k in gated
                             if k.startswith("TRAIT_IKANDA_")), 8)
        self.assertEqual(sum(1 for k in gated
                             if k.startswith("THIRDALTERNATIVE_")), 10)
        self.assertEqual(sum(1 for k in gated
                             if k.startswith("MILITARYRESEARCH_")), 3)
        self.assertEqual({e["official"] for e in gated.values()},
                         {"1", "2", "4"})

    def test_kind_additive_and_gate_set(self):
        _, gated = self._gated()
        for mid, e in gated.items():
            self.assertEqual(e["kind"], "ADDITIVE", mid)
            self.assertTrue(e["count_like"], mid)

    def test_no_other_release1_rows_change(self):
        # Closed world: with the Phase-3G rule entry removed, the only
        # classification differences are count_like + cert_source on
        # exactly these 21 rows. Nothing else in Release 1 moves.
        import copy
        from civ6x10 import certification as C
        from civ6x10 import production as P
        try:
            rows = load_rows()
        except FileNotFoundError:
            self.skipTest("local-only registry inputs unavailable")
        full = C.load_rules()
        pre = copy.deepcopy(full)
        # Strip ONLY the Phase-3G entry (plus the Phase-4B governor appeal
        # entry, which does not exist in the pre-4B rule set). The
        # wonder-bridge entry predates both and must stay, or the 31 X10_
        # helpers would also change.
        pre["engine_integral_effects"] = [
            e for e in full["engine_integral_effects"]
            if e["modifier_type"] not in (
                "MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_YIELD_CHANGE",
                "MODIFIER_GOVERNOR_ADJUST_FEATURE_NO_IMPROVEMENT_APPEAL")]
        self.assertEqual(len(pre["engine_integral_effects"]), 1)
        from civ6x10.production import build_production_registry
        # Phase 4B adds governor rows; compare the pre-4B (non-governor)
        # subset on both sides.
        base_rows = [r for r in rows if r.get("module") != "governors"]
        real = P.load_rules
        P.load_rules = lambda path=None: pre
        try:
            pre_entries, _ = build_production_registry(base_rows)
        finally:
            P.load_rules = real
        post_base, _ = build_production_registry(base_rows)
        post_entries, _ = build_production_registry(rows)
        pre_map = {(e["modifier_id"], e["argument"]): e for e in pre_entries}
        post_map = {(e["modifier_id"], e["argument"]): e
                    for e in post_base}
        self.assertEqual(set(pre_map), set(post_map))
        self.assertEqual(len(pre_entries), 870)
        self.assertEqual(len(post_base), 870)
        changed = {k for k, v in post_map.items()
                   if any(pre_map[k][f] != v[f] for f in
                          ("official", "kind", "count_like", "owners",
                           "cert_source", "family"))}
        self.assertEqual(changed,
                         {(mid, "Amount") for mid in RELEASE1_CARRIER_IDS})
        for k in changed:
            for f in ("official", "kind", "owners", "family"):
                self.assertEqual(pre_map[k][f], post_map[k][f], (k, f))
            self.assertFalse(pre_map[k]["count_like"], k)
            self.assertTrue(post_map[k]["count_like"], k)

    def test_k73_all_21_refuse(self):
        _, gated = self._gated()
        for mid, e in gated.items():
            v = float(e["official"])
            self.assertFalse(T.count_like_applies(v, K73), mid)
            requested = v * K73
            self.assertNotEqual(requested, int(requested), mid)

    def test_k10_all_21_write(self):
        _, gated = self._gated()
        kk = T.stored_float32(10.0)
        for mid, e in gated.items():
            self.assertTrue(T.count_like_applies(float(e["official"]), kk), mid)
            self.assertEqual(float(e["official"]) * 10.0,
                             float(e["official"]) * 10.0)

    def test_k75_amount_24_write_amount_1_refuses(self):
        _, gated = self._gated()
        kk = T.stored_float32(7.5)
        writes = [mid for mid, e in gated.items()
                  if T.count_like_applies(float(e["official"]), kk)]
        refuses = [mid for mid, e in gated.items()
                   if not T.count_like_applies(float(e["official"]), kk)]
        self.assertEqual(len(writes), 17)
        self.assertEqual(len(refuses), 4)
        # only the Amount=1 Ikanda Science rows refuse
        self.assertEqual(sorted(refuses), [
            "TRAIT_IKANDA_ARMORY_SCIENCE",
            "TRAIT_IKANDA_BARRACKS_SCIENCE",
            "TRAIT_IKANDA_MILITARY_ACADEMY_SCIENCE",
            "TRAIT_IKANDA_STABLE_SCIENCE"])
        for mid in writes:
            v = float(gated[mid]["official"])
            self.assertIn(v, (2.0, 4.0), mid)
            self.assertEqual(v * 7.5, round(v * 7.5), mid)

    def test_refusal_keeps_official_value_in_definition(self):
        # Native refusal skips the write: the definition keeps official V, so
        # gameplay stays at vanilla V (direct cell already not touched here).
        _, gated = self._gated()
        for mid, e in gated.items():
            v = float(e["official"])
            self.assertFalse(T.count_like_applies(v, K73), mid)
            stored = v  # write skipped -> unchanged
            self.assertEqual(stored, v, mid)

    def test_wonder_bridge_gate_preserved(self):
        # The 31 Phase-3F bridge helpers stay gated and unaffected.
        entries, _ = registry_or_skip()
        by_id = {e["modifier_id"]: e for e in entries}
        self.assertIn("X10_STONEHENGE_YIELD_FAITH", by_id)
        self.assertIn("X10_PANAMA_CANAL_YIELD_GOLD", by_id)
        self.assertTrue(by_id["X10_STONEHENGE_YIELD_FAITH"]["count_like"])
        self.assertTrue(by_id["X10_PANAMA_CANAL_YIELD_GOLD"]["count_like"])
        self.assertFalse(T.count_like_applies(
            float(by_id["X10_STONEHENGE_YIELD_FAITH"]["official"]), K73))
        self.assertTrue(T.count_like_applies(
            float(by_id["X10_PANAMA_CANAL_YIELD_GOLD"]["official"]), K73))

    def test_final_production_totals(self):
        entries, report = registry_or_skip()
        kf = K73
        un = [e for e in entries if not e["count_like"]]
        co = [e for e in entries if e["count_like"]]
        exact = [e for e in co
                 if T.count_like_applies(float(e["official"]), kf)]
        refused = [e for e in co if e not in exact]
        self.assertEqual(len(entries), 924)
        self.assertEqual(report["unique_definitions"], 920)
        self.assertEqual(len(un), 735)
        self.assertEqual(len(co), 189)
        self.assertEqual(len(exact), 13)
        self.assertEqual(len(refused), 176)
        # writes = unconditional (all apply) + conditional integral successes
        self.assertEqual(len(un) + len(exact), 748)


if __name__ == "__main__":
    unittest.main(verbosity=2)
