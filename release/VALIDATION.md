# X10 validation summary (compact public evidence)

No raw log dumps are included. Full native logs remain in the private
development workspace; their SHA-256 hashes are recorded below so the
summaries stay checkable.

## Phase 8B — under pre-publication gameplay validation

The Playtest-1 closure expansion grew the registry to 2481 entries
(2475 unique definitions, 26 shared; 1333 unconditional + 1148
count-like) with three new native kinds (VECTOR/DELTA/REPEAT), six new
modules (promotions, dedications, modes, religion, greatpeople,
projects), and a new native build:

- CE fork branch `phase-8b-coverage`, commit `1e89e1b`
- DLL SHA-256:
  `ced8f01750d22f44725ed61de7c0926c58e423388b3ee7fce0fd18522081b744`

Static gate expectation at Custom 7.3: 1333 apply + 20 exact
conditionals = 1353 of 2481; 1128 refuse safely (never floored).
The live validation matrix below (RC2, 1010 set) is retained as the
prior validated point; the 8B matrix (preset x10 all-ON, Custom 7.3,
per-module OFF, invalid Custom, save/reload, plus focused live checks
for Jebel/Petra/Pyramids/Potala/Colosseum/Eiffel/Discipline/Monument)
is recorded in `docs/PHASE_8B.md` as it completes. No public release
is cut from the 8B tree until that matrix is green.

## RC2 record v1.0.0-rc2 (prior validated point, 1010 set)

RC2 — not RC1 — was the final validated candidate before Phase 8B:
RC2 carries the new preset/custom/bool configuration path (DLL
`3b6dc3d2…ab14`, CE `0655190`) over the unchanged 1010-entry
gameplay set.

### Semantic validation (registry freeze `2cf953e`)

- Validation tag: `phase6b-1010-live-validated`
- Registry: 1010 entries / 1006 unique definitions / 25 shared
  (788 unconditional + 222 count-like)
- Run A, all seven modules ON, initial load AND save/reload identical:
  `writes=801 transform_refused=209 official_mismatch=0 post_add_match=801
  post_add_mismatch=0 post_add_unreadable=0 skipped_other=0`
- Run B, Governors OFF + Suzerain OFF:
  `writes=698 transform_refused=174 official_mismatch=0 post_add_match=698
  post_add_mismatch=0 post_add_unreadable=0 skipped_other=138`
  (exactly the 70 + 68 manifest skip sets; zero masked mutations)
- Representative witnesses (native `stored_after_add ... MATCH
  via=store-lookup`): Toqui loyalty 29.2 x2 (traits-owned), Bishop
  pressure 730, Owls loyalty 29.2, Preslav identity 14.6 x3, Vatican
  religious pressure 2920, Citadel completion 182.5, Ayutthaya completion
  73, Lahore combat 38.10 (`transform=COMBAT`), Valletta discount
  99.3654 x3 (`transform=DISCOUNT`, compound — never 365/500)
- Intentional refusals (previously fractional writes, now exact-integral
  by reviewed semantic correction): Corporate Libertarianism retains 1,
  Coal/Iron retain 2; all 21 new count-like pairs refuse at k=7.3
- Setup: Gathering Storm, Rome/Trajan, Small map, 2 AI, multiplier 7.3,
  Secret Societies ON, Workshop Community Extension disabled

### Final configuration/UX validation (RC2)

- CE fork commit: `0655190` (branch `x10-lifecycle-log`)
- DLL SHA-256:
  `3b6dc3d26c3eab51fa5be4272252b926deaf10b6d4e7bedb094c2c6c8272ab14`
- Controller runtime: `release/release-manifest.yml`
  `controller_release_commit`
- Run A — preset ×10 Classic, all ON (load+reload):
  `writes=1010 refused=0 mismatch=0 unreadable=0 skipped=0`,
  `post_add_match=1010`, sessions identical.
- Run B — Custom 7.3, all ON: `writes=801 refused=209`,
  pair-for-pair identical to the semantic evidence above.
- Run C — Custom 7.3, Governors OFF: `writes=745 refused=195
  skipped=70` (exactly the 70 governor-manifest skips, zero Governor
  mutations, Toqui still writes).
- Run D — preset Off: disarmed, zero mutations, concise OFF reason.
- Run E — invalid Custom: `abc` (TEXT variant, fail-closed),
  `-1`/`101` (INT32 out-of-range, fail-closed); blank enters INT32 0
  (Off-equivalent); each disarmed with an explicit reason and zero
  transforms.
- RC2 smoke (probe-free, preset ×10, save/reload): 1010/0 both
  sessions, per-row identical to matrix Run A.

Private archived evidence (hashes only):
- `X10Lifecycle.1010-6C-runA.log`:
  `9b41d240b3f52aa28e7c60597b96f13f1b2f1f55a9820587ab553a59c84f9f44`
- `X10Lifecycle.1010-6C-runB.log`:
  `f21e5944acd8c7637154496ff8947dd84f526b7d63267d9f487cd4f959eb1919`
- `X10Probe.1010-6C-runA.log`:
  `100e9a0861c89056cabaff1880c62447938238247daadfe0d9c6cd4a02ae5689`
- `X10Probe.1010-6C-runB.log`:
  `f4868369b112926e435340435e34207fa964016fb6fad02e3ba93bcf62030082`

## 7C.2 UX validation matrix (RC2, DLL `3b6dc3d2...ab14`, same 1010 set)

Setup UI: preset dropdown `X10_MULTIPLIER_PRESET`, custom
`X10_MULTIPLIER` text, seven bool `X10_MODULE_*` checkboxes,
AdvancedOptions 2400-2408, en_US localization.

- Run A -- preset x10 Classic, all ON (load+reload):
  `writes=1010 refused=0 mismatch=0 unreadable=0 skipped=0`,
  `post_add_match=1010`, sessions identical.
- Run B -- Custom 7.3, all ON: `writes=801 refused=209`,
  pair-for-pair identical to the 6C evidence above.
- Run C -- Custom 7.3, Governors OFF: `writes=745 refused=195
  skipped=70` (exactly the 70 governor-manifest skips, zero Governor
  mutations, Toqui still writes).
- Run D -- preset Off: disarmed, zero mutations, concise OFF reason.
- Run E -- invalid Custom: `abc` (TEXT variant, fail-closed),
  `-1`/`101` (INT32 out-of-range, fail-closed); each disarmed with an
  explicit reason and zero transforms. Blank enters INT32 0
  (Off-equivalent, measured-live, bit-identical to explicit 0).
- RC2 smoke (probe-free, preset x10, save/reload): PASS 1010/0 both
  sessions, per-row identical to matrix Run A (evidence X10Lifecycle.1010-RC2-smoke-{load,reload}.log).
