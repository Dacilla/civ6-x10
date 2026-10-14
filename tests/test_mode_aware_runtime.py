"""Phase 8B.4 mode-aware runtime expectations.

The static registry holds 2481 entries, but the GAME only populates
definitions for content that is actually loaded. In the standard
Secret-Societies-only setup the Dramatic Ages (58), Heroes & Legends
(52), Monopolies & Corporations (51), and Apocalypse (8) mode bundles
are absent: 169 definitions never reach native population. They are
NOT skips, NOT errors, NOT refused -- they simply never iterate.

Observed live (Playtest-2 P0, x10 Classic, SS-only):
  writes=1682 transform_refused=0 official_mismatch=0
  post_add_match=1682 post_add_mismatch=0 post_add_unreadable=0
  skipped_other=0 repeat_idle=630
1851 - 169 = 1682 exactly.

All expectations here are derived from the registry + manifest bundle
attribution, never hardcoded. The static full-content math
(tests/test_phase8b1_counts.py: 1851 at x10, 1353 at 7.3) remains valid
for the ALL-RELEVANT-MODES-ENABLED configuration.
"""
from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from civ6x10 import transforms as T
from civ6x10.bridge import collect_registry_rows
from civ6x10.production import MODULE_BITS, build_production_registry

# Mode bundles absent unless their game mode is enabled. Zombie /
# Barbarians / Shuffle produced zero registry entries, so only these
# four matter. Attributed via the modes-manifest certification source.
DISABLED_BUNDLES_SS_ONLY = frozenset(
    {"dramatic", "heroes", "monopolies", "apocalypse"})


def bundle_of_manifest_row(row: dict) -> str:
    src = str(row.get("certification_source", ""))
    if "phase8b-mode-audit" in src:
        return src.split(":")[-1]
    return "base-or-society"


def mode_bundle_map() -> dict:
    import yaml
    doc = yaml.safe_load(
        (ROOT / "manifests" / "modes.yml").read_text(encoding="utf-8"))
    return {(r["modifier_id"], r["argument_name"]): bundle_of_manifest_row(r)
            for r in doc["modes"]}


def registry_or_skip():
    try:
        return build_production_registry(collect_registry_rows(ROOT))
    except FileNotFoundError:
        raise unittest.SkipTest("local-only registry inputs unavailable")


def present_in_config(entries, disabled_bundles) -> tuple[list, list]:
    try:
        bundles = mode_bundle_map()
    except FileNotFoundError:
        raise unittest.SkipTest("local-only registry inputs unavailable")
    present, absent = [], []
    for e in entries:
        if e["owners"] != MODULE_BITS["modes"]:
            present.append(e)
            continue
        b = bundles.get((e["modifier_id"], e["argument"]), "unknown")
        (absent if b in disabled_bundles else present).append(e)
    return present, absent


def applies_count_like(entry, kf, kerr) -> bool:
    official = float(entry["official"])
    if entry["kind"] == "DELTA":
        return T.count_like_applies_delta(official, kf, kerr)
    return T.count_like_applies(official, kf, kerr)


class TestModeAwareRuntimeSSOnly(unittest.TestCase):
    def test_absent_split_matches_live_evidence(self):
        entries, _ = registry_or_skip()
        present, absent = present_in_config(
            entries, DISABLED_BUNDLES_SS_ONLY)
        self.assertEqual((len(present), len(absent)), (2312, 169))
        self.assertEqual(
            dict(Counter(
                mode_bundle_map()[(e["modifier_id"], e["argument"])]
                for e in absent)),
            {"dramatic": 58, "heroes": 52, "monopolies": 51,
             "apocalypse": 8})

    def test_r1_ss_only_1682(self):
        # The corrected R1: 1682 writes, 0 refused, 630 idle.
        entries, _ = registry_or_skip()
        present, _ = present_in_config(entries, DISABLED_BUNDLES_SS_ONLY)
        nonrep = [e for e in present if e["kind"] != "REPEAT"]
        reps = [e for e in present if e["kind"] == "REPEAT"]
        self.assertEqual(len(nonrep), 1619)
        copies = T.repeat_copies(10.0, 0.0)
        active = sum(1 for e in reps if e["aux"] <= copies + 1)
        idle = len(reps) - active
        self.assertEqual((active, idle), (63, 630))
        self.assertEqual(len(nonrep) + active, 1682)

    def test_r2_ss_only_1204(self):
        entries, _ = registry_or_skip()
        present, _ = present_in_config(entries, DISABLED_BUNDLES_SS_ONLY)
        kf = T.stored_float32(7.3)
        kerr = T.float_quantization_error(kf)
        un = [e for e in present if not e["count_like"]]
        exact = [e for e in present
                 if e["count_like"] and e["kind"] != "REPEAT"
                 and applies_count_like(e, kf, kerr)]
        self.assertEqual((len(un), len(exact)), (1187, 17))
        self.assertEqual(len(un) + len(exact), 1204)
        self.assertEqual(len(present) - len(un) - len(exact), 1108)

    def test_r3_module_present_counts_ss_only(self):
        # Modes OFF (checkbox) in an SS-only game skips exactly the 34
        # present society rows -- not 203.
        entries, _ = registry_or_skip()
        present, _ = present_in_config(entries, DISABLED_BUNDLES_SS_ONLY)
        by_module = Counter()
        for e in present:
            for name, bit in MODULE_BITS.items():
                if e["owners"] == bit:
                    by_module[name] += 1
        self.assertEqual(by_module["modes"], 34)
        self.assertEqual(by_module["governors"], 48)


class TestAllModesValidation(unittest.TestCase):
    def test_full_content_math_unchanged(self):
        # ALL-RELEVANT-MODES-ENABLED (Secret Societies + Dramatic Ages +
        # Heroes & Legends + Monopolies & Corporations + Apocalypse):
        # every definition present, static math holds.
        entries, _ = registry_or_skip()
        present, absent = present_in_config(entries, frozenset())
        self.assertEqual((len(present), len(absent)), (2481, 0))
        nonrep = [e for e in present if e["kind"] != "REPEAT"]
        self.assertEqual(len(nonrep), 1788)
        copies = T.repeat_copies(10.0, 0.0)
        active = sum(1 for e in entries
                     if e["kind"] == "REPEAT" and e["aux"] <= copies + 1)
        self.assertEqual(len(nonrep) + active, 1851)


if __name__ == "__main__":
    unittest.main(verbosity=2)
