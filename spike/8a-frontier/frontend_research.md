# Part B — Frontend validation research (8A read-only)

Scope: official installed FrontEnd Lua only (Base/Assets/UI + DLC UI dirs).
No prototype mod files written (explicit task constraint).
X10 config under test: `X10Custom` Domain `text` (`controller/X10/Config/X10Config.sql`
L30-33), preset enum `X10MultiplierPresets`, seven `bool` module checkboxes.

## 1. Range-label recommendation: `(0 to 100)`

- No official `(0-100)`-style parameter-range label precedent exists. A scan of
  204 official text files (`Base/Assets/Text`, DLC `*ConfigText.xml`) found 115
  `(N-N)` hits — every sampled hit is a historical date range
  (e.g. `(1618-1648)`, `(1872-2006)`), never a UI input range; 13 `from-N-to-M`
  hits are prose, same class.
- The one official numeric-setting description found uses words, not a hyphen:
  `LOC_GAME_REALISM_DESCRIPTION` (`DLC/Expansion2/Text/en_US/Expansion2_ConfigText.xml`):
  *"Set natural disaster intensity. Choose from a setting of **0** …
  **to 4** …"*. Firaxis slider values render via `NumberDisplay`, not label ranges
  (`AdvancedSetup.lua` L1034-1038).
- Recommendation: label `X10 — Custom multiplier (0 to 100)`. The hyphen form
  risks misreading as a negative/minus in a numeric-input context, and matches no
  Firaxis precedent; the word form matches the only official style evidence.

## 2. What the native setup framework can and cannot do (file:line evidence)

Widget mapping is identical in both setup screens:

| Domain | Widget | Commit behavior |
|---|---|---|
| `bool` | checkbox | `o:SetParameterValue(parameter, not …IsSelected())` (`AdvancedSetup.lua` L870-871, L908-909; `GameSetupLogic.lua` L156-159) |
| `int` | string edit box | `tonumber(textString)`, **no range check** (`AdvancedSetup.lua` L952-958; `GameSetupLogic.lua` L205-211) |
| `uint` | string edit box | `math.max(tonumber(textString) or 0, 0)` — garbage **silently becomes 0** (`AdvancedSetup.lua` L959-966; `GameSetupLogic.lua` L212-219) |
| `text` | string edit box | raw `textString`, **zero validation** (`AdvancedSetup.lua` L967-979; `GameSetupLogic.lua` L220-231) |
| custom enum domain | pulldown | (`AdvancedSetup.lua` L1053-1099) |
| `IntRange` domain | integer-step slider | `minimumValue + stepNum` (`AdvancedSetup.lua` L1001-1029); range type is hardcoded `Type = "IntRange"` with integer `MinimumValue`/`MaximumValue` (`SetupParameters.lua` L1043-1049) |

POD domains are exactly `bool/int/uint/text` (`SetupParameters.lua` L1030-1035);
every other domain resolves to `IntRange` or an enumerated value list
(`SetupParameters.lua` L1252-1286). There is **no float/decimal domain, no
min/max/step/Validate hook on text** (`docs/UX_REVIEW.md` §17 independently
records: "No numeric formatting, min/max, step, or Validate hook exists anywhere
in the setup framework (verified by source search)"). The `text` domain is the
only one that preserves malformed input instead of coercing it, which is why X10
uses it for Custom.

Start-button gating (`AdvancedSetup.lua` `UI_PostRefreshParameters`, L1254-1293):

- `Controls.StartButton:SetDisabled(false)` unconditionally, then disabled only
  if `GetGameParametersError()` / `GetPlayerParameterError(player_id)` return
  non-nil (L1261-1278), with tooltips `LOC_SETUP_PARAMETER_ERROR` /
  `LOC_SETUP_PLAYER_PARAMETER_ERROR`.
- `GetGameParametersError()` returns only the global `g_GameParameters.Error or
  … Stalled` flag (`PlayerSetupLogic.lua` L268-272). Per-parameter `.Error`
  (`MissingDomainValue` / `InvalidDomainValue`) is set only for IntRange
  out-of-range-without-write-access and enum domain mismatches
  (`SetupParameters.lua` L1752-1796, L1813-1822). **A text parameter can never
  set `.Error`** — garbage custom input is invisible to the veto.
- Pre-host flow is warnings-only: city-state / leader-pool `ShowOkCancelDialog`
  → `HostGame()` → `Network.HostGame` (`AdvancedSetup.lua` L1451-1483). No
  custom-parameter validation hook exists in the path.

Popups: `PopupDialog` (`include("PopupDialog")`) is usable from any loaded
context (`FrontEndPopup.lua` L1-15; `UserSetupWarning.lua` L24-39,
`Events.UserSetupWarning`), but **loading** an additive frontend context has no
official precedent (see §3).

## 3. Additive frontend-extension mechanism: none demonstrated officially

Across all 42 official `.modinfo`, `FrontEndActions` use exactly these action
types (counts): `UpdateDatabase` 39, `UpdateIcons` 35, `UpdateArt` 34,
`UpdateText` 34, `UpdateColors` 32, `AddMap` 5, `ImportFiles` 2 (both are
`.bk2` movies). **Zero** `AddUserInterfaces` / `ReplaceUIScript` /
`AddGameplayScripts` / Lua-file `ImportFiles` in any `FrontEndActions`.
Every official setup extension (all 8 game modes, all scenarios) flows through
config-database rows (`*ConfigData.xml` parameters) rendered by the shared
`AdvancedSetup` / `ScenarioSetup` drivers — never through custom frontend Lua.
An additive observer context therefore has no supported load channel; one would
have to replace `AdvancedSetup.lua` / `GameSetupLogic.lua` outright.

## 4. Architecture ranking

- **(A) Native SetupParameter decimal/range text-input constraint — not
  possible.** No float domain; `IntRange` is integer-slider-only; `text` has no
  validation entry point (evidence §2). Would require engine changes.
- **(B) Additive non-replacement frontend Lua observer using native popups —
  not supportable.** No official load channel exists (§3); in practice it
  degenerates into (C) (a file replacement) with identical conflict cost and
  speculative loading behavior.
- **(C) Start-button veto hook — high risk, low gain.** Veto state derives from
  a global error flag with no per-parameter custom-constraint channel (§2); any
  implementation replaces shared setup files, colliding 1:1 with UI-mod setup
  overrides (CQUI/YnAMP-style: single-winner file replacement — the same
  winner-takes-all semantics official `ReplaceUIScript` demonstrates in-game,
  e.g. `BarbarianClansMode` `PlotToolTip`/`UnitFlagManager` replacements).
  Breaks or gets broken by any other setup replacer; changes shared start-gating
  semantics.
- **(D) Additive visual warning only — same load problem as (B)** (no additive
  channel), and a warning that cannot block adds the least safety value.
- **(E) In-game one-time notification on map load via `AddGameplayScripts` —
  feasible and conflict-free, but post-commit.** Officially precedented (10
  `AddGameplayScripts` actions, e.g. `AlexanderScenarioScripts`; mode
  `AddUserInterfaces` Context `InGame`, e.g. `Heroes_InGameUI`). Fires after
  the user already committed to the setup, so it can only report "X10 did not
  arm", never prevent a wasted game. Complement at best.
- **(F) Current behavior only (visible range in label + tooltip + fail-closed +
  lifecycle log) — recommended.** Zero file conflicts (pure config-database
  rows), and safety is already enforced natively: every invalid custom input
  measured so far resolves to `writes DISABLED` with an explicit reason and
  `definitions_added=3336` official definitions untouched
  (`X10Lifecycle.1010-7C2-runE-*.log`). The only gap is UX (the user may not
  notice X10 didn't arm), addressable with label/tooltip wording + README/FAQ.

**Recommendation: (F).** Rationale: (A) is engine-impossible; (B)/(D) have no
supported load channel; (C) requires replacing shared setup files, guaranteeing
conflicts with UI-mod setup overrides for a veto the native error model cannot
even express for text params; (E) cannot act pre-game. (F) keeps 100% of the
measured safety (fail-closed reader, see `invalid_input_matrix.md`) at zero
compatibility cost. Optional future complement: (E) as a purely informational
post-load notice — never as a gate.

## 5. Safest pre-game UX (no code changes)

1. Label: `X10 — Custom multiplier (0 to 100)` (§1).
2. Tooltip/description: valid range 0–100; decimals need a **period**
   (`7.3` — comma rejected); blank = `0` = Off; anything else disables X10
   safely (no partial application); check `%TEMP%\X10Lifecycle.log` for the
   explicit reason.
3. Keep preset default ×10 Classic (`DefaultValue` INTEGER 10;
   `docs/UX_REVIEW.md` §16 — text `'10'` never `==`-matches integer domain
   values and falls back to the first row, Off).
4. Document in README/FAQ: "Custom must be 0–100" + fail-closed table
   (`invalid_input_matrix.md`).

## 6. Prototype built: none — why

No prototype mod files were written, per the task constraint and deliberately:
any pre-game enforcement prototype must replace `AdvancedSetup.lua` (no
additive channel, §3), prejudging architecture (C) that this research rejects
on compatibility grounds; the safety property it would demonstrate (invalid →
disabled) is already measured-live in `spike/validation-evidence/`
(`runE-invalid`, `runE-minus1`, `runE-101`). Nothing further can be learned
pre-game without game/Steam launches, which are out of scope.
