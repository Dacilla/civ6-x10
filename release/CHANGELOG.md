# Changelog

## Phase 8B.3 regional wonder semantics closure (under pre-publication gameplay validation, not published)

- Jebel Faith (+4, range 6) and Maracana Culture (+6, civilization-wide)
  helpers re-homed to the regional city-yield carrier (Jebel via a
  generated X10 requirement set mirroring COLOSSEUM_REQUIREMENTS;
  Maracana ungated). Registry byte-identical: no CE rebuild.
- Closed-world guard: every regional direct Wonder yield must carry a
  faithful regional helper or a documented exception (none).
- Regional Entertainment investigated and deferred: no official
  player-cities entertainment carrier exists; multi-city behavior
  unprovable without a game boot. Aura stays vanilla.
- Checklist: new J2 + MC1 regional checks; C1 retained.

## Phase 8B.2 final pre-Playtest-2 correction (under pre-publication gameplay validation, not published)

- Colosseum culture helper re-homed to the official regional graph
  (player-cities city-yield carrier + COLOSSEUM_REQUIREMENTS); host
  +20 AND in-range cities +20 at x10, direct +2 preserved for UI.
  Registry untouched (no CE rebuild). Maracana/Jebel helpers stay
  host-only (no official gate; neighbors keep vanilla).
- Reserve picker UX gated by new Playtest-2 step P0B (not an accepted
  cost); installer defaults repaired (1.0.0-8b + ced8); Modes check
  renamed MD1; R3 covers Great People + City Projects OFF isolation.

## Phase 8B.1 pre-Playtest-2 correction (under pre-publication gameplay validation, not published)

- Policy-slot fillers re-typed per slot (MILITARY 200 / DIPLOMATIC 100
  / ECONOMIC 200 / WILDCARD 200; the 8B wildcard-only design could not
  fill typed bonus slots); filler LOC key fixed; slotting stays manual.
- Secret Society bonuses re-homed to Game Modes (22 rows, bit 32→512);
  Governors setup label simplified. Registry totals unchanged (2481).
- Playtest-2 expectations corrected from the registry: ×10 writes 1851
  (+630 idle, refused 0); Custom 7.3 writes 1353 / refused 1128; Petra
  at 7.3 is 14.6,14.6,7.3.
- BRS/EPC preview claim retracted: previews read gameplay SQLite and
  show vanilla values while gameplay scales (P1 known incompatibility,
  preview-only); no shim shipped.
- Colosseum DELTA kept with corrected scope evidence (culture
  host-only; loyalty regional automatic; entertainment aura vanilla).
- New CE build `ced8f017...b744` (CE `1e89e1b`); all pins re-pinned.
  Prior RC2 history (DLL `3b6dc3d2…ab14`, 1010 set) preserved as-is.

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
