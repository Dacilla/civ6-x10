"""Phase 8B.1 mechanical EXIT expectations (Playtest-2 correction).

Every expectation here is DERIVED from the live registry plus the native
accounting rules (X10Write.cpp), never hard-coded from stale notes:

- a REPEAT row writes iff its copy index aux N satisfies N <= copies + 1
  (copies = k - 1 at integral k); otherwise it stays idle WITHOUT
  incrementing writes / post_add_match / transform_refused;
- at integral k every count-like official is integral (verified, not
  assumed), so transform_refused = 0 and post_add_match = writes;
- at fractional k (Custom 7.3) all 693 REPEAT rows refuse and only
  exact-integral count-like rows write: 1333 + 20 = 1353, refused 1128.

These tests would have caught both Playtest-2 checklist errors:
the impossible R1 `writes=2481` at x10 (correct: 1851 + 630 idle) and
the R2 Petra `20,20,10` at 7.3 (correct: 14.6,14.6,7.3).
"""
from __future__ import annotations

import re
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from civ6x10 import transforms as T
from civ6x10.bridge import collect_registry_rows
from civ6x10.production import build_production_registry


def registry_or_skip():
    try:
        return build_production_registry(collect_registry_rows(ROOT))
    except FileNotFoundError:
        raise unittest.SkipTest("local-only registry inputs unavailable")


def applies_count_like(entry, kf, kerr) -> bool:
    """Native-mirror exactness per kind (REPEAT handled by the caller)."""
    official = float(entry["official"])
    if entry["kind"] == "DELTA":
        return T.count_like_applies_delta(official, kf, kerr)
    return T.count_like_applies(official, kf, kerr)


class TestRepeatAccountingDerived(unittest.TestCase):
    def test_structure_seven_bases_copies_2_to_100(self):
        entries, _ = registry_or_skip()
        reps = [e for e in entries if e["kind"] == "REPEAT"]
        self.assertEqual(len(reps), 693)
        by_base: dict[str, list[int]] = {}
        for e in reps:
            base = e["modifier_id"].rsplit("_X10R", 1)[0]
            by_base.setdefault(base, []).append(e["aux"])
        self.assertEqual(len(by_base), 7)
        for base, auxes in by_base.items():
            self.assertEqual(sorted(auxes), list(range(2, 101)), base)

    def test_integral_preset_matrix_derived(self):
        entries, _ = registry_or_skip()
        total = len(entries)
        nonrep = [e for e in entries if e["kind"] != "REPEAT"]
        reps = [e for e in entries if e["kind"] == "REPEAT"]
        self.assertEqual(total, 2481)
        self.assertEqual(len(nonrep), 1788)
        for k in (2, 3, 5, 10, 20, 50, 100):
            copies = T.repeat_copies(float(k), 0.0)
            self.assertEqual(copies, k - 1, f"k={k}")
            active = sum(1 for e in reps if e["aux"] <= copies + 1)
            idle = len(reps) - active
            self.assertEqual(active, 7 * (k - 1), f"k={k}")
            self.assertEqual(idle, 693 - 7 * (k - 1), f"k={k}")
            # Every count-like non-REPEAT official is integral at
            # integral k (verified per entry, never assumed).
            bad = [e["modifier_id"] for e in nonrep if e["count_like"]
                   and not applies_count_like(e, float(k), 0.0)]
            self.assertEqual(bad, [], f"k={k}")
            writes = len(nonrep) + active
            self.assertEqual(writes + idle, total, f"k={k}")

    def test_x10_exit_values(self):
        # The R1 correction: writes=1851 (NOT 2481), repeat_idle=630,
        # transform_refused=0, post_add_match=1851.
        entries, _ = registry_or_skip()
        nonrep = [e for e in entries if e["kind"] != "REPEAT"]
        reps = [e for e in entries if e["kind"] == "REPEAT"]
        copies = T.repeat_copies(10.0, 0.0)
        active = sum(1 for e in reps if e["aux"] <= copies + 1)
        idle = len(reps) - active
        self.assertEqual((len(nonrep), active, idle), (1788, 63, 630))
        self.assertEqual(len(nonrep) + active, 1851)

    def test_x100_writes_everything(self):
        # x100 is the preset at which all 2481 rows write (idle 0).
        entries, _ = registry_or_skip()
        reps = [e for e in entries if e["kind"] == "REPEAT"]
        copies = T.repeat_copies(100.0, 0.0)
        self.assertEqual(copies, 99)
        self.assertTrue(all(e["aux"] <= copies + 1 for e in reps))


class TestCustom73ExitValues(unittest.TestCase):
    def test_one_exit_value_1353_refused_1128(self):
        # The R2 correction, stated as one EXIT value: writes=1353
        # (1333 unconditional + 20 exact), refused=1128.
        entries, _ = registry_or_skip()
        kf = T.stored_float32(7.3)
        kerr = T.float_quantization_error(kf)
        un = [e for e in entries if not e["count_like"]]
        exact = [e for e in entries
                 if e["count_like"] and e["kind"] != "REPEAT"
                 and applies_count_like(e, kf, kerr)]
        refused = [e for e in entries if e not in un and e not in exact]
        self.assertEqual(len(un), 1333)
        self.assertEqual(len(exact), 20)
        self.assertEqual(len(un) + len(exact), 1353)
        self.assertEqual(len(refused), 1128)

    def test_all_repeat_rows_refuse_at_73(self):
        entries, _ = registry_or_skip()
        kf = T.stored_float32(7.3)
        self.assertIsNone(T.repeat_copies(kf))
        reps = [e for e in entries if e["kind"] == "REPEAT"]
        self.assertEqual(len(reps), 693)

    def test_petra_vector_at_73(self):
        # Would-have-caught: the checklist claimed Petra 20,20,10 at 7.3.
        # 2,2,1 x 7.3 = 14.6,14.6,7.3 (vectors are not count-like).
        self.assertEqual(T.vector_multiply("2,2,1", T.stored_float32(7.3)),
                         "14.6,14.6,7.3")
        entries, _ = registry_or_skip()
        by_id = {e["modifier_id"]: e for e in entries}
        self.assertFalse(by_id["PETRA_YIELD_MODIFIER"]["count_like"])

    def test_verification_buffer_never_truncates(self):
        # Touched touched[8] is per definition: no definition carries more
        # than 8 X10 arguments, so post_add_match always equals writes.
        entries, _ = registry_or_skip()
        from collections import Counter
        widest = max(Counter(e["modifier_id"] for e in entries).values())
        self.assertLessEqual(widest, 8)


class TestTypedFillers(unittest.TestCase):
    def test_counts_cover_x100_worst_case(self):
        from civ6x10.eight_b import FILLER_COUNTS, SLOT_BASES
        from collections import Counter
        per_type_sources = Counter(slot for _, slot, _, _, _ in SLOT_BASES)
        for slot, count in FILLER_COUNTS.items():
            # Zero real cards assumed: fillers alone must cover every
            # bonus slot of the type at x100 (100 per source).
            self.assertGreaterEqual(count, 100 * per_type_sources[slot],
                                    slot)
        self.assertEqual(set(FILLER_COUNTS),
                         {"SLOT_MILITARY", "SLOT_DIPLOMATIC",
                          "SLOT_ECONOMIC", "SLOT_WILDCARD"})

    def test_sql_uses_valid_loc_and_typed_slots(self):
        from civ6x10.eight_b import emit_slot_sql
        sql = emit_slot_sql()
        self.assertNotIn("LOC_POLICY_X10_FILLER_DESCRIPTION", sql)
        self.assertIn("LOC_POLICY_X10_FILLER_DESC", sql)
        text = (ROOT / "controller" / "X10" / "Config"
                / "X10Text.sql").read_text(encoding="utf-8")
        self.assertIn("LOC_POLICY_X10_FILLER_DESC", text)
        self.assertIn("LOC_POLICY_X10_FILLER_NAME", text)
        for slot in ("SLOT_MILITARY", "SLOT_DIPLOMATIC",
                     "SLOT_ECONOMIC", "SLOT_WILDCARD"):
            self.assertIn(f"'{slot}', 1", sql)
        # Phase 8B.4: dormant fillers (ExplicitUnlock, no civic) --
        # never Code of Laws.
        self.assertNotIn("CIVIC_CODE_OF_LAWS", sql)
        self.assertIn("NULL, 'LOC_POLICY_X10_FILLER_NAME'", sql)
        from civ6x10.eight_b import FILLER_COUNTS
        ids = re.findall(r"POLICY_X10_FILLER_[A-Z]+_\d{3}", sql)
        self.assertEqual(len(set(ids)), sum(FILLER_COUNTS.values()))
        by_fam = Counter(i.rsplit("_", 1)[0] for i in set(ids))
        for slot, count in FILLER_COUNTS.items():
            fam = "POLICY_X10_FILLER_" + slot.replace("SLOT_", "")
            self.assertEqual(by_fam[fam], count, fam)

    def test_no_backwards_wildcard_comment(self):
        src = (ROOT / "civ6x10" / "eight_b.py").read_text(encoding="utf-8")
        self.assertNotIn("Wildcard cards can occupy any slot type", src)


class TestSecretSocietyOwnership(unittest.TestCase):
    SOCIETY_IDS = {
        "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_3_AMENITY_FROM_COUNTERSPY",
        "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_3_LOYALTY_FROM_COUNTERSPY",
        "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_4_GOLD_INTEREST",
        "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_4_SPY_SUCCESS_GRANTS_CULTURE",
        "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_4_SPY_SUCCESS_GRANTS_FAITH",
        "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_4_SPY_SUCCESS_GRANTS_GOLD",
        "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_4_SPY_SUCCESS_GRANTS_SCIENCE",
        "GOVERNOR_PROMOTION_VOIDSINGERS_2_CULTURE_FROM_FAITH",
        "GOVERNOR_PROMOTION_VOIDSINGERS_2_GOLD_FROM_FAITH",
        "GOVERNOR_PROMOTION_VOIDSINGERS_2_SCIENCE_FROM_FAITH",
        "HERMETIC_ORDER_COMANDANTE_GENERAL_LEY_LINE_SCIENCE",
        "HERMETIC_ORDER_GREAT_ADMIRAL_LEY_LINE_SCIENCE",
        "HERMETIC_ORDER_GREAT_ARTIST_LEY_LINE_CULTURE",
        "HERMETIC_ORDER_GREAT_ENGINEER_LEY_LINE_PRODUCTION",
        "HERMETIC_ORDER_GREAT_GENERAL_LEY_LINE_SCIENCE",
        "HERMETIC_ORDER_GREAT_MERCHANT_LEY_LINE_GOLD",
        "HERMETIC_ORDER_GREAT_MUSICIAN_LEY_LINE_CULTURE",
        "HERMETIC_ORDER_GREAT_PROPHET_LEY_LINE_FAITH",
        "HERMETIC_ORDER_GREAT_SCIENTIST_LEY_LINE_SCIENCE",
        "HERMETIC_ORDER_GREAT_WRITER_LEY_LINE_CULTURE",
        "SECRET_SOCIETY_GRANT_ONE_VAMPIRE_BUILD",
        "SECRET_SOCIETY_GRANT_TWO_VAMPIRE_BUILDS",
    }

    def test_all_society_rows_solely_modes_owned(self):
        from civ6x10.production import MODULE_BITS
        entries, _ = registry_or_skip()
        by_id: dict[str, list] = {}
        for e in entries:
            by_id.setdefault(e["modifier_id"], []).append(e)
        for mid in sorted(self.SOCIETY_IDS):
            self.assertIn(mid, by_id, mid)
            for e in by_id[mid]:
                self.assertEqual(e["owners"], MODULE_BITS["modes"], mid)
                self.assertEqual(e["owner_names"], ["modes"], mid)

    def test_governors_manifest_has_no_society_rows(self):
        import yaml
        from civ6x10.governors import is_secret_society_manifest_row
        p = ROOT / "manifests" / "governors.yml"
        if not p.is_file():
            raise unittest.SkipTest("local-only registry inputs unavailable")
        doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        rows = doc["governors"]
        self.assertEqual(len(rows), 48)
        self.assertEqual(
            [r["modifier_id"] for r in rows
             if is_secret_society_manifest_row(r)], [])

    def test_modes_manifest_carries_all_22(self):
        import yaml
        p = ROOT / "manifests" / "modes.yml"
        if not p.is_file():
            raise unittest.SkipTest("local-only registry inputs unavailable")
        doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        ids = {r["modifier_id"] for r in doc["modes"]}
        self.assertTrue(self.SOCIETY_IDS <= ids)
        # vampire duplicate still collapsed with both provenances
        vamp = [r for r in doc["modes"] if r["modifier_id"] ==
                "SECRET_SOCIETY_GRANT_ONE_VAMPIRE_BUILD"]
        self.assertEqual(len(vamp), 1)
        srcs = " ".join(str(s) for s in vamp[0].get("backlog_sources", []))
        self.assertIn("SANGUINE_PACT_3", srcs)
        self.assertIn("SANGUINE_PACT_4", srcs)

    def test_setup_copy_matches_ownership(self):
        text = (ROOT / "controller" / "X10" / "Config"
                / "X10Text.sql").read_text(encoding="utf-8")
        self.assertIn("'Affects: Governors')", text)
        self.assertNotIn("Governors & Secret Societies", text)
        self.assertIn("Includes Secret Society bonuses.", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
