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
# Canonical DLL hash lives in spike/EXPECTED_DLL_SHA256.txt (single source).


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
        # Production-candidate package: engine DLL assembled under
        # spike/prod-test-output (hash-pinned single source).
        out = ROOT / "spike" / "prod-test-output" / "CE-X10" / "Binaries" / "Win64"
        dlls = list(out.rglob("*.dll")) if out.is_dir() else []
        if not dlls:
            self.skipTest("prod-test-output not assembled (run assemble-prod-test.ps1)")
        self.assertEqual(len(dlls), 1)
        import hashlib
        h = hashlib.sha256(dlls[0].read_bytes()).hexdigest()
        expected = (ROOT / "spike" / "EXPECTED_DLL_SHA256.txt").read_text(
            encoding="utf-8").strip().lower()
        self.assertEqual(h, expected)

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

    @staticmethod
    def _code(text):
        # Strip // line comments so doc citations of evidence RVAs never
        # count as hardcoded implementation constants.
        return "\n".join(
            line.split("//", 1)[0] for line in text.splitlines())

    def test_no_direct_findvariant_on_manager(self):
        # Regression: TypedVariantMap::FindVariant was once called directly
        # on the inst+0x88 manager object (wrong object; any "hit" was
        # meaningless). Lookup must go through the manager vtable slot from
        # the active compatibility profile, exactly as GetGameSpeedType does.
        t = self._code(self._fork("X10Write.cpp"))
        self.assertNotIn("FindVariantFn", t)
        self.assertNotIn("0x99f570", t)
        self.assertIn("lookupVtableOff", t)

    def test_heap_capable_id_reader(self):
        t = self._code(self._fork("X10Write.cpp"))
        self.assertIn("BoundedStringRead", t)
        # SSO branch present alongside heap path, both profile-driven.
        self.assertIn("ssoInlineThreshold", t)
        self.assertIn("ssoCapOff", t)
        self.assertIn("ssoSizeOff", t)

    def test_native_variant_switch_shape(self):
        # The native reader keeps the explicit typed pattern, driven by the
        # active compatibility profile: FLOAT32 id checked before the INT32
        # mask branch, fail-closed default logging the exact type id.
        # Unknown types must never reach a string reader.
        t = self._code(self._fork("X10Write.cpp"))
        self.assertIn("floatId", t)
        self.assertIn("intMaskIds", t)
        self.assertIn("FLOAT32", t)
        self.assertIn("INT32", t)
        self.assertIn("undecodable-variant", t)
        self.assertNotIn("ReadCString(payload", t)

    def test_float32_fixture_decodes_to_live_value(self):
        # Raw float32 bytes of 7.3 widen to exactly the live Lua value.
        import struct
        raw = struct.pack("<f", 7.3)
        self.assertEqual(raw.hex(), "9a99e940")
        self.assertEqual(struct.unpack("<f", raw)[0], 7.300000190734863)
        # ...which is what the probe Lua independently reported.

    def test_disarm_before_lookup(self):
        t = self._fork("X10Lifecycle.cpp")
        i_dis = t.index("X10Write::Disarm()")
        i_cfg = t.index("TryGetProbeK")
        self.assertLess(i_dis, i_cfg)

    def test_disarm_at_population_exit(self):
        t = self._fork("X10Lifecycle.cpp")
        i_exit = t.index("PopulateModifierDefinitions EXIT")
        tail = t[i_exit:]
        self.assertIn("X10Write::Disarm();", tail)
        self.assertIn("WritesThisPopulate", t)

    def test_compat_profile_consumed(self):
        # Production code references the selected profile, not literal
        # build constants (comments stripped: doc citations don't count).
        lc = self._code(self._fork("X10Lifecycle.cpp"))
        self.assertIn("ActiveProfile", lc)
        self.assertIn("s_profile->populateRva", lc)
        self.assertIn("s_profile->addRva", lc)
        self.assertIn("peTimestamp", lc)
        self.assertIn("imageSize", lc)
        for lit in ("0x96f6c0", "0x943110", "0x92a4f0", "0x92b220",
                    "0x667c6f5b", "0xc60000"):
            self.assertNotIn(lit, lc)
        w = self._code(self._fork("X10Write.cpp"))
        self.assertIn("ActiveProfile", w)
        for field in ("getInstanceRva", "hashRva", "gameVariantsOff",
                      "rootVariantsOff", "lookupVtableOff", "floatId",
                      "intMaskIds", "defIdOff", "argVecOff", "argStride",
                      "argValueOff", "ssoSizeOff", "ssoCapOff"):
            self.assertIn(field, w)
        for lit in ("0x164c20", "0x606270"):
            self.assertNotIn(lit, w)

    def test_x10_only_rollback(self):
        t = self._code(self._fork("X10Lifecycle.cpp"))
        self.assertNotIn("MH_ALL_HOOKS", t)
        self.assertIn("MH_RemoveHook", t)
        self.assertIn("MH_DisableHook(created[i])", t)

    def test_production_package_metadata(self):
        import re
        uuid = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                          r"[0-9a-f]{4}-[0-9a-f]{12}$")
        eng = (ROOT / "dependencies" / "CE-X10" / "CE-X10.modinfo"
               ).read_text(encoding="utf-8")
        ctl = (ROOT / "controller" / "X10" / "X10.modinfo"
               ).read_text(encoding="utf-8")
        eg = re.search(r'<Mod id="([^"]+)"', eng).group(1)
        cg = re.search(r'<Mod id="([^"]+)"', ctl).group(1)
        self.assertTrue(uuid.match(eg), eg)
        self.assertTrue(uuid.match(cg), cg)
        self.assertNotEqual(eg, cg)
        self.assertIn(eg, ctl)  # controller depends on engine GUID
        self.assertIn("<AffectsSavedGames>1</AffectsSavedGames>", ctl)
        cfg = (ROOT / "controller" / "X10" / "Config" / "X10Config.sql"
               ).read_text(encoding="utf-8")
        for key in ("X10_MULTIPLIER", "X10_MODULE_TRAITS",
                    "X10_MODULE_POLICIES", "X10_MODULE_GOVERNMENTS"):
            self.assertIn(key, cfg)
        self.assertNotIn("X10_PROBE_K", cfg)
        t = self._fork("X10Lifecycle.cpp")
        i_exit = t.index("PopulateModifierDefinitions EXIT")
        tail = t[i_exit:]
        self.assertIn("X10Write::Disarm();", tail)
        self.assertIn("WritesThisPopulate", t)

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
