# Invalid-input matrix — X10 Custom multiplier (`X10_MULTIPLIER`, Domain `text`)

Reader: `X10Write.cpp` (`X10Config::TryGetMultiplier` L287-327,
`ResolveEffectiveMultiplier` L238-281, `TryGetMultiplierPreset` L201-226,
`VariantToDouble` L81-126, `FindConfigState` L145-170).
Frontend: `text` domain commits the raw string with zero validation
(`AdvancedSetup.lua` L967-979; `GameSetupLogic.lua` L220-231); the engine's
`TableToTypedVariantMap` materializes integer strings as INT32 (mask id 2) and
fractional strings as FLOAT32 (id 4), non-numeric strings stay string variants
(id 5) — split proven live (`X10Lifecycle.1010-7C2-runB.log` FLOAT32 7.3;
`runE-101`/`runE-minus1` INT32; `runE-invalid` id 5).
Assumes preset = Custom (101) except where noted.

| # | FrontEnd input | FrontEnd stores / engine emits | Native resolution (arm k / off / disabled + reason) | Confidence |
|---|---|---|---|---|
| 1 | blank `""` | UI inserts INT32 0 before native sees it | k = 0 → **off-equivalent, disarmed**, no writes | measured-live (`docs/UX_REVIEW.md` §17) |
| 2 | whitespace `"   "` | raw string committed (no trim in driver) | expected string variant → **fail-closed, disabled** (same path as `abc`) | inferred (no live run; driver has no trim/normalize) |
| 3 | `abc` | string variant id 5, flags `0x21000004` | **fail-closed, disabled**: `undecodable-variant` → "blank, malformed, or outside 0-100" → `writes DISABLED`, 3336 defs untouched | measured-live (`X10Lifecycle.1010-7C2-runE-invalid.log` L18-21) |
| 4 | `7,3` | raw string; engine numeric parse uses period (`X10Write` log hint: "decimals need a period, e.g. 7.3") → stays string variant | **fail-closed, disabled** (same path as `abc`) | source-derived + log-hint (no live comma run) |
| 5 | `-1` | INT32 −1 | **fail-closed, disabled**: `out-of-range` → custom-invalid message → `writes DISABLED` | measured-live (`X10Lifecycle.1010-7C2-runE-minus1.log` L18-20) |
| 6 | `100.1` | FLOAT32 100.1 | **fail-closed, disabled**: `d <= 100` check (`TryGetMultiplier` L301) fails → `out-of-range` | source-derived (no live 100.1 run; same check as measured `-1`/`101` rejections) |
| 7 | `101` | INT32 101 | **fail-closed, disabled**: `out-of-range` (preset-101 means Custom and never passes through as a multiplier, `TryGetMultiplierPreset` L198-200) | measured-live (`X10Lifecycle.1010-7C2-runE-101.log` L18-20) |
| 8 | `0` | INT32 0 | in-range → k = 0 → caller normalizes to **disarmed (Off-equivalent)**, no writes | measured-live pattern (`docs/UX_REVIEW.md` §17 "0 → valid (Off-equivalent)"; k==0 convention `X10Write.cpp` L236-237; module `numeric=0` = OFF in gov/suz-off runs) |
| 9 | `0.1` | FLOAT32 0.1 | in-range → **arms**, k = 0.1 | source-derived (same accept path as measured `0.5`/`7.3`; no dedicated 0.1 live run) |
| 10 | `0.5` | FLOAT32 0.5 | in-range → **arms**, k = 0.5 | source-derived (`docs/UX_REVIEW.md` §17 "0.5/7.3/100 → accept") |
| 11 | `7.3` | FLOAT32 `7.30000019073486`, kerr `2.38e-07` | **arms**, k = 7.3 → `writes=801 transform_refused=209` (1010-entry registry) | measured-live (`X10Lifecycle.1010-7C2-runB.log` L18-19; `X10Lifecycle.1010-7C2-runC.log`; `X10Lifecycle.1010-RC-smoke.log` L18; README Phase 6B Run A) |
| 12 | `100` | INT32 100 | in-range → **arms**, k = 100 | source-derived (`docs/UX_REVIEW.md` §17; same accept path as measured preset-100-class values; preset ×10 path measured: "effective multiplier: preset 10", `X10Lifecycle.1010-7C2-runA.log` L18, `X10Lifecycle.1010-RC2-smoke-load.log` L18) |

Related measured anchors (not custom-field rows): preset Off → "multiplier
preset OFF; definition transforms disabled", `writes DISABLED`
(`X10Lifecycle.1010-7C2-runD.log` L18-19); preset ×10 → "effective multiplier:
preset 10" (runA, RC2-smoke-load); bool `numeric=0` = OFF / `numeric=1` = ON
(`X10Lifecycle.1010-6C-runB.log` L29-31; RC-smoke L19-32).

## Notes

- **0 == Off? Yes in net effect.** Explicit `0` (INT32 0, in-range) resolves to
  k = 0, which the caller normalizes to disarmed — zero definition writes,
  identical outcome to preset Off. Log reasons differ (custom-0 arm-with-k=0 vs
  "preset OFF"), game state does not.
- **Blank vs explicit 0? Indistinguishable at the native layer.** Blank enters
  as INT32 0 (measured, §17 doc), bit-identical to typing `0`. Both disarm.
  (`FindConfigState` *can* distinguish a true UNSET type-0/flags-0/zero-payload
  shape from INT32 0 — but blank does not arrive in that shape, so the
  distinction never applies to blank input.)
- **Comma behavior.** No live comma run exists. The engine materializes only
  period-decimals as FLOAT32 (all measured fractional commits use periods; the
  user-facing fail-closed message explicitly says "decimals need a period, e.g.
  7.3"), so `7,3` stays a string variant and fails closed like `abc`. Treat as
  source-derived, not measured.
- **Fail-closed is total.** All three rejection shapes (undecodable variant,
  out-of-range, invalid preset with no legacy fallback — `X10Write.cpp`
  L278-280) end in `writes DISABLED` with `definitions_added=3336`,
  `official_mismatch=0`: official definitions are never partially written.
- **No clamping/rounding anywhere.** The reader never coerces (`uint`'s
  `math.max(tonumber or 0, 0)` frontend coercion is exactly why Custom is Domain
  `text`, `docs/UX_REVIEW.md` §17). `0.5`/`7.3` arm at full float32 precision
  (redisplay artifact `7.3000001907349` documented in `docs/UX_REVIEW.md` §14/§16).
