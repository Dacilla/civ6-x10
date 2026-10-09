"""Probe packaging regression: the shipped production probe must not load the
retired Phase-3E Stonehenge gameplay diagnostic.

Phase 3G intentionally integral-gates Stonehenge (2 × 7.3 = 14.6 refuses), so
the old diagnostic's 14.6 expectation is obsolete and would mutate a
disposable game for no reason. The historical source stays under
spike/X10_Probe_Test/stonediag.lua for provenance, but the probe that gets
packaged for live runs must reference probe.lua only.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

PROBE_DIR = ROOT / "spike" / "X10_Probe_Test"
MODINFO = PROBE_DIR / "X10_Probe_Test.modinfo"


class TestProbePackaging(unittest.TestCase):
    def test_modinfo_exists(self):
        self.assertTrue(MODINFO.is_file(), str(MODINFO))

    def test_stonediag_not_registered_as_gameplay_script(self):
        text = MODINFO.read_text(encoding="utf-8")
        # No AddGameplayScripts action may reference stonediag.lua.
        actions = text.split("<AddGameplayScripts")
        for chunk in actions[1:]:
            body = chunk.split("</AddGameplayScripts>")[0]
            self.assertNotIn("stonediag.lua", body,
                             "retired Phase-3E diagnostic still registered")
        self.assertNotIn('id="X10StoneDiag"', text)

    def test_stonediag_not_imported_or_listed(self):
        text = MODINFO.read_text(encoding="utf-8")
        self.assertNotIn("stonediag.lua", text)

    def test_probe_lua_still_registered(self):
        text = MODINFO.read_text(encoding="utf-8")
        self.assertIn('<AddGameplayScripts id="X10Probe">', text)
        self.assertIn("<File>probe.lua</File>", text)

    def test_probe_script_count_is_two(self):
        # Exactly one AddGameplayScripts action (probe.lua); the Stonehenge
        # diagnostic is retired.
        text = MODINFO.read_text(encoding="utf-8")
        self.assertEqual(text.count("<AddGameplayScripts"), 1)
        self.assertEqual(text.count("<File>probe.lua</File>"), 3)  # Import, Action, Files

    def test_historical_source_kept_for_provenance(self):
        self.assertTrue((PROBE_DIR / "stonediag.lua").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
