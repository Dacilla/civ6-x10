# UX copy style guide (Phase 7C.2a)

Primary source: 4,878 sampled official en_US strings (setup, modes,
victories, governors, policies, traits, beliefs, city-states, frontend),
plus 14 installed Workshop item names/teasers. Style characteristics
only; no Firaxis text is quoted or copied here.

## Labels

- Title Case short noun phrases, no terminal punctuation:
  "Game Difficulty", "Suzerain Bonuses", "Policy Card",
  "Start Position", "Pantheon Beliefs".
- Field labels use colons: "Required Government Tier:", "Pantheon:",
  "Envoys Sent:". Our `X10: ...` label convention matches this.
- Proper nouns capped ("World Wonder", "Secret Society"); generic nouns
  lowercase in sentences ("world wonder {name}", "city-state",
  "of which you are suzerain", "One extra Wildcard policy slot").

## Tooltips and descriptions

- Full sentences, median 9 words; ~54% end with a period. Labels never do.
- Descriptive, not imperative (under 1% start with Choose/Select/Enable).
  Second person ("you", "your") is normal.
- Caveats use "Does not affect X" or parenthetical mechanics notes
  ("(Cannot make peace.)"), never hedging paragraphs.
- Rarely used: em dash ~1%, semicolons ~5%, ellipsis ~3%, parens ~13%
  (mostly mechanics). Prefer colon, comma, period, or a shorter sentence.

## Workshop items (installed sample)

- Short functional sentences: "Buff all wonders by ten times.",
  "Shows more info in Tech and Civics Trees." No hype, no caps shouting.

## Decisions applied to X10 copy

- Colon labels (`X10: Multiplier`), never em-dash labels.
- "Policy slots" lowercase in sentences; "World Wonder" capped;
  "Unique Units"/"Improvements" plain (corpus has no "intrinsic stats").
- Caveats as "Does not affect ..." sentences.
- Preset names bare ("×10 Classic", no parens); "Custom..." with three
  periods (Firaxis ellipsis style), never ….
- Descriptions vary verbs (doubles/triples/multiplies) instead of
  repeating one template eight times.
- Humanizer skill used as lint only (report in UX_REVIEW); Civ
  terminology overrode generic suggestions throughout.
- stop-slop skill: not available in this harness; not used.

## Humanizer lint report (7C.2a)

Surfaces linted: X10Text.sql display values, both modinfo Name/Teaser/
Description, both packaged READMEs, both Workshop drafts, KNOWN_ISSUES,
README-public, CHANGELOG current entry.

- ACCEPT (applied while drafting): em/en dashes removed from all
  player copy; ellipsis characters replaced with three periods;
  semicolon-joined clauses split into sentences; preset descriptions
  de-templated (doubles/triples/multiplies-by-N); tooltip voice kept
  descriptive (corpus: <1% imperative); no contractions added;
  caveats kept ("Does not affect ...", Off behavior, blank-custom rule).
- REJECT (Civ terminology/style wins): keeping formal register instead
  of conversational prose; keeping "Suzerain"/"Pantheon"/"Beliefs"
  capitalization; keeping parallel "Apply the X10 multiplier to ..."
  openings (each names a distinct category; merging would lose the
  per-checkbox mapping).
- REJECT (caveat removal): no behavior caveat was dropped for tone.
- MANUAL (Civ-specific rewrite applied): "official values" becomes
  "normal values" or "unchanged"; "intrinsic stats" becomes plain
  "Unique Units or Improvements"; "structural values" becomes "Does
  not affect ..." sentences; "semantic multiplier" becomes "Bonus
  Multiplier" in player surfaces only.
- stop-slop: no such skill in this harness; the banned-term sweep
  (em/en dash, ellipsis, semicolons, jargon list) served instead.

## 7C.2a.1 cleanup (parallel presets, descriptive modules)

- Preset descriptions use one parallel settings-menu pattern
  ('Sets the multiplier to ×N.' / 'Disables X10.' /
  'Uses the custom multiplier below.') instead of varied verbs.
- Module tooltips are descriptive ('... use the X10 multiplier.')
  instead of imperative ('Apply ...'); caveat sentences unchanged.
- Workshop HOW paragraph rewritten in player language (no 'discount
  maths' / 'combat scaling' / 'anything left over' / 'safely');
  technical source docs keep exact transform terminology.
- Banned-phrase lint extended (test_no_player_surface_banned_phrases):
  'supported bonuses', 'content populates', 'floating-point noise',
  'discount maths', 'combat scaling', 'Anything left over',
  'Apply the X10 multiplier'. Zero hits expected in player surfaces.

## 7C.2a.2 public brand (Overpowered Bonuses)

- Public product: **Overpowered Bonuses**; engine: **Overpowered
  Bonuses CE Engine**. X10 is the historical/internal namespace only
  (LOC_X10_* keys, X10_* config IDs, X10Lifecycle.log,
  X10ProductionRegistry.inc, source symbols, Mod IDs, folder names,
  validation tags). Internal identifiers were NOT renamed.
- Setup labels are product-name neutral: no product prefix. Categories
  use the 'Affects: ...' pattern so the block reads as one scoped list
  under 'Bonus Multiplier'. Preset names ('x10 Classic' notation) are
  not branding and are unchanged.
- Tooltips say 'the selected multiplier', never 'the X10 multiplier'.
- Preset Off description is 'Disables the multiplier.'
- Controller teaser is mechanical (range + categories) under the
  expressive product name; the Workshop opening positions the mod as
  deliberately-overpowered builds, not a balance utility.
