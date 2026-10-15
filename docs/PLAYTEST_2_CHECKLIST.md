# Playtest-2 checklist (human — game runs + log capture)

STATUS 8B.5: full ×10 Playtest-2 campaign — PASS (PROVISIONAL
RELEASE-QUALITY GAMEPLAY PASS, 2026-10-15). A complete real campaign
with all 13 categories enabled + Secret Societies exercised the
expanded build without an obvious critical failure: no OB-caused
crash, no persistent softlock, no obvious catastrophic double-scaling,
no category leakage severe enough to block play; save/reload worked
across multiple sessions. This is strong integration evidence, NOT
exhaustive proof of every one of the 2481 registry entries. P0, P0B,
P0C, P1 below are PASS for ×10; Custom 7.3 runtime is NOT yet
validated (next gate); no ×50/×100 stress until 7.3 closes.

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

## P0 boot smoke — PASS (8B.5: six campaign sessions)

Live result, six recent ×10 native sessions (all 13 modules ON,
Secret Societies), every one a clean EXIT (`spike/
validation-evidence/X10Lifecycle.playtest2-x10-campaign.log`):

  definitions_added=4029
  writes=1682 transform_refused=0 official_mismatch=0
  post_add_match=1682 post_add_mismatch=0 post_add_unreadable=0
  skipped_other=0 repeat_idle=630

- [x] **P0** confirmed on the 8B.4.4 build across multiple campaign
  sessions (load + save/reload): game boots, Government screen opens,
  no SLOT_NONE errors, EXIT line exactly as above every session.
  (The 693 inert slot copies carry `GovernmentSlotType=SLOT_NONE`,
  which has no official `GovernmentSlots` row.)
  Do NOT use the obsolete 1851 SS-only expectation: 1851 is now only
  the theoretical all-relevant-optional-modes-loaded count
  (`tests/test_mode_aware_runtime.py::TestAllModesValidation`).

## P0B Reserve picker — HARD FAIL (replaced below, do not re-run as-is)

Recorded failure: at Code of Laws the Government screen flooded with
700 Reserve Policies (scrolling borderline unusable, real cards
buried) and filler LOC keys rendered literally. The 700-visible-cards
architecture is rejected. The replacement gates:

## P0B-replacement (on-demand fillers + localization) — PASS (8B.5)

- [x] Reached Code of Laws with the normal intended UI stack including
  Extended Policy Cards through a full campaign. Government/Policy
  screen: ZERO X10 Reserve cards visible at ordinary
  Chiefdom/Code-of-Laws (fillers ship dormant: ExplicitUnlock, no
  civic). Picker remained normally usable — no mass Reserve flood.
- [x] No literal `LOC_POLICY_X10_FILLER_*` strings anywhere in the
  Government screen (filler text now loads InGame).

## P0C (source-driven unlock + save/load) -- 8B.4.4 — PASS (8B.5)

- [x] Potala ×10: Government displayed 10 Diplomatic slots;
  source-driven manager unlocked 9 Diplomatic Reserve policies —
  sufficient to fill the multiplied slots; menu stayed usable;
  policies confirmed; turn ended/continued; next-turn
  reconciliation unlocked nothing further; save/reload unlocked
  nothing further. Later campaign save: `BUILDING_POTALA_PALACE`
  target Diplomatic = 9, have Diplomatic = 9.
- [x] Second source survived save/reload without multiplication:
  `BUILDING_FORBIDDEN_CITY` target Wildcard = 9, have Wildcard = 9.
- [x] ExplicitUnlock experiment record: with ONE fresh filler,
  verify IsPolicyUnlocked flips true after UnlockPolicy, the card is
  slottable normally, and save/reload retains valid state. Report
  any deviation before wider use.

## Matrix runs (native lifecycle)

- [x] **R1** preset ×10 Classic, ALL 13 modules ON, Secret
  Societies only (load + save/reload): PASS — six campaign sessions
  all show `writes=1682 transform_refused=0 official_mismatch=0
  post_add_match=1682 post_add_mismatch=0 post_add_unreadable=0
  skipped_other=0 repeat_idle=630`, sessions identical.
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
- [x] **R6** save/reload on R1 config: PASS — sessions identical
  across the multi-session campaign (save/reload used successfully
  across multiple sessions).

## Focused gameplay checks

- [x] **P1 BRS/EPC calculated display (BLOCKER until green)** — PASS
  for ACTUALLY TESTED calculated witnesses only (8B.5). Compat
  context loads, loads the generated 1788-entry data, wraps
  RMA.CalculateModifierEffect, and reports wrapper active. With
  Better Report Screen + Extended Policy Cards enabled, God King
  card tooltip/BRS Policy page reads +10 Faith/+10 Gold at x10
  (gameplay already does: native log proves `GOD_KING_GOLD 1 -> 10
  MATCH`) — INSPECTED. Urban Planning reads +10 Production —
  INSPECTED. Discipline ~+29 (NOT +50, NOT +5) remains an EXPECTED
  COMBAT witness, NOT individually validated: no archived human
  evidence proves it was inspected — do not cite it as validated
  on native transform math alone. KNOWN DISPLAY LIMITATION (not a
  gameplay/native failure, not a compat failure): static Firaxis
  prose may still show vanilla numbers (e.g. God King body +1/+1)
  while only the CALCULATED result must be truthful. No
  localization-number rewriting in this pass.
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
- [x] **P2a Potala ×10 functional policy-slot test**: PASS — ×10 →
  10 Diplomatic slots; 9 Diplomatic Reserves unlocked on completion
  (target 9, then 0 next turn); usable picker; Reserves legal in
  Diplomatic slots with localized name/description; policies
  confirmed; End Turn works; save/reload valid; idempotent
  reconciliation (no further unlocks).
- [ ] **P2b multiplied policy-slot stress — NOT RUN**: ×20 / ×50 /
  ×100 slot sources; record the highest stable slot count and set a
  practical TESTED cap if below 100. Grouped with the later
  ×20/×50/×100 stress phase (see S1). Do not imply this passed.
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

## Next gate: Custom 7.3 (NOT yet run — do not start ×50/×100 first)

Mechanically-derived SS-only expectation (source of truth:
`tests/test_mode_aware_runtime.py::test_r2_ss_only_1204`, derived
from the registry + manifest bundle attribution, never hand-entered):

  writes=1204 transform_refused=1108
  (1204 = 1187 unconditional + 17 exact count-like; all 693 REPEAT
  refuse; 169 disabled-mode definitions absent, not refused.)

- [ ] **R2** Custom 7.3, all ON, Secret Societies only: EXIT line
  exactly `writes=1204 transform_refused=1108 ...` with zero
  mismatches/unreadables. Save/reload identical.
- [ ] Exact whole/count-like refusal: Eiffel +2 Appeal stays vanilla
  +2; Jebel +6 Iron/turn stays +6 (never 43.8); one-time integer
  grants (e.g. Pyramids Builder count) refuse fractional scaling.
- [ ] REPEAT refusal: all 693 REPEAT copies refuse; NO Reserve filler
  unlocks from refused fractional slot sources — Potala/Forbidden
  City/etc remain vanilla +1 slots at 7.3.
- [ ] Additive fractional multiplication: ordinary yields use exact
  fractional values where the game supports them.
- [ ] VECTOR element-wise: Petra desert tiles +14.6 Food / +14.6 Gold
  / +7.3 Production.
- [ ] COMBAT transform: Discipline calculated value matches the native
  7.3 transform (neither simple 5×7.3 nor vanilla +5).
- [ ] DISCOUNT + DELTA behavior: spot-check one of each against the
  twin math (`tests/test_phase8b4_ux_compat.py::TestApplyTwin`).
- [ ] Owner/module gating unchanged at 7.3 (R3 spot-check one module).
- [ ] BRS/EPC compatibility under fractional Custom: God King + Urban
  Planning calculated footers match native 7.3 values; static prose
  limitation still applies.

## Artwork (separate human task, still the only content blocker)

`release/PREVIEW_ART_BRIEF.md` — two 1024×1024 PNGs still missing.
