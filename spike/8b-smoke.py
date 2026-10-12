import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import civ6x10.eight_b as e
from civ6x10.certification import certify_row, load_sem_floor, load_rules
from civ6x10.bridge import collect_registry_rows  # noqa
db = e.open_db()
rows, notes = e.build_envoy_manifest_rows(db)
sem = load_sem_floor(e.ROOT / "data" / "local" / "effect_semantics.csv")
rules = load_rules()
okc = 0
for r in rows:
    key = (r['modifier_type'], r['effect_type'], r['argument_name'])
    cert = certify_row(r, sem.get(key), rules)
    if cert['certified']:
        okc += 1
    else:
        print('NOT-CERT:', r['modifier_id'], r['argument_name'], cert['resolution'])
print('certified:', okc, '/', len(rows))
