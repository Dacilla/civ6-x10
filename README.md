# Civ VI Overpowered Bonuses

Civilization VI Overpowered Bonuses creates deliberately overpowered
builds by multiplying Civilization VI bonuses, with per-module
category controls. Install two Workshop items:
**Overpowered Bonuses** plus its required
**Overpowered Bonuses CE Engine** dependency, and configure everything
in Advanced Setup (Windows x64 + Gathering Storm, single-player).

> Note: `X10` is the project's historical/internal namespace (config
> keys, source symbols, log/registry filenames). The public v1.0
> product is **Overpowered Bonuses**.

> Status: **Phase 8B (Playtest-1 closure) is under pre-publication
> gameplay validation.** The registry grew to the 2481-entry production
> set (13 modules: traits, policies, governments, pantheons, wonders,
> governors, suzerain/city-state, promotions, dedications, modes,
> religion, greatpeople, projects; see `docs/PHASE_8B.md`). The prior
> 1010-entry state remains where explicitly historical (RC2 matrix,
> `spike/validation-evidence/`). **Steam Workshop release is not
> ready** pending Playtest-2 validation.

## Architecture status

| Area | Status |
|---|---|
| Database generator (idempotent absolute-SET SQL) | working |
| Semantic transforms (canonical ×10, combat/probability/discount) | working / per-family certified |
| Semantic certification gate (sem floor + curated overrides) | working |
| Community Extension dependency | implemented (CE-X10 engine mod) |
| Arbitrary multiplier (e.g. 7.3×, 0 = Off) | **under 8B validation** |
| Module ownership (bitmask, shared-definition rule) | 13 modules (bit 4096 = projects) |
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
