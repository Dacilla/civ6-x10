import sqlite3
db = sqlite3.connect('file:data/local/DebugGameplay_official.sqlite?mode=ro', uri=True)
c = db.cursor()
for t in ('BeliefModifiers', 'Modifiers', 'Policies'):
    cols = [r[1] for r in c.execute('PRAGMA table_info(' + t + ')')]
    print(t, cols)
