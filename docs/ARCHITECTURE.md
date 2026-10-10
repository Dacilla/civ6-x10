# Architecture

One configurable Workshop item, independently tested components.

ARBITRARY NATIVE MULTIPLIER PATH: LIVE_VALIDATED. The Community Extension
(GameCore replacement) reads FLOAT32 configuration at init, walks the
generated registry and writes each certified definition's argument through a
native store lookup, then re-verifies every write
(`stored_after_add ... MATCH via=store-lookup`). Save/reload recomputes
identically, and the ownership bitmask proves module isolation (Governors OFF
leaves the non-Governor written set byte-identical to Governors ON).

Current production state: **971 registry entries / 967 unique definitions** -
traits/policies/governments (684), pantheons (31), wonders (97), governors (54),
suzerain (47),
with owner bits `1=traits 2=policies 4=governments 8=pantheons 16=wonders
32=governors 64=suzerain`. Suzerain is CERTIFIED (not yet live-validated);
bit 128 is the next free bit.

Proven numeric definition transforms: ADDITIVE, COMBAT (canonical `b_k`),
DISCOUNT (percent discount / flat cost reduction), PROBABILITY, plus the
engine-integral gate for effects the engine applies integrally. Unsupported
structurally: slots/UI, booleans, selectors, object grants, bespoke
repeat/grant mechanics (they stay SQL/generator or pending).

## Pipeline

```text
official runtime DB (local, private, read-only)
  -> audit per component (governors / wonders / pantheons / suzerain)
       discovery -> recursive modifier graph -> semantic disposition
  -> inventory (counts derived, never hard-coded)
  -> RELEASE scope (registry rows reachable from the component roots)
  -> family review / certification gate (auto-certify proven numerics;
     refuse the rest loudly)
  -> per-object manifests (traits/policies/governments/pantheons/wonders/
     governors/suzerain.yml)
  -> generator (deterministic, idempotent absolute-SET SQL only)
  -> direct-table bridge for columns no modifier addresses (guarded)
  -> validation (8 checks incl. idempotent reapply)
  -> CE registry (.inc) + controller packaging
```

Two multiplier paths are combined:

- **Generated preset SQL** (Off/*2/*3/*5/*10/*20/*50/*100): deterministic,
  audited, works today. Shippable fallback, retained regardless.
- **CE dynamic overrides** (arbitrary k, e.g. 7.3): the engine writes each
  certified argument at runtime; live-validated for traits, pantheons,
  wonders and governors; suzerain is certified and statically verified,
  awaiting its targeted live validation.

Current architecture: **HYBRID** - numeric DB modifiers stay generated and
certified; the CE path applies the arbitrary multiplier and module ownership,
validated per release on the production candidate before any Workshop publish.

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
Phase 3: wonders (53 audited - 19 complete, 14 partial, 20 unsupported/none;
+97 registry rows plus the guarded direct-table bridge for 813 total;
LIVE_VALIDATED at k=7.3, tag `phase3-813-live-validated`; see
`docs/WONDER_AUDIT.md`).
Phase 4: governors (54 audited candidate rows for 924 total, owner bit 32;
LIVE_VALIDATED at k=7.3 in both module states, tag
`phase4b-924-live-validated`; see `docs/GOVERNOR_AUDIT.md`).
Phase 5A: suzerain / city-states - closed-world semantic audit only
(`docs/SUZERAIN_AUDIT.md`, `civ6x10/rules/suzerain_audit.yml`); proposed
owner bit 64, no production rows, no CE/native/controller change. Phase 5B
is the reviewed production slice.
Phase 5B: suzerain production integration (+47 conservative rows for 971
total, owner bit 64, `X10_MODULE_SUZERAIN` default ON) - CERTIFIED, awaiting
targeted live validation (Phase 5C).
Then optional belief/great-people/promotion modules.
Unrelated global semantics stay NEEDS_REVIEW by design. See
`docs/PRODUCTION_RELEASE.md` for packaging, shared-ownership rule, and
UUIDs, and `docs/SEMANTIC_CERTIFICATION.md` for the certification gate.
