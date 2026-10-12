import io
p = 'tests/test_semantics.py'
t = io.open(p, encoding='utf-8').read()
old = '''                    # Phase 8B: Kupe first-city free Builder (countable
                    # one-time grant, Pyramids class).
                    ("BUILDER_PRESETTLEMENT", "Amount")):'''
assert t.count(old) == 1
new = '''                    # Phase 8B: Kupe first-city free Builder (countable
                    # one-time grant, Pyramids class).
                    ("BUILDER_PRESETTLEMENT", "Amount"),
                    # Phase 8B: one-time free Spy unit grants (Wu Zetian,
                    # Catherine second spy). Spy CAPACITY stays excluded.
                    ("WU_ZETIAN_FREE_SPY", "Amount"),
                    ("UNIQUE_LEADER_ADD_SPY_UNIT", "Amount")):'''
t = t.replace(old, new, 1)
old = '''        for mid in ("WU_ZETIAN_FREE_SPY",'''
assert t.count(old) == 1
new = '''        for mid in ('''
t = t.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('ok')
