import csv, sqlite3
db = sqlite3.connect('file:data/local/DebugGameplay_official.sqlite?mode=ro', uri=True)
c = db.cursor()
for trait in ('MINOR_CIV_TRADE_TRAIT', 'MINOR_CIV_SCIENTIFIC_TRAIT'):
    print('---', trait)
    for (mid,) in c.execute('SELECT ModifierId FROM TraitModifiers WHERE TraitType=?', (trait,)).fetchall():
        m = c.execute('SELECT ModifierType,SubjectRequirementSetId,OwnerRequirementSetId,RunOnce,Permanent FROM Modifiers WHERE ModifierId=?', (mid,)).fetchone()
        args = c.execute('SELECT Name,Value FROM ModifierArguments WHERE ModifierId=?', (mid,)).fetchall()
        print('  ', mid, '|', m)
        for a in args:
            print('      ', a)
