# X10 v1.0.0-rc1 — validation summary (compact public evidence)

No raw log dumps are included. Full native logs remain in the private
development workspace; their SHA-256 hashes are recorded below so the
summaries stay checkable.

- Validated production commit: `2cf953e`
- Validation tag: `phase6b-1010-live-validated`
- CE fork commit: `1ce3188` (branch `x10-lifecycle-log`)
- DLL SHA-256:
  `e33d84b83d752a9eb7b52b4740291c97183af4d079d1ca82b8bd9d92b5c4d619`
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

Private archived evidence (hashes only):
- `X10Lifecycle.1010-6C-runA.log`:
  `9b41d240b3f52aa28e7c60597b96f13f1b2f1f55a9820587ab553a59c84f9f44`
- `X10Lifecycle.1010-6C-runB.log`:
  `f21e5944acd8c7637154496ff8947dd84f526b7d63267d9f487cd4f959eb1919`
- `X10Probe.1010-6C-runA.log`:
  `100e9a0861c89056cabaff1880c62447938238247daadfe0d9c6cd4a02ae5689`
- `X10Probe.1010-6C-runB.log`:
  `f4868369b112926e435340435e34207fa964016fb6fad02e3ba93bcf62030082`
