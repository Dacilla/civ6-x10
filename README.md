# Civ VI X10 — configurable semantic multiplier mod (prototype)

Civilization VI X10 is intended to be **one configurable mod/Workshop item**,
internally composed of independently tested gameplay components (traits,
policies, governments first; pantheons, governors, wonders, city-states
later).

> Status: prototype. The database generator and semantic transforms work and
> are tested; the native arbitrary-multiplier path is an in-progress
> experiment; controller packaging and Workshop release are not finalized.
> Nothing here claims in-game-tested functionality beyond what the docs mark
> LIVE GAME VERIFIED (currently: nothing beyond the audit's replay
> verification — see below).

## Architecture status

| Area | Status |
|---|---|
| Database generator (idempotent absolute-SET SQL) | working |
| Semantic transforms (canonical ×10, combat/probability/discount) | working / provisional by family |
| Community Extension dependency | accepted candidate / expected hard dependency |
| Arbitrary multiplier (e.g. 7.3×) | native prototype in progress |
| Controller packaging | not finalized until native prototype result |
| Steam Workshop release | not ready |

Details: `docs/ARCHITECTURE.md`. Development setup: `docs/DEVELOPMENT.md`.
Tests: `docs/TESTING.md`. Plan: `docs/ROADMAP.md`. CE research:
`docs/COMMUNITY_EXTENSION_EVALUATION.md`, `docs/DYNAMIC_MULTIPLIER_SPIKE.md`.

## Quick start (no game files needed)

```powershell
python -m pytest -q            # 35 unit tests, synthetic fixtures only
```

With the sibling audit workspace present (private Firaxis data, gitignored):

```powershell
python -m civ6x10 review --scope release1
python -m civ6x10 generate --module policies --out build/policies.sql
python -m civ6x10 verify --module policies --db data/local/DebugGameplay_official.sqlite
```

## License

AGPL-3.0 (see `LICENSE`). Third-party research sources: `THIRD_PARTY_NOTICES.md`.
