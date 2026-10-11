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
field `boolId` candidate), `...X10_MULTIPLIER...` absent-key control
(`found=false` if the pointer is null, or the UNSET type-0 shape — both
mean legacy-fallback permission, corrected 7C.1a §15).

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

## 14. Phase-7C.1a closure (visual verdict + measured variants)

Visual verdict (human screenshots reviewed): ACCEPTED — AdvancedOptions
positioning works; 2400–2408 block visually contiguous; native bool
checkboxes correct; repeated `X10 —` prefix acceptable; all seven labels
fit at 2560×1440; Custom dependency visibility works (field hides until
Custom… is selected); Governors/Suzerain long tooltips wrap readably; no
custom AdvancedSetup UI replacement warranted.

Open defects carried into the second prototype revision: preset
defaults to Off instead of ×10 (root cause §15, fixed); Custom shows
float32 noise `7.3000001907349` (investigation §16); mod-browser
multiplayer metadata wrong (root cause §17, fixed in prototype);
"semantic multiplier" too technical (renamed §9/§18).

## 15. Measured configuration variant table (scratch DLL 153344b7…b49d3d)

| key | stored | variant | type id | flags | decode |
|---|---|---|---|---|---|
| `X10_UX_PRESET` = Custom 101 | INT32 | integer scalar | 2 | 0 | 101 |
| `X10_UX_CUSTOM` = 7.3 | FLOAT32 | float scalar | 4 | — | 7.30000019073486 |
| `X10_UX_BOOL_*` = ON | integer scalar | bool-as-int | 1 | 0 | 1 |
| `X10_UX_BOOL_GOVERNORS` = OFF | integer scalar | bool-as-int | 1 | 0 | exact 0 |
| `X10_MULTIPLIER` (absent) | — | control | — | — | `found=false` |

Consequences: NO speculative direct bool payload decoding — bools arrive
through the proven integer path (type 1 ∈ verbatim engine int mask
`{1,2,3,4,5,17,18}`). With the documented type-name order
Bool,Int,UInt,Float and measured 1/2/4, type IDs are 1-based and type 0
is the null/unset sentinel (also absent from the engine int mask, so the
current reader can never misdecode it as INT32 0).

`TryGetConfigBool(key, out)`: require integer-decoded variant; accept
only exact 0/1 (covers legacy INT32 module params and new bool-checkbox
integer variants); reject all other numerics; present-but-malformed
fails closed.

### Unset/null reader-state model (7C.2)

- `ABSENT`: `FindConfigVariant()` returns null.
- `UNSET`: real variant pointer with type 0, flags 0 (payload observed
  zero; a type-0/flags-0 variant with nonzero payload is INVALID).
- `VALID`: decoded value in domain.
- `INVALID`: present but undecodable/out-of-domain/malformed.
- Absent OR unset preset → try legacy `X10_MULTIPLIER` path.
- Present-but-invalid preset → fail closed, never silent fallback.
- Narrow helper: `IsUnsetConfigVariant()` checking exactly the above.

### Reader API (7C.2)

`TryGetConfigScalar(...)`, `TryGetConfigBool(...)`,
`TryGetMultiplierPreset(...)` (accepts exactly 0,2,3,5,10,20,50,100,101
Custom — no other integer), `ResolveEffectiveMultiplier(...)`:
1. read new preset; 2. valid standard → use it; 3. Off → k=0/no writes;
4. Custom → require valid custom 0–100; 5. ABSENT/UNSET → legacy path
(INT32/FLOAT32 as proven); 6. present INVALID → fail closed. Stop
abusing `TryGetMultiplier()` per type. NOT implemented in 7C.1a.

## 16. Default-Off root cause and fix (prototype revision 2)

`SetupParameters.lua` coerces `DefaultValue` ONLY for `bool`/`int`/`uint`
domains; custom domains compare the RAW value with `==` against domain
`Value`s, falling back to the first valid row on mismatch (Firaxis's own
`-- blech! get the first valid value`). Our `DefaultValue '10'` is TEXT
while `DomainValues.Value 10` is INTEGER → Lua `"10" == 10` is false →
Off selected. This is NOT a first-row-default mechanism.
Fix (supported native mechanism, no reordering): store INTEGER `10`
(`Parameters.DefaultValue` is typeless; unquoted 10 persists as integer
and `==`-matches). Verified by test; proven live by second-review
screenshot B (fresh setup + Restore Defaults → ×10 Classic).

## 17. Custom-value precision and validation (driver evidence)

`AdvancedSetup.lua`: `int`/`uint`/`text` all render as the same string
edit box. `int` commits `tonumber(text)`; `uint` commits
`math.max(tonumber or 0, 0)` — SILENTLY coercing garbage to 0, which
disqualifies both for Custom (malformed input must fail closed, never
become 0). `text` commits the raw string; the FLOAT32 materialization
happens deeper in the config layer, and redisplay shows the widened
`7.3000001907349`. No numeric formatting, min/max, step, or Validate
hook exists anywhere in the setup framework (verified by source search).
A 1000-entry dropdown is banned by design review.

Decision: keep the `text` field (option D, and the ONLY option that
preserves malformed input for fail-closed handling). Document the
float-display artifact in user text. Native validation behavior for the
final control (enforced in native code, never clamp/round/silent-zero):
blank → the UI inserts INT32 0 before native sees it (measured live),
accepted as Off-equivalent, X10 disarmed; `abc` → TEXT variant, reject;
`-1`/`101` → INT32 out-of-range, reject; `0.5`/`7.3`/`100` → accept;
`0` → valid (Off-equivalent, no writes).
User fallback with no frontend error channel: Custom + invalid → X10
does not arm + explicit lifecycle-log reason + README/FAQ states
"Custom must be 0–100". Optional slider (`IntRange`) exists natively
but is integer-step — unsuitable for decimals.

## 18. Multiplayer metadata root cause (prototype revision 2)

SetupParameter support flags do NOT drive the Additional Content
`Multiplayer?` line (proven by screenshot). The root properties are
modinfo `<Properties>` tags `<SupportsSinglePlayer>` /
`<SupportsMultiplayer>` (official precedent: Alexander/CivRoyale/
Pirates/WarMachine scenario modinfos use exactly these). Prototype now
declares `<SupportsSinglePlayer>1</SupportsSinglePlayer>` +
`<SupportsMultiplayer>0</SupportsMultiplayer>`; second-review
screenshot A must show Single Player Yes / Multiplayer No. Production
modinfo adoption is 7C.2 (frozen in 7C.1a). Module controls stay
unsupported in LAN/Internet/Hotseat/Cloud via the parameter flags.

## 19. Second-revision prototype deltas (installed for re-review)

- Preset `DefaultValue` INTEGER 10 (§16).
- `SupportsSinglePlayer 1` / `SupportsMultiplayer 0` in prototype
  modinfo (§18).
- Custom presentation: text field retained with float-artifact wording
  (§17); no structural change (layout 2400–2408, defaults ON, tooltips
  unchanged per §10).
- Engine metadata: prototype is disposable; production engine targets
  recorded in `release/workshop-engine.md` (Name/Teaser/Description per
  brief; build details moved to SOURCE/README).
- Controller naming: `X10 — Configurable Bonus Multiplier` (+ teaser +
  short description) adopted in `release/workshop-controller.md` and the
  release manifest; production modinfo rename is 7C.2 (Mod IDs frozen).

Required second-review screenshots: A. Additional Content (SP Yes / MP
No). B. Fresh setup AND after Restore Defaults: ×10 Classic, custom
hidden, seven ON. C. Custom + 7.3 in the final presentation. If
precision cannot be improved natively (finding: it cannot — §17), the
human accepts the documented artifact. Re-run the scratch config probe
ONLY if a storage representation changes (it did not: same keys,
domains, and types).
