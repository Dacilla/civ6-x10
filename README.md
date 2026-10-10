# Civ VI X10 — configurable semantic multiplier mod

Civilization VI X10 is **one configurable mod/Workshop item**, internally
composed of independently tested gameplay components. A Community Extension
replacement GameCore performs the arbitrary multiplier at runtime; the
controller carries configuration plus a generated, guarded SQL fallback and
a direct-table bridge.

> Status: **traits, policies, governments, pantheons, wonders and governors
> are LIVE_VALIDATED** at stored FLOAT32 k=7.3 (see
> `docs/PRODUCTION_RELEASE.md` for per-module counters and
> `spike/validation-evidence/` for the archived native logs). City-states /
> suzerain is audited (Phase 5A) but not yet produced.  Controller packaging is functionally complete
> locally; **Steam Workshop release is not ready** pending the public-data
> hygiene step.

## Architecture status

| Area | Status |
|---|---|
| Database generator (idempotent absolute-SET SQL) | working |
| Semantic transforms (canonical ×10, combat/probability/discount) | working / per-family certified |
| Semantic certification gate (sem floor + curated overrides) | working |
| Community Extension dependency | implemented (CE-X10 engine mod) |
| Arbitrary multiplier (e.g. 7.3×, 0 = Off) | **LIVE_VALIDATED** |
| Module ownership (bitmask, shared-definition rule) | **LIVE_VALIDATED** (6 modules, bit 32 = governors) |
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
python -m pytest -q            # 223+ tests; DB-backed groups skip
                               # cleanly without private data (CI runs this)
```

With the sibling audit workspace present (private Firaxis data, gitignored):

```powershell
python -m civ6x10 review --scope release1
python -m civ6x10 generate --module policies --out build/policies.sql
python -m civ6x10 verify --module policies --db data/local/DebugGameplay_official.sqlite
```

## License

AGPL-3.0 (see `LICENSE`). Third-party research sources: `THIRD_PARTY_NOTICES.md`.
