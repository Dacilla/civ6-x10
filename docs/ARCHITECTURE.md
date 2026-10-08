# Architecture

One configurable Workshop item, independently tested components.

ARBITRARY NATIVE MULTIPLIER PATH: LIVE_GAME_VERIFIED (7.3 test — native
FLOAT32 config read, four definition writes with stored_after_add MATCH,
Rome runtime PASS, identical save/reload recomputation).

Proven: numeric definition transforms (ADDITIVE/COMBAT/DISCOUNT/PROBABILITY
families). Unsupported structurally: slots/UI, booleans, bespoke
repeat/grant mechanics (stay SQL/generator or pending).

## Pipeline

```text
official runtime DB (local, private)
  → inventory (counts derived, never hard-coded)
  → RELEASE_1 scope (registry rows reachable from traits/policies/governments)
  → family review (auto-certify obvious numerics; refuse the rest loudly)
  → per-object manifests (traits/policies/governments.yml)
  → generator (deterministic, idempotent absolute-SET SQL only)
  → validation (8 checks incl. idempotent reapply)
```

Two multiplier paths were evaluated:

- **A. Generated preset SQL** (Off/×2/×3/×5/×10/×20/×50/×100): deterministic,
  audited, works today. Shippable fallback, retained regardless.
- **B. CE dynamic overrides** (arbitrary k, e.g. 7.3×): four-ID architecture
  proof is LIVE_GAME_VERIFIED (2026-10-07); the 686-entry certified production
slice
  (generated registry + native transforms + controller packaging) is
  STATICALLY VERIFIED and awaits the production-candidate live test —
  see `docs/PRODUCTION_RELEASE.md`. The init-phase Lua setter is abandoned.

Current recommendation: **HYBRID** — numeric DB modifiers stay generated;
CE path for arbitrary multipliers and special mechanics, validated per
release on the production candidate before any Workshop publish.

## Clean-room policy

Workshop X10 mods are behavioural references only. No SQL, text, or assets
are copied. All structure derives from the official runtime database; all
numbers are generated from `rules/` + `manifests/`.

## Component status

Release 1: traits, policies, governments (684-entry certified production
registry — 680 unique definitions; LIVE_VALIDATED at FLOAT32 k=7.3 with
610 writes + 74 refusals and 610/0/0 store-lookup verification, tag
`release1-684-live-validated`, evidence in `spike/validation-evidence/`).
Phase 2: pantheons (23 audited, +31 registry rows for 715 total;
LIVE_VALIDATED at k=7.3 with 638 writes + 77 refusals and 638/0/0
verification, tag `phase2-715-live-validated`; see `docs/PANTHEON_AUDIT.md`).
Phase 3: wonders (53 audited — 19 complete, 14 partial, 20 unsupported/none;
+97 registry rows for 813 total; see `docs/WONDER_AUDIT.md`). Later:
governors, city-states/suzerain; then optional belief/great-people/promotion
modules.
Unrelated global semantics stay NEEDS_REVIEW by design. See
`docs/PRODUCTION_RELEASE.md` for packaging, shared-ownership rule, and
UUIDs, and `docs/SEMANTIC_CERTIFICATION.md` for the certification gate.
