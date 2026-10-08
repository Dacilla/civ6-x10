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
