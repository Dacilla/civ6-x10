import io
p = 'civ6x10/modules/__init__.py'
t = io.open(p, encoding='utf-8').read()
old = '''    if transform in ("unchanged",):
        return (official, "ok")
    if transform in ("refused_no_multiplier", "decision_required"):
        return ("", "refused" if "refused" in transform else "undecided")
    try:
        v = float(official)
    except (TypeError, ValueError):
        return ("", "undecided")
    try:'''
assert t.count(old) == 1
new = '''    if transform in ("unchanged",):
        return (official, "ok")
    if transform in ("refused_no_multiplier", "decision_required"):
        return ("", "refused" if "refused" in transform else "undecided")
    if transform == "vector_multiply":
        from ..transforms import vector_multiply
        try:
            return (vector_multiply(official, k), "ok")
        except ValueError:
            return ("", "undecided")
    if transform == "repeat_count":
        from ..transforms import repeat_copies
        n = repeat_copies(k)
        if n is None:
            return ("", "undecided")
        return (str(n + 1), "ok")
    try:
        v = float(official)
    except (TypeError, ValueError):
        return ("", "undecided")
    try:'''
t = t.replace(old, new, 1)

# Remove the now-duplicated vector/repeat branches in the numeric section.
old2 = '''        if transform == "vector_multiply":
            from ..transforms import vector_multiply
            return (vector_multiply(official, k), "ok")
        if transform == "bridge_delta":
            from ..transforms import bridge_delta
            return (_fmt(bridge_delta(v, k)), "ok")
        if transform == "repeat_count":
            from ..transforms import repeat_copies
            n = repeat_copies(k)
            if n is None:
                return ("", "undecided")
            return (str(n + 1), "ok")
'''
assert t.count(old2) == 1
new2 = '''        if transform == "bridge_delta":
            from ..transforms import bridge_delta
            return (_fmt(bridge_delta(v, k)), "ok")
'''
t = t.replace(old2, new2, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('ok')
