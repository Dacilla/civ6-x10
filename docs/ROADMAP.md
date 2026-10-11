# Roadmap

## Live-validated components (stored FLOAT32 k=7.3, per-module counters in
`docs/PRODUCTION_RELEASE.md`)

1. traits / policies / governments - **LIVE_VALIDATED**   (684-entry Release-1 registry, tag `release1-684-live-validated`).
2. pantheons - **LIVE_VALIDATED** (+31 rows, tag `phase2-715-live-validated`,
   audit `docs/PANTHEON_AUDIT.md`).
3. wonders - **LIVE_VALIDATED** (+97 modifier-backed rows plus the guarded
   direct-table bridge, tag `phase3-813-live-validated`, audit
   `docs/WONDER_AUDIT.md`).
4. governors - **LIVE_VALIDATED** (Phase 4B + 4C, +54 rows for 924 total,
   owner bit 32, tag `phase4b-924-live-validated`, audit
   `docs/GOVERNOR_AUDIT.md`).
5. **Suzerain / City-States - LIVE_VALIDATED as the 47-row slice**
   (Phase 5A.1 audit + Phase 5B production integration + Phase 5C live
   validation, +47 rows for 971 total, owner bit 64, tag
   `phase5b-971-live-validated`, audit `docs/SUZERAIN_AUDIT.md`).
   **Phase 6B extends Suzerain to 68 rows** (+21 backlog rows incl. Lahore
   COMBAT and Valletta DISCOUNT x3) **and Governors to 70 rows** (+16),
   plus 2 re-admitted Toqui traits rows: **1010 total, LIVE_VALIDATED**
   (Phase 6C, tag `phase6b-1010-live-validated`; Run A 801 writes / 209
   refusals, Run B 698 / 174 / 138).
   Still open: ScalingFactor rows, direct Governor IdentityPressure
   columns, unique-improvement intrinsics, Nihang intrinsics/progression,
   Sanguine -5, healing, Kandy scaling and other held side paths
   (narrow improvement ownership stays adopted).

## Remaining work

6. Phase 6C targeted live validation of the 1010 build — **DONE 2026-10-11**
   (39 new rows, 3 write-to-refusal corrections, Toqui-from-traits,
   Valletta DISCOUNT, Lahore COMBAT, strong-family overrides, module ON/OFF
   isolation all pass; see `docs/PRODUCTION_RELEASE.md`).
7. Unresolved semantic backlog remainder (still open after Phase 6B):
   - 29 reachable + 24 direct/structural Governor decisions deliberately left
     out of Phase 4B (`docs/GOVERNOR_AUDIT.md`).
   - Regional entertainment / Sanguine / Laying-on-Hands style
     decision-required families.
   - Negative-strength combat (canonical `b_k` transform undefined) and the
     probability family.
   - Factor-versus-percent scaling families (`ScalingFactor`, tourism,
     multiplicative mirrors).
8. Optional later modules: beliefs, great people, promotions.
9. **Public-data hygiene / Steam Workshop release - still pending.** Nothing is
   published to the Workshop: the local package must be re-checked for
   Firaxis-sourced data, and the AGPL-3.0 dependency on the Community
   Extension must be accepted before any publish.
