import sqlite3
db = sqlite3.connect('file:data/local/DebugGameplay_official.sqlite?mode=ro', uri=True)
c = db.cursor()
print('== BELIEFS LIKE GOD/KING ==')
for r in c.execute("SELECT BeliefType,Name FROM Beliefs WHERE BeliefType LIKE '%GOD%' OR BeliefType LIKE '%KING%'"):
    print(r)
print('== ALL PANTHEON BELIEF MODIFIERS (sample) ==')
for r in c.execute("SELECT BeliefType,ModifierID FROM BeliefModifiers WHERE BeliefType IN (SELECT BeliefType FROM Beliefs WHERE BeliefClassType='BELIEF_CLASS_PANTHEON') LIMIT 8"):
    print(r)
print('== JEBEL MODIFIERS ==')
for mid in ('JEBELBARKAL_GRANT_TWO_IRON', 'JEBELBARKAL_GRANT_FOUR_IRON_PER_TURN'):
    print(c.execute('SELECT * FROM Modifiers WHERE ModifierId=?', (mid,)).fetchone())
    for d in c.execute('SELECT CollectionType,EffectType FROM DynamicModifiers WHERE ModifierType=(SELECT ModifierType FROM Modifiers WHERE ModifierId=?)', (mid,)):
        print('    DYN', d)
print('== GOD KING via Beliefs table ==')
for r in c.execute("SELECT BeliefType FROM Beliefs WHERE BeliefType LIKE '%KING%'"):
    print(r)
    for (mid,) in c.execute('SELECT ModifierID FROM BeliefModifiers WHERE BeliefType=?', (r[0],)):
        print('  ', mid, c.execute('SELECT ModifierType,RunOnce,Permanent FROM Modifiers WHERE ModifierId=?', (mid,)).fetchone())
        for a in c.execute('SELECT Name,Value FROM ModifierArguments WHERE ModifierId=?', (mid,)):
            print('     ', a)
