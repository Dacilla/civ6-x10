"""Phase 7C.1: disposable UX prototype + design invariants.

The prototype (spike/X10_UX_Prototype) is front-end only: native
SetupParameters, LOC text, no Lua UI replacement, no production keys.
Production freeze (registry/DLL/bridge/controller) is re-asserted here
so the research phase cannot silently perturb the validated build.
"""
from __future__ import annotations

import hashlib
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "spike" / "X10_UX_Prototype"
PROD_CONTROLLER_ID = "55d7b934-62f9-46fb-a771-badf3d1a1538"
PROD_ENGINE_ID = "397f2070-dfde-4124-88ce-e34249fc8190"


def norm_hash(path: Path) -> str:
    return hashlib.sha256(
        path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def proto_config() -> str:
    p = PROTO / "Config" / "X10UxConfig.sql"
    if not p.is_file():
        raise unittest.SkipTest("UX prototype unavailable")
    return p.read_text(encoding="utf-8")


def proto_text() -> str:
    return (PROTO / "Config" / "X10UxText.sql").read_text(encoding="utf-8")


class TestPrototypeLayout(unittest.TestCase):
    def test_advanced_options_group(self):
        groups = set(re.findall(r"'(AdvancedOptions|GameOptions)'",
                                proto_config()))
        self.assertEqual(groups, {"AdvancedOptions"})

    def test_contiguous_sort_block(self):
        idx = sorted(int(v) for v in
                     re.findall(r"'AdvancedOptions', (\d+)", proto_config()))
        self.assertEqual(idx, [2400, 2401, 2402, 2403, 2404, 2405, 2406,
                               2407, 2408])

    def test_preset_domain_complete_ordered(self):
        vals = re.findall(
            r"\('X10UxMultiplierPresets', (\d+), '(LOC_[^']+)', '(LOC_[^']+)'",
            proto_config())
        self.assertEqual([int(v) for v, _, _ in vals],
                         [0, 2, 3, 5, 10, 20, 50, 100, 101])
        self.assertIn("'X10UxPreset', 'LOC_X10_UX_PRESET_NAME', "
                      "'LOC_X10_UX_PRESET_DESC',\n   'X10UxMultiplierPresets', 10",
                      proto_config())
        # default MUST be SQLite INTEGER 10, not TEXT '10': the driver only
        # coerces bool/int/uint domains and ==-compares custom-domain
        # defaults against (numeric) domain values
        self.assertNotIn("'X10UxMultiplierPresets', '10'", proto_config())

    def test_multiplayer_metadata_explicit(self):
        import xml.etree.ElementTree as ET
        m = ET.parse(str(PROTO / "X10_UX_Prototype.modinfo")).getroot()
        props = m.find("Properties")
        self.assertEqual(props.find("SupportsSinglePlayer").text, "1")
        self.assertEqual(props.find("SupportsMultiplayer").text, "0")

    def test_custom_dependency(self):
        cfg = proto_config()
        self.assertIn("'X10UxCustom', 'Game', 'X10_UX_PRESET', 'Equals', 101",
                      " ".join(cfg.split()))

    def test_module_controls_native_bool(self):
        for mod in ("TRAITS", "POLICIES", "GOVERNMENTS", "PANTHEONS",
                    "WONDERS", "GOVERNORS", "SUZERAIN"):
            self.assertIn(f"'X10_UX_BOOL_{mod}'", proto_config())
            self.assertIn(f"'Game', 'X10_UX_BOOL_{mod}', 'AdvancedOptions'",
                          proto_config())
        self.assertEqual(proto_config().count("'bool'"), 7)
        self.assertNotIn("radio", proto_config().lower())

    def test_scope_flags_explicit(self):
        cfg = proto_config()
        rows = re.findall(r"1, 1, 0, 0, 0, 0, 0\)[,;]", cfg)
        self.assertEqual(len(rows), 9)  # SP=1, LAN=0, NET=0, HS=0, Cloud=0, Changeable=0

    def test_no_lua_replacement(self):
        self.assertFalse(list(PROTO.rglob("*.lua")))
        modinfo = (PROTO / "X10_UX_Prototype.modinfo").read_text(
            encoding="utf-8")
        self.assertNotIn("ReplaceUIScript", modinfo)
        self.assertNotIn("AdvancedSetup.lua", modinfo)
        self.assertIn("<UpdateText", modinfo)

    def test_own_identity_no_production_collision(self):
        modinfo = (PROTO / "X10_UX_Prototype.modinfo").read_text(
            encoding="utf-8")
        self.assertIn("880f3337-49a9-4ba1-8946-368aa8ea6aa9", modinfo)
        self.assertNotIn(PROD_CONTROLLER_ID, modinfo)
        self.assertNotIn(PROD_ENGINE_ID, modinfo)
        cfg = proto_config()
        self.assertNotIn("X10_MULTIPLIER_PRESET", cfg)  # final name lives in 7C.2
        for key in ("X10_MULTIPLIER", "X10_MODULE_TRAITS",
                    "X10_MODULE_GOVERNORS", "X10_MODULE_SUZERAIN"):
            self.assertNotIn(f"'{key}'", cfg, key)


class TestPrototypeLocalization(unittest.TestCase):
    def test_all_loc_keys_resolve_en_us(self):
        cfg = proto_config()
        keys = set(re.findall(r"LOC_X10_UX_[A-Z0-9_]+", cfg))
        self.assertTrue(keys)
        text = proto_text()
        have = set(re.findall(r"^\('en_US', '(LOC_[^']+)'",
                              text, re.M))
        missing = sorted(keys - have)
        self.assertEqual(missing, [])

    def test_no_raw_english_names(self):
        cfg = proto_config().split("INSERT OR IGNORE INTO DomainValues")[0]
        for m in re.finditer(r"'X10Ux\w+', '([^']+)', '([^']+)'", cfg):
            self.assertTrue(m.group(1).startswith("LOC_"), m.group(1))
            self.assertTrue(m.group(2).startswith("LOC_"), m.group(2))


class TestProductionUntouched(unittest.TestCase):
    def test_controller_sql_hashes(self):
        self.assertEqual(
            norm_hash(ROOT / "controller" / "X10" / "Config" / "X10Config.sql"),
            "f08ffe9e1255035cc111ec14210b5fb9ea5b936a484d3fede6157b50803db860")
        self.assertEqual(
            norm_hash(ROOT / "controller" / "X10" / "Config" /
                      "X10WonderBridge.sql"),
            "d5e9556dc63a05da086b7604851bfa468cec593aa8f1dcb336e63e7e16aaf34e")

    def test_registry_and_dll_freeze(self):
        inc = ROOT / "build" / "X10ProductionRegistry.inc"
        if not inc.is_file():
            self.skipTest("local production registry unavailable")
        self.assertEqual(norm_hash(inc),
                         "28c987493717c2e107a9e8bf2669372267651104d1931e2a4b2eebbeff3d4203")
        pin = ROOT / "spike" / "EXPECTED_DLL_SHA256.txt"
        if not pin.is_file():
            self.skipTest("expected DLL hash unavailable")
        self.assertEqual(
            pin.read_text(encoding="utf-8").strip().lower(),
            "ced8f01750d22f44725ed61de7c0926c58e423388b3ee7fce0fd18522081b744")

    def test_scratch_pin_distinct(self):
        pin = ROOT / "spike" / "UX_PROBE_DLL_SHA256.txt"
        if not pin.is_file():
            self.skipTest("scratch probe DLL not built yet")
        scratch = pin.read_text(encoding="utf-8").strip().lower()
        self.assertRegex(scratch, r"^[0-9a-f]{64}$")
        self.assertNotEqual(
            scratch,
            "ced8f01750d22f44725ed61de7c0926c58e423388b3ee7fce0fd18522081b744")

    def test_modinfo_gameplay_nodes_stable(self):
        import xml.etree.ElementTree as ET
        m = ET.parse(str(ROOT / "controller" / "X10" / "X10.modinfo")).getroot()
        self.assertEqual(m.get("id"), PROD_CONTROLLER_ID)
        self.assertEqual(
            [(a.tag, a.get("id")) for a in m.find("InGameActions")],
            [("UpdateDatabase", "X10Dummy"),
             ("UpdateDatabase", "X10WonderBridge"),
             ("UpdateDatabase", "X10SlotCopies")])
        deps = [d.get("id") for d in m.find("Dependencies")]
        self.assertEqual(deps, ["4873eb62-8ccc-4574-b784-dda455e74e68",
                                PROD_ENGINE_ID])


if __name__ == "__main__":
    unittest.main(verbosity=2)
