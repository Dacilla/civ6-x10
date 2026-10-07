# Native Hook Validation (X10 lifecycle test fork)

Fork: `../CivilizationVI_CommunityExtension-x10-spike`, branch
`x10-lifecycle-log`. Logging + definition-write prototype. Built DLL (local,
gitignored): 2,678,272 B, current write build SHA-256 `989617c7…fad2c`
(MSVC 14.51, SDK 26100,
Release x64).

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
relied upon. Post-`orig_Add`, the touched element is re-read for
`stored_after_add`.

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
| `AddModifierDefinition` | 0x943110 | Named entry, size 330. Full signature `void(this, ModifierDefinitionReference)`; the reference is passed as two 8-byte slots, consistent with the shared_ptr reference pattern used throughout this TU (`FAutoVariable<vector<shared_ptr<…>>>` entries at 0x92f6b0, 0x934790, …). Observed prologue `48 89 5c 24 08…`. Residual risk: struct width is inferred, not proven — stated openly; a wrong width would corrupt the forwarded call, which is why validation is fail-closed and the run is disposable. |
| `DynamicModifier` ctor A | 0x92a4f0 | Named entry, size 3367. Full signature: this + 5 const references (all pointers — exact under x64 ABI). Neighbors are same-family object code (`AttachModifierResult` ctor 0x929a80, `ModifierObject` ctor 0x92d1b0). Observed prologue `48 89 5c 24 08…`. |
| `DynamicModifier` ctor B | 0x92b220 | Named entry, size 2141, same signature as A. Both overload entries are hooked because either may construct the first instance. |

Dropped: `SimpleModifierDefinition` ctor (ordering evidence covered by Add;
its 9-parameter prototype is the most error-prone) and all `AttachModifier*`
(struct return ABI would need exact layout — documented as the reason the
safer constructor hook is preferred, per §9).

## Runtime validation (fail-closed)

Before installing anything, the fork checks: module filename,
PE timestamp, SizeOfImage, each RVA inside executable `.text` (parsed from
the loaded image, cross-checked by confirming CE's own working offsets land
in `.text`), and a masked prologue class per target
(`48 89 ?? 24 ??` / `40 5?` / `48 83 EC ??` — generic x64 shapes, never
copies of observed bytes). Any failure → `HOOK VALIDATION FAILED` +
`NO X10 LIFECYCLE HOOKS INSTALLED`, zero hooks. Success logs
`ALL_REQUIRED_SIGNATURES_VALID` plus per-hook PASS lines.

## Residual risks (open)

- Prologue classes confirm "function entry", not identity; identity rests on
  reference names/sizes/adjacency. A wrong-but-plausible address remains
  possible — hence disposable profile + instant rollback (disable the mod).
- `ModifierDefinitionReference` width is inferred (see table).
- Reference build 15038592 vs user Steam build 15296837 numbering is
  unresolved; PE timestamp/size pin the actual bytes instead.
