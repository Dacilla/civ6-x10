# Testing

CI-safe: `python -m pytest -q` needs only synthetic `data/fixtures/`.

Levels used in this project:

- **UNIT TESTED**: pure-python behavior (transforms, config, generator,
  validation fixtures). 35 tests.
- **STATICALLY VERIFIED**: manifest/SQL properties checked without the game
  (no relative SETs, idempotent reapply on scratch DB copies).
- **LIVE GAME VERIFIED**: requires Civ VI. Only the audit's replay
  verification currently holds this status (21394 MATCH / 0 MISMATCH).
  The CE write path is NOT live-verified; the manual checklist lives in
  `docs/DYNAMIC_MULTIPLIER_SPIKE.md`.
