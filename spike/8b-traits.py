import yaml
t = yaml.safe_load(open('manifests/traits.yml', encoding='utf-8'))
rows = t['traits'] if isinstance(t, dict) else t
print('total rows:', len(rows))
print('keys:', sorted(rows[0].keys()))
vec = [r for r in rows if isinstance(r.get('official_value'), str) and ',' in r['official_value']]
print('comma rows:', len(vec))
for r in vec[:20]:
    print(r['object_id'], '|', r['modifier_id'], '|', r['argument_name'], '|', repr(r['official_value']), '|', r['semantic_family'], '|', r['transformation'], '|', r['status'])
