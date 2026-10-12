import sqlite3
db = sqlite3.connect('file:data/local/DebugGameplay_official.sqlite?mode=ro', uri=True)
c = db.cursor()
print('== GOD KING ==')
for (btype, mid) in c.execute("SELECT BeliefType,ModifierID FROM BeliefModifiers WHERE BeliefType LIKE '%GOD_KING%'"):
    mtype = c.execute('SELECT ModifierType FROM Modifiers WHERE ModifierId=?', (mid,)).fetchone()
    print(btype, mid, mtype)
    for a in c.execute('SELECT Name,Value FROM ModifierArguments WHERE ModifierId=?', (mid,)):
        print('   ', a[0], '=', a[1])
    if mtype:
        for d in c.execute('SELECT CollectionType,EffectType FROM DynamicModifiers WHERE ModifierType=?', (mtype[0],)):
            print('    DYN', d[0], d[1])
print('== POLICY SLOTTYPE COUNTS ==')
for r in c.execute('SELECT GovernmentSlotType,COUNT(*) FROM Policies GROUP BY 1'):
    print(r)
print('== JEBEL ROW ==')
for r in c.execute("SELECT ModifierId,Name,Value FROM ModifierArguments WHERE ModifierId LIKE 'JEBEL%'"):
    print(r)
print('== PETRA ARGS ==')
for r in c.execute("SELECT Name,Value FROM ModifierArguments WHERE ModifierId='PETRA_YIELD_MODIFIER'"):
    print(r)
print('== WONDER SLOT MODIFIERS ==')
for r in c.execute("SELECT BuildingType,ModifierId FROM BuildingModifiers WHERE ModifierId LIKE '%GOVERNMENT_SLOT%'"):
    print(r)
