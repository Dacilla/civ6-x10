import io
p = 'civ6x10/bridge.py'
t = io.open(p, encoding='utf-8').read()

old_doc = """  authoritative direct value V
    -> generated guarded SQL zeroes the direct cell AND creates one helper
       modifier carrying Amount=V attached to the wonder
    -> the helper flows through the existing native registry
       (official-mismatch guard, FLOAT32 k, count rules, store lookup)

Invariant (no new native arithmetic required):
  module OFF or k=1:  0 + V = vanilla (helper passes through untransformed)
  module ON at k:     0 + kV = semantic multiplier.

Every statement is guarded on the audited official value: drift (or another
mod) means zeroing never fires AND the helper is never created, leaving
vanilla untouched while the dormant registry row can never match at runtime."""
assert t.count(old_doc) == 1, t.count(old_doc)
new_doc = """  authoritative direct value V (PRESERVED: vanilla UI keeps reading it)
    -> generated guarded SQL creates one helper modifier carrying
       Amount=0 (inert) attached to the wonder
    -> the native DELTA kind contributes V*(k-1) through the existing
       registry machinery (zero-match guard, FLOAT32 k, count rules)

Invariant (Phase 8B non-destructive delta):
  module OFF or k=1:  V + 0 = vanilla (helper inert)
  module ON at k:     V + (k-1)V = semantic multiplier.

Every statement is guarded on the audited official value: drift (or another
mod) means the helper is never created, leaving vanilla untouched while
the dormant registry row can never match at runtime."""
t = t.replace(old_doc, new_doc, 1)

old_zero = """        chunks.extend(_helper_inserts(spec, hid, r, keys, base))
        vcol = r["value_column"]
        chunks.append(
            "UPDATE %s SET %s = 0\\nWHERE %s\\n"
            "  AND EXISTS (SELECT 1 FROM Modifiers WHERE ModifierId = '%s');"
            % (r["source_table"], vcol, base, hid))
        chunks.append(_diag_insert(hid, r, keys))"""
assert t.count(old_zero) == 1, t.count(old_zero)
new_zero = """        chunks.extend(_helper_inserts(spec, hid, r, keys, base))
        chunks.append(_diag_insert(hid, r, keys))"""
t = t.replace(old_zero, new_zero, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('ok')
