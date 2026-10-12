# Playtest-2 checklist (human — game runs + log capture)

Build installed: `X10` + `CE-X10` in Civ VI Mods (8B tree), DLL
`e0486aee...0ea06c`. Disable upstream Community Extension and any other
GameCore replacement. Standard setup for every run unless noted:
Gathering Storm, ROME (Trajan), Small map, 2 AI, Secret Societies ON
(so mode payloads are present).

Logs: after each run, copy `%TEMP%\X10Lifecycle.log` to
`spike/validation-evidence/` BEFORE the next run (the file appends).
The run is green only if the EXIT line matches AND the listed
witnesses show `MATCH`.

## Matrix runs (native lifecycle)

- [ ] **R1** preset ×10 Classic, ALL 13 modules ON (load + save/reload):
  expect `writes=2481 refused=0 mismatch=0 unreadable=0 skipped=0`,
  `post_add_match=2481`, sessions identical.
- [ ] **R2** Custom 7.3, all ON: expect `writes=1333` + 20 exact,
  `refused=1128`, `mismatch=0`, `unreadable=0`, `skipped=0`.
  Spot witnesses: Panama delta 63 MATCH; Stonehenge delta refused;
  Jebel iron refused (stays 6); Petra vector `20,20,10` MATCH.
- [ ] **R3** new modules OFF one at a time (promotions, dedications,
  modes, religion, city-state, wonders): each run must show exactly
  that module's `owners=` skip lines and zero mutations of its rows.
- [ ] **R4** preset Off: disarmed, zero mutations.
- [ ] **R5** invalid Custom (`abc`, `-1`, `101`, blank): disarmed with
  explicit reasons, zero transforms.
- [ ] **R6** save/reload on R1 config: sessions identical.

## Focused gameplay checks

- [ ] **P1 BRS/EPC**: with Better Report Screen + Extended Policy
  Cards enabled, God King card tooltip/BRS Policy page reads
  +10 Faith/+10 Gold at ×10 (gameplay already does).
- [ ] **C1 Colosseum**: build queue shows +2 Culture (not +0);
  cities in range get +20 Culture at ×10; cities outside get none.
- [ ] **J1 Jebel Barkal**: +60 Iron/turn at ×10; stays +6 at 7.3.
- [ ] **P3 Petra**: desert tiles +20 Food/+20 Gold/+10 Production.
- [ ] **P4 Pyramids**: 10 Builders at ×10.
- [ ] **E1 Eiffel**: +20 Appeal at ×10; unchanged at 7.3.
- [ ] **D1 Discipline**: ~+29 vs Barbarians (NOT +50).
- [ ] **M1 Monument to the Gods**: +150% wonder production magnitude.
- [ ] **P2 Potala**: ×10 → 10 Diplomatic slots; turn ends with Reserve
  fillers; save/reload valid. Then probe +20/+50/+100 and record the
  highest stable slot count (set the TESTED cap if below 100).
- [ ] **S1 Spawn stress**: Pyramids/Zeus/Kotoku at ×20/×50/×100 —
  record placement failures, stacking, hangs, dropped units.
- [ ] **M1 Modes**: Monopolies industry/corporation bonuses scale
  with mode ON; a standard game with modes OFF shows zero mode
  mutations (no leakage).
- [ ] **G1 Great People**: one burst activation (e.g. gold) pays ×10
  once, no double-apply on reload.
- [ ] **A1 Appeal spot**: Golden Gate city Appeal scales at ×10.
- [ ] **C7 Custom 7.3 count proof**: one new count-like family shows
  exact-integral apply (Panama 63) AND inexact refusal (Jebel 43.8).

## Artwork (separate human task, still the only content blocker)

`release/PREVIEW_ART_BRIEF.md` — two 1024×1024 PNGs still missing.
