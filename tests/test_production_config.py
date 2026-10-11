"""Phase 7C.2: production setup-UI/config tests + resolution-mirror tests.

Parses the real production X10Config.sql / X10Text.sql / modinfos.
The ResolveEffectiveMultiplier mirror below is spec-derived from the C++
implementation (same ordered table); it pins the §23 compatibility matrix
and the fail-closed rules. Native execution is proven live (Runs A-D).
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "controller" / "X10" / "Config" / "X10Config.sql"
TEXT = ROOT / "controller" / "X10" / "Config" / "X10Text.sql"

MODULE_IDS = ["X10_MODULE_TRAITS", "X10_MODULE_POLICIES",
              "X10_MODULE_GOVERNMENTS", "X10_MODULE_PANTHEONS",
              "X10_MODULE_WONDERS", "X10_MODULE_GOVERNORS",
              "X10_MODULE_SUZERAIN"]


def config_rows():
    """Parse the Parameters VALUES tuples (positional)."""
    text = CONFIG.read_text(encoding="utf-8")
    body = text.split("VALUES", 1)[1].split(";")[0]
    rows = []
    for m in re.finditer(r"\(([^;]*?)\)\s*,?\s*$", body, re.M):
        cells = [c.strip() for c in m.group(1).split(",")]
        rows.append(cells)
    return rows


class TestProductionSetupLayout(unittest.TestCase):
    def test_nine_params_advanced_options(self):
        rows = config_rows()
        self.assertEqual(len(rows), 9)
        for r in rows:
            self.assertEqual(r[8].strip("'"), "AdvancedOptions", r)
        self.assertEqual([int(r[9]) for r in rows],
                         [2400, 2401, 2402, 2403, 2404, 2405, 2406, 2407,
                          2408])

    def test_preset_row(self):
        rows = config_rows()
        preset = rows[0]
        self.assertEqual(preset[0].strip("'"), "X10Preset")
        self.assertEqual(preset[3].strip("'"), "X10MultiplierPresets")
        self.assertEqual(preset[6].strip("'"), "Game")
        self.assertEqual(preset[7].strip("'"), "X10_MULTIPLIER_PRESET")
        # INTEGER default (never TEXT): the driver ==-compares against
        # numeric domain values
        self.assertEqual(preset[4], "10")
        self.assertNotEqual(preset[4], "'10'")

    def test_custom_row(self):
        rows = config_rows()
        custom = rows[1]
        self.assertEqual(custom[0].strip("'"), "X10Custom")
        self.assertEqual(custom[3].strip("'"), "text")
        self.assertEqual(custom[7].strip("'"), "X10_MULTIPLIER")

    def test_module_rows_bool_unchanged_ids(self):
        rows = config_rows()[2:]
        self.assertEqual([r[7].strip("'") for r in rows], MODULE_IDS)
        for r in rows:
            self.assertEqual(r[3].strip("'"), "bool", r)
            self.assertEqual(r[4].strip("'"), "1", r)

    def test_scope_flags(self):
        for r in config_rows():
            # Visible, SP, LAN, NET, HS, Cloud, Changeable
            self.assertEqual([c.strip() for c in r[10:17]],
                             ["1", "1", "0", "0", "0", "0", "0"], r)

    def test_domain_values_exact(self):
        text = CONFIG.read_text(encoding="utf-8")
        body = text.split("DomainValues")[1].split(";")[0]
        vals = re.findall(r"\('X10MultiplierPresets', (\d+),", body)
        self.assertEqual([int(v) for v in vals],
                         [0, 2, 3, 5, 10, 20, 50, 100, 101])

    def test_custom_dependency_exact(self):
        text = CONFIG.read_text(encoding="utf-8")
        dep = text.split("ParameterDependencies")[1]
        self.assertIn("'X10Custom', 'Game', 'X10_MULTIPLIER_PRESET', "
                      "'Equals', 101",
                      " ".join(dep.split()))

    def test_no_config_id_jargon_in_labels(self):
        text = CONFIG.read_text(encoding="utf-8")
        # Names/Descriptions reference only LOC keys (checked precisely
        # below); raw X10_* keys appear solely as ConfigurationIds
        names = re.findall(
            r"\('X10\w+', '(LOC_[^']+)', '(LOC_[^']+)'", text)
        self.assertEqual(len(names), 9)
        for name, desc in names:
            self.assertTrue(name.startswith("LOC_X10_"), name)
            self.assertTrue(desc.startswith("LOC_X10_"), desc)


class TestProductionLocCoverage(unittest.TestCase):
    def test_every_loc_key_resolves_en_us(self):
        cfg = CONFIG.read_text(encoding="utf-8")
        keys = set(re.findall(r"LOC_X10_[A-Z0-9_]+", cfg))
        self.assertTrue(keys)
        text = TEXT.read_text(encoding="utf-8")
        have = set(re.findall(r"\('en_US', '(LOC_[^']+)'", text))
        self.assertEqual(sorted(keys - have), [])
        # preset display names + descriptions all covered
        for tag in ("LOC_X10_PRESET_OFF", "LOC_X10_PRESET_10",
                    "LOC_X10_PRESET_CUSTOM", "LOC_X10_PRESET_CUSTOM_DESC"):
            self.assertIn(tag, have, tag)


class TestProductionModinfo7C2(unittest.TestCase):
    def _mod(self, rel):
        import xml.etree.ElementTree as ET
        return ET.parse(str(ROOT / rel)).getroot()

    def test_controller_metadata(self):
        m = self._mod("controller/X10/X10.modinfo")
        self.assertEqual(m.get("id"),
                         "55d7b934-62f9-46fb-a771-badf3d1a1538")
        props = m.find("Properties")
        self.assertEqual(props.find("Name").text,
                         "X10 — Configurable Bonus Multiplier")
        self.assertTrue(props.find("Teaser").text)
        self.assertEqual(props.find("CompatibleVersions").text, "2.0")
        self.assertEqual(props.find("SupportsSinglePlayer").text, "1")
        self.assertEqual(props.find("SupportsMultiplayer").text, "0")
        self.assertEqual(
            [f.text for f in m.find("Files")].count("Config/X10Text.sql"),
            1)
        self.assertIn("Config/X10Text.sql",
                      [f.text for f in m.find("Files")])

    def test_engine_metadata(self):
        m = self._mod("dependencies/CE-X10/CE-X10.modinfo")
        self.assertEqual(m.get("id"),
                         "397f2070-dfde-4124-88ce-e34249fc8190")
        props = m.find("Properties")
        self.assertEqual(props.find("Name").text, "X10 CE Engine")
        self.assertTrue(props.find("Teaser").text)
        self.assertNotIn("branch", props.find("Description").text or "")
        self.assertEqual(props.find("SupportsSinglePlayer").text, "1")
        self.assertEqual(props.find("SupportsMultiplayer").text, "0")

    def test_gameplay_actions_stable(self):
        m = self._mod("controller/X10/X10.modinfo")
        self.assertEqual(
            [(a.tag, a.get("id")) for a in m.find("FrontEndActions")],
            [("UpdateDatabase", "X10Config"), ("UpdateText", "X10Text")])
        self.assertEqual(
            [(a.tag, a.get("id")) for a in m.find("InGameActions")],
            [("UpdateDatabase", "X10Dummy"),
             ("UpdateDatabase", "X10WonderBridge")])


# --- Resolution mirror (spec-derived from X10Write.cpp) --------------------
ABSENT, UNSET, VALID, INVALID = "ABSENT", "UNSET", "VALID", "INVALID"
PRESETS = (0, 2, 3, 5, 10, 20, 50, 100, 101)


def decode_bool(state, value):
    """Mirror of TryGetConfigBool: (ok, value_or_state)."""
    if state in (ABSENT, UNSET):
        return (False, state)
    if state == VALID and value in (0, 1):
        return (True, bool(value))
    return (False, INVALID)


def resolve(preset, custom, legacy):
    """Mirror of ResolveEffectiveMultiplier.

    Each arg is (state, value). Returns ("arm", k) | ("off",) |
    ("disabled", reason).
    """
    pst, pval = preset
    if pst == VALID and pval in PRESETS:
        if pval == 101:
            cst, cval = custom
            if cst == VALID and isinstance(cval, (int, float)) \
                    and 0 <= cval <= 100:
                return ("arm", float(cval))
            return ("disabled", "custom-invalid")
        if pval == 0:
            return ("off",)
        return ("arm", float(pval))
    if pst in (ABSENT, UNSET):
        lst, lval = legacy
        if lst == VALID and isinstance(lval, (int, float)) \
                and 0 <= lval <= 100:
            return ("arm", float(lval)) if lval != 0 else ("off",)
        return ("disabled", "legacy-invalid")
    return ("disabled", "preset-invalid")


class TestResolutionMirror(unittest.TestCase):
    def test_legacy_73_no_preset(self):
        self.assertEqual(resolve((ABSENT, None), (INVALID, None),
                                 (VALID, 7.3)),
                         ("arm", 7.3))

    def test_unset_preset_legacy_73(self):
        self.assertEqual(resolve((UNSET, None), (INVALID, None),
                                 (VALID, 7.3)),
                         ("arm", 7.3))

    def test_legacy_module_ints(self):
        self.assertEqual(decode_bool(ABSENT, None), (False, ABSENT))
        self.assertEqual(decode_bool(UNSET, None), (False, UNSET))
        self.assertEqual(decode_bool(VALID, 0), (True, False))
        self.assertEqual(decode_bool(VALID, 1), (True, True))
        self.assertEqual(decode_bool(VALID, 2), (False, INVALID))

    def test_preset_wins_over_legacy(self):
        self.assertEqual(resolve((VALID, 10), (INVALID, None),
                                 (VALID, 7.3)),
                         ("arm", 10.0))

    def test_custom_path(self):
        self.assertEqual(resolve((VALID, 101), (VALID, 7.3),
                                 (VALID, 10)),
                         ("arm", 7.3))

    def test_invalid_preset_no_fallback(self):
        self.assertEqual(resolve((INVALID, None), (VALID, 7.3),
                                 (VALID, 7.3)),
                         ("disabled", "preset-invalid"))

    def test_invalid_custom_cases(self):
        for bad in ("", "abc", -1, 101):
            st = VALID if isinstance(bad, (int, float)) else INVALID
            self.assertEqual(resolve((VALID, 101), (st, bad),
                                     (VALID, 10))[0],
                             "disabled", bad)

    def test_valid_custom_cases(self):
        self.assertEqual(resolve((VALID, 101), (VALID, 0.5), (VALID, 10)),
                         ("arm", 0.5))
        self.assertEqual(resolve((VALID, 101), (VALID, 7.3), (VALID, 10)),
                         ("arm", 7.3))
        self.assertEqual(resolve((VALID, 101), (VALID, 100), (VALID, 10)),
                         ("arm", 100.0))
        # custom 0 resolves as k=0; the caller normalizes k==0 to OFF
        # (long-standing convention, preserved)
        self.assertEqual(resolve((VALID, 101), (VALID, 0), (VALID, 10)),
                         ("arm", 0.0))

    def test_off(self):
        self.assertEqual(resolve((VALID, 0), (INVALID, None),
                                 (VALID, 7.3)),
                         ("off",))

    def test_native_reader_source_matches_spec(self):
        src = (ROOT.parent / "CivilizationVI_CommunityExtension-x10-spike"
               / "X10Write.cpp")
        if not src.is_file():
            self.skipTest("CE fork unavailable")
        text = src.read_text(encoding="utf-8")
        # allowlist enforced in native code
        m = re.search(r"kAllowed\[\] = \{([^}]*)\}", text)
        self.assertIsNotNone(m)
        self.assertEqual(
            sorted(int(v) for v in m.group(1).split(",") if v.strip()),
            [0, 2, 3, 5, 10, 20, 50, 100, 101])
        # ordered resolution keys present
        for needle in ("X10_MULTIPLIER_PRESET", "X10_MULTIPLIER",
                       "TryGetProbeKEx", "fail closed"):
            self.assertIn(needle, text)


class TestRegistryStill1010(unittest.TestCase):
    def test_counts(self):
        from civ6x10.bridge import collect_registry_rows
        from civ6x10.production import build_production_registry
        try:
            entries, report = build_production_registry(
                collect_registry_rows(ROOT))
        except FileNotFoundError:
            raise unittest.SkipTest("local-only registry inputs unavailable")
        self.assertEqual(len(entries), 1010)
        self.assertEqual(report["unique_definitions"], 1006)
        self.assertEqual(report["certified_unconditional"], 788)
        self.assertEqual(report["certified_count_like_conditional"], 222)


if __name__ == "__main__":
    unittest.main(verbosity=2)
