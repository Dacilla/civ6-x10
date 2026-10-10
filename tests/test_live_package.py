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

    def test_float32_quantization_provenance(self):
        # Count-like exactness consumes the multiplier's source quantization
        # (FLOAT32 half-ULP, 0 for INT32): no strict double equality, no
        # coarse epsilon.
        tr = self._code(self._fork("X10Transforms.h"))
        self.assertIn("kErr", tr)
        self.assertNotIn("if (v != r) return false", tr)
        w = self._code(self._fork("X10Write.cpp"))
        self.assertIn("TryGetMultiplier", w)
        self.assertIn("nextafterf", w)
        self.assertIn("g_kErr", w)
        lc = self._code(self._fork("X10Lifecycle.cpp"))
        self.assertIn("TryGetMultiplier", lc)
        self.assertIn("Arm(k, mods, kErr)", lc)

    def test_x10_only_rollback(self):
        t = self._code(self._fork("X10Lifecycle.cpp"))
        self.assertNotIn("MH_ALL_HOOKS", t)
        self.assertIn("MH_RemoveHook", t)
        self.assertIn("MH_DisableHook(created[i])", t)

    def test_pantheon_module_bit_wired(self):
        # Pantheons are a supported module (bit 8): native slots, mask,
        # config default ON. Governors is now also supported (bit 32, covered
        # by its own test); suzerain remains the only unsupported module.
        w = self._code(self._fork("X10Write.cpp"))
        self.assertIn("s_modEnabled[3]", w)
        self.assertIn("mask |= 8", w)
        lc = self._fork("X10Lifecycle.cpp")
        self.assertIn('ModuleEnabled("pantheons", true)', lc)
        self.assertIn("bool mods[6]", lc)
        self.assertNotIn('"pantheons", "governors"',
                         lc.replace(" ", "").replace("\n", ""))
        # governors is supported; only suzerain stays in the warn loop
        self.assertIn('{"suzerain"}', lc.replace(" ", "").replace("\n", ""))
        h = self._fork("X10Write.h")
        self.assertIn("Arm(double k, const bool* mods, double kErr)", h)
        cfg = (ROOT / "controller" / "X10" / "Config" / "X10Config.sql"
               ).read_text(encoding="utf-8")
        self.assertIn("X10_MODULE_PANTHEONS', 'X10: Pantheons', "
                      "'Apply to founded-pantheon belief effects.',\n   'int', '1',",
                      cfg.replace("\r\n", "\n"))
        import re
        m = re.search(r"X10_MODULE_SUZERAIN'.*?\n.*?'(int)', '(0|1)'", cfg, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "0")

    def test_wonder_module_bit_wired(self):
        # Wonders are the fifth supported module (bit 16): native slots,
        # mask, config default ON, and no unsupported warning for wonders.
        w = self._code(self._fork("X10Write.cpp"))
        self.assertIn("s_modEnabled[6]", w)
        self.assertIn("mask |= 16", w)
        lc = self._fork("X10Lifecycle.cpp")
        self.assertIn('ModuleEnabled("wonders", true)', lc)
        self.assertIn("bool mods[6]", lc)
        flat = lc.replace(" ", "").replace("\n", "")
        self.assertNotIn('"wonders","suzerain"', flat)
        self.assertIn('{"suzerain"}', flat)
        cfg = (ROOT / "controller" / "X10" / "Config" / "X10Config.sql"
               ).read_text(encoding="utf-8")
        self.assertIn("X10_MODULE_WONDERS', 'X10: Wonders', ",
                      cfg.replace("\r\n", "\n"))
        self.assertNotIn("X10: Wonders (unsupported)", cfg)
        import re
        m = re.search(r"X10_MODULE_WONDERS'.*?\n.*?'(int)', '(0|1)'",
                      cfg, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "1")

    def test_governor_module_bit_wired(self):
        # Governors are the sixth supported module (bit 32): native slots,
        # mask, config default ON, and no unsupported warning for governors.
        # Suzerain remains the only unsupported module.
        w = self._code(self._fork("X10Write.cpp"))
        self.assertIn("s_modEnabled[6]", w)
        self.assertIn(
            "static bool s_modEnabled[6] = {true, true, true, true, true, true};",
            w)
        self.assertIn("for (int i = 0; i < 6; i++) s_modEnabled[i] = mods[i];",
                      w)
        self.assertIn("mask |= 32", w)
        lc = self._fork("X10Lifecycle.cpp")
        self.assertIn('ModuleEnabled("governors", true)', lc)
        self.assertIn("bool mods[6]", lc)
        flat = lc.replace(" ", "").replace("\n", "")
        self.assertIn('ModuleEnabled("governors",true)', flat)
        self.assertIn('{"suzerain"}', flat)
        cfg = (ROOT / "controller" / "X10" / "Config" / "X10Config.sql"
               ).read_text(encoding="utf-8")
        self.assertIn("X10_MODULE_GOVERNORS', 'X10: Governors', ",
                      cfg.replace("\r\n", "\n"))
        self.assertNotIn("X10: Governors (unsupported)", cfg)
        import re
        m = re.search(r"X10_MODULE_GOVERNORS'.*?\n.*?'(int)', '(0|1)'",
                      cfg, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "1")
        m = re.search(r"X10_MODULE_SUZERAIN'.*?\n.*?'(int)', '(0|1)'",
                      cfg, re.S)
        self.assertEqual(m.group(2), "0")

    def test_post_add_mismatch_increments_counter(self):
        # A post-Add MISMATCH must feed the aggregate mismatch counter;
        # the old code logged MISMATCH while mismatches= stayed 0.
        w = self._fork("X10Write.cpp")
        inc = "InterlockedIncrement(&s_postAddMismatch)"
        self.assertEqual(w.count(inc), 2)  # id-mismatch + value-mismatch
        for needle in ("MISMATCH via=store-lookup", "stored_id_mismatch"):
            i_log = w.index(needle)
            # an increment precedes each MISMATCH log line
            prev = w.rfind(inc, 0, i_log)
            self.assertNotEqual(prev, -1, needle)
            self.assertLess(i_log - prev, 600, needle)
        h = self._fork("X10Write.h")
        self.assertIn("PostAddMismatchThisPopulate", h)

    def test_unreadable_is_not_match(self):
        # Lookup miss / typed-or-consumed / fault paths count unreadable;
        # MATCH is emitted only on a verified string read.
        w = self._fork("X10Write.cpp")
        self.assertGreaterEqual(
            w.count("InterlockedIncrement(&s_postAddUnreadable)"), 4)
        self.assertEqual(w.count("expected=%s MATCH via=store-lookup"), 1)
        self.assertEqual(w.count("MISMATCH via=store-lookup"), 1)
        self.assertIn("PostAddUnreadableThisPopulate",
                      self._fork("X10Write.h"))

    def test_summary_reports_post_add_counters(self):
        # The exit summary derives every field from counters, so it cannot
        # report zero mismatches after a MISMATCH line was emitted.
        t = self._fork("X10Lifecycle.cpp")
        i_exit = t.index("PopulateModifierDefinitions EXIT")
        tail = t[i_exit:]
        for acc in ("PostAddMatchThisPopulate",
                    "PostAddMismatchThisPopulate",
                    "PostAddUnreadableThisPopulate",
                    "TransformRefusedThisPopulate"):
            self.assertIn(acc, tail)
        self.assertNotIn("mismatches=%ld", tail)
        w = self._fork("X10Write.cpp")
        for reset in ("s_postAddMatch = 0", "s_postAddMismatch = 0",
                      "s_postAddUnreadable = 0", "s_transformRefused = 0"):
            self.assertIn(reset, w)

    def test_verifier_uses_no_preadd_pointer(self):
        # Touched carries logical identity only; post-Add proof comes from
        # the registered store via the engine getter, never a retained
        # pre-Add element address.
        h = self._fork("X10Write.h")
        body = h[h.index("struct Touched"):h.index("};", h.index("struct Touched"))]
        self.assertNotIn("element", body)
        self.assertNotIn("void*", body)
        self.assertIn("VerifyStoredAfterAdd(void* system", h)
        w = self._fork("X10Write.cpp")
        self.assertNotIn("touched[i].element", w)
        self.assertNotIn(".element", self._code(w))
        self.assertIn("getDefRva", self._code(w))

    def test_store_lookup_validated_not_hooked(self):
        # getDefRva lives in the profile, is validated like a hook target
        # (in-text + prologue), is called but never hooked; a failed
        # validation degrades the witness loudly without touching the writer.
        c = self._fork("X10Compat.h")
        self.assertIn("getDefRva", c)
        self.assertIn("0x951d90", c)
        lc = self._fork("X10Lifecycle.cpp")
        self.assertIn("GetModifierDefinition", lc)
        self.assertIn("SetStoreLookupProven", lc)
        self.assertIn("STORE LOOKUP UNPROVEN", lc)
        i_val = lc.index("s_profile->getDefRva")
        self.assertIn("IsPrologue", lc[i_val:i_val + 600])

    def test_toqui_loyalty_excluded_pending_recert(self):
        import yaml
        rules = yaml.safe_load(
            open(ROOT / "civ6x10" / "rules" / "certified_overrides.yml",
                 encoding="utf-8"))
        hit = [e for e in rules["excluded_effects"]
               if e["effect"] == "EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE"]
        self.assertEqual(len(hit), 1)
        self.assertIn("TOQUI", hit[0]["rationale"])
        self.assertIn("re-certif", hit[0]["rationale"].lower())

    def test_verifier_id_buffer_fits_registry(self):
        # Live 684-run proved truncation: the 66-char Magnificences ID was
        # cut to 63 by Touched.id[64]. The buffer now follows an explicit
        # capacity contract: no literal 63-cap, no silent truncation.
        h = self._fork("X10Write.h")
        body = h[h.index("struct Touched"):h.index("};", h.index("struct Touched"))]
        self.assertIn("char id[256]", body)
        w = self._fork("X10Write.cpp")
        self.assertNotIn("len > 63", w)
        self.assertIn("sizeof(t->id) - 1", w)
        self.assertIn("verifier-key-too-long", w)
        self.assertIn("key.capa = sizeof(t->id)", w)

    def test_installer_clears_previous_run_logs(self):
        # Fresh install clears both TEMP logs once; nothing clears them
        # between new game and save reload (append required within one test).
        inst = (ROOT / "spike" / "install-prod-test.ps1"
                ).read_text(encoding="utf-8")
        self.assertIn("X10Lifecycle.log", inst)
        self.assertIn("X10Probe.log", inst)
        self.assertIn("GetTempPath", inst)
        self.assertEqual(inst.count("Remove-Item $p"), 1)

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
