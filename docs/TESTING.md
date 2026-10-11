# Testing

CI-safe: `python -m pytest -q` runs the full suite (358 tests); DB-backed
groups skip cleanly without private data.

Levels used in this project:

- **UNIT TESTED**: pure-python behavior (transforms, config, generator,
  validation fixtures, synthetic audit fixtures).
- **STATICALLY VERIFIED**: manifest/SQL properties checked without the game
  (no relative SETs, idempotent reapply on scratch DB copies; certification
  gate, registry parity, packaging/ownership invariants).
- **LIVE VALIDATED**: requires Civ VI. The production native definition
  mutation path is live-validated for the 971-entry slice covering all seven modules at stored FLOAT32
  k=7.3 in both ON and OFF module states (Run A 786 writes / 185 refusals,
  Run B 748 / 176 + 47 ownership skips; save/reload identical; evidence in
  `spike/validation-evidence/`). The Phase-6B 1010-entry build is CERTIFIED with static expectation
  801 writes / 209 refusals at k=7.3 and awaits Phase-6C targeted live validation (`tests/test_phase6b_production.py`).
- **Disposable probes** (`spike/X10_Probe_Test/probe.lua`, never production)
  are still used for new semantic/storage questions — e.g. whether a
  held-out identity-pressure definition has become observable through the
  current store-lookup mechanism.
- **Unresolved families are not production-approved**: rows the audits leave
  `DECISION_REQUIRED` / `EXCLUDED` never enter the registry, however
  obviously scalable they look; the closed-world gate fails loudly instead.
