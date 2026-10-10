"""Probe packaging regression: the shipped production probe must not load the
retired Phase-3E Stonehenge gameplay diagnostic.

Phase 3G intentionally integral-gates Stonehenge (2 × 7.3 = 14.6 refuses), so
the old diagnostic's 14.6 expectation is obsolete and would mutate a
disposable game for no reason. The historical source stays under
spike/X10_Probe_Test/stonediag.lua for provenance, but the probe that gets
packaged for live runs must reference probe.lua only.
"""
from __future__ import annotations

import re
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


GOVERNOR_WITNESSES = {
    "GROUNDBREAKER_BONUS_HARVEST_YIELDS": "flat",
    "GARRISON_COMMANDER_ADJUST_CITY_COMBAT_BONUS": "combat",
    "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_4_GOLD_INTEREST": "flat",
    "HERMETIC_ORDER_GREAT_ENGINEER_LEY_LINE_PRODUCTION": "flat",
}

# Engine-integral Governor rows must NEVER become ordinary probe PASS targets.
GOVERNOR_INTEGRAL_ROWS = {
    "FORESTRY_MANAGEMENT_FEATURE_NO_IMPROVEMENT_APPEAL",
    "RENEWABLE_ENERGY_IMPROVEMENT_BUILDING_GOLD",
    "INDUSTRIALIST_COAL_POWER_PLANT_PRODUCTION",
    "INDUSTRIALIST_OIL_POWER_PLANT_PRODUCTION",
    "INDUSTRIALIST_NUCLEAR_POWER_PLANT_PRODUCTION",
}


def probe_targets():
    text = (PROBE_DIR / "probe.lua").read_text(encoding="utf-8")
    body = text[text.find("local TARGETS"):text.find("local raw")]
    out = {}
    for m in re.finditer(r'\{\s*id\s*=\s*"([^"]+)",\s*arg\s*=\s*"([^"]+)",'
                         r'\s*official\s*=\s*"([^"]+)",\s*kind\s*=\s*"([^"]+)"',
                         body):
        out[m.group(1)] = {"arg": m.group(2), "official": m.group(3),
                           "kind": m.group(4)}
    return out


class TestGovernorProbeWitnesses(unittest.TestCase):
    """Phase 4C: the disposable probe carries four Governor witnesses.

    Absent runtime handles are reported, not failed: the authoritative proof
    is the native stored_after_add MATCH line. The five engine-integral
    Governor rows must stay OUT of the PASS set because they refuse at
    fractional k by design.
    """

    def test_all_four_witnesses_present(self):
        targets = probe_targets()
        for mid, kind in GOVERNOR_WITNESSES.items():
            self.assertIn(mid, targets)
            self.assertEqual(targets[mid]["kind"], kind, mid)

    def test_witness_arguments(self):
        targets = probe_targets()
        self.assertEqual(
            targets["GROUNDBREAKER_BONUS_HARVEST_YIELDS"]["arg"], "Amount")
        self.assertEqual(
            targets["GROUNDBREAKER_BONUS_HARVEST_YIELDS"]["official"], "50")
        self.assertEqual(
            targets["GARRISON_COMMANDER_ADJUST_CITY_COMBAT_BONUS"]["official"],
            "5")
        self.assertEqual(
            targets["GOVERNOR_PROMOTION_OWLS_OF_MINERVA_4_GOLD_INTEREST"]["arg"],
            "Percent")
        self.assertEqual(
            targets["GOVERNOR_PROMOTION_OWLS_OF_MINERVA_4_GOLD_INTEREST"]["official"],
            "3")
        self.assertEqual(
            targets["HERMETIC_ORDER_GREAT_ENGINEER_LEY_LINE_PRODUCTION"]["official"],
            "1")

    def test_integral_rows_not_probe_targets(self):
        targets = probe_targets()
        for mid in GOVERNOR_INTEGRAL_ROWS:
            self.assertNotIn(mid, targets, mid)

    def test_existing_witnesses_retained(self):
        targets = probe_targets()
        for mid in ("STAUEZEUS_ANTI_CAVALRY_PRODUCTION",
                    "X10_PANAMA_CANAL_YIELD_GOLD",
                    "GOD_OF_THE_FORGE_UNIT_ANCIENT_CLASSICAL_PRODUCTION_MODIFIER"):
            self.assertIn(mid, targets, mid)

    def test_probe_expectations_match_native_semantics(self):
        # The probe recomputes expectations from official + k using the same
        # semantics as the native engine; verify against the published values.
        import math
        from civ6x10 import transforms as T
        targets = probe_targets()
        kf = T.stored_float32(7.3)
        cases = {
            "GROUNDBREAKER_BONUS_HARVEST_YIELDS": 365.0,
            "GARRISON_COMMANDER_ADJUST_CITY_COMBAT_BONUS": 24.04,
            "GOVERNOR_PROMOTION_OWLS_OF_MINERVA_4_GOLD_INTEREST": 21.9,
            "HERMETIC_ORDER_GREAT_ENGINEER_LEY_LINE_PRODUCTION": 7.3,
        }
        for mid, want in cases.items():
            v = float(targets[mid]["official"])
            if targets[mid]["kind"] == "combat":
                got = 25.0 * math.log(kf * (math.exp(v / 25.0) - 1) + 1)
            else:
                got = v * kf
            self.assertAlmostEqual(got, want, delta=0.02, msg=mid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
