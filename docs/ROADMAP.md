# Roadmap

## Live-validated components (stored FLOAT32 k=7.3, per-module counters in
`docs/PRODUCTION_RELEASE.md`)

1. traits / policies / governments - **LIVE_VALIDATED**
   (684-entry Release-1 registry, tag `release1-684-live-validated`).
2. pantheons - **LIVE_VALIDATED** (+31 rows, tag `phase2-715-live-validated`,
   audit `docs/PANTHEON_AUDIT.md`).
3. wonders - **LIVE_VALIDATED** (+97 modifier-backed rows plus the guarded
   direct-table bridge, tag `phase3-813-live-validated`, audit
   `docs/WONDER_AUDIT.md`).
4. governors - **LIVE_VALIDATED** (Phase 4B + 4C, +54 rows for 924 total,
   owner bit 32, tag `phase4b-924-live-validated`, audit
   `docs/GOVERNOR_AUDIT.md`).

## In progress

5. **Suzerain / City-States (Phase 5)** - Phase 5A is a closed-world semantic
   audit only: authoritative active City-State discovery from the official
   runtime DB, recursive modifier-graph traversal, per-argument disposition,
   unique-improvement / unique-unit side-path inventory, legacy x10 coverage
   comparison, and a proposed owner bit (`64 = suzerain`, next free `128`).
   No production rows, no bit 64, no native change, no live test until the
   audit is reviewed - see `docs/SUZERAIN_AUDIT.md` and
   `civ6x10/rules/suzerain_audit.yml`. Phase 5B is the reviewed production
   slice.

## Remaining work

6. Unresolved semantic backlog (still open after Phase 5):
   - 29 reachable + 24 direct/structural Governor decisions deliberately left
     out of Phase 4B (`docs/GOVERNOR_AUDIT.md`).
   - Regional entertainment / Sanguine / Laying-on-Hands style
     decision-required families.
   - Loyalty / identity pressure stored-form hold (Toqui class) re-certification
     via the store-lookup witness.
   - Negative-strength combat (canonical `b_k` transform undefined) and the
     probability family.
   - Factor-versus-percent scaling families (`ScalingFactor`, tourism,
     multiplicative mirrors).
7. Optional later modules: beliefs, great people, promotions.
8. **Public-data hygiene / Steam Workshop release - still pending.** Nothing is
   published to the Workshop: the local package must be re-checked for
   Firaxis-sourced data, and the AGPL-3.0 dependency on the Community
   Extension must be accepted before any publish.
