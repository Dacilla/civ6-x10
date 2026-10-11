# Validation evidence: Release-1 684-entry live run (FLOAT32 k=7.3)

Source: `%TEMP%\X10Lifecycle.log` + `%TEMP%\X10Probe.log` from the validating
run (2026-10-08). Sanitized: ASLR addresses normalized to `0xADDR`; no
usernames, hostnames, or paths present in the originals.

Result (initial load AND reload, identical):
`definitions_added=3210 writes=610 transform_refused=74 official_mismatch=0
post_add_match=610 post_add_mismatch=0 post_add_unreadable=0 skipped_other=0`

Rome gameplay witness (`X10Probe.684-live.log`): `Amount=7.3 PASS`.

Files:
- `X10Lifecycle.684-live.log` — full native session for the 684-entry core
  (`writes=610 ... post_add_match=610 ...`, tag baseline).
- `X10Probe.684-live.log` — Lua gameplay probe readback for the 684 run.
- `X10Lifecycle.715-live.log` — full native session with pantheons
  (`writes=638 transform_refused=77 ... post_add_match=638 ...`).
- `X10Probe.715-live.log` — probe readback incl. the (unfounded) Forge
  witness reported ABSENT, not failed.

Baseline tags: `release1-684-live-validated` (X10 @ d7266ab); pantheon run
archived against X10 @ 702a05d / CE-X10 @ 5a5473c.

---

# Phase 4B/4C Governor live validation (924-entry registry, FLOAT32 k=7.3)

Source: `%TEMP%\X10Lifecycle.log` + `%TEMP%\X10Probe.log` from the two
validating runs (2026-10-10). Unmodified logs; no sanitization was needed
(the originals carry no user identifiers).

Setup (identical for both runs): Gathering Storm, ROME (Trajan), Small map,
2 AI, X10 multiplier **7.3**, Workshop Community Extension disabled, X10 CE
Engine + X10 + X10 Production Probe enabled, **Secret Societies game mode
ON** (so the Ethiopia mode payload is present).

DLL: `81965998d7a04997279d8d51cf08eea1114e3e84a9dd61d51f2ee441119e8399`
(X10 `6960801` + probe `e499e6d`; CE-X10 `d0fda78`). Registry: **924 entries
/ 920 definitions** (684 Release-1 + 31 Pantheon + 155 Wonder/Suleiman
+ 54 Governors).

## Run A — Governors ON (`X10*924-gov-live.log`)

Two population sessions (initial load and save/reload), **byte-identical**:

`definitions_added=3336 writes=748 transform_refused=176 official_mismatch=0
post_add_match=748 post_add_mismatch=0 post_add_unreadable=0 skipped_other=0`

- 748 + 176 = 924 = the entire registry.
- Governor subset (measured per row against the 54 registry entries):
  **49 written (MATCH via=store-lookup) + 5 transform-refused**, 0
  unaccounted, 0 ownership skips.
- Witnesses (native `stored_after_add ... MATCH via=store-lookup`):
  `GROUNDBREAKER_BONUS_HARVEST_YIELDS` 365, `GARRISON_COMMANDER_ADJUST_CITY_COMBAT_BONUS`
  24.04 (combat), `GOVERNOR_PROMOTION_OWLS_OF_MINERVA_4_GOLD_INTEREST` 21.9
  (supplemental mode floor), `HERMETIC_ORDER_GREAT_ENGINEER_LEY_LINE_PRODUCTION`
  7.3 (mode payload).
- Six Governor COMBAT rows stored: Air Defense 65.15 (25), Grand Inquisitor
  38.10 (10), Redoubt 24.04 (5), Garrison 24.04 (5), Head Falconer 24.04 (5),
  Serasker 38.10 (10).
- Five engine-integral rows refused, never rounded: appeal `1 × 7.3`, and
  Renewable Energy / Industrialist coal, oil, nuclear `2 × 7.3`.
- Pre-existing witnesses still pass: `STAUEZEUS_ANTI_CAVALRY_PRODUCTION` 365,
  `X10_PANAMA_CANAL_YIELD_GOLD` 73, bridge diagnostics
  `bridge_expected=57 bridge_materialized=57 bridge_unavailable=0`.

## Run B — Governors OFF (`X10*924-govoff-live.log`)

The log file is **appended** across sessions; the final `===== X10 native
session =====` block is the Governor-OFF run (the two preceding blocks are
Run A's load and reload). Native config line confirms
`X10_MODULE_GOVERNORS ... numeric=0`.

`definitions_added=3336 writes=699 transform_refused=171 official_mismatch=0
post_add_match=699 post_add_mismatch=0 post_add_unreadable=0 skipped_other=54`

- 699 + 171 + 54 = 924.
- Exactly **54** `owners=0x20 not-all-enabled skipped` lines, covering exactly
  the 54 Governor registry rows.
- Zero Governor `stored_after_add`, zero Governor `transform-refused`, zero
  Governor official-mismatch lines: no Governor definition was mutated.
- Non-Governor behaviour unchanged: the non-Governor written set is
  **identical** between Run A and Run B; `STAUEZEUS…` 365 and
  `X10_PANAMA_CANAL_YIELD_GOLD` 73 still MATCH.

Files:
- `X10Lifecycle.924-gov-live.log` / `X10Probe.924-gov-live.log` — Run A.
- `X10Lifecycle.924-govoff-live.log` / `X10Probe.924-govoff-live.log` —
  Run B (3 native sessions: Run A load, Run A reload, Run B).

Validation tag: `phase4b-924-live-validated` (X10 @ 6960801/CE-X10 @ d0fda78,
probe witnesses added in e499e6d).

---

# Phase 5B/5C Suzerain live validation (971-entry registry, FLOAT32 k=7.3)

Source: `%TEMP%\\X10Lifecycle.log` + `%TEMP%\\X10Probe.log` from the two
validating runs. Unmodified logs.

Setup (identical for both runs): Gathering Storm, ROME (Trajan), Small map,
2 AI, X10 multiplier **7.3**, Workshop Community Extension disabled, X10 CE
Engine + X10 + X10 Production Probe enabled, **Secret Societies game mode
ON**.

DLL: `b6862b28d86aa67d20cd6ffecd1588cfc2e528dbb75d484cb8c4e52a387fb20d`
(X10 `fc176ca`; CE-X10 `d17bdb6`). Registry: **971 entries / 967 unique
definitions** (924 pre-Suzerain + 47 suzerain-only, owner bit 64).

## Run A — Suzerain ON (`X10*971-suz-live.log`)

Two population sessions (initial load and save/reload), **identical**:

`definitions_added=3336 writes=786 transform_refused=185 official_mismatch=0
post_add_match=786 post_add_mismatch=0 post_add_unreadable=0 skipped_other=0`

- 786 + 185 = 971 = the entire registry.
- Suzerain subset (matched per row against the 47 manifest pairs):
  **38 written (MATCH via=store-lookup) + 9 transform-refused**, 0
  unaccounted, 0 ownership skips, 0 mismatches, 0 unreadables.
- Witnesses (native `stored_after_add ... MATCH via=store-lookup`):
  Auckland shallow-water production 1 -> 7.3, Antananarivo 2 -> 14.6,
  Ngazargamu 20 -> **80.3864 with native `transform=DISCOUNT`** (all three
  Ngazargamu rows store the same compound-discount value; never 20 x 7.3).
- Family representatives: AMENITY 1 -> 7.3, EXPERIENCE 100 -> 730,
  FLAT_YIELD 1 -> 7.3, GOLD 1 -> 7.3, PERCENT_BONUS 2 -> 14.6,
  PERCENT_DISCOUNT 20 -> 80.3864, PRODUCTION_PERCENT 15 -> 109.5.
- Nine Bologna `Amount=1` rows refused, never rounded (no 7.3/7/8 writes),
  retaining vanilla 1: owner bit 64 does not bypass count-integrality.
- Pre-existing witnesses still pass: Groundbreaker 365, Garrison ~24.04,
  Zeus 365, Panama 73, bridge 57/57/0, five Governor integral refusals.

## Run B — Suzerain OFF (`X10*971-suzoff-live.log`)

The log file is **appended** across sessions; the final `===== X10 native
session =====` block is the Suzerain-OFF run. Native config line confirms
`X10_MODULE_SUZERAIN ... numeric=0`.

`definitions_added=3336 writes=748 transform_refused=176 official_mismatch=0
post_add_match=748 post_add_mismatch=0 post_add_unreadable=0 skipped_other=47`

- 748 + 176 + 47 = 971; reproduces the Phase-4C all-existing baseline.
- Exactly **47** `owners=0x40 not-all-enabled skipped` lines, covering exactly
  the 47 manifest rows. Zero Suzerain writes/refusals/mismatches: the nine
  Bologna rows are ownership-skipped before the integrality transform, so
  refusals return 185 -> 176.
- No-collateral proof: after removing the 47 Suzerain rows from Run A, the
  non-Suzerain written set (702 definitions), stored values and refusal set
  (176) are identical to Run B; Zeus/Panama still transform with Suzerain
  OFF.

Files:
- `X10Lifecycle.971-suz-live.log` / `X10Probe.971-suz-live.log` — Run A.
- `X10Lifecycle.971-suzoff-live.log` / `X10Probe.971-suzoff-live.log` —
  Run B (appended sessions: Run A load, Run A reload, Run B).

Validation tag: `phase5b-971-live-validated` (X10 @ fc176ca / CE-X10 @
d17bdb6, probe witnesses added pre-run).


---

# Phase 6B/6C cross-module backlog validation (1010-entry registry, FLOAT32 k=7.3)

Source: `%TEMP%\X10Lifecycle.log` + `%TEMP%\X10Probe.log` from the two
validating runs (2026-10-11). Unmodified logs (Run-B files hold exactly the
Run-B session; Run-A files hold load + reload).

Setup: Gathering Storm, ROME (Trajan), Small map, 2 AI, X10 multiplier
**7.3**, Workshop Community Extension disabled, X10 CE Engine + X10 + X10
Production Probe enabled, **Secret Societies game mode ON**.

DLL: `e33d84b83d752a9eb7b52b4740291c97183af4d079d1ca82b8bd9d92b5c4d619`
(X10 `2cf953e`; CE-X10 `1ce3188`; bridge SQL `d0faabfa` unchanged).
Registry: **1010 entries / 1006 unique definitions** (971 Phase-5B baseline
+ 37 backlog pairs + 2 Toqui addendum pairs; 3 intentional count-like
reclassifications).

## Run A - all modules ON (`X10*1010-6C-runA.log`)

Two population sessions (initial load and save/reload), **identical**:

`definitions_added=3336 writes=801 transform_refused=209 official_mismatch=0
post_add_match=801 post_add_mismatch=0 post_add_unreadable=0 skipped_other=0`

- 801 + 209 = 1010 = the entire registry.
- 39 new pairs, matched per row against the backlog boundary: **18 written
  (MATCH via=store-lookup) + 21 transform-refused**, 0 unaccounted, 0
  ownership skips, 0 mismatches, 0 unreadables (16 governors / 21 suzerain
  / 2 traits; 35 ADDITIVE / 3 DISCOUNT / 1 COMBAT).
- New-witness stored values: Toqui 29.2 x2, Bishop 730, Owls loyalty 29.2,
  Preslav 14.6 x3, Vatican 2920, Citadel 182.5, Ayutthaya 73, Lahore 38.10
  (`transform=COMBAT`), Valletta 99.3654 x3 (`transform=DISCOUNT`,
  compound - never 365/500).
- The 3 accumulation rows refuse with zero write lines
  (`CORPORATE_LIBERTARIANISM_RESOURCE_EXTRACTION`,
  `TRAIT_ACCUMULATE_MORE_COAL/_IRON`): previously 7.3/14.6/14.6 in 5C
  evidence - intentional semantic correction, not a regression.
- Regressions hold: Groundbreaker 365, Garrison 24.04, Owls interest 21.9,
  Ley Line 7.3, Auckland 7.3, Antananarivo 14.6, Ngazargamu 80.3864, Zeus
  365, Panama 73, bridge 57/57/0.

## Run B - Governors OFF + Suzerain OFF (`X10*1010-6C-runB.log`)

`definitions_added=3336 writes=698 transform_refused=174 official_mismatch=0
post_add_match=698 post_add_mismatch=0 post_add_unreadable=0 skipped_other=138`

- 698 + 174 + 138 = 1010. Exactly **70** `owners=0x20` + **68** `owners=0x40`
  `not-all-enabled skipped` lines, covering exactly the manifest sets. Zero
  masked writes/refusals/mismatches.
- Toqui still writes 29.2 x2 (traits owner proven); accumulations still
  refuse; Zeus/Panama still MATCH. Run-A-minus-masked equals Run B exactly
  (write sets, stored values, refusal sets).
- Note: a first Run-B attempt with Secret Societies OFF yielded 116 skips
  (22 mode-gated governor definitions absent from the DB); the re-run with
  the mode ON gives the letter-perfect 70/68. No evidence was taken from
  the mode-OFF session.

Files:
- `X10Lifecycle.1010-6C-runA.log` / `X10Probe.1010-6C-runA.log` - Run A.
- `X10Lifecycle.1010-6C-runB.log` / `X10Probe.1010-6C-runB.log` - Run B.

Validation tag: `phase6b-1010-live-validated` (X10 @ 2cf953e / CE-X10 @
1ce3188, probe witnesses added in 94f95fe).
