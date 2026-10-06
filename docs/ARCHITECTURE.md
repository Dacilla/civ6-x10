# Architecture

One configurable Workshop item, independently tested components.

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

Two multiplier paths are being evaluated:

- **A. Generated preset SQL** (Off/×2/×3/×5/×10/×20/×50/×100): deterministic,
  audited, works today. Shippable fallback.
- **B. CE dynamic overrides** (arbitrary k, e.g. 7.3×): needs a small generic
  CE extension (`ModifierDefinitions.Get/SetArgument`, init-phase only).
  Probe + design in `docs/DYNAMIC_MULTIPLIER_SPIKE.md`.

Current recommendation: **HYBRID** pending the native write test —
numeric DB modifiers stay generated; CE path for arbitrary multipliers and
special mechanics once validated.

## Clean-room policy

Workshop X10 mods are behavioural references only. No SQL, text, or assets
are copied. All structure derives from the official runtime database; all
numbers are generated from `rules/` + `manifests/`.

## Component status

Release 1: traits, policies, governments (RELEASE_1 scope: 513 registry rows,
407 family-certified, 106 genuinely ambiguous). Later: pantheons, governors,
wonders, city-states/suzerain; then optional belief/great-people/promotion
modules. Unrelated global semantics stay NEEDS_REVIEW by design.
