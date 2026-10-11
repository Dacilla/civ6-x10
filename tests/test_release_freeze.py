"""Phase 7A: release-freeze invariant for the validated gameplay state.

Pins the Phase-6B/6C validated production point
(2cf953e + CE 1ce3188 + DLL e33d84b8...d619): registry digest/counts,
manifests, owner bits, CE include, DLL pin, bridge/config hashes,
controller toggles. Phase 7A may change docs/tests/release tooling, but
production runtime files must stay byte-identical.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

# Frozen Phase-6B/6C gameplay-production point.
#
# Text-file hashes are LF-NORMALIZED (universal-newlines read) so they are
# identical on Windows (CRLF worktree) and Linux (LF checkout) CI, matching
# the project's existing text-mode digest convention. The live-validated
# Windows packaging bytes hash differently (bridge CRLF d0faabfa...,
# registry CRLF f42c6a61...); SQL semantics are line-ending insensitive and
# the 7B assembler must normalize before comparing.
FROZEN_REGISTRY_SHA256 = (
    "181ab439f98c40e85b0cd178a3cc0cd8da7a3f1a20c0c779300f923792315208")
FROZEN_DLL_SHA256 = (
    "e33d84b83d752a9eb7b52b4740291c97183af4d079d1ca82b8bd9d92b5c4d619")
FROZEN_BRIDGE_SHA256 = (
    "81c3dda2f80625acf55bb9c3f99b8850b4c5ebe2109b9e26193ddd8497950fbe")
FROZEN_CONFIG_SHA256 = (
    "1987a11f29be4ba3434ffd416f48ed9c5a6297153dc984a821866920726d3b4b")
FROZEN_X10_MODINFO_SHA256 = (
    "54c278b66e48e921cb1ecef80e2a43d37560a14e8cfdc10214bfadca9d30877d")
FROZEN_ENGINE_MODINFO_SHA256 = (
    "2a761d7abf4e7c364e9610af06946f0e823f39ce1b7e73f8810da99c22ace0fe")
FROZEN_REDIRECT_SHA256 = (
    "3bb8544dd2babc9e2851628c3ce8470b36800f464430401eba09884f85df2ea3")


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


class TestReleaseFreeze(unittest.TestCase):
    def test_registry_digest_and_counts(self):
        from civ6x10.bridge import collect_registry_rows
        from civ6x10.production import build_production_registry
        inc = ROOT / "build" / "X10ProductionRegistry.inc"
        if not inc.is_file():
            self.skipTest("local production registry unavailable")
        self.assertEqual(sha256(inc), FROZEN_REGISTRY_SHA256)
        try:
            entries, report = build_production_registry(
                collect_registry_rows(ROOT))
        except FileNotFoundError:
            self.skipTest("local-only registry inputs unavailable")
        self.assertEqual(len(entries), 1010)
        self.assertEqual(report["unique_definitions"], 1006)
        self.assertEqual(report["shared_definitions"], 25)
        self.assertEqual(report["certified_unconditional"], 788)
        self.assertEqual(report["certified_count_like_conditional"], 222)
        self.assertEqual(report["ownership_counts"]["governors"], 70)
        self.assertEqual(report["ownership_counts"]["suzerain"], 68)
        self.assertEqual(report["ownership_counts"]["traits"], 360)

    def test_manifest_counts(self):
        import yaml
        for name, module, want in (("governors.yml", "governors", 70),
                                   ("suzerain.yml", "suzerain", 68)):
            p = ROOT / "manifests" / name
            if not p.is_file():
                self.skipTest(f"local manifest {name} unavailable")
            rows = yaml.safe_load(p.read_text(encoding="utf-8"))[module]
            self.assertEqual(len(rows), want, name)
            self.assertEqual(len({(r["modifier_id"], r["argument_name"])
                                  for r in rows}), want, name)

    def test_owner_bits_and_modules(self):
        from civ6x10.bridge import REGISTRY_MODULES
        from civ6x10.production import MODULE_BITS
        self.assertEqual(MODULE_BITS, {"traits": 1, "policies": 2,
                                       "governments": 4, "pantheons": 8,
                                       "wonders": 16, "governors": 32,
                                       "suzerain": 64})
        self.assertEqual(tuple(REGISTRY_MODULES),
                         ("traits", "policies", "governments", "pantheons",
                          "wonders", "governors", "suzerain"))

    def test_ce_include_byte_identical(self):
        src = ROOT / "build" / "X10ProductionRegistry.inc"
        fork = (ROOT.parent / "CivilizationVI_CommunityExtension-x10-spike"
                / "X10" / "X10ProductionRegistry.inc")
        if not src.is_file():
            self.skipTest("local production registry unavailable")
        if not fork.is_file():
            self.skipTest("CE fork registry copy unavailable")
        self.assertEqual(src.read_bytes(), fork.read_bytes())

    def test_dll_pin(self):
        p = ROOT / "spike" / "EXPECTED_DLL_SHA256.txt"
        if not p.is_file():
            self.skipTest("expected DLL hash unavailable")
        self.assertEqual(p.read_text(encoding="utf-8").strip().lower(),
                         FROZEN_DLL_SHA256)

    def test_controller_hashes(self):
        frozen = {
            "controller/X10/Config/X10WonderBridge.sql":
                FROZEN_BRIDGE_SHA256,
            "controller/X10/Config/X10Config.sql": FROZEN_CONFIG_SHA256,
            "controller/X10/X10.modinfo": FROZEN_X10_MODINFO_SHA256,
            "dependencies/CE-X10/CE-X10.modinfo":
                FROZEN_ENGINE_MODINFO_SHA256,
            "dependencies/CE-X10/Config/EngineRedirect.sql":
                FROZEN_REDIRECT_SHA256,
        }
        for rel, want in frozen.items():
            p = ROOT / rel
            if not p.is_file():
                self.skipTest(f"{rel} unavailable")
            self.assertEqual(sha256(p), want, rel)

    def test_seven_toggles_default_on(self):
        import re
        p = ROOT / "controller" / "X10" / "Config" / "X10Config.sql"
        if not p.is_file():
            self.skipTest("controller config unavailable")
        text = p.read_text(encoding="utf-8")
        # ParameterId position opens the VALUES tuple; ConfigurationId
        # occurrences are preceded by 'Game' and never match this prefix.
        names = re.findall(r"\('X10_MODULE_([A-Z]+)',", text)
        self.assertEqual(
            names,
            ["TRAITS", "POLICIES", "GOVERNMENTS", "PANTHEONS",
             "GOVERNORS", "WONDERS", "SUZERAIN"])
        defaults = re.findall(r"'int',\s*'(\d)'", text)
        self.assertEqual(defaults, ["1"] * 7)

    def test_release_manifest_matches_reality(self):
        import yaml
        p = ROOT / "release" / "release-manifest.yml"
        if not p.is_file():
            self.skipTest("release manifest unavailable")
        man = yaml.safe_load(p.read_text(encoding="utf-8"))
        self.assertNotIn("C:", yaml.safe_dump(man),
                         "no absolute developer paths in release manifest")
        self.assertNotIn("Users", yaml.safe_dump(man))
        self.assertEqual(man["dll_sha256"], FROZEN_DLL_SHA256)
        ctrl = man["workshop_items"]["controller"]
        bridge = [e for e in ctrl["runtime_files"]
                  if e["stage_path"] == "Config/X10WonderBridge.sql"][0]
        self.assertEqual(bridge["sha256"], FROZEN_BRIDGE_SHA256)
        reg = [a for a in man["source_release"]["build_assets"]
               if a["asset_path"] == "X10ProductionRegistry.inc"][0]
        self.assertEqual(reg["sha256"], FROZEN_REGISTRY_SHA256)
        self.assertEqual(man["registry_entries"], 1010)
        self.assertEqual(man["production_commit"], "2cf953e")
        self.assertEqual(man["ce_commit"], "1ce3188")
        self.assertEqual(man["live_validation_tag"],
                         "phase6b-1010-live-validated")
        self.assertIn("X10_Probe_Test", man["forbidden_in_release"])
        self.assertIn("probe.lua", man["forbidden_in_release"])
        self.assertEqual(man["release_version"], "1.0.0-rc1")
        self.assertEqual(man["modinfo_version"], 1)
        self.assertEqual(man["workshop_items"]["engine"]["mod_id"],
                         "397f2070-dfde-4124-88ce-e34249fc8190")
        self.assertEqual(man["workshop_items"]["controller"]["mod_id"],
                         "55d7b934-62f9-46fb-a771-badf3d1a1538")
        self.assertEqual(man["workshop_items"]["controller"]["requires"],
                         ["engine"])
        # every staged file resolves to a source file with the pinned
        # LF-normalized hash (engine DLL resolves to the pinned build)
        for item in man["workshop_items"].values():
            for entry in item["runtime_files"] + item["auxiliary_files"]:
                if entry.get("dll_input"):
                    continue
                src = ROOT / entry["source"]
                self.assertTrue(src.is_file(), entry["stage_path"])
                self.assertEqual(sha256(src), entry["sha256"],
                                 entry["stage_path"])
        self.assertEqual(len(man["workshop_items"]["engine"]["runtime_files"]
                             + man["workshop_items"]["engine"]
                             ["auxiliary_files"]), 8)
        self.assertEqual(len(man["workshop_items"]["controller"]
                             ["runtime_files"]
                             + man["workshop_items"]["controller"]
                             ["auxiliary_files"]), 8)


class TestReleaseSurfaceInventory(unittest.TestCase):
    def _report(self):
        import json
        p = ROOT / "reports" / "release_surface.json"
        if not p.is_file():
            self.skipTest("release-surface report unavailable")
        return json.loads(p.read_text(encoding="utf-8"))

    def test_report_reproduces(self):
        import json
        from civ6x10.release_surface import build_release_surface
        rep = self._report()
        fresh = build_release_surface(ROOT)
        # exact equality over the TRACKED subset only: untracked local
        # inputs (build/, gitignored manifests, data/local/) are
        # machine-specific and covered structurally below
        old = [f for f in rep["files"] if f["tracked"]]
        new = [f for f in fresh["files"] if f["tracked"]]
        self.assertEqual(new, old)
        def summary(files):
            from collections import Counter
            agg = {}
            for f in files:
                agg.setdefault(f["surface"], {"files": 0, "bytes": 0})
                agg[f["surface"]]["files"] += 1
                agg[f["surface"]]["bytes"] += f["bytes"]
            return agg
        self.assertEqual(summary(new),
                         summary([f for f in rep["files"] if f["tracked"]]))
        # structural invariants over the full local report
        paths = {f["path"] for f in fresh["files"]}
        for rel in ("controller/X10/Config/X10WonderBridge.sql",
                    "dependencies/CE-X10/CE-X10.modinfo"):
            self.assertIn(rel, paths, rel)

    def test_every_runtime_source_classified(self):
        rep = self._report()
        by_path = {f["path"]: f for f in rep["files"]}
        for rel in ("controller/X10/X10.modinfo",
                    "controller/X10/Config/X10Config.sql",
                    "controller/X10/Config/X10WonderBridge.sql",
                    "controller/X10/Config/Dummy.sql",
                    "dependencies/CE-X10/CE-X10.modinfo",
                    "dependencies/CE-X10/Config/EngineRedirect.sql",
                    "dependencies/CE-X10/Config/Dummy.sql"):
            self.assertIn(rel, by_path, rel)
            self.assertEqual(by_path[rel]["surface"], "workshop_runtime",
                             rel)
            self.assertTrue(by_path[rel]["tracked"], rel)

    def test_probe_forbidden_from_runtime(self):
        import yaml
        man = yaml.safe_load(
            (ROOT / "release" / "release-manifest.yml")
            .read_text(encoding="utf-8"))
        staged = [e["stage_path"]
                  for item in man["workshop_items"].values()
                  for e in item["runtime_files"] + item["auxiliary_files"]]
        self.assertTrue(all("Probe" not in a for a in staged))
        self.assertIn("X10_Probe_Test", man["forbidden_in_release"])
        rep = self._report()
        by_path = {f["path"]: f for f in rep["files"]}
        for path, entry in by_path.items():
            if "Probe_Test" in path or "probe.lua" in path:
                self.assertNotEqual(entry["surface"], "workshop_runtime",
                                    path)

    def test_no_unclassified_files(self):
        rep = self._report()
        un = [f["path"] for f in rep["files"]
              if f["kind"] == "unclassified"]
        self.assertEqual(un, [])

    def test_improvement_closure_zero_open_decisions(self):
        import yaml
        bl = yaml.safe_load(
            (ROOT / "civ6x10" / "rules" / "semantic_backlog.yml")
            .read_text(encoding="utf-8"))
        self.assertNotIn("NEEDS_PRODUCT_DECISION", bl["by_resolution"])
        imp = [r for r in bl["rows"] if r["source_kind"] == "improvement"]
        self.assertEqual(len(imp), 58)
        self.assertTrue(all(r["resolution"] == "RESOLVED_EXCLUDED"
                            for r in imp))


if __name__ == "__main__":
    unittest.main(verbosity=2)
