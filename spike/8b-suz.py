import yaml
s = yaml.safe_load(open('manifests/suzerain.yml', encoding='utf-8'))
rows = s['suzerain']
print('rows:', len(rows))
print('keys:', sorted(rows[0].keys()))
for r in rows[:3]:
    print(r)
