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
- [ ] DLL hash exact (`e33d84b8…d619`)
- [ ] final CHECKSUMS.sha256 generated
- [ ] no probe content
- [ ] engine/controller Mod IDs correct
- [ ] `CompatibleVersions` present in both modinfos
- [ ] preview images present (`release/preview-engine.png`,
      `release/preview-controller.png`; PNG/JPG, <1 MB, ≥512x512)

## After unlisted engine upload
- [ ] subscribe/install test passes
- [ ] numeric Workshop item ID recorded in publication state
- [ ] source link works

## After unlisted controller upload
- [ ] engine configured as Steam Required Item
- [ ] subscribing to the controller pulls the engine automatically
- [ ] exactly the two staged folders install (no duplicates/old copies)
- [ ] launch smoke test + save/reload: lifecycle 801/209, reload identical

## Before making anything public
- [ ] EXPLICIT HUMAN APPROVAL (never automatic)
