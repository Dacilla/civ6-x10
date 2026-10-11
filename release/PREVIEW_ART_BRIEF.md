# Workshop preview art brief (HUMAN/CONTENT task — not started)

Two 1024×1024 preview images are the only remaining local content
blocker for publication (see `release/PUBLISH_CHECKLIST.md`). Do NOT
generate art in a coding phase; this brief is for the human artist.

Working target: 1024×1024 square. Final Workshop file: PNG under 1 MB.
Hard requirement: thumbnail readability — each image must communicate
at small mod-browser thumbnail size, not just at full size.

## Controller preview — `release/preview-controller.png`

Must communicate at thumbnail size:
- `Overpowered Bonuses` (readable title: `OVERPOWERED BONUSES`)
- absurdly amplified Civ VI bonuses
- the multiplier concept

Avoid: tiny paragraphs, source/build text, huge lists of categories.

Suggested concept direction: a Civilization-VI-inspired but original
composition featuring exaggerated yield/bonus icons and a prominent
multiplier motif (e.g. a large ×10-style mark), with the readable
title `OVERPOWERED BONUSES`.

Do NOT copy Firaxis copyrighted artwork directly from game assets
unless the human explicitly chooses to use screenshots/game imagery
under the Workshop's normal mod presentation context. Prefer original
graphic treatment.

## Engine preview — `release/preview-engine.png`

Same visual family as the controller image, but it must be obvious at
thumbnail size that this is NOT the main mod. Must clearly say:

- `OVERPOWERED BONUSES`
- `CE ENGINE`

and visually communicate `Required Dependency` (e.g. a subordinate
lock/cog/link treatment — quieter than the main item).

Do not make the dependency thumbnail more visually prominent than the
main item.

## Acceptance (human)

- Both files exist at `release/preview-controller.png` and
  `release/preview-engine.png`, PNG, under 1 MB, ≥512x512
  (1024×1024 square recommended).
- Titles legible at thumbnail size; engine item reads as a dependency.
- No Firaxis assets copied without an explicit human decision.
- The `-PublishReady` assembler gate requires these files; publish-ready
  generation is correctly blocked until they exist.
