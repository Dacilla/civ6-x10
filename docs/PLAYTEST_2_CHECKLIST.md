# Playtest-2 checklist (human — game runs + log capture)

Build installed: `X10` + `CE-X10` in Civ VI Mods (8B.1 tree), DLL
recorded in `spike/EXPECTED_DLL_SHA256.txt`. Disable upstream Community
Extension and any other GameCore replacement. Standard setup for every
run unless noted: Gathering Storm, ROME (Trajan), Small map, 2 AI,
Secret Societies ON (so mode payloads are present).

Logs: after each run, copy `%TEMP%\X10Lifecycle.log` to
`spike/validation-evidence/` BEFORE the next run (the file appends).
The run is green only if the EXIT line matches AND the listed
witnesses show `MATCH`.

EXIT line fields:
`writes transform_refused official_mismatch post_add_match
post_add_mismatch post_add_unreadable skipped_other repeat_idle`.
`repeat_idle` rows are by-design inert REPEAT copies (copy index above
integral k): neither writes nor failures. `post_add_match` always
equals `writes` (per-definition witness buffer never truncates: max 2
X10 arguments per definition).

## P0 boot smoke (SLOT_NONE tolerance gate — run FIRST)

- [ ] **P0** preset ×10 Classic, ALL 13 modules ON: start a game, open
  the government screen, end turn once. Game must not crash, hang, or
  log errors about `SLOT_NONE`; EXIT line must be the R1 line below.
  (The 693 inert slot copies carry `GovernmentSlotType=SLOT_NONE`,
  which has no official `GovernmentSlots` row. If the engine chokes
  here, STOP: fall back to a tested static cap per docs/PHASE_8B.md
  §6-C2 instead of proceeding.)

## P0B Reserve picker UX gate (run BEFORE the full campaign)

- [ ] **P0B**: reach/start after Code of Laws with the normal intended
  UI stack including Extended Policy Cards. Open the
  Government/Policy screen and verify all four filler families
  (Military/Diplomatic/Economic/Wildcard Reserve policies) are legal
  in their slots. Measure whether opening, scrolling, selecting, and
  confirming remains responsive and reasonably usable with 700
  Reserve cards in the picker. Capture a screenshot + Lua log if
  there are errors. If the 700-card picker is materially unusable,
  STOP and reopen the policy-slot architecture — the filler count is
  NOT an accepted cost until P0B passes.

## Matrix runs (native lifecycle)

- [ ] **R1** preset ×10 Classic, ALL 13 modules ON (load + save/reload):
  expect `writes=1851 transform_refused=0 official_mismatch=0
  post_add_match=1851 post_add_mismatch=0 post_add_unreadable=0
  skipped_other=0 repeat_idle=630`, sessions identical.
  (1851 = 1788 non-REPEAT + 63 active REPEAT copies; 630 idle by
  design. `writes=2481` is impossible at ×10 — only ×100 writes all.)
- [ ] **R2** Custom 7.3, all ON: expect `writes=1353
  transform_refused=1128 official_mismatch=0 post_add_mismatch=0
  post_add_unreadable=0 skipped_other=0` (repeat_idle is 0 at
  fractional k: all 693 REPEAT rows refuse via transform_refused).
  1353 = 1333 unconditional + 20 exact (19 ADDITIVE + Panama DELTA
  63). Spot witnesses: Panama delta 63 MATCH; Stonehenge delta
  refused; Jebel iron refused (stays 6); Petra vector
  `14.6,14.6,7.3` MATCH (NOT `20,20,10` — that is the ×10 value).
- [ ] **R3** new modules OFF one at a time (promotions, dedications,
  modes, religion, greatpeople, projects, city-state, wonders): each
  run must show exactly that module's `owners=` skip lines and zero
  mutations of its rows.
  Modes OFF additionally skips all 22 Secret Society rows (they are
  modes-owned since 8B.1); Governors OFF skips only the 48 base
  governor rows.
- [ ] **R4** preset Off: disarmed, zero mutations.
- [ ] **R5** invalid Custom (`abc`, `-1`, `101`, blank): disarmed with
  explicit reasons, zero transforms.
- [ ] **R6** save/reload on R1 config: sessions identical.

## Focused gameplay checks

- [ ] **P1 BRS/EPC — KNOWN INCOMPATIBLE (preview only, do not expect
  PASS)**: with Better Report Screen + Extended Policy Cards
  enabled, God King card tooltip/BRS Policy page is EXPECTED to read
  vanilla +1 Faith/+1 Gold at ×10 (they read gameplay SQLite, which
  CE never rewrites; see docs/PHASE_8B.md §6-C1). Instead verify
  GAMEPLAY: God King actually yields +10/+10 in-game. Record the
  preview values as the known-divergence evidence.
- [ ] **C1 Colosseum**: build queue shows +2 Culture (not +0); host
  City Center gets +20 total Culture at ×10; every eligible City
  Center within 6 tiles gets +20 total Culture; a city outside range
  gets none. A nearby city receiving only +2 Culture is FAILURE, not
  expected behavior (that was the 8B.1 host-only helper bug).
  Loyalty stays ×10 via its existing regional modifier; the +2
  Entertainment aura within 6 tiles stays VANILLA (never bridged,
  not scaled).
- [ ] **J1 Jebel Barkal**: +60 Iron/turn at ×10; stays +6 at 7.3.
- [ ] **J2 Jebel regional**: ×10 host/in-range city +40 Faith total; another eligible city within 6 tiles +40 Faith; outside 6 tiles no Jebel Faith.
- [ ] **MC1 Maracana regional**: ×10 every city +60 Culture total.
- [ ] **P3 Petra**: desert tiles +20 Food/+20 Gold/+10 Production
  at ×10 (at 7.3: +14.6/+14.6/+7.3).
- [ ] **P4 Pyramids**: 10 Builders at ×10.
- [ ] **E1 Eiffel**: +20 Appeal at ×10; unchanged at 7.3.
- [ ] **D1 Discipline**: ~+29 vs Barbarians (NOT +50).
- [ ] **M1 Monument to the Gods**: +150% wonder production magnitude.
- [ ] **P2 Potala**: ×10 → 10 Diplomatic slots; turn ends with
  manually slotted typed Reserve fillers (DIPLOMATIC family for
  Potala; typed cards also fit wildcard slots); save/reload valid.
  Then probe +20/+50/+100 and record the highest stable slot count
  (set the TESTED cap if below 100). No auto-slotting ships: fillers
  are manual, as in the proven Wonder-x10 pattern.
- [ ] **S1 Spawn stress**: Pyramids/Zeus/Kotoku at ×20/×50/×100 —
  record placement failures, stacking, hangs, dropped units.
- [ ] **MD1 Modes**: Monopolies industry/corporation bonuses scale
  with mode ON; a standard game with modes OFF shows zero mode
  mutations (no leakage). Secret Society bonuses scale with modes ON
  (Owls/Voidsingers/Hermetic/Vampire rows are modes-owned).
- [ ] **G1 Great People**: one burst activation (e.g. gold) pays ×10
  once, no double-apply on reload.
- [ ] **A1 Appeal spot**: Golden Gate city Appeal scales at ×10.
- [ ] **C7 Custom 7.3 count proof**: one new count-like family shows
  exact-integral apply (Panama 63) AND inexact refusal (Jebel 43.8).

## Artwork (separate human task, still the only content blocker)

`release/PREVIEW_ART_BRIEF.md` — two 1024×1024 PNGs still missing.
