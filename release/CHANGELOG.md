# Changelog

## Phase 8B Playtest-1 closure (under pre-publication gameplay validation, not published)

- Registry 1010 → 2481 entries (2475 unique, 26 shared; 1333
  unconditional + 1148 count-like): wonder one-time grants, Jebel
  per-turn iron, Petra-style vectors, bonus policy slots (REPEAT +
  Reserve fillers), generic envoy tiers, promotions & abilities,
  dedications, game modes, religion beliefs, Great People, projects.
- Non-destructive wonder bridge (DELTA): direct tables keep official
  values (vanilla UI truthful); helpers contribute `official*(k-1)`.
- New native kinds VECTOR/DELTA/REPEAT; 13-module owner mask (new CE
  build `e0486aee...0ea06c`, CE `29e8b7f`).
- Setup grows to thirteen checkboxes; City-State module broadened to
  Envoy + Suzerain bonuses. No Workshop upload yet.

## v1.0.0-rc2 (release candidate, not published)

- Native preset/custom/bool config readers; setup migrates to Advanced
  Setup (preset dropdown, custom value, checkbox modules) with en_US
  localization. New DLL `3b6dc3d2…ab14`.
- Same 1010-entry gameplay registry, transforms, and ownership; no
  semantic change vs the validated `2cf953e` state.
- Controller/engine display names, teasers, and single/multiplayer
  metadata polished; `CompatibleVersions=2.0` retained.
- Public product identity: **Overpowered Bonuses** + **Overpowered
  Bonuses CE Engine**; setup labels are product-name neutral
  (`Bonus Multiplier`, `Affects: ...`). `X10` remains the
  internal/historical namespace only (config keys, log/registry
  filenames, source symbols).
- Custom Multiplier label/tooltip FINAL for v1.0:
  `Custom Multiplier (0 to 100)`; blank/0/invalid leave bonuses
  unchanged (measured fail-closed). No frontend validation override.
- Planned public source repo: `Dacilla/civ6-overpowered-bonuses`.
- v1.1 research roadmap: normalized Phase-8A/8A.1 support frontier
  (Religion → Promotions & Abilities → Great People → Monopolies →
  later families). Internal roadmap only; not promised in Workshop
  copy.

## v1.0.0-rc1 (release candidate, not published)

- Validated gameplay: 1010-entry registry (1006 definitions, 25 shared;
  788 unconditional + 222 count-like), seven modules, DLL `e33d84b8…d619`.
- Live validation: Run A 801 writes / 209 refusals (load + reload);
  Run B 698 / 174 / 138 with exact 70 + 68 ownership skips.
- Packaging: two Workshop items (X10 controller + X10 CE Engine
  dependency), auxiliary README/LICENSE/notices/source files, CHECKSUMS.
- No gameplay change vs. the validated `2cf953e` state; metadata only.

## v1.0.0 (planned, after RC approval + smoke run)

- First public release. Modinfo integer stays 1.
