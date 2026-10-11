# X10 release source (v1.0.0-rc1 clean snapshot)

Configurable Civilization VI semantic multiplier: generator and
certification source, curated rules, controller/engine text sources,
and the release tooling that stages the two Workshop items
(X10 controller + required X10 CE Engine dependency).

## Contents

- `civ6x10/` — generator, certification gate, transforms, CLI
  (audit engines included as source; bulk audit inputs are NOT included)
- `civ6x10/rules/` — curated rules only (no audit YAMLs, no backlog)
- `controller/`, `dependencies/` — Workshop text sources (modinfo, config)
- `data/fixtures/` — synthetic CI fixtures (no official game data)
- `tests/` — deliberately reviewed subset: every included test passes or
  skips cleanly with only this snapshot present
- `release/` — release manifest, VALIDATION, BUILDING, CHANGELOG,
  Workshop drafts, auxiliary sources, assembler + export tooling
- `LICENSE`, `THIRD_PARTY_NOTICES.md`, `PROVENANCE.md`

## Test

```powershell
python -m pytest -q
```

Tests needing private development inputs (official DB copies, audit
YAMLs, built registry, CE fork checkout) are deliberately omitted from
this snapshot — see PROVENANCE.md — never weakened to pass. Included
tests that cannot run here skip with a documented reason. Expected:
0 failures; skips require the private workspace.

## Reproduce the release

`release/BUILDING.md` documents the exact engine binary build and the
controller/assembler path. `release/VALIDATION.md` is the compact public
validation summary. `release/release-manifest.yml` pins every staged file.
