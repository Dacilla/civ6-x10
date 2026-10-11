"""Phase 7B.1: allowlist-based clean public-source export (no .git).

Copies ONLY reviewed paths into <out>/civ6-x10-release-source/.
Writes PROVENANCE.md (no absolute paths, usernames, or private data).
Usage: python release/export_public_source.py --out <dir> [--version 1.0.0-rc1]
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Exact repo-relative files copied (no globs over dev trees).
FILES = [
    "pyproject.toml",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "release/release-manifest.yml",
    "release/VALIDATION.md",
    "release/BUILDING.md",
    "release/CHANGELOG.md",
    "release/workshop-engine.md",
    "release/workshop-controller.md",
    "release/assemble-release.ps1",
    "release/export_public_source.py",
    ".github/workflows/test.yml",
]
TREES = [
    # (source dir, destination dir, suffix filter or None)
    ("civ6x10", "civ6x10", ".py"),
    ("controller", "controller", None),
    ("dependencies", "dependencies", None),
    ("data/fixtures", "data/fixtures", None),
]
# Curated rule inputs only (audits + backlog stay private).
RULE_FILES = [
    "certified_overrides.yml",
    "transformations.yml",
    "semantics.yml",
    "mode_sem_floor.yml",
    "overrides.yml",
]
# Deliberately reviewed test subset (see export notes in PROVENANCE.md).
# Determined empirically: every listed file passes-or-skips with only the
# export present; files needing private inputs are omitted (never weakened).
TESTS = [
    "tests/test_building_yield_integral.py",
    "tests/test_determinism.py",
    "tests/test_dynamic_spike.py",
    "tests/test_governors.py",
    "tests/test_governors_production.py",
    "tests/test_phase6b_production.py",
    "tests/test_production.py",
    "tests/test_semantic_backlog.py",
    "tests/test_semantics.py",
    "tests/test_strong_family_override.py",
    "tests/test_suzerain_production.py",
    "tests/test_transforms.py",
    "tests/test_validation.py",
]

# Omitted (require private workspace; documented in PROVENANCE.md):
#   test_bridge, test_live_package, test_pantheons, test_probe_packaging,
#   test_release_freeze, test_scope_rules, test_suzerain, test_wonders.

FORBIDDEN_SUBSTRINGS = (
    "audits are unavailable",
)


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--version", default="1.0.0-rc1")
    args = ap.parse_args()
    out = Path(args.out)
    if str(out.resolve()) == str(REPO.resolve()) or REPO in out.resolve().parents:
        print("refusing: --out must be outside the private repo", file=sys.stderr)
        return 2
    dest = out / "civ6-x10-release-source"
    if dest.exists():
        print(f"refusing: output exists: {dest}", file=sys.stderr)
        return 2

    copied: list[Path] = []

    def put(src: Path, rel: str):
        if not src.is_file():
            print(f"missing export input: {src}", file=sys.stderr)
            raise SystemExit(1)
        d = dest / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        d.write_bytes(data)
        copied.append(Path(rel))

    for rel in FILES:
        put(REPO / rel, rel)
    for fname in RULE_FILES:
        put(REPO / "civ6x10" / "rules" / fname,
            f"civ6x10/rules/{fname}")
    for src_dir, dst_dir, suffix in TREES:
        for f in sorted((REPO / src_dir).rglob("*")):
            if not f.is_file() or "__pycache__" in f.parts:
                continue
            if suffix and f.suffix != suffix:
                continue
            put(f, str(Path(dst_dir) / f.relative_to(REPO / src_dir)))
    # test support trees + package marker
    for rel in ["tests/__init__.py"]:
        put(REPO / rel, rel)
    for tree in ("tests/fixtures", "tests/golden"):
        for f in sorted((REPO / tree).rglob("*")):
            if f.is_file():
                put(f, str(f.relative_to(REPO)))
    for rel in TESTS:
        put(REPO / rel, rel)
    # public README (not the private dev README)
    put(REPO / "release" / "README-public.md", "README.md")

    # PROVENANCE.md: no absolute paths, usernames, or private locations
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                          capture_output=True, text=True).stdout.strip()
    file_hash = hashlib.sha256("\n".join(
        f"{r.as_posix()}:{sha_file(dest / r)}" for r in sorted(copied)
    ).encode()).hexdigest()
    prov = (
        "# Public-source provenance (X10 v1.0.0-rc1)\n\n"
        f"- private development source head: `{head}`\n"
        "- validated gameplay commit: `2cf953e`\n"
        "- validation tag: `phase6b-1010-live-validated`\n"
        "- CE fork commit: `1ce3188`\n"
        f"- release candidate version: `{args.version}`\n"
        "- export command: `python release/export_public_source.py --out <dir>`\n"
        f"- exported files: {len(copied)}\n"
        f"- export file-list hash: `{file_hash}`\n"
        "- included tests: deliberately reviewed subset; tests needing\n"
        "  private audit/DB inputs are omitted (never weakened to pass).\n"
        "- omitted test files (need official DB copies, audit YAMLs, built\n"
        "  registry, spike tree, or CE fork checkout): test_bridge,\n"
        "  test_live_package, test_pantheons, test_probe_packaging,\n"
        "  test_release_freeze, test_scope_rules, test_suzerain,\n"
        "  test_wonders.\n"
    )
    (dest / "PROVENANCE.md").write_text(prov, encoding="utf-8")
    print(f"exported {len(copied)} files + PROVENANCE.md -> {dest}")
    print(f"file-list hash: {file_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
