"""Phase 8B structural gates: owner-mask growth, new-kind invariants,
module-off/shared-owner rules, and BRS/EPC non-dependency.

Mirrors the native EnabledOwnerMask loop (X10Write.cpp) and the REPEAT /
VECTOR / DELTA registry contracts. Live population behavior is proven in
Playtest 2; these prove the static structure it depends on.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

from civ6x10.production import MODULE_BITS, build_production_registry
from civ6x10.bridge import collect_registry_rows


def registry_or_skip():
    try:
        return build_production_registry(collect_registry_rows(ROOT))
    except FileNotFoundError:
        raise unittest.SkipTest("local-only registry inputs unavailable")


def enabled_owner_mask(mods):
    """Python mirror of native EnabledOwnerMask (loop-built, 13 modules)."""
    mask = 0
    for i, on in enumerate(mods):
        if on:
            mask |= (1 << i)
    return mask


MODULE_ORDER = ["traits", "policies", "governments", "pantheons", "wonders",
                "governors", "suzerain", "promotions", "dedications",
                "modes", "religion", "greatpeople", "projects"]


class TestOwnerMaskGrowth(unittest.TestCase):
    def test_bits_match_canonical_order(self):
        for i, name in enumerate(MODULE_ORDER):
            self.assertEqual(MODULE_BITS[name], 1 << i, name)

    def test_high_bits_no_truncation(self):
        # Bits >= 0x80 and >= 0x100 behave like the low seven: the int
        # mask holds all 13 without silent truncation.
        self.assertEqual(MODULE_BITS["promotions"], 0x80)
        self.assertEqual(MODULE_BITS["dedications"], 0x100)
        self.assertEqual(MODULE_BITS["modes"], 0x200)
        self.assertEqual(MODULE_BITS["religion"], 0x400)
        self.assertEqual(MODULE_BITS["greatpeople"], 0x800)
        self.assertEqual(MODULE_BITS["projects"], 0x1000)
        self.assertEqual(
            enabled_owner_mask([True] * 13), 0x1FFF)
        self.assertEqual(
            enabled_owner_mask([True] * 7 + [False] * 6), 0x7F)

    def test_single_high_bit_isolation(self):
        for i in range(7, 13):
            mods = [False] * 13
            mods[i] = True
            self.assertEqual(enabled_owner_mask(mods), 1 << i)


class TestModuleOffAndShared(unittest.TestCase):
    def test_disabling_new_module_blocks_its_entries(self):
        entries, _ = registry_or_skip()
        for name in ("promotions", "dedications", "modes", "religion",
                     "greatpeople", "projects"):
            bit = MODULE_BITS[name]
            owned = [e for e in entries if e["owners"] == bit]
            self.assertTrue(owned, name)
            enabled = 0x1FFF & ~bit
            for e in owned:
                self.assertNotEqual(e["owners"] & enabled, e["owners"],
                                    (name, e["modifier_id"]))

    def test_shared_union_requires_all_owners(self):
        # The greatpeople+promotions definition applies only with BOTH on.
        entries, _ = registry_or_skip()
        both = MODULE_BITS["greatpeople"] | MODULE_BITS["promotions"]
        shared = [e for e in entries if e["owners"] == both]
        self.assertEqual(len(shared), 1)
        e = shared[0]
        self.assertEqual(
            (e["owners"] & MODULE_BITS["greatpeople"]), MODULE_BITS["greatpeople"])
        self.assertNotEqual(e["owners"] & MODULE_BITS["greatpeople"],
                            e["owners"])
        self.assertNotEqual(e["owners"] & MODULE_BITS["promotions"],
                            e["owners"])

    def test_suzerain_bit_covers_envoys(self):
        entries, _ = registry_or_skip()
        suz = [e for e in entries if e["owners"] == MODULE_BITS["suzerain"]]
        self.assertEqual(len(suz), 123)


class TestRepeatInvariants(unittest.TestCase):
    def test_copies_well_formed(self):
        entries, _ = registry_or_skip()
        reps = [e for e in entries if e["kind"] == "REPEAT"]
        self.assertEqual(len(reps), 693)
        seen_aux = {}
        for e in reps:
            self.assertEqual(e["official"], "SLOT_NONE", e["modifier_id"])
            self.assertTrue(e["count_like"], e["modifier_id"])
            self.assertIn(e["target"], ("SLOT_DIPLOMATIC", "SLOT_WILDCARD",
                                        "SLOT_MILITARY", "SLOT_ECONOMIC"),
                          e["modifier_id"])
            self.assertTrue(2 <= e["aux"] <= 100, e["modifier_id"])
            base = e["modifier_id"].rsplit("_X10R", 1)[0]
            seen_aux.setdefault(base, []).append(e["aux"])
        # Seven bases (4 wonder + 3 trait), copies 2..100 each, no gaps.
        self.assertEqual(len(seen_aux), 7)
        for base, auxes in seen_aux.items():
            self.assertEqual(sorted(auxes), list(range(2, 101)), base)

    def test_fractional_k_activates_nothing(self):
        from civ6x10.transforms import repeat_copies, stored_float32
        self.assertIsNone(repeat_copies(stored_float32(7.3)))
        self.assertEqual(repeat_copies(10.0, 0.0), 9)
        self.assertEqual(repeat_copies(100.0, 0.0), 99)
        self.assertIsNone(repeat_copies(101.0, 0.0))


class TestVectorInvariants(unittest.TestCase):
    def test_vectors_short_and_certified(self):
        entries, _ = registry_or_skip()
        vecs = [e for e in entries if e["kind"] == "VECTOR"]
        self.assertEqual(len(vecs), 4)
        from civ6x10.transforms import vector_multiply
        for e in vecs:
            # Every certified vector fits SSO-inline at every k<=100.
            self.assertLess(len(vector_multiply(e["official"], 100.0)), 16,
                            e["modifier_id"])
            self.assertTrue(e["cert_source"].startswith(
                "curated-effect:vector:"), e["modifier_id"])
        by_id = {e["modifier_id"] for e in vecs}
        self.assertEqual(by_id, {"PETRA_YIELD_MODIFIER",
                                 "HALICARNASSUS_MAUSOLEUM_YIELD_MODIFIER",
                                 "CLEOPATRA_FLOODPLAINS_RESOURCE_YIELD",
                                 "TRAIT_SULEIMAN_ALT_SCIENCE_CULTURE_GOLDEN_AGE"})

    def test_petra_scales_elementwise(self):
        from civ6x10.transforms import vector_multiply
        self.assertEqual(vector_multiply("2,2,1", 10.0), "20,20,10")


class TestDeltaInvariants(unittest.TestCase):
    def test_helpers_inert_and_generated(self):
        entries, _ = registry_or_skip()
        deltas = [e for e in entries if e["kind"] == "DELTA"]
        self.assertEqual(len(deltas), 57)
        for e in deltas:
            self.assertTrue(e["count_like"], e["modifier_id"])
            self.assertTrue(e["cert_source"].startswith(
                "curated-effect:delta_effects:"), e["modifier_id"])
            float(e["official"])  # numeric delta base, never SLOT_NONE


class TestBrsEpcNonDependency(unittest.TestCase):
    def test_no_brs_epc_references_in_tree(self):
        # No hard dependency: our tree must not name their modules. This
        # proves architectural independence ONLY, never preview
        # compatibility (see test_brs_preview_divergence_is_documented).
        hits = []
        for rel in ("controller/X10/X10.modinfo",
                    "controller/X10/Config/X10Config.sql",
                    "controller/X10/Config/X10Text.sql",
                    "controller/X10/Config/X10WonderBridge.sql",
                    "controller/X10/Config/X10SlotCopies.sql",
                    "dependencies/CE-X10/CE-X10.modinfo"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            for needle in ("Better Report Screen", "Extended Policy Cards",
                           "RealModifierAnalysis", "ExposedMembers"):
                if needle in text:
                    hits.append((rel, needle))
        self.assertEqual(hits, [])

    def test_god_king_in_registry(self):
        # God King scales through the native registry (gameplay). This does
        # NOT imply BRS/EPC previews see it: they read ModifierArguments
        # through DB.Query (gameplay SQLite), which CE never rewrites.
        # Preview divergence is a documented known incompatibility.
        entries, _ = registry_or_skip()
        by_id = {e["modifier_id"]: e for e in entries}
        for mid in ("GOD_KING_FAITH", "GOD_KING_GOLD"):
            self.assertIn(mid, by_id, mid)
            self.assertEqual(by_id[mid]["kind"], "ADDITIVE", mid)
            self.assertEqual(by_id[mid]["owners"],
                             MODULE_BITS["policies"], mid)

    def test_brs_preview_divergence_is_documented(self):
        # Phase 8B.1 retraction: no automated gate may claim BRS/EPC
        # previews work. P1 stays an explicit known incompatibility until
        # a verified additive integration ships.
        import re
        phase = (ROOT / "docs" / "PHASE_8B.md").read_text(encoding="utf-8")
        self.assertIn("known incompatib",
                      re.sub(r"\s+", " ", phase.lower()))
        checklist = (ROOT / "docs" / "PLAYTEST_2_CHECKLIST.md").read_text(
            encoding="utf-8")
        self.assertIn("known incompatib",
                      re.sub(r"\s+", " ", checklist.lower()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
