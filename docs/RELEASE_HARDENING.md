# Release Hardening (Phase 7A — audit/design only, no release mutation)

Freeze point: **civ6-x10 `2cf953e` + CE `1ce3188` + DLL
`e33d84b83d752a9eb7b52b4740291c97183af4d079d1ca82b8bd9d92b5c4d619**
(1010-entry registry, LIVE_VALIDATED, tag `phase6b-1010-live-validated`).
Machine inventory: `reports/release_surface.json`
(`python -m civ6x10 audit-release-surface`). Text-file hashes/sizes are
LF-normalized (CRLF/LF-checkout independent). Nothing in this document
changes runtime behavior.

## 1. Release-surface inventory summary

155 files classified, 0 unclassified (sizes LF-normalized):

| surface | files | bytes | content |
|---|---|---:|---|
| `workshop_runtime` | 7 | 439,988 | the 7 text payload files (DLL excluded — binary, tracked separately) |
| `corresponding_source` | 81 | ~1.01 MB | generator/certification code, curated rules, tests, docs, CI, license |
| `corresponding_source_candidate` | 2 | 83,774 | tracked Governor/Suzerain manifests (decision open, §6) |
| `corresponding_build_artifact` | 1 | 71,543 | generated `.inc` (distributed alongside DLL, not in repo main) |
| `private` | 64 | ~6.58 MB | audits, backlog, evidence logs, local DB copies, spike work |

### A. Workshop runtime payload (exact, from the validated assembly)

| file | bytes | sha256 (prefix) |
|---|---|---|
| `CE-X10/CE-X10.modinfo` | 1,033 | `d6b580fe…` |
| `CE-X10/Config/EngineRedirect.sql` | 388 | `3bb8544d…` |
| `CE-X10/Config/Dummy.sql` | 83 | `8a48ba74…` |
| `CE-X10/Binaries/Win64/GameCore_XP2_CE_FinalRelease.dll` | 2,769,920 | `e33d84b8…` (pinned) |
| `X10/X10.modinfo` | 1,370 | `62d5e06a…` |
| `X10/Config/X10Config.sql` | 2,767 | `1987a11f…` |
| `X10/Config/Dummy.sql` | 149 | `ff629829…` |
| `X10/Config/X10WonderBridge.sql` | 439,096 | `81c3dda2…` (LF-normalized; Windows CRLF packaging bytes `d0faabfa…`) |

Full hashes in `release/release-manifest.yml` (LF-normalized; single
source of truth for 7B assembly — the assembler normalizes before
comparing; Windows CRLF packaging bytes of the bridge hash `d0faabfa…`). The production probe (`X10_Probe_Test`) is explicitly
forbidden in release and is absent from this list by construction.

### B. Public corresponding-source surface (proposed)

`civ6x10/` generator + certification + CLI code, curated rules
(`certified_overrides.yml`, `transformations.yml`, `semantics.yml`,
`mode_sem_floor.yml`, `overrides.yml`), `controller/` + `dependencies/`
text sources, `tests/` (bounded regression constants only — largest
offender `test_suzerain.py` holds 77 distinct quoted IDs for the 47-slice
+ side-path expectations, accepted as necessary), `docs/` prose (audit
docs quote official IDs in analysis tables; kept as analysis, not bulk
dumps), `LICENSE`, `THIRD_PARTY_NOTICES.md` (after 7A accuracy fix),
`release/release-manifest.yml`, CI config, `pyproject.toml`.

### C. Private developer/audit workspace (stays internal)

`data/local/` (13.6 MB official DB copies + coverage, gitignored),
`build/` outputs, all five audit YAMLs, the backlog artifact, local-only
manifests (traits/policies/governments/pantheons/wonders), `reports/`
decision outputs, `spike/` scratch + superseded probe heritage +
test-only scripts, `research/` clones, all validation evidence logs.

## 2. Firaxis-derived footprint (measured, nothing deleted in 7A)

| artifact | bytes (LF) | lines | UPPER_ID tokens | tracked |
|---|---|---:|---:|---|
| `suzerain_audit.yml` | 794,426 | 21,101 | 10,278 | yes |
| `governor_audit.yml` | 279,474 | 7,501 | 3,443 | yes |
| `semantic_backlog.yml` | 237,734 | 5,215 | 1,858 | yes |
| `wonder_audit.yml` | 69,323 | 1,733 | 964 | yes |
| `pantheon_audit.yml` | 11,815 | 281 | 160 | yes |
| `manifests/governors.yml` | 39,719 | 1,102 | 436 | yes (exception) |
| `manifests/suzerain.yml` | 44,055 | 1,178 | 540 | yes (exception) |
| `X10WonderBridge.sql` | 434,198 | 4,898 | 10,916 | yes (**ships**) |
| `X10ProductionRegistry.inc` | 71,543 | 1,029 | 1,016 | no (build artifact) |
| evidence logs (19 files) | ~4.4 MB | — | bulk dumps | yes |

("tokens" = regex `[A-Z][A-Z0-9_]{5,}`; over-counts prose constants but
bounds the footprint honestly.)

### Engineering policy (replaces the vague "no Firaxis data" prose)

The old policy is internally inconsistent: the mod cannot function without
official IDs/values, and `X10WonderBridge.sql` must ship. New policy:

- **Allowed public/runtime-derived constants** (minimal, functional):
  target ModifierIds, guard/expected values in bridge SQL, the exact
  generated registry source shipped alongside the DLL (hash-pinned release
  asset, not repo main), the 77-ID-scale regression constants in tests.
- **Private research/audit material** (bulk, not needed to run/build):
  all five audit YAMLs, the backlog artifact, raw DB-derived reports,
  `data/local/`, local-only manifests. Never in the public surface.
- **Public summarized evidence**: counts, hashes, semantic decisions,
  compact validation summaries (this document + evidence README section),
  never megabytes of raw logs.
- **Acknowledged boundary**: the distributed binary necessarily encodes
  registry behavior (1010 transformed definitions). "Zero derived game
  data anywhere" is not a realistic engineering boundary; the policy
  controls *bulk redistributable representations*, not functional constants.

## 3. Git-history hygiene

Making the dev repo public unchanged would expose, currently AND
historically: all audit YAMLs at every revision, all 19 evidence logs,
early `mods/X10-*/` split-mod prototypes (deleted since), and old
`spike/prod-test-output/` copies (deleted since). Largest historical blobs
are the audits/logs/bridge above; no binaries, credentials, or private
data beyond Firaxis-derived material (repo total ~12.8 MB blobs).

- **A. Publish unchanged**: simplest, but permanently publishes bulk audit
  material + full decision trail. Rejected.
- **B. Rewrite/sanitize history**: `filter-repo` surgery on a 861-object
  repo is feasible but invalidates all existing tags/hashes
  (`phase6b-1010-live-validated` etc.), risks subtle content changes, and
  must be re-audited. Rejected as disproportionate.
- **C. (Recommended) Clean `civ6-x10-release-source` snapshot**: new repo,
  single squashed history (or fresh root + CHANGELOG), containing ONLY the
  §1B allowlist. Dev repo stays private with evidence intact. Effort: one
  allowlist copy + README. Preserves tag integrity of the private repo.

Do NOT create/push any public repo in 7A.

## 4. AGPL/upstream release-engineering checklist (no legal advice)

Fork base: `Wild-W/CivilizationVI_CommunityExtension`, AGPL-3.0
(`LICENSE.txt` at fork root, upstream). For the binary release provide:

- [ ] exact fork source at `1ce3188` (branch `x10-lifecycle-log`) —
  available, unpushed deltas: none (pushed to `x10` remote)
- [ ] upstream attribution + AGPL-3.0 text **inside the Workshop package**
      — MISSING (verified: package holds 0 license/notice/source-link
      files; modinfo carries no version metadata beyond `version="1"`)
- [ ] build instructions/toolchain (MSBuild 18, Release x64, OutDir
      convention) — TO WRITE in 7B
- [ ] exact registry source for the DLL (`X10ProductionRegistry.inc` at
      `b60a280`, hash-pinned) — available
- [ ] DLL hash `e33d84b8…d619` — pinned
- [ ] source URL visible to users — TODO (placeholder in manifest)

`THIRD_PARTY_NOTICES.md` accuracy: the "contains no third-party code"
claim is true of the *source repo* (no vendored CE code; fork external)
but would be misleading *inside a runtime bundle* whose DLL is built from
AGPL fork source. 7B must add a release-context section (or a separate
package notice) rather than editing the dev-repo claim.

## 5. Workshop packaging topology

Goal: one configurable Workshop item. Validated local package: two mods
(`CE-X10` engine + `X10` controller) + disposable probe (test only).

- **A. Two Workshop items** (engine + controller with declared
  `<Dependencies>` on the engine Mod ID): matches the validated package
  1:1, uses the proven CE-ecosystem pattern (cf. CE Workshop ID
  3277976174 + dependents), zero revalidation, independent engine
  versioning. Friction: two subscriptions; skew risk mitigated by the
  declared dependency + matching release versions.
- **B. One item containing two mod packages**: the Workshop uploader takes
  a SINGLE `.modinfo`; nested/second-`.modinfo` topologies are unproven
  and community reports show uploader pickiness. Do NOT assume support.
  Rejected unless proven by experiment.
- **C. One merged mod** (redirect + DLL + config + bridge in one
  `.modinfo`/Mod ID): would change the GameCore `PackageId`, mod identity
  (`AffectsSavedGames=1` already), and action ordering; developer split
  can remain while release merges, but the merged artifact is a NEW
  runtime identity requiring full live revalidation. Deferred option.

**Recommendation: A now** (no new validation), C only as a deliberate
later migration with revalidation. Do NOT implement in 7A.

## 6. Current test packaging audit (`spike/assemble-prod-test.ps1`)

Recorded defects (test-packager, not release-packager): hard-coded local
DLL path `C:\Users\alex\Desktop\Code\ce-native-build\...`; emits three
folders **including `X10_Probe_Test`**; no release README; no
license/notice bundle; no source reference; no manifest/checksum file; no
archive/staging artifact; copies whole source dirs (`controller\X10`,
`dependencies\CE-X10`) instead of an allowlist (today equivalent to the
allowlist, but unproven mechanically).

7B `spike/assemble-release.ps1` (proposed, not implemented): parameterized
`(-OutDir, -Manifest release/release-manifest.yml)`, copies ONLY
allowlisted paths, verifies each sha256, emits `CHECKSUMS.txt` +
`README-RELEASE.txt` + `LICENSE`/`THIRD_PARTY` bundle + source-URL file,
refuses if any extra file appears, never copies arbitrary dev-dir content.

## 7. Release manifest + versioning + metadata

Schema: `release/release-manifest.yml` (checked in 7A as proposal with
frozen values; URLs TODO). Single source of truth for 7B assembly; extend
with `CHECKSUMS.txt` generation.

Versioning: keep stable Mod IDs (`55d7b934…`, `397f2070…`); modinfo
integer increments monotonically per Workshop update (1→2→3…);
human-facing tags `v1.0.0`, `v1.0.1`… map to integers in the manifest.
First public release: modinfo `version=2` (1 was the private test series),
tag `v1.0.0`.

Workshop page checklist (structure only, no artwork): display name,
one-line teaser, full description (multiplier semantics in plain language:
arbitrary k, 0=Off; per-module toggles; integral/refusal rule in plain
language — "whole-number bonuses wait for exact values instead of
rounding"), Windows-x64-only + Gathering Storm requirement, Secret
Societies-note (mode-gated definitions populate only with the mode),
known exclusions (scaling factors, healing caps, improvement intrinsics),
save-game note (`AffectsSavedGames=1`), stock/upstream-CE incompatibility
warning (disable Workshop CE), troubleshooting + log location
(`%TEMP%\X10Lifecycle.log`), source/license links, changelog.

## 8. Reproducibility audit (fresh clone containing ONLY the §1B surface)

- **Fully self-contained rebuild**: impossible today — traits/policies/
  governments/pantheons/wonders manifests are gitignored locals, audits
  are private, and the registry generator needs both. Missing: all five
  local manifests + audit YAMLs.
- **Rebuild requiring the user's own Civ VI install**: feasible —
  generator + curated rules ship; user recreates manifests/registry/bridge
  from their install. Missing: a documented `bootstrap-from-install`
  command + the local-inventory step (7B work).
- **Hash-verifiable corresponding build (RECOMMENDED)**: ship the exact
  generated `.inc` (+ bridge SQL, both hash-pinned) as release assets
  alongside the DLL; public repo keeps generator + curated rules so the
  transformation is auditable and the bytes are verifiable without
  redistributing bulk audit DBs. Tradeoff accepted: one 72 KB derived file
  per release vs. megabyte-scale audit republication.

No legal conclusion drawn; recommendation is engineering-only.

## 9. Validation-evidence policy

Public release source does NOT need raw logs (4.4 MB tracked). Public
evidence = pinned hashes of the archived logs + the compact per-run
summaries (evidence README §6B/6C sections) + live-validation tag/commit.
Full logs stay in the private workspace. Nothing deleted in 7A.

## 10. Phase-7B implementation plan (for review)

1. Fix `THIRD_PARTY_NOTICES.md` release-context section.
2. Write `spike/assemble-release.ps1` (parameterized, allowlist from
   manifest, CHECKSUMS + README + license bundle, probe refusal test).
3. Decide tracked-manifest disposition (publish generated vs
   inputs-only) with reproducibility consequence (§8).
4. Create private `civ6-x10-release-source` allowlist export; dry-run the
   §8 recommended path (verify DLL-byte reproducibility or document the
   hash-verifiable boundary).
5. Workshop metadata text (checklist §7) + preview image (outside 7A
   scope: artwork only).
6. Upload as TWO items (engine + controller) to Workshop (unlisted first),
   verify subscription install + one live smoke run, then visibility
   decision — separate explicit approval, never implicit.
