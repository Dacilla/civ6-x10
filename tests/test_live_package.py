"""Package checks for the disposable live-test mod (no game needed)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "spike" / "live-test-package" / "X10_CEFork_Test"
OUT = ROOT / "spike" / "live-test-output" / "X10_CEFork_Test"
WORKSHOP_CE_GUID = "3351473b-0746-417a-a618-2b66a04d8f3d"
EXPECTED_DLL_HASH = "977136d9679814d786f55648b0d4b91f6b02b29f364ae3026c1e52686051fcf8"


class TestLivePackage(unittest.TestCase):
    def test_modinfo_exists_with_unique_guid(self):
        mi = (PKG / "X10_CEFork_Test.modinfo").read_text(encoding="utf-8")
        self.assertIn("308d6fa9-0fb8-4153-8376-5a5a5a1b5d2d", mi)
        self.assertNotIn(WORKSHOP_CE_GUID, mi)
        self.assertIn("Gathering Storm", mi)

    def test_gamecore_redirect_declared(self):
        sql = (PKG / "Config" / "ForkRedirect.sql").read_text(encoding="utf-8")
        self.assertIn("GameCores", sql)
        self.assertIn("GameCore_XP2_CE", sql)
        self.assertIn("Expansion2", sql)

    def test_probe_param_declared(self):
        sql = (PKG / "Config" / "ProbeConfig.sql").read_text(encoding="utf-8")
        self.assertIn("X10_PROBE_K", sql)
        self.assertIn("'7.3'", sql)

    def test_probe_lua_has_no_silent_fallback(self):
        lua = (PKG / "probe.lua").read_text(encoding="utf-8")
        self.assertIn("GameConfiguration.GetValue", lua)
        self.assertIn("error(", lua)
        self.assertNotIn("or 7.3", lua)
        self.assertNotIn("RegisterProcessor", lua)
        self.assertNotIn("ObjMem", lua)

    def test_assembled_output_if_present(self):
        dlls = list(OUT.rglob("*.dll")) if OUT.is_dir() else []
        if not dlls:
            self.skipTest("live-test-output not assembled (run assemble-live-test.ps1)")
        self.assertEqual(len(dlls), 1)
        import hashlib
        h = hashlib.sha256(dlls[0].read_bytes()).hexdigest()
        self.assertEqual(h, EXPECTED_DLL_HASH)

    def test_installer_never_writes_to_workshop(self):
        inst = (ROOT / "spike" / "install-live-test.ps1").read_text(encoding="utf-8")
        self.assertNotIn("289070", inst)
        self.assertNotIn("steamapps\\workshop", inst.replace("/", "\\").lower())
        self.assertIn("workshop", inst.lower())  # refusal guard present
        self.assertIn("My Games", inst)
        uninst = (ROOT / "spike" / "uninstall-live-test.ps1").read_text(encoding="utf-8")
        self.assertIn("X10_CEFork_Test", uninst)
        self.assertNotIn("Remove-Item $mods", uninst)


class TestWriteProbeRegressions(unittest.TestCase):
    FORK = ROOT.parent / "CivilizationVI_CommunityExtension-x10-spike"

    def _fork(self, name):
        p = self.FORK / name
        if not p.is_file():
            self.skipTest(f"fork checkout unavailable ({name})")
        return p.read_text(encoding="utf-8", errors="replace")

    def test_no_self_as_definition(self):
        t = self._fork("X10Lifecycle.cpp")
        self.assertNotIn("OnAddModifierDefinition(self)", t)
        self.assertIn("OnAddModifierDefinition(d0,", t)
        w = self._fork("X10Write.cpp")
        self.assertIn("ResolveDefinitionReference", w)

    def test_heap_capable_id_reader(self):
        t = self._fork("X10Write.cpp")
        self.assertIn("BoundedStringRead", t)
        self.assertIn("capa < 0x10", t)  # SSO branch present alongside heap path

    def test_disarm_before_lookup(self):
        t = self._fork("X10Lifecycle.cpp")
        i_dis = t.index("X10Write::Disarm()")
        i_cfg = t.index("TryGetProbeK")
        self.assertLess(i_dis, i_cfg)

    def test_modinfo_is_write_enabled(self):
        mi = (PKG / "X10_CEFork_Test.modinfo").read_text(encoding="utf-8")
        self.assertNotIn("Read-only", mi)
        self.assertNotIn("Logging-only", mi)
        self.assertNotIn("logging-only", mi)
        self.assertIn("<AffectsSavedGames>1</AffectsSavedGames>", mi)
        self.assertIn('version="2"', mi)

    def test_probe_uses_handles_not_string_ids(self):
        lua = (PKG / "probe.lua").read_text(encoding="utf-8")
        self.assertIn("GameEffects.GetModifiers()", lua)
        self.assertIn("GetModifierDefinition(handle)", lua)
        self.assertNotIn("GetModifierArgumentString(p.id", lua)
        self.assertNotIn("GetModifierArgumentString(t.id", lua)
        self.assertIn("PASS", lua)

    def test_proof_witness_is_guaranteed_active(self):
        # Rome trading-post gold attaches for the human playing Rome (Trajan);
        # installer must name Rome as the required pick.
        lua = (PKG / "probe.lua").read_text(encoding="utf-8")
        self.assertIn("TRAIT_GOLD_FROM_DOMESTIC_TRADING_POSTS", lua)
        inst = (ROOT / "spike" / "install-live-test.ps1").read_text(encoding="utf-8")
        self.assertIn("ROME", inst)

if __name__ == "__main__":
    unittest.main(verbosity=2)
