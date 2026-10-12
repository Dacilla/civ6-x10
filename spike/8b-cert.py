import io
p = 'civ6x10/certification.py'
t = io.open(p, encoding='utf-8').read()
old = '''    # Explicit 8B pipeline transformations (checked after excluded_effects;'''
assert t.count(old) == 1
new = '''    # Curated per-effect evidence for heuristic-only floors (Phase 8B):
    # an AUTO_PATTERN / NEEDS_REVIEW floor row is never proof by itself,
    # but a certified_effect_args entry naming this exact tuple is positive
    # human evidence (same trust class as combat_effects). Proven floors
    # never reach this branch, so pre-8B certifications are untouched.
    if not proven:
        curated = _effect_arg_override(mt, et, arg, rules)
        if curated is not None:
            return {**base, "certified": True, "kind": curated["kind"],
                    "count_like": curated["count_like"],
                    "source": curated["source"],
                    "resolution": "certified"}

    # Explicit 8B pipeline transformations (checked after excluded_effects;'''
t = t.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('ok')
