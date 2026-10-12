import csv, sqlite3
db = sqlite3.connect('file:data/local/DebugGameplay_official.sqlite?mode=ro', uri=True)
floor = {}
for r in csv.DictReader(open('data/local/effect_semantics.csv', encoding='utf-8')):
    floor[(r['modifier_type'], r['effect_type'], r['argument_name'])] = (r['semantic_family'], r['confidence'])

def carriers(link_table):
    c = db.cursor()
    mids = [x[0] for x in c.execute('SELECT DISTINCT ModifierId FROM ' + link_table).fetchall()]
    out = {}
    for mid in mids:
        m = c.execute('SELECT ModifierType FROM Modifiers WHERE ModifierId=?', (mid,)).fetchone()
        if not m:
            out.setdefault(('NO-MODIFIER-ROW', '?', '?'), []).append(mid)
            continue
        args = c.execute('SELECT Name,Value FROM ModifierArguments WHERE ModifierId=?', (mid,)).fetchall()
        effs = c.execute('SELECT EffectType FROM DynamicModifiers WHERE ModifierType=?', (m[0],)).fetchall()
        eff = effs[0][0] if effs else '?NO-DYN?'
        for (name, val) in args:
            out.setdefault((m[0], eff, name), []).append((mid, val))
    return out

for tbl in ('UnitPromotionModifiers', 'UnitAbilityModifiers', 'CommemorationModifiers'):
    print('=' * 30, tbl)
    cov = carriers(tbl)
    print('distinct (mt,eff,arg):', len(cov))
    for key in sorted(cov):
        fl = floor.get(key, ('NO-FLOOR', ''))
        vals = sorted(set(v for _, v in cov[key]))
        print('  ', key[0][:50], '|', key[1][:46], '|', key[2], '=>', fl, '| n=', len(cov[key]), '| vals=', vals[:8])
