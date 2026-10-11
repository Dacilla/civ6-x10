# X10: Configurable Bonus Multiplier (v1.0.0-rc2 clean snapshot)

X10 scales Civilization VI bonuses by the multiplier
you choose instead of fixed hand-tuned numbers.

## What you install (two Workshop items)

- **X10: Configurable Bonus Multiplier** (controller): setup,
  configuration, guarded SQL bridge, user documentation.
- **X10 CE Engine** (required dependency): the GameCore replacement that
  performs the scaling at runtime. Subscribe to both; configure
  only the controller.

## Using it (single-player Gathering Storm)

1. Subscribe to the controller item; Steam also installs the required
   X10 CE Engine.
2. Make sure no other Community Extension/GameCore replacement is
   enabled.
3. Create a new single-player Gathering Storm game.
4. Open Advanced Setup.
5. Choose **X10: Multiplier** (×10 Classic is the default); choose
   **Custom** for values from 0 to 100 (decimals use a period).
6. Leave all seven category checkboxes on, or uncheck anything you
   want to keep unchanged.
7. Start the game.

Whole-unit bonuses such as charges, power, and granted resources
apply only for exact whole-number results; otherwise they keep their
normal values instead of rounding. Some effects stay unchanged because
multiplying them would not give a reliable result. Leaving Custom
blank enters 0 (Off-equivalent).

Requirements: Windows x64, Gathering Storm. Incompatible with any
other active Community Extension / GameCore replacement. X10 affects
saved games: choose settings when creating the campaign.

## Source/build architecture

- `civ6x10/` - generator, semantic certification gate, transforms.
  Bulk game-data audits are NOT in this snapshot (private inputs).
- `civ6x10/rules/` - the curated rule files the gate actually evaluates.
- `controller/`, `dependencies/` - the exact Workshop text sources.
- `data/fixtures/` - synthetic CI fixtures (no official game data).
- `tests/` - reviewed subset; everything here passes or skips cleanly
  (DB/audit-dependent tests are omitted, never weakened).
- `release/` - manifest (all staged hashes), assembler, VALIDATION,
  BUILDING, Workshop drafts. `release/out/` staging is generated, never
  committed.
- `LICENSE`, `THIRD_PARTY_NOTICES.md`, `PROVENANCE.md`.

Validated release: registry 1010 entries / 1006 definitions; preset
×10 = 1010 writes; Custom 7.3 = 801/209; Governors OFF = 745/195/70;
Off disarmed; invalid Custom entries are rejected. Details in
`release/VALIDATION.md`; provenance in `PROVENANCE.md`.
