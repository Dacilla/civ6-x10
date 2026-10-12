import sqlite3
db = sqlite3.connect('file:data/local/DebugGameplay_official.sqlite?mode=ro', uri=True)
c = db.cursor()
for mid in ('WU_ZETIAN_FREE_SPY', 'UNIQUE_LEADER_ADD_SPY_CAPACITY', 'UNIQUE_LEADER_ADD_SPY_UNIT'):
    print('==', mid)
    print('  MOD:', c.execute('SELECT ModifierType,RunOnce,Permanent FROM Modifiers WHERE ModifierId=?', (mid,)).fetchone())
    print('  ARGS:', c.execute('SELECT Name,Value FROM ModifierArguments WHERE ModifierId=?', (mid,)).fetchall())
    mt = c.execute('SELECT ModifierType FROM Modifiers WHERE ModifierId=?', (mid,)).fetchone()
    if mt:
        print('  DYN:', c.execute('SELECT CollectionType,EffectType FROM DynamicModifiers WHERE ModifierType=?', (mt[0],)).fetchall())
