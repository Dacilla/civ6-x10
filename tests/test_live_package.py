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
EXPECTED_DLL_HASH = "f82c73346fc44ecaa111dc54d1e7819e985744568e2b738518b94724e2706cdc"


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
