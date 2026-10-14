# Publication checklist (hard gates; 7B.2b needs explicit approval per stage)

## Before GitHub creation
- [ ] clean export generated from current head
- [ ] export isolated pytest: 0 failures (skips documented)
- [ ] export file-list hash recorded
- [ ] no forbidden artifacts / `.git` / absolute paths in export

## After GitHub creation
- [ ] public URL opens anonymously
- [ ] remote tree matches local export (PROVENANCE.md file-list hash)
- [ ] LICENSE visible
- [ ] BUILDING visible
- [ ] source provenance visible

## Before Workshop upload
- [ ] `release/verified-sources.yml` completed from the example and URLs verified
- [ ] publish-ready assembler rerun (`-PublishReady`, no RC flag): passes
- [ ] no `PLANNED-PLACEHOLDER` markers anywhere staged
- [ ] DLL hash exact (`ced8f017...b744`, Phase-8B.1 coverage build)
- [ ] final CHECKSUMS.sha256 generated
- [ ] no probe content
- [ ] engine/controller Mod IDs correct
- [ ] `CompatibleVersions` present in both modinfos
- [ ] setup localization present (`Config/X10Text.sql` in controller Files)
- [ ] both modinfos Single Player Yes / Multiplayer No
- [ ] preview images present (`release/preview-engine.png`,
      `release/preview-controller.png`; PNG/JPG, <1 MB, ≥512x512 px (1024x1024 square recommended))

## After unlisted engine upload
- [ ] subscribe/install test passes
- [ ] numeric Workshop item ID recorded in publication state
- [ ] source link works

## After unlisted controller upload
- [ ] engine configured as Steam Required Item
- [ ] subscribing to the controller pulls the engine automatically
- [ ] exactly the two staged folders install (no duplicates/old copies)
- [ ] launch smoke test + save/reload: lifecycle `writes=1682
  transform_refused=0 official_mismatch=0 post_add_match=1682
  post_add_mismatch=0 post_add_unreadable=0 skipped_other=0
  repeat_idle=630` at preset ×10 in the standard Secret-Societies-only
  setup, reload identical
  (Custom 7.3 = 1204/1108 retained as a secondary spot check, not primary;
  all-modes = 1851/1353 variants; the old RC2 1010/0 smoke with DLL
  `3b6dc3d2...ab14` stays a historical record only, not the expectation
  for this tree)

## Before making anything public
- [ ] EXPLICIT HUMAN APPROVAL (never automatic)
