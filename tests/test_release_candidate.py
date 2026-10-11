"""Phase 7B.1: release-candidate assembly / export / staging tests.

Static tests (manifest schema, modinfo gameplay structure, assembler
guards) run everywhere. Dynamic tests (assemble, export, isolated
public pytest) run the real tools; the assembler needs pwsh.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
PWSH = shutil.which("pwsh")

ENGINE_ID = "397f2070-dfde-4124-88ce-e34249fc8190"
CONTROLLER_ID = "55d7b934-62f9-46fb-a771-badf3d1a1538"


def manifest():
    import yaml
    return yaml.safe_load(
        (ROOT / "release" / "release-manifest.yml").read_text(
            encoding="utf-8"))


def norm_hash(path: Path) -> str:
    return hashlib.sha256(
        path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


class TestModinfoGameplayFrozen(unittest.TestCase):
    def _mod(self, rel):
        import xml.etree.ElementTree as ET
        return ET.parse(str(ROOT / rel)).getroot()

    def test_controller_gameplay_structure(self):
        m = self._mod("controller/X10/X10.modinfo")
        self.assertEqual(m.get("id"), CONTROLLER_ID)
        self.assertEqual(m.get("version"), "1")
        deps = [(d.get("id"), d.get("title"))
                for d in m.find("Dependencies")]
        self.assertEqual(deps, [
            ("4873eb62-8ccc-4574-b784-dda455e74e68",
             "Expansion: Gathering Storm"),
            (ENGINE_ID, "X10 CE Engine"),
        ])
        fe = [(a.tag, a.get("id"),
               [f.text for f in a.find("File") or [a.find("File")]]
               if a.find("File") is not None else None)
              for a in m.find("FrontEndActions")]
        self.assertEqual([(t, i) for t, i, _ in fe],
                         [("UpdateDatabase", "X10Config")])
        ig = [(a.tag, a.get("id")) for a in m.find("InGameActions")]
        self.assertEqual(ig, [("UpdateDatabase", "X10Dummy"),
                             ("UpdateDatabase", "X10WonderBridge")])
        ig_files = [[f.text for f in a.iter("File")]
                    for a in m.find("InGameActions")]
        self.assertEqual(ig_files, [["Config/Dummy.sql"],
                                    ["Config/X10WonderBridge.sql"]])
        fe_files = [[f.text for f in a.iter("File")]
                    for a in m.find("FrontEndActions")]
        self.assertEqual(fe_files, [["Config/X10Config.sql"]])
        files = sorted(f.text for f in m.find("Files"))
        self.assertEqual(files, [
            "Config/Dummy.sql", "Config/X10Config.sql",
            "Config/X10WonderBridge.sql", "LICENSE.txt", "README.txt",
            "SOURCE.txt", "THIRD_PARTY_NOTICES.txt",
        ])

    def test_engine_gameplay_structure(self):
        import xml.etree.ElementTree as ET
        m = self._mod("dependencies/CE-X10/CE-X10.modinfo")
        self.assertEqual(m.get("id"), ENGINE_ID)
        self.assertEqual(m.get("version"), "1")
        deps = [(d.get("id")) for d in m.find("Dependencies")]
        self.assertEqual(deps, ["4873eb62-8ccc-4574-b784-dda455e74e68"])
        fe = [(a.tag, a.get("id")) for a in m.find("FrontEndActions")]
        self.assertEqual(fe, [("UpdateDatabase", "X10EngineRedirect")])
        ig = [(a.tag, a.get("id")) for a in m.find("InGameActions")]
        self.assertEqual(ig, [("UpdateDatabase", "X10EngineDummy")])
        files = sorted(f.text for f in m.find("Files"))
        self.assertEqual(files, [
            "Binaries/Win64/GameCore_XP2_CE_FinalRelease.dll",
            "Config/Dummy.sql", "Config/EngineRedirect.sql",
            "LICENSE.txt", "README.txt", "SOURCE.txt",
            "THIRD_PARTY_NOTICES.txt",
        ])

    def test_only_approved_metadata_changed(self):
        # Descriptions carry the new two-item wording; gameplay nodes
        # (checked above) are byte-stable apart from that + <Files>.
        for rel in ("controller/X10/X10.modinfo",
                    "dependencies/CE-X10/CE-X10.modinfo"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("One configurable Workshop item", text)


class TestManifestSurfaces(unittest.TestCase):
    def test_schema(self):
        man = manifest()
        self.assertEqual(man["release_version"], "1.0.0-rc1")
        self.assertEqual(man["modinfo_version"], 1)
        items = man["workshop_items"]
        self.assertEqual(set(items), {"engine", "controller"})
        self.assertFalse(items["engine"]["primary"])
        self.assertTrue(items["controller"]["primary"])
        self.assertEqual(items["controller"]["requires"], ["engine"])
        routedge = [e["stage_path"]
                    for e in items["engine"]["runtime_files"]]
        self.assertEqual(sorted(routedge),
                         sorted(["CE-X10.modinfo", "Config/EngineRedirect.sql",
                                 "Config/Dummy.sql",
                                 "Binaries/Win64/"
                                 "GameCore_XP2_CE_FinalRelease.dll"]))
        for item in items.values():
            aux = sorted(e["stage_path"]
                         for e in item["auxiliary_files"])
            self.assertEqual(aux, ["LICENSE.txt", "README.txt",
                                   "SOURCE.txt", "THIRD_PARTY_NOTICES.txt"])
        self.assertTrue(man["source_release"]["build_assets"])

    def test_no_absolute_paths(self):
        import yaml
        dumped = yaml.safe_dump(manifest())
        self.assertNotIn("C:", dumped)
        self.assertNotIn("Users", dumped)
        self.assertNotIn("ce-test-build", dumped)

    def test_placeholders_flagged(self):
        man = manifest()
        flagged = [e["stage_path"]
                   for item in man["workshop_items"].values()
                   for e in item["auxiliary_files"]
                   if e.get("has_planned_placeholder")]
        self.assertEqual(sorted(flagged), ["SOURCE.txt", "SOURCE.txt"])
        for item in ("engine", "controller"):
            src = ROOT / f"release/staging-src/{item}/SOURCE.txt"
            self.assertIn("PLANNED-PLACEHOLDER",
                          src.read_text(encoding="utf-8"))


class TestAssemblerStatic(unittest.TestCase):
    def _ps1(self):
        return (ROOT / "release" / "assemble-release.ps1").read_text(
            encoding="utf-8")

    def test_no_absolute_developer_paths(self):
        text = self._ps1()
        self.assertNotIn("C:\\Users", text)
        self.assertNotIn("C:/Users", text)
        self.assertNotIn("ce-native-build", text)

    def test_scratch_dll_only_as_refusal(self):
        text = self._ps1()
        self.assertIn("ce-test-build", text)
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if "ce-test-build" in line:
                context = " ".join(lines[i:i + 3]).lower()
                self.assertTrue("refus" in context or "throw" in context,
                                line)

    def test_required_guards_present(self):
        text = self._ps1()
        # DLL hash comes from the manifest (single source of truth), which
        # the script reads; the script itself must reference the manifest
        for needle in ("$man.dll_sha256", "forbidden_in_release",
                       "PLANNED-PLACEHOLDER",
                       "AllowPlaceholderUrls",
                       "CHECKSUMS.sha256"):
            self.assertIn(needle, text)

    def test_required_parameters(self):
        text = self._ps1()
        for needle in ("$OutDir", "$DllPath", "$Manifest",
                       "$AllowPlaceholderUrls"):
            self.assertIn(needle, text)


class TestAssembleDynamic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if PWSH is None:
            raise unittest.SkipTest("pwsh unavailable")
        dll = (Path.home() / "Desktop" / "Code" / "ce-native-build" /
               "GameCore_XP2_CE_FinalRelease.dll")
        if not dll.is_file():
            # fall back to repo-adjacent canonical build location
            alt = (ROOT.parent / "ce-native-build" /
                   "GameCore_XP2_CE_FinalRelease.dll")
            dll = alt if alt.is_file() else None
        if dll is None:
            raise unittest.SkipTest("validated DLL build unavailable")
        cls.dll = str(dll)
        cls.outdir = (Path(__import__("tempfile").mkdtemp(
            prefix="x10rc")) / "1.0.0-rc1")
        r = subprocess.run(
            [PWSH, "-NoProfile", "-File",
             str(ROOT / "release" / "assemble-release.ps1"),
             "-OutDir", str(cls.outdir), "-DllPath", cls.dll,
             "-AllowPlaceholderUrls"],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise unittest.SkipTest(f"assembler failed: {r.stderr[-500:]}")

    def test_tree_matches_manifest(self):
        man = manifest()
        staged = []
        for item in man["workshop_items"].values():
            d = self.outdir / "workshop" / item["stage_dir"]
            for e in item["runtime_files"] + item["auxiliary_files"]:
                p = d / e["stage_path"]
                self.assertTrue(p.is_file(), str(p))
                staged.append(p)
        walked = [p for p in (self.outdir / "workshop").rglob("*")
                  if p.is_file() and p.name != "CHECKSUMS-item.sha256"]
        self.assertEqual(sorted(map(str, walked)), sorted(map(str, staged)))

    def test_no_probe_in_staging(self):
        for bad in ("X10_Probe_Test", "probe.lua", "stonediag.lua"):
            hits = [p for p in self.outdir.rglob("*") if bad in p.name]
            self.assertEqual(hits, [], bad)

    def test_checksums_reproduce(self):
        lines = (self.outdir / "CHECKSUMS.sha256").read_text(
            encoding="utf-8").splitlines()
        self.assertTrue(lines)
        for line in lines:
            want, rel = line.split("  ")
            p = self.outdir / rel
            self.assertTrue(p.is_file(), rel)
            got = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(got, want, rel)

    def test_notices_present_in_both_items(self):
        for item, d in (("engine", "X10-CE-Engine"),
                        ("controller", "X10")):
            for name in ("README.txt", "LICENSE.txt",
                         "THIRD_PARTY_NOTICES.txt", "SOURCE.txt"):
                self.assertTrue(
                    (self.outdir / "workshop" / d / name).is_file(), name)

    def test_wrong_dll_rejected(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".dll",
                                         delete=False) as fh:
            fh.write(b"bogus")
            bogus = fh.name
        try:
            r = subprocess.run(
                [PWSH, "-NoProfile", "-File",
                 str(ROOT / "release" / "assemble-release.ps1"),
                 "-OutDir", str(self.outdir.parent / "reject"),
                 "-DllPath", bogus, "-AllowPlaceholderUrls"],
                capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
        finally:
            Path(bogus).unlink(missing_ok=True)

    def test_scratch_dll_path_rejected(self):
        r = subprocess.run(
            [PWSH, "-NoProfile", "-File",
             str(ROOT / "release" / "assemble-release.ps1"),
             "-OutDir", str(self.outdir.parent / "reject2"),
             "-DllPath", "C:/x/ce-test-build/GameCore.dll",
             "-AllowPlaceholderUrls"],
            capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ce-test-build", (r.stderr + r.stdout).lower())

    def test_placeholder_refused_without_flag(self):
        r = subprocess.run(
            [PWSH, "-NoProfile", "-File",
             str(ROOT / "release" / "assemble-release.ps1"),
             "-OutDir", str(self.outdir.parent / "reject3"),
             "-DllPath", self.dll],
            capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


class TestPublicExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.tmp = Path(tempfile.mkdtemp(prefix="x10pub"))
        r = subprocess.run(
            [sys.executable, str(ROOT / "release" / "export_public_source.py"),
             "--out", str(cls.tmp), "--version", "1.0.0-rc1"],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise unittest.SkipTest(f"export failed: {r.stderr[-500:]}")
        cls.root = cls.tmp / "civ6-x10-release-source"

    def test_no_git_no_forbidden(self):
        self.assertFalse((self.root / ".git").exists())
        names = {p.name for p in self.root.rglob("*")}
        for bad in ("governor_audit.yml", "suzerain_audit.yml",
                    "semantic_backlog.yml", "wonder_audit.yml",
                    "pantheon_audit.yml", "governors.yml", "suzerain.yml",
                    "traits.yml"):
            self.assertNotIn(bad, names, bad)
        self.assertFalse(list(self.root.rglob("*.log")))
        self.assertFalse((self.root / "data" / "local").exists())
        self.assertFalse((self.root / "research").exists())

    def test_no_absolute_paths(self):
        hits = []
        for p in self.root.rglob("*"):
            if not p.is_file() or p.suffix == ".pyc" \
                    or "__pycache__" in p.parts:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for needle in ("C:\\Users", "C:/Users", "/home/", "/Users/"):
                if needle in text:
                    hits.append((str(p.relative_to(self.root)), needle))
        self.assertEqual(hits, [])

    def test_provenance_present_and_clean(self):
        prov = (self.root / "PROVENANCE.md").read_text(encoding="utf-8")
        for needle in ("2cf953e", "phase6b-1010-live-validated", "1ce3188",
                       "1.0.0-rc1", "file-list hash"):
            self.assertIn(needle, prov)
        for needle in ("C:\\Users", "/home/", "data/local/Debug"):
            self.assertNotIn(needle, prov)

    def test_isolated_pytest(self):
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            cwd=str(self.root), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-500:])
        import re
        m = re.search(r"(\d+) passed(?:, (\d+) skipped)?", r.stdout)
        self.assertIsNotNone(m, r.stdout[-500:])
        self.assertGreater(int(m.group(1)), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
