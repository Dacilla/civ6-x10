"""Phase 7A: release-surface inventory (audit/design only).

Walks the working tree + git index and classifies every relevant file into
Workshop runtime payload / public corresponding-source surface / private
developer workspace, with provenance, size, and a proposed release
disposition. Writes reports/release_surface.json (regenerable).
Does not mutate production runtime files.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

# (prefix, surface, kind, generated, runtime_required, rebuild_required,
#  audit_only, provenance, disposition)
RULES = [
    ("controller/X10/Config/X10WonderBridge.sql",
     "workshop_runtime", "generated_guarded_bridge", True, True, False,
     False, "generated from official DB direct cells + curated guards",
     "ship (required runtime behavior; minimal-guard policy already applied)"),
    ("controller/", "workshop_runtime", "authored_source", False, True,
     False, False, "authored",
     "ship (modinfo/config sources are the controller)"),
    ("dependencies/CE-X10/", "workshop_runtime", "authored_source", False,
     True, False, False, "authored redirect + modinfo",
     "ship modinfo/redirect/dummy; DLL ships as pinned build artifact"),
    ("spike/X10_Probe_Test/", "private", "test_fixture", False, False,
     False, False, "authored disposable diagnostics",
     "NEVER ship (explicitly forbidden in release manifest)"),
    ("spike/validation-evidence/", "private", "validation_evidence_log",
     False, False, False, True, "live-game output dumps",
     "keep private; publish hashes + compact summary only"),
    ("spike/prod-test-output/", "private", "assembled_test_package", True,
     False, False, False, "assembled by spike/assemble-prod-test.ps1",
     "rebuild-only staging; never publish as-is (contains probe)"),
    ("spike/assemble-prod-test.ps1", "private", "test_packaging_tool", False,
     False, False, False, "authored",
     "replace with allowlist-based assemble-release in 7B"),
    ("spike/install-prod-test.ps1", "private", "test_packaging_tool", False,
     False, False, False, "authored",
     "test-only installer; release uses Workshop upload, not scripts"),
    ("spike/EXPECTED_DLL_SHA256.txt", "private", "build_pin", False, False,
     True, False, "pinned DLL hash (build gate)",
     "keep; public value duplicated in release manifest"),
    ("spike/assemble-live-test.ps1", "private", "test_packaging_tool",
     False, False, False, False, "authored",
     "test-only; superseded for release by 7B assembler"),
    ("spike/live-test-package/", "private", "superseded_test_package",
     False, False, False, False, "earlier live-test staging",
     "keep for history or remove in 7B cleanup"),
    ("spike/native-probe/", "private", "superseded_probe_heritage", False,
     False, False, False, "earlier probe iteration", "keep for history"),
    ("spike/probe-mod/", "private", "superseded_probe_heritage", False,
     False, False, False, "earlier probe iteration", "keep for history"),
    ("civ6x10/rules/governor_audit.yml", "private", "bulk_audit", False,
     False, True, True, "derived from official runtime DB (checked in)",
     "keep private; public surface gets hashes/summaries only"),
    ("civ6x10/rules/suzerain_audit.yml", "private", "bulk_audit", False,
     False, True, True, "derived from official runtime DB (checked in)",
     "keep private; public surface gets hashes/summaries only"),
    ("civ6x10/rules/semantic_backlog.yml", "private", "research_artifact",
     False, False, True, True,
     "derived from checked-in audits + authored resolutions",
     "keep private; publish resolution counts/decisions summary only"),
    ("civ6x10/rules/certified_overrides.yml", "corresponding_source",
     "authored_curated_rules", False, False, True, False,
     "authored curation with rationale per entry",
     "publish (required to reproduce certification)"),
    ("civ6x10/rules/transformations.yml", "corresponding_source",
     "authored_curated_rules", False, False, True, False, "authored",
     "publish"),
    ("civ6x10/rules/semantics.yml", "corresponding_source",
     "authored_curated_rules", False, False, True, False, "authored",
     "publish"),
    ("civ6x10/rules/mode_sem_floor.yml", "corresponding_source",
     "authored_curated_rules", False, False, True, False, "authored",
     "publish"),
    ("civ6x10/rules/overrides.yml", "corresponding_source",
     "authored_curated_rules", False, False, True, False, "authored",
     "publish"),
    ("civ6x10/rules/pantheon_audit.yml", "private", "bulk_audit", False,
     False, True, True, "derived from official runtime DB (checked in)",
     "keep private"),
    ("civ6x10/rules/wonder_audit.yml", "private", "bulk_audit", False,
     False, True, True, "derived from official runtime DB (checked in)",
     "keep private"),
    ("manifests/governors.yml", "corresponding_source_candidate",
     "generated_derived_manifest", True, False, True, False,
     "generated from audit + backlog (tracked exception)",
     "decide in 7B: publish generated file OR publish generator inputs only"),
    ("manifests/suzerain.yml", "corresponding_source_candidate",
     "generated_derived_manifest", True, False, True, False,
     "generated from audit + backlog (tracked exception)",
     "decide in 7B: publish generated file OR publish generator inputs only"),
    ("manifests/", "private", "generated_derived_manifest", True, False,
     True, False, "generated locally, gitignored",
     "local rebuild inputs; not published (recreated by user generator run)"),
    ("build/X10ProductionRegistry.inc", "corresponding_build_artifact",
     "generated_derived_registry", True, False, True, False,
     "generated from manifests via certified gate (gitignored)",
     "distribute exact file alongside DLL (hash-pinned), not in repo main"),
    ("build/", "private", "generated_derived_registry", True, False, False,
     False, "generated", "local build outputs; not published"),
    ("data/local/", "private", "official_db_inputs", False, False, True,
     True, "copies of official game database + coverage (gitignored)",
     "never publish; user regenerates from own install"),
    ("data/fixtures/", "corresponding_source", "test_fixture", False,
     False, False, False, "authored synthetic fixtures",
     "publish (CI-safe, no official data)"),
    ("data/", "private", "research_output", False, False, False, True,
     "mixed generated datasets", "keep private except fixtures"),
    ("civ6x10/", "corresponding_source", "authored_source", False, False,
     True, False, "authored generator/certification code",
     "publish (AGPL corresponding source core)"),
    ("tests/", "corresponding_source", "test_fixture", False, False, False,
     False, "authored tests + small regression constants",
     "publish; scrub bulk inventories if any found (see footprint)"),
    ("docs/", "corresponding_source", "authored_docs", False, False, False,
     False, "authored analysis (quotes official IDs/values in prose)",
     "publish; audit docs under review for bulk tables (see footprint)"),
    ("reports/", "private", "research_output", False, False, False, True,
     "generated decision reports (tracked)",
     "keep private pending bulk-content review"),
    ("research/", "private", "upstream_clones", False, False, False, True,
     "external clones (gitignored)", "never publish"),
    ("release/", "corresponding_source", "release_metadata", False, False,
     False, False, "authored release descriptor",
     "publish (single source of truth for 7B assembly)"),
    ("spike/toqui-probe/", "private", "research_output", False, False,
     False, True, "scratch probe helpers", "keep private"),
    ("LICENSE", "corresponding_source", "license_text", False, False, False,
     False, "project license", "publish; bundle into Workshop package (7B)"),
    ("THIRD_PARTY_NOTICES.md", "corresponding_source", "license_notice",
     False, False, False, False, "authored notices",
     "publish; bundle into Workshop package (7B); accuracy review in 7A"),
    ("README.md", "corresponding_source", "authored_docs", False, False,
     False, False, "authored", "publish"),
    (".github/", "corresponding_source", "ci_config", False, False, False,
     False, "authored", "publish"),
    ("pyproject.toml", "corresponding_source", "build_config", False,
     False, True, False, "authored", "publish"),
    # generic fallback: must stay last (first-prefix-match wins)
    ("spike/", "private", "spike_scratch", False, False, False, False,
     "mixed spike work area", "triage per file; never package wholesale"),
    (".gitattributes", "corresponding_source", "repo_meta", False, False,
     False, False, "authored", "publish"),
    (".gitignore", "corresponding_source", "repo_meta", False, False, False,
     False, "authored", "publish (public repo needs a release variant)"),
]

FIRAXIS_TOKEN = re.compile(r"\b[A-Z][A-Z0-9_]{5,}\b")


def tracked_files(root: Path) -> set[str]:
    out = subprocess.run(["git", "ls-files"], cwd=str(root),
                         capture_output=True, text=True)
    return set(out.stdout.split()) if out.returncode == 0 else set()


def measured_size(path: Path) -> int:
    """LF-normalized size for text files (CRLF/LF checkout independent)."""
    raw = path.read_bytes()
    try:
        return len(raw.decode("utf-8").replace("\r\n", "\n").encode("utf-8"))
    except UnicodeDecodeError:
        return len(raw)


def classify(rel: str) -> tuple:
    for prefix, *rest in RULES:
        if rel == prefix or rel.startswith(prefix):
            return tuple(rest)
    return ("private", "unclassified", False, False, False, False,
            "unknown", "triage in 7B")


def firaxis_tokens(path: Path) -> int | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None
    return len(FIRAXIS_TOKEN.findall(text))


FOOTPRINT_PATHS = [
    "civ6x10/rules/governor_audit.yml",
    "civ6x10/rules/suzerain_audit.yml",
    "civ6x10/rules/semantic_backlog.yml",
    "civ6x10/rules/pantheon_audit.yml",
    "civ6x10/rules/wonder_audit.yml",
    "manifests/governors.yml",
    "manifests/suzerain.yml",
    "controller/X10/Config/X10WonderBridge.sql",
    "build/X10ProductionRegistry.inc",
]


def build_release_surface(root: Path) -> dict:
    tracked = tracked_files(root)
    # candidate universe: tracked files + key untracked runtime inputs
    paths = sorted(tracked)
    for extra in ("build/X10ProductionRegistry.inc",
                  "manifests/traits.yml", "manifests/policies.yml",
                  "manifests/governments.yml", "manifests/pantheons.yml",
                  "manifests/wonders.yml"):
        if extra not in tracked and (root / extra).is_file():
            paths.append(extra)
    paths = sorted(set(paths))
    # the report never inventories itself (byte count would never converge)
    paths = [p for p in paths if p != "reports/release_surface.json"]
    files = []
    for rel in paths:
        p = root / rel
        if not p.is_file():
            continue
        if ".pytest_cache" in rel or "__pycache__" in rel:
            continue
        (surface, kind, generated, run_req, rebuild_req, audit_only,
         provenance, disposition) = classify(rel)
        files.append({
            "path": rel,
            "tracked": rel in tracked,
            "bytes": measured_size(p),
            "size_normalization": "LF",
            "surface": surface,
            "kind": kind,
            "generated": generated,
            "runtime_required": run_req,
            "rebuild_required": rebuild_req,
            "audit_only": audit_only,
            "provenance": provenance,
            "disposition": disposition,
        })
    footprint = {}
    for rel in FOOTPRINT_PATHS:
        p = root / rel
        if not p.is_file():
            continue
        try:
            lines = sum(1 for _ in open(p, encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            lines = None
        footprint[rel] = {
            "bytes": measured_size(p),
            "bytes_normalization": "LF",
            "lines": lines,
            "uppercase_identifier_tokens": firaxis_tokens(p),
            "tracked": rel in tracked,
        }
    # data/local inventory: sizes only, never contents
    local = root / "data" / "local"
    local_files = []
    if local.is_dir():
        for f in sorted(local.iterdir()):
            if f.is_file():
                local_files.append({"name": f.name,
                                    "bytes": f.stat().st_size})
    surfaces = {}
    for f in files:
        surfaces.setdefault(f["surface"], {"files": 0, "bytes": 0})
        surfaces[f["surface"]]["files"] += 1
        surfaces[f["surface"]]["bytes"] += f["bytes"]
    return {
        "generated_by": "civ6x10.release_surface (Phase 7A audit/design)",
        "freeze": {
            "production_commit": "2cf953e",
            "ce_commit": "1ce3188",
            "dll_sha256": "e33d84b83d752a9eb7b52b4740291c97183af4d079d1ca82b8bd9d92b5c4d619",
            "registry": {"entries": 1010, "unique": 1006, "shared": 25,
                         "unconditional": 788, "count_like": 222},
        },
        "files": files,
        "surface_summary": surfaces,
        "firaxis_footprint": footprint,
        "data_local_sizes_only": local_files,
        "open_policy_questions": [
            "tracked manifests: publish generated files or generator-inputs-only?",
            "audit docs with bulk tables: publish as analysis or summarize?",
            "reports/*.md tracked decision outputs: publish or keep private?",
            "validation evidence: hashes + compact summary vs raw logs?",
        ],
    }


def write_report(root: Path) -> Path:
    out = root / "reports" / "release_surface.json"
    out.write_text(json.dumps(build_release_surface(root), indent=1),
                   encoding="utf-8")
    return out
