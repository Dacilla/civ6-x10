import sqlite3
db = sqlite3.connect('file:data/local/DebugGameplay_official.sqlite?mode=ro', uri=True)
c = db.cursor()
print('== POLICY_GOD_KING ==')
print(c.execute("SELECT PolicyType,GovernmentSlotType FROM Policies WHERE PolicyType LIKE '%GOD_KING%'").fetchall())
cols = [r[1] for r in c.execute('PRAGMA table_info(PolicyModifiers)')]
print('PolicyModifiers cols:', cols)
for r in c.execute("SELECT * FROM PolicyModifiers WHERE PolicyType LIKE '%GOD_KING%'"):
    print(r)
    mid = r[1]
    print('   MOD:', c.execute('SELECT ModifierType,RunOnce,Permanent FROM Modifiers WHERE ModifierId=?', (mid,)).fetchone())
    for a in c.execute('SELECT Name,Value FROM ModifierArguments WHERE ModifierId=?', (mid,)):
        print('     ', a)
    mt = c.execute('SELECT ModifierType FROM Modifiers WHERE ModifierId=?', (mid,)).fetchone()
    if mt:
        for d in c.execute('SELECT CollectionType,EffectType FROM DynamicModifiers WHERE ModifierType=?', (mt[0],)):
            print('    DYN', d)
