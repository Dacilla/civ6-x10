# UX Review (Phase 7C.1 — audit/design + disposable prototype)

The mod is technically correct but setup is developer-oriented. This
document inventories every ordinary-player surface, records the target
design proven by the disposable prototype
(`spike/X10_UX_Prototype/`, Mod ID `880f3337-...`, X10_UX_* keys only),
and defines the 7C.2 implementation plan. Nothing here changes
production (`controller/X10`, DLL `e33d84b8…d619`, registry 1010).

## 1. User-journey inventory (severity classified)

### Blockers (must fix before public release)
1. **Multiplier is a raw text field** (`X10_MULTIPLIER`, Domain text, GameOptions).
   Ordinary players must discover the key name, type an exact decimal, and
   know 0 means Off. No presets, no guidance, no validation feedback.
2. **Module toggles are seven INT32 text-ish rows** with internal names.
   No checkboxes, no grouping, no plain-language meaning.
3. **Setup location is generic GameOptions** (default SortIndex 100):
   X10 rows float wherever the UI puts unsorted game options instead of
   sitting together under Advanced Setup.
4. **No localization architecture**: Name/Description are raw English
   strings in SQL, so community translation requires editing config SQL
   and the setup screen bypasses Civ VI text conventions.
5. **Multiplayer scope undeclared**: support flags unset (schema defaults
   happen to be SP-inclusive), so the UI implies an unvalidated mode.
6. **Saved-game wording suggests mid-campaign editing** ("toggling ...
   mid-campaign changes definition values"); parameters are game-creation
   settings and must be presented that way.

### Important polish (7C.2 scope)
7. Workshop/mod-browser metadata is terse; Name/Teaser must sell the
   two-item model in one line each (proposals §5).
8. `(Not compatible)` label: fixed in 7B.2a via `CompatibleVersions=2.0`
   (matches the Gathering Storm dependency; presentation only).
9. Duplicate-mod confusion seen in 7B.1 smoke (stale Mods copies sharing
   Mod IDs) → installer now refuses in-Mods backups; user docs must still
   say "exactly two X10 folders".
10. Troubleshooting expects native counters; rewrite for symptoms
    (proposed FAQ §8).
11. README/Workshop drafts still carry certification vocabulary
    (`X10_MULTIPLIER`, module bit language) as primary text (§9 audit).

### Optional future (not 7C.2)
12. In-game status widget: evaluated, default NO — Advanced Setup is the
    proper surface; a widget adds UI-mod conflict risk for no validated
    benefit. Revisit only with a proven no-conflict native hook.
13. Hiding the engine mod (`ShowInBrowser=AlwaysHidden`): NO local
    precedent found (zero of ~12 Workshop + all official DLC modinfos use
    it), so dependency-pull/action-loading behavior while hidden is
    unproven. Keep the engine visible with a `Required dependency — no
    settings` teaser. Never use `EnabledAtStartup`.

## 2. Installed framework capabilities (local ground truth)

Source: installed Gathering Storm `Configuration/Data/SetupParameters.xml`
+ `Schema/SetupParameters.sql` (not internet examples).

- Custom domains via `DomainValues(Domain, Value, Name, Description,
  SortIndex)`; dropdown rendering is the standard path for named domains
  (cf. StandardDifficulties). No `UxHint` needed for a plain dropdown.
- Conditional visibility via `ParameterDependencies(ParameterId,
  ConfigurationGroup, ConfigurationId, Operator, ConfigurationValue)`
  (official pattern: AlexanderScenario gates Resources/StartPosition with
  `Operator="NotEquals"`). Prototype uses `Equals 101` for the custom
  field; the human screenshot run proves whether the UI honors it, with
  the always-visible fallback already worded in.
- `GroupId='AdvancedOptions'` is the native advanced section (official
  SortIndex 2000–3020); prototype block 2400–2408 verified free.
- `Domain='bool'` renders native checkboxes (official: PrivateGame,
  NoDupeLeaders, ...). No radio-boolean workaround needed.
- Support flags default 1 (`Supports*`) / 0 (`ChangeableAfterGameStart`):
  explicit `1,0,0,0,0,0` + `ChangeableAfterGameStart=0` is a deliberate
  statement, not a behavior change — but stated explicitly so a schema
  default change can never silently widen scope.
- FrontEnd `UpdateDatabase` (config SQL) + `UpdateText` (text SQL) is the
  standard mod packaging (observed in Workshop mods); no UI replacement.

## 3. Proposed final Advanced Setup layout (contiguous, prefixed)

Group `AdvancedOptions`, SortIndex block 2400–2408 (reconfirm free at
implementation time):

| order | control | key (final) |
|---|---|---|
| 2400 | dropdown `X10 — Multiplier` (Off/×2/×3/×5/×10 Classic/×20/×50/×100/Custom…; default ×10) | `X10_MULTIPLIER_PRESET` |
| 2401 | text `X10 — Custom multiplier` (visible iff Custom; fallback wording retained) | `X10_MULTIPLIER` (unchanged) |
| 2402–2408 | bool checkboxes, all default ON (labels §4) | `X10_MODULE_*` (unchanged) |

Preset values: `0,2,3,5,10,20,50,100` + Custom sentinel provisionally
`101` (valid ONLY if the scratch run proves safe scalar storage).

## 4. Labels and tooltips (player language; §12 wording adopted verbatim
in the prototype text SQL; adjust only for measured wrapping issues)

Module labels: `X10 — Civilization & leader traits`, `X10 — Policy
cards`, `X10 — Governments`, `X10 — Pantheons`, `X10 — Wonders`,
`X10 — Governors & Secret Societies`, `X10 — City-State Suzerain
bonuses`. Tooltips per the Phase-7C.1 brief (traits/policies/
governments-shared-rule/pantheons-scope/wonders-structural/governors-
mode-gating/suzerain-unlocks).

## 5. Mod-browser metadata (prototype values; production in 7C.2)

- Controller: Name `X10 - Configurable Semantic Multiplier`, Teaser
  `Choose a multiplier and scale supported Civ VI bonuses by category.
  Requires X10 CE Engine.` Retain `CompatibleVersions=2.0`.
- Engine: Name `X10 CE Engine`, Teaser `Required engine dependency for
  X10. No settings here; use the main X10 mod.`
- Authors: add ONLY the project's chosen public identity; never invent
  a personal real name (currently absent — acceptable).
- Description stays for metadata/source readers, never the sole summary.

## 6. Saved-game wording (target)

`X10 affects saved games. Choose your X10 settings when creating the
game; changing X10 configuration for an existing campaign is not
supported.` Keep `AffectsSavedGames=1`.

## 7. Scope statement (target, all surfaces)

`Single-player supported and validated. Multiplayer/Hotseat/Play-by-
Cloud are not supported in v1.0.` (No claim about engine behavior —
simply unadvertised and unexposed.)

## 8. Troubleshooting FAQ (target text for README/Workshop)

- **Nothing changed** → both X10 items enabled; no other GameCore/
  Community Extension replacement active; Multiplier not Off.
- **One bonus stayed normal** → whole-unit fractional result, or an
  intentionally unscaled/ambiguous mechanic (see KNOWN_ISSUES.md).
- **Secret Society bonuses unchanged** → the Secret Societies game mode
  must be enabled (mode-gated definitions only exist with it).
- **Change settings in an existing save?** → not supported; choose at
  new-game creation.
- **Log?** → `%TEMP%\X10Lifecycle.log`, for troubleshooting/support
  (no counter literacy expected).

## 9. Vocabulary audit (release/public surfaces)

Banned as primary user language (may remain in BUILDING/VALIDATION/dev
docs): `X10_MULTIPLIER`, `X10_MODULE_*`, `CERTIFIED`, `semantic floor`,
`owners`, registry counts as marketing, `ModifierId`,
`transform-refused`. Remaining instances: private README references
`X10_MULTIPLIER` in status-adjacent prose (7C.2 doc rewrite); Workshop
drafts already clean; KNOWN_ISSUES clean.

## 10. Native variant evidence (pending human run)

Disposables installed: prototype mod + scratch DLL
`153344b7…b49d3d` (pin `spike/UX_PROBE_DLL_SHA256.txt`; ≠ production).
Expected log lines per key: `CONFIG key=X10_UX_PRESET ...` (preset
storage type — int vs text decides the reader), `...X10_UX_CUSTOM...`
(text payload shape), `...X10_UX_BOOL_TRAITS...` ON +
`...X10_UX_BOOL_GOVERNORS...` OFF (bool type id/flags/payload; profile
field `boolId` candidate), `...X10_MULTIPLIER... found=false` (control).

## 11. Screenshot + run instructions (for the human)

Profile: disposable. Mods: DISABLE Workshop CE, controller, all probes;
ENABLE X10 CE Engine (scratch) + X10 UX Prototype. Game: Gathering
Storm, ROME/Trajan, Small, 2 AI (Secret Societies ON for a populated
Advanced Setup screen state is optional — definitions are display-only
here; the config run uses the same setup).
A. Additional Content screen (prototype Name/Teaser presentation).
B. Advanced Setup at defaults (×10 Classic, custom hidden?, seven
   checked checkboxes, contiguous X10 block).
C. Custom… selected, custom `7.3`, Governors OFF.
D. Multiplier tooltip visible. E. Suzerain or Governors tooltip visible.
Then: new game → reach map (no save/reload) → send
`%TEMP%\X10Lifecycle.log`. Then: run `spike/restore-prod-rc.ps1`.

## 12. 7C.2 implementation plan (evidence-contingent)

If the probe confirms bool/int-or-text storage as expected:
preset/custom effective-k reader (`X10_MULTIPLIER_PRESET` + legacy
`X10_MULTIPLIER` fallback, fail-closed malformed handling, Off→untouched);
strict `TryGetConfigBool` (proven BOOL + legacy INT32 0/1, else
fail-closed) with profile `boolId`; native Advanced Setup migration
(2400-block, LOC text, bool checkboxes, SP-only flags); modinfo
Teasers; doc rewrite (README/Workshop/KNOWN_ISSUES/UX); assembler +
export updates; new CE DLL; new RC `1.0.0-rc2`.
Fallbacks: (2) native On/Off dropdowns if bool unprovable; (3) always-
visible custom field if dependency ignored; (4) custom Lua only with
explicit review. Redesign from observed values on any surprise.

## 13. 7C.2 validation matrix (predefined, NOT run)

- Run 1: preset ×10, all ON → 1010 writes / 0 refusals.
- Run 2: Custom 7.3, all ON → 801 / 209 (exact 6C reproduction).
- Run 3: Custom 7.3, Governors OFF → 745 / 195 / 70 owner-32 skips.
- Optional Run 4: preset Off → disarmed, zero mutations.
- Final exact RC gets a probe-free save/reload smoke.
