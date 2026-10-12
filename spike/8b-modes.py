import json
d = json.load(open('spike/8a-frontier/modes.json', encoding='utf-8'))
for m in d['modes']:
    if m['mode_id'] in ('GAMEMODE_MONOPOLIES', 'GAMEMODE_DRAMATICAGES', 'GAMEMODE_HEROES'):
        print('=' * 20, m['mode_id'])
        for f in m.get('overlay_files', []):
            rp = f.get('relpath', '')
            if rp.endswith('.sql') or rp.endswith('.xml'):
                print('  ', f.get('modinfo', '').split('::')[0] if '::' in f.get('modinfo','') else f.get('modinfo'), '|', rp)
