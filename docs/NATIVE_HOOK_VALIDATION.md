# Native Hook Validation (X10 lifecycle test fork)

Fork: `../CivilizationVI_CommunityExtension-x10-spike`, branch
`x10-lifecycle-log`. Logging + production definition-write engine. Built DLL
(local, gitignored): 2,741,760 B, current production-candidate SHA-256
`69b80793…afddd1` (MSVC 14.51, SDK 26100, Release x64). Superseded hashes
(`989617c7…`, `f0daac3d…`, `1594d354…`, `2fe9c778…`, `269a1ed6…`, `bb4f1520…`)
must NOT be used for any new run — the production-candidate package is
hash-pinned in `spike/EXPECTED_DLL_SHA256.txt`.

Assumed GameCore: file `GameCore_XP2_FinalRelease.dll`, PE timestamp
`0x667c6f5b`, `SizeOfImage` `0xc60000`, SHA-256 `324c51e9…` (user install).
Reference RVAs are the `cur` column (installed build 15038592) of
`civ6-gamecore-reference/reference/data/function_index.json`.

## TypedVariant id=4 (proven FLOAT32, 2026-10-07)

Live: variant id=4, Lua value 7.3000001907349. Proof chain:
1. Fractional Lua numbers are committed as float32 (`cvtsd2ss` + virtual
   store at TableToTypedVariantMap 0x9af376); integral ones take the int
   path. The setup value 7.3 is fractional, so the stored form is float32.
2. The widened double matches float32(7.3) exactly (byte-verified:
   `9a99e940`).
3. Reader decodes float@+8, widens, checks finite + 0–100. The INT32 branch
   explicitly excludes id 4 (the engine mask's inclusion of 4 only covers
   the engine's own int-keyed callers). No float64 branch: no evidence any
   setup value uses it. Unknown types fail closed logging exact id/flags/
   payload; unknown types never reach a string reader.

## ModifierDefinitionReference ABI (resolved, 2026-10-07)

Full disassembly of `AddModifierDefinition` (0x943110) shows the reference
arriving as a **single 8-byte pointer in RDX** to a 16-byte shared_ptr-like
`{_Ptr, _Rep}` object: the callee dereferences `[RDX+0]` then virtual `+0x10`,
and ref-counts with `lock xadd` on the second qword (uses@+8/weaks@+0xc —
classic `shared_ptr` control block). Raw definition = `*(void**)d0`, with
null + vtable-pointer validation (`ResolveDefinitionReference`, fail-closed).
Mutation happens BEFORE `orig_Add`: the definition is fully constructed by
the caller and not yet system-visible, so no shared-reference aliasing is
relied upon.

## ModifierSystem::GetModifierDefinition ABI (resolved, 2026-10-08)

Reference: `GameEffects::ModifierSystem::GetModifierDefinition`
(installed-build RVA **0x951d90**, size 139, `effects`, `unique`;
signature `ModifierDefinitionReference(... this, const ModifierId& id)`).
Recursive-descent disassembly of the installed DLL establishes the physical
ABI (no linear-sweep desync: re-verified instruction by instruction):

- **Call shape:** `void __thiscall Get(system /*RCX=this*/, out16 /*RDX*/,
  idKey /*R8*/)` — the 16-byte shared_ptr-like result is written to caller
  storage (no hidden-retptr confusion: RCX demonstrably addresses the
  `ModifierSystem`, since the store map is read at `RCX+0x70`/`+0x78`).
- **Key = the ID string itself** (MSVC `std::string` layout): the callee's
  find helper (0x1811f0) reads key size from `[key+0x10]`, chooses SSO vs
  heap by `[key+0x18] < 0x10`, and FNV-1a-64 hashes the key bytes
  (`0xcbf29ce484222325` / `0x100000001b3`), then walks string-keyed buckets
  with full string-equality compare. The caller builds the key over its own
  stable storage in heap form (cap ≥ 0x10); the engine only reads it during
  the call. No vtable key call, no string hash needed.
- **Store node layout** (cross-validated in Add's insert path and Get's
  read path): key string @ node+0x10, definition `_Ptr` @ node+0x30,
  `_Rep` @ node+0x38 — the same store (map head at system+0x78, consistent
  in both functions).
- **Result discipline:** hit → zeroed-out storage filled with a shared_ptr
  copy (`lock inc` on `_Rep+8`, i.e. AddRef — the witness releases its copy
  with the mirrored decref; the store's own ref makes destroy unreachable,
  and a last-ref surprise logs + leaks rather than running destroy paths);
  miss → out zeroed after an internal call (returns normally; SEH-guarded
  anyway).
- **Validation:** `getDefRva` lives in the compatibility profile and is
  checked in-`.text` + prologue-class at Install like a hook target, but is
  **called, never hooked**. Validation failure degrades the witness loudly
  (`STORE LOOKUP UNPROVEN`, every touched entry counts unreadable) without
  touching the proven writer path.
- **Self-validating lookup:** the witness re-reads the returned definition's
  own ID string and requires equality with the expected ID before trusting
  any value. A wrong-definition return (which would refute the key
  derivation) logs `stored_id_mismatch` + MISMATCH — the key hypothesis is
  therefore proven or refuted live across every sample, not assumed.

## Post-Add witness tiers (2026-10-08 fix)

The old witness re-read the retained pre-Add element pointer — invalid as
stored-system proof (see Toqui analysis below). `Touched` now carries logical
identity only (ID + argument + expected, copied; no pointers), and
`VerifyStoredAfterAdd(system, ...)` resolves each entry through the
registered store:

- textual definition retained → `MATCH` / `MISMATCH` (`post_add_match` /
  `post_add_mismatch` incremented);
- definition found + ID cross-checked but value blank/absent →
  `typed-or-consumed` (`post_add_unreadable`, never MATCH);
- lookup miss / fault / degraded path → `post_add_unreadable`, never MATCH.

Exit summary is fully counter-derived (`writes / transform_refused /
official_mismatch / post_add_match / post_add_mismatch / post_add_unreadable
/ skipped_other`) and cannot report zero mismatches after a MISMATCH line.
Expected count refusals live in `transform_refused`, never in mismatch
statistics.

## Toqui loyalty analysis (2026-10-08)

Live runs (initial load AND reload, identically): `TOQUI_DOMESTIC_LOYALTY`
and `TOQUI_FOREIGN_LOYALTY` (`MODIFIER_PLAYER_GOVERNORS_ADJUST_GOVERNOR_
IDENTITY_PRESSURE` / `EFFECT_ADJUST_GOVERNOR_IDENTITY_PRESSURE`, Amount 4 →
29.2) log `before=4 after=29.2 stored_after_add= MISMATCH` while all other
610 writes MATCH. The blank (not `<unreadable>`) means the string object was
legitimately emptied in place (size 0, clean read) — a deliberate engine
string op during `orig_Add` (move/clear of the Amount string), not dangling
memory (which reads as garbage → `<unreadable>`). Unique to the two
definitions sharing that effect plus `OncePerCity` / `Domestic|ForeignCities`
flag args: effect-specific post-Add consumption of the raw Amount string.
Which exact op (move-out, clear, vector realloc with zeroing) is unproven
statically — and the distinction decides nothing, because the pre-Add
pointer is retired regardless. The store-lookup witness determines live
whether 29.2 survives in the registered definition (textual MATCH) or the
effect consumes raw strings (typed-or-consumed → per-effect typed-value work
or continued exclusion). Until then both entries are temporarily excluded
from the certified registry (684 entries, 610 static writes at k=7.3).

## String reader (SSO + heap reads, SSO-only writes)

Proof IDs (37/30/21 chars) exceed MSVC SSO capacity, so reads use a bounded
reader: size@+0x10, capacity@+0x18; inline bytes iff capacity < 0x10, else
heap pointer (capacity ≥ size required). Fail-closed unless size ≤ 256,
printable ASCII, NUL-terminated. Heap WRITES remain refused; proof values
(≤5 chars) stay SSO-inline.

## Retained hooks (4)

| Hook | RVA | Reference identity evidence |
|---|---|---|
| `PopulateModifierDefinitions` | 0x96f6c0 | Named entry, size 2180; ends at 0x96FF40, immediately before `PopulateRequirementDefinitions` 0x96FF50 (exact adjacency, same `DatabaseUtility` family). Full signature `void(pDB, ModifierSystem&)` — 2 pointers, exact detour. Observed prologue `48 89 54 24 10…` (mov-spill, consistent with ≥2 args). |
| `AddModifierDefinition` | profile `addRva` | Named entry, size 330. Full signature `void(this, ModifierDefinitionReference)`; the reference arrives as a single pointer (RDX) to a 16-byte shared_ptr-like `{_Ptr,_Rep}` (see ABI section above). The hook forwards both reference slots to `orig_Add` for call fidelity and resolves the raw definition via `*(void**)d0` (fail-closed). Observed prologue `48 89 5c 24 08…`. Residual risk: reference width is inferred, not proven — stated openly; validation is fail-closed and every run is disposable. |
| `DynamicModifier` ctor A | 0x92a4f0 | Named entry, size 3367. Full signature: this + 5 const references (all pointers — exact under x64 ABI). Neighbors are same-family object code (`AttachModifierResult` ctor 0x929a80, `ModifierObject` ctor 0x92d1b0). Observed prologue `48 89 5c 24 08…`. |
| `DynamicModifier` ctor B | 0x92b220 | Named entry, size 2141, same signature as A. Both overload entries are hooked because either may construct the first instance. |

Dropped: `SimpleModifierDefinition` ctor (ordering evidence covered by Add;
its 9-parameter prototype is the most error-prone) and all `AttachModifier*`
(struct return ABI would need exact layout — documented as the reason the
safer constructor hook is preferred, per §9).

## Runtime validation (fail-closed)

Before installing anything, the fork selects a `GameCoreCompatibilityProfile`
(`X10Compat.h`: PE timestamp, image size, hook/config RVAs, manager offsets,
vtable slot, variant + definition + SSO layout) by loaded-module identity or
installs zero hooks. Each profile target is then checked inside executable
`.text` (parsed from the loaded image) with a masked prologue class per
target (`48 89 ?? 24 ??` / `40 5?` / `48 83 EC ??` — generic x64 shapes,
never copies of observed bytes). Any failure → `HOOK VALIDATION FAILED` +
`NO X10 LIFECYCLE HOOKS INSTALLED`, zero hooks. Success logs
`ALL_REQUIRED_SIGNATURES_VALID` plus per-hook PASS lines. Hook installation
is transactional and X10-only (create-all, then enable-all, unwinding only
X10 hooks on failure); unrelated CE hooks are never disabled or removed.

## Residual risks (open)

- Prologue classes confirm "function entry", not identity; identity rests on
  reference names/sizes/adjacency. A wrong-but-plausible address remains
  possible — hence disposable profile + instant rollback (disable the mod).
- `ModifierDefinitionReference` width is inferred (see table).
- Reference build 15038592 vs user Steam build 15296837 numbering is
  unresolved; PE timestamp/size pin the actual bytes instead.
