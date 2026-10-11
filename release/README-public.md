# X10 — configurable Civilization VI semantic multiplier (v1.0.0-rc1)

X10 scales certified numeric game effects (yields, bonuses, discounts,
loyalty pressure, ...) by the multiplier you choose instead of fixed
hand-tuned numbers.

## What you install (two Workshop items)

- **X10 — Configurable Semantic Multiplier** (this release's controller):
  configuration, guarded SQL bridge, user documentation.
- **X10 CE Engine** (required dependency): the GameCore replacement that
  performs the transformation at runtime. Subscribe to both; configure
  only the controller.

The engine does nothing without the controller, and the controller does
nothing without the engine.

## Using it

Multiplier `X10_MULTIPLIER` 0–100 (default **10**; **0 disables** the
multiplier). Seven module toggles — traits, policies, governments,
pantheons, wonders, governors, suzerain — default ON.

Whole-unit bonuses (charges, power, granted resources, ...) apply only
for exact whole-number results: a fractional result keeps its official
value instead of rounding. Deliberately ambiguous mechanics (healing
caps, factor-vs-percent scaling, improvement intrinsics, ...) stay
vanilla; see `release/KNOWN_ISSUES.md`.

Requirements: Windows x64, Gathering Storm. Incompatible with any other
active Community Extension / GameCore replacement.

## Source/build architecture

- `civ6x10/` — generator, semantic certification gate, transforms.
  Bulk game-data audits are NOT in this snapshot (private inputs).
- `civ6x10/rules/` — the curated rule files the gate actually evaluates.
- `controller/`, `dependencies/` — the exact Workshop text sources.
- `release/` — manifest (all staged hashes), assembler, VALIDATION,
  BUILDING, Workshop drafts. `release/out/` staging is generated, never
  committed.
- `tests/` — reviewed subset; everything here passes or skips cleanly
  (DB/audit-dependent tests are omitted, never weakened).

Validated release: registry 1010 entries / 1006 definitions; Run A 801
writes / 209 refusals; Run B 698 / 174 / 138 ownership skips. Details in
`release/VALIDATION.md`; provenance in `PROVENANCE.md`.
