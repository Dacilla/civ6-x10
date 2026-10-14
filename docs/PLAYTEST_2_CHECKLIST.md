# Playtest-2 checklist (human — game runs + log capture)

STATUS 8B.4: the Playtest-2 campaign is STOPPED. P0B hard-failed in
real gameplay (700 Code-of-Laws Reserve cards flood the picker; filler
LOC keys render literally). Do not run the campaign matrix until the
8B.4 corrected build passes P0, P0B-replacement, P0C, and P1 below.

Build installed: `X10` + `CE-X10` in Civ VI Mods (8B.4 tree), DLL
recorded in `spike/EXPECTED_DLL_SHA256.txt`. Disable upstream Community
Extension and any other GameCore replacement. Standard setup for every
run unless noted: Gathering Storm, ROME (Trajan), Small map, 2 AI,
Secret Societies ON (so mode payloads are present).

Game-mode content rule: the native engine only populates definitions
for ENABLED content. In the standard Secret-Societies-only setup the
Dramatic Ages (58), Heroes & Legends (52), Monopolies & Corporations
(51), and Apocalypse (8) definitions are ABSENT: 169 rows never
iterate. Absent is not skipped, refused, or error. Full-registry math
(1851 at x10, 1353 at 7.3) applies only to the
ALL-RELEVANT-MODES-ENABLED configuration (Secret Societies + Dramatic
Ages + Heroes & Legends + Monopolies & Corporations + Apocalypse).

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

## P0 boot smoke — PROVISIONALLY PASS (8B.3 evidence, re-confirm)

Prior live result (x10 Classic, all 13 modules ON, Secret Societies):

  writes=1682 transform_refused=0 official_mismatch=0
  post_add_match=1682 post_add_mismatch=0 post_add_unreadable=0
  skipped_other=0 repeat_idle=630

- [ ] **P0** re-confirm on the 8B.4 build: game boots, Government
  screen opens, no SLOT_NONE errors, EXIT line exactly as above.
  (The 693 inert slot copies carry `GovernmentSlotType=SLOT_NONE`,
  which has no official `GovernmentSlots` row.)

## P0B Reserve picker — HARD FAIL (replaced below, do not re-run as-is)

Recorded failure: at Code of Laws the Government screen flooded with
700 Reserve Policies (scrolling borderline unusable, real cards
buried) and filler LOC keys rendered literally. The 700-visible-cards
architecture is rejected. The replacement gates:

## P0B-replacement (on-demand fillers + localization)

- [ ] Reach Code of Laws with the normal intended UI stack including
  Extended Policy Cards. Open the Government/Policy screen: expect
  ZERO X10 Reserve cards visible at ordinary Chiefdom/Code-of-Laws
  (fillers ship dormant: ExplicitUnlock, no civic). Picker remains
  normally usable.
- [ ] No literal `LOC_POLICY_X10_FILLER_*` strings anywhere in the
  Government screen (filler text now loads InGame).

## P0C (demand-driven unlock + save/load)

- [ ] Force/build a multiplied bonus slot source (e.g. x10 Potala =
  10 Diplomatic slots): only the deficit of Reserve cards for the
  CURRENT slots unlocks (Diplomatic family for Potala; typed cards
  also fit wildcard slots). Count visible Reserve cards: expect the
  deficit only (single digits at x10 Potala with few real Diplomatic
  cards), never hundreds.
- [ ] Fill the slots with the unlocked Reserves, confirm policies,
  turn ends. Save/reload: slots, policies, and unlocks remain valid.
- [ ] ExplicitUnlock experiment record: with ONE fresh filler,
  verify IsPolicyUnlocked flips true after UnlockPolicy, the card is
  slottable normally, and save/reload retains valid state. Report
  any deviation before wider use.

## Matrix runs (native lifecycle)

- [ ] **R1** preset ×10 Classic, ALL 13 modules ON, Secret
  Societies only (load + save/reload): expect `writes=1682
  transform_refused=0 official_mismatch=0 post_add_match=1682
  post_add_mismatch=0 post_add_unreadable=0 skipped_other=0
  repeat_idle=630`, sessions identical.
  (1682 = 1619 present non-REPEAT + 63 active REPEAT; 169
  disabled-mode definitions absent, 630 idle by design.)
- [ ] **R1-ALL** same but ALL-RELEVANT-MODES-ENABLED: expect
  `writes=1851 ... repeat_idle=630` (1851 = 1788 + 63).
- [ ] **R2** Custom 7.3, all ON, Secret Societies only: expect
  `writes=1204 transform_refused=1108 ...` (1204 = 1187 + 17 exact;
  all 693 REPEAT refuse). Spot witnesses: Panama delta 63 MATCH;
  Stonehenge delta refused; Jebel iron refused (stays 6); Petra
  vector `14.6,14.6,7.3` MATCH.
- [ ] **R2-ALL** Custom 7.3, all modes: `writes=1353 refused=1128`.
- [ ] **R3** module checkboxes OFF one at a time in an SS-only game
  (promotions, dedications, modes, religion, greatpeople, projects,
  city-state, wonders): each run must show exactly that module's
  `owners=` skip lines and zero mutations of its rows. Modes OFF
  skips the 34 present society rows (203 in an all-modes game);
  Governors OFF skips only the 48 base governor rows.
- [ ] **R4** preset Off: disarmed, zero mutations; policy screen shows
  zero Reserve cards (manager must not unlock when disarmed).
- [ ] **R5** invalid Custom (`abc`, `-1`, `101`, blank): disarmed with
  explicit reasons, zero transforms.
- [ ] **R6** save/reload on R1 config: sessions identical.

## Focused gameplay checks

- [ ] **P1 BRS/EPC calculated display (BLOCKER until green)** with
  Better Report Screen + Extended Policy Cards enabled, God King
  card tooltip/BRS Policy page must read +10 Faith/+10 Gold at x10
  (gameplay already does: native log proves `GOD_KING_GOLD 1 -> 10
  MATCH`). Discipline must reflect ~+29 (NOT +50, NOT +5). Urban
  Planning must read +10 Production. Static Firaxis prose may still
  show vanilla numbers; only the CALCULATED result must be truthful.
- [ ] **C1 Colosseum**: build queue shows +2 Culture (not +0); host
  City Center gets +20 total Culture at ×10; every eligible City
  Center within 6 tiles gets +20 total Culture; a city outside range
  gets none. A nearby city receiving only +2 Culture is FAILURE.
  Loyalty stays ×10 via its existing regional modifier; the +2
  Entertainment aura within 6 tiles stays VANILLA (never bridged,
  not scaled).
- [ ] **J1 Jebel Barkal**: +60 Iron/turn at ×10; stays +6 at 7.3.
- [ ] **J2 Jebel regional**: ×10 host/in-range city +40 Faith total;
  another eligible city within 6 tiles +40 Faith; outside 6 tiles no
  Jebel Faith.
- [ ] **MC1 Maracana regional**: ×10 every city +60 Culture total.
- [ ] **P3 Petra**: desert tiles +20 Food/+20 Gold/+10 Production
  at ×10 (at 7.3: +14.6/+14.6/+7.3).
- [ ] **P4 Pyramids**: 10 Builders at ×10.
- [ ] **E1 Eiffel**: +20 Appeal at ×10; unchanged at 7.3.
- [ ] **D1 Discipline**: ~+29 vs Barbarians (NOT +50).
- [ ] **M1 Monument to the Gods**: +150% wonder production magnitude.
- [ ] **P2 Potala**: ×10 → 10 Diplomatic slots; deficit-only
  Diplomatic Reserves unlock on demand; turn ends; save/reload
  valid. Then probe +20/+50/+100 and record the highest stable slot
  count (set the TESTED cap if below 100).
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
