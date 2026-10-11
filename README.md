# Civ VI X10: Configurable Bonus Multiplier

Civilization VI X10 scales supported numeric bonuses by the multiplier
you choose, with per-module category controls. Install two Workshop
items: **X10: Configurable Bonus Multiplier** plus its required
**X10 CE Engine** dependency, and configure everything in Advanced
Setup (Windows x64 + Gathering Storm, single-player).

> Status: **all seven modules (traits, policies, governments, pantheons,
> wonders, governors, suzerain) are LIVE_VALIDATED in the 1010-entry
> production state** at stored FLOAT32 k=7.3 (see
> `docs/PRODUCTION_RELEASE.md` for per-module counters and
> `spike/validation-evidence/` for the archived native logs; the prior
> 971-entry slice evidence remains where explicitly historical). Phase 6C:
> Run A 801 writes / 209 refusals, Run B 698 / 174 / 138. Phase 7C.2
> migrates setup to a native preset/checkbox UI (same 1010 gameplay set).
> Controller packaging is functionally complete locally; **Steam Workshop
> release is not ready** pending the public-data hygiene step.

## Architecture status

| Area | Status |
|---|---|
| Database generator (idempotent absolute-SET SQL) | working |
| Semantic transforms (canonical ×10, combat/probability/discount) | working / per-family certified |
| Semantic certification gate (sem floor + curated overrides) | working |
| Community Extension dependency | implemented (CE-X10 engine mod) |
| Arbitrary multiplier (e.g. 7.3×, 0 = Off) | **LIVE_VALIDATED** |
| Module ownership (bitmask, shared-definition rule) | 7 modules, all LIVE_VALIDATED (bit 64 = suzerain) |
| Controller packaging | local production candidate assembled (`spike/assemble-prod-test.ps1`) |
| Steam Workshop release | not ready |

Details: `docs/ARCHITECTURE.md`. Development setup: `docs/DEVELOPMENT.md`.
Tests: `docs/TESTING.md`. Plan: `docs/ROADMAP.md`. Audits:
`docs/WONDER_AUDIT.md`, `docs/PANTHEON_AUDIT.md`, `docs/GOVERNOR_AUDIT.md`,
`docs/SUZERAIN_AUDIT.md`, `docs/SEMANTIC_CERTIFICATION.md`. CE research:
`docs/COMMUNITY_EXTENSION_EVALUATION.md`, `docs/DYNAMIC_MULTIPLIER_SPIKE.md`,
`docs/NATIVE_HOOK_VALIDATION.md`.

## Quick start (no game files needed)

```powershell
python -m pytest -q            # full suite (359 tests at last count);
                               # DB-backed groups skip cleanly without
                               # private data (CI runs this)
```

With the sibling audit workspace present (private Firaxis data, gitignored):

```powershell
python -m civ6x10 review --scope release1
python -m civ6x10 generate --module policies --out build/policies.sql
python -m civ6x10 verify --module policies --db data/local/DebugGameplay_official.sqlite
```

## License

AGPL-3.0 (see `LICENSE`). Third-party research sources: `THIRD_PARTY_NOTICES.md`.
